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
# git reset --hard
_add(r"\bgit\b\s+reset\b.*--hard\b", DESTRUCTIVE, "git reset --hard")
# git push --force / -f
_add(
    r"\bgit\b\s+push\b.*--force\b|\bgit\b\s+push\b.*\s+-f\b",
    DESTRUCTIVE,
    "git push --force",
)
# git clean -fdx / -fd -x / --force
_add(r"\bgit\b\s+clean\b.*(-fdx|-fd.*-x|--force)", DESTRUCTIVE, "git clean -fdx")
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
# git reset without --hard (rewrites history but safer)
_add(r"\bgit\b\s+reset\b", CAUTION, "git reset (rewrites history)")
# git clean (untracked file deletion) — destructive only with -fdx
_add(r"\bgit\b\s+clean\b", CAUTION, "git clean (deletes untracked files)")
# git checkout / switch branches
_add(r"\bgit\b\s+(checkout|switch)\b", CAUTION, "git checkout/switch")
# chmod (permission changes, not -R 777)
_add(r"\bchmod\b", CAUTION, "chmod permission change")
# mv (can overwrite files)
_add(r"\bmv\b", CAUTION, "mv move/overwrite")
# shell redirect overwrite
_add(r">\s*\S", CAUTION, "shell redirect overwrite")
# dd (general)
_add(r"\bdd\b", CAUTION, "dd low-level copy")


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
    return SafetyResult(command=command, level=level, matched_rules=matched)
