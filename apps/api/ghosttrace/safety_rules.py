"""Deterministic safety engine for shell commands.

This module is a rule-based (regex/AST, NOT LLM-based) classifier that
inspects a shell command the user is about to run and classifies it as:

    SAFE      — ordinary read-only or benign operation
    CAUTION   — potentially disruptive but not outright destructive
    DESTRUCTIVE — can delete data, rewrite history, or damage the system

Design principles:
* Zero LLM dependency — this module must work with Ollama stopped. The
  safety verdict is computed purely from pattern matching; Gemma is only
  ever used later (Part B) to *explain* the verdict, never to second-guess
  it.
* Regex with word boundaries and anchored alternation, not naive
  substring matching, so that e.g. ``git reset --soft`` is not confused
  with ``git reset --hard`` and ``rmdir emptydir`` is not confused with
  ``rm -rf /``.
* Caution is cheap: false positives are acceptable, false negatives
  (missing a genuinely destructive command) are not. Patterns therefore
  err on the side of matching.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from typing import Final

# --- Classification levels ------------------------------------------------

SAFE: Final[str] = "SAFE"
CAUTION: Final[str] = "CAUTION"
DESTRUCTIVE: Final[str] = "DESTRUCTIVE"


@dataclass
class SafetyResult:
    """Outcome of classifying a single shell command."""

    command: str
    level: str
    matched_rules: list[str] = field(default_factory=list)

    @property
    def is_destructive(self) -> bool:
        return self.level == DESTRUCTIVE

    @property
    def is_caution(self) -> bool:
        return self.level == CAUTION

    @property
    def is_safe(self) -> bool:
        return self.level == SAFE


# Each rule: (compiled regex, level, human-readable description).
# Order matters: DESTRUCTIVE rules are checked first, then CAUTION, then
# anything left unmatched is SAFE. Within a level, more specific patterns
# should come before more general ones.
_RULES: list[tuple[re.Pattern[str], str, str]] = []


def _add(pattern: str, level: str, description: str, flags: int = re.IGNORECASE) -> None:
    _RULES.append((re.compile(pattern, flags), level, description))


# --- DESTRUCTIVE rules (checked first) ------------------------------------

# rm with recursive + force (any order/form): rm -rf, rm -fr, rm -r -f, etc.
_add(
    r"\brm\b(?:\s+-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*"
    r"|\s+-[a-zA-Z]*f[a-zA-Z]*r[a-zA-Z]*"
    r"|\s+--recursive|\s+--force"
    r"|\s+-r\b.*\s+-f\b|\s+-f\b.*\s+-r\b)",
    DESTRUCTIVE,
    "rm with recursive + force (rm -rf)",
)
# rm -rf with explicit path that looks like root or home
_add(
    r"\brm\b\s+-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s+(/|~|\$HOME|\.\.|\\\\|\.)",
    DESTRUCTIVE,
    "rm -rf targeting root/home/parent",
)
# Windows rmdir /s /q
_add(r"\brd\b\s+/[sSqQ]", DESTRUCTIVE, "Windows rmdir /s (recursive delete)")
# SQL DROP TABLE / DATABASE / SCHEMA / VIEW / INDEX / COLLECTION
_add(
    r"\bDROP\s+(TABLE|DATABASE|SCHEMA|VIEW|INDEX|COLLECTION|CONTAINER)\b",
    DESTRUCTIVE,
    "SQL DROP statement",
)
# SQL TRUNCATE
_add(r"\bTRUNCATE\s+(TABLE\s+)?\w", DESTRUCTIVE, "SQL TRUNCATE statement")
# chmod -R 777 (any order)
_add(
    r"\bchmod\b.*(-R.*777|777.*-R|--recursive.*777|777.*--recursive)",
    DESTRUCTIVE,
    "chmod -R 777",
)
# curl/wget piped into a shell interpreter from a remote URL
_add(
    r"\b(curl|wget)\b.*\|\s*(sh|bash|zsh|dash|sh\b)", DESTRUCTIVE, "remote script piped to shell"
)
# dd writing to a block device (of=/dev/... or of=\\.\... on Windows)
_add(
    r"\bdd\b.*\bof\s*=\s*(/dev/|\\\\\\.\\|\\\\\\?\\)",
    DESTRUCTIVE,
    "dd block-device write",
)

# --- CAUTION rules (checked after destructive) ----------------------------

# plain rm (file deletion, but not recursive+force)
_add(r"\brm\b", CAUTION, "rm file deletion")
# chmod (permission changes, not -R 777)
_add(r"\bchmod\b", CAUTION, "chmod permission change")
# mv (can overwrite files)
_add(r"\bmv\b", CAUTION, "mv move/overwrite")
# shell redirect overwrite
_add(r">\s*\S", CAUTION, "shell redirect overwrite")
# dd (general)
_add(r"\bdd\b", CAUTION, "dd low-level copy")

_GIT_SUBCOMMANDS: Final[frozenset[str]] = frozenset(
    {"reset", "push", "clean", "checkout", "switch"}
)
_GIT_GLOBAL_OPTIONS_WITH_VALUES: Final[frozenset[str]] = frozenset(
    {
        "-c",
        "-C",
        "--config-env",
        "--exec-path",
        "--git-dir",
        "--namespace",
        "--super-prefix",
        "--work-tree",
    }
)
_GIT_RULE_DESCRIPTIONS: Final[dict[str, str]] = {
    "reset-hard": "git reset --hard",
    "reset": "git reset (rewrites history)",
    "push-force": "git push --force",
    "clean-destructive": "git clean -fdx",
    "clean": "git clean (deletes untracked files)",
    "checkout": "git checkout/switch",
}


def _git_commands(command: str) -> list[tuple[str, list[str]]]:
    """Find sensitive Git subcommands despite global flags before the verb.

    Git normally expects global options such as ``-C`` before the subcommand.
    Treating all leading dash-prefixed tokens as options also catches malformed
    or alias-like inputs such as ``git --reset`` conservatively.
    """
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|()")
    lexer.whitespace_split = True
    lexer.commenters = ""
    try:
        tokens = list(lexer)
    except ValueError:
        tokens = command.split()

    found: list[tuple[str, list[str]]] = []
    separators = {";", "&", "&&", "|", "||", "(", ")"}
    index = 0
    while index < len(tokens):
        if tokens[index].casefold() != "git":
            index += 1
            continue

        end = index + 1
        while end < len(tokens) and tokens[end] not in separators:
            end += 1
        segment = tokens[index + 1 : end]
        verb_index: int | None = None
        for candidate_index, token in enumerate(segment):
            if candidate_index > 0 and segment[candidate_index - 1].casefold() in _GIT_GLOBAL_OPTIONS_WITH_VALUES:
                continue

            normalized = token.lstrip("-").casefold()
            if normalized in _GIT_SUBCOMMANDS:
                verb_index = candidate_index
                break

            option = token.casefold()
            if option in _GIT_GLOBAL_OPTIONS_WITH_VALUES:
                # The next token is this option's argument, not the subcommand.
                continue

            # A positional token other than a sensitive verb starts arguments;
            # do not mistake a later commit message/ref/path for a subcommand.
            if not token.startswith("-"):
                break

        if verb_index is not None:
            options_before_verb = segment[:verb_index]
            options_after_verb = segment[verb_index + 1 :]
            found.append(
                (
                    segment[verb_index].lstrip("-").casefold(),
                    options_before_verb + options_after_verb,
                )
            )
        index = end + 1
    return found


def classify(command: str) -> SafetyResult:
    """Classify a shell command into SAFE / CAUTION / DESTRUCTIVE.

    The first matching rule (in rule order) wins. DESTRUCTIVE rules are
    ordered before CAUTION rules so a command that matches both levels is
    reported as DESTRUCTIVE.
    """
    matched: list[str] = []
    level = SAFE
    for pattern, rule_level, description in _RULES:
        if pattern.search(command):
            matched.append(description)
            # Escalate: destructive > caution > safe.
            if rule_level == DESTRUCTIVE:
                level = DESTRUCTIVE
            elif rule_level == CAUTION and level == SAFE:
                level = CAUTION

    for subcommand, options in _git_commands(command):
        normalized_options = [option.casefold() for option in options]
        if subcommand == "reset":
            if "--hard" in normalized_options:
                matched.append(_GIT_RULE_DESCRIPTIONS["reset-hard"])
                level = DESTRUCTIVE
            else:
                matched.append(_GIT_RULE_DESCRIPTIONS["reset"])
                if level == SAFE:
                    level = CAUTION
        elif subcommand == "push":
            forced = any(
                option in {"-f", "--force"}
                or option.startswith("--force-")
                for option in normalized_options
            )
            if forced:
                matched.append(_GIT_RULE_DESCRIPTIONS["push-force"])
                level = DESTRUCTIVE
        elif subcommand == "clean":
            destructive_flags = False
            short_flags = set()
            for option in normalized_options:
                if option == "--force":
                    destructive_flags = True
                elif option.startswith("-") and not option.startswith("--"):
                    short_flags.update(option[1:])
            if {"f", "d", "x"}.issubset(short_flags):
                destructive_flags = True
            if destructive_flags:
                matched.append(_GIT_RULE_DESCRIPTIONS["clean-destructive"])
                level = DESTRUCTIVE
            else:
                matched.append(_GIT_RULE_DESCRIPTIONS["clean"])
                if level == SAFE:
                    level = CAUTION
        elif subcommand in {"checkout", "switch"}:
            matched.append(_GIT_RULE_DESCRIPTIONS["checkout"])
            if level == SAFE:
                level = CAUTION
    return SafetyResult(command=command, level=level, matched_rules=matched)
