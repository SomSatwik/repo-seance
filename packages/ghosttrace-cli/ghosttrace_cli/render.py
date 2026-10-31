"""ANSI-styled terminal rendering for GhostTrace.

Ports the web visual identity to raw ANSI escape codes:

  * Blood-red (true-color #B5121B = 181;18;27) for DESTRUCTIVE warnings
  * Amber for CAUTION
  * Dim/understated for SAFE
  * Original ASCII logo as a startup banner with a fast line-by-line reveal
"""

from __future__ import annotations

import random
import shutil
import sys
import textwrap
import time
from itertools import cycle

# ANSI true-color foreground: \033[38;2;R;G;Bm
# Reset: \033[0m
# Bold: \033[1m, Dim: \033[2m, Italic: \033[3m, Underline: \033[4m

RED = "\033[38;2;181;18;27m"      # #B5121B blood-red (DESTRUCTIVE)
RED_BOLD = "\033[1m\033[38;2;181;18;27m"
AMBER = "\033[38;2;245;166;35m"   # #F5A623 amber (CAUTION)
AMBER_BOLD = "\033[1m\033[38;2;245;166;35m"
GREEN = "\033[38;2;46;204;113m"   # #2ECC71 green (connected / ready)
CYAN = "\033[38;2;0;200;255m"      # #00C8FF cyan (seance / ask)
CYAN_BOLD = "\033[1m\033[38;2;0;200;255m"
PURPLE = "\033[38;2;175;82;222m"   # #AF52DE purple (roadmap / gap)
PURPLE_BOLD = "\033[1m\033[38;2;175;82;222m"
DIM = "\033[2m"
ITALIC = "\033[3m"
BOLD = "\033[1m"
RESET = "\033[0m"

WAITING_MESSAGES = [
    "listening to the commit log...",
    "the repository stirs...",
    "tracing what came before...",
    "old commits are speaking...",
    "something moved in the history...",
    "the ghost recalls this file...",
    "digging through buried commits...",
    "the blame trail runs deep...",
    "waking the dead branches...",
    "the archive remembers...",
    "a shadow passes through the diff...",
    "the dead code twitches...",
    "something was left unfinished here...",
    "the logs whisper of what happened...",
    "retracing abandoned footsteps...",
    "the last commit grows cold...",
    "sifting through forgotten changes...",
    "this file has seen things...",
    "the history does not forget...",
    "something familiar in this blame...",
]

STARTUP_MESSAGES = [
    "a presence stirs in the repository...",
    "the ghost has found your files...",
    "something still lingers here...",
    "the archive wakes...",
    "old code, old ghosts...",
]

# Original GhostTrace mark; use ASCII cursor blocks for compatibility with
# Windows terminals that replace unsupported glyphs instead of raising.
ASCII_LOGO = r"""  ___       ___       ___
 /\_ \     /\_ \     /\_ \
 \/_/ /    \/_/ /    \/_/ /
   / /      / /      / /
  / /      / /      / /
 / /   ___ / /   ___ / /
 / /   / __\ \ \   / __\ \
/ /___/ /   \ \_\ / /   \ \
 \ \____/  / / / /____/  / /
  \/_____/   \/_/ \/_____/ \/_/
          ||#||
          #  #"""

DESTRUCTIVE_SPLASH = (
    "   _''''_",
    "  ( !!   )",
    "  | !! !!|",
    "   \\    /",
)

_CAUTION_FLAVORS = cycle(
    (
        "The repository remembers every turn. Check the target before proceeding.",
        "A small change can leave a long trace. Verify what this will touch.",
        "Pause here; the next step may be harder to reverse than it looks.",
    )
)
_DESTRUCTIVE_FLAVORS = cycle(
    (
        "This action may leave a mark that cannot be undone. Verify the target.",
        "The history is watching. Check what will be overwritten or removed.",
        "Stop and inspect the consequences before crossing this line.",
    )
)


def supports_color() -> bool:
    """Return True if the terminal likely supports ANSI color."""
    return sys.stdout.isatty() and "NO_COLOR" not in __import__("os").environ


def colorize(text: str, code: str) -> str:
    if not supports_color():
        return text
    return f"{code}{text}{RESET}"


def banner_line(line: str, delay: float = 0.05) -> None:
    """Print a single banner line with a slight delay for the reveal."""
    try:
        if supports_color():
            print(colorize(line, RED))
        else:
            print(line)
    except UnicodeEncodeError:
        # Fall back to ASCII-safe output on Windows consoles that don't
        # support UTF-8 (e.g. cp1252).
        safe = line.encode("ascii", errors="replace").decode("ascii")
        if supports_color():
            print(colorize(safe, RED))
        else:
            print(safe)
    if delay > 0:
        time.sleep(delay)


def print_logo(delay: float = 0.04) -> None:
    """Print the ASCII logo with a fast line-by-line startup reveal
    (under ~1.5 seconds total)."""
    for line in ASCII_LOGO.splitlines():
        banner_line(line, delay)


def level_style(level: str) -> tuple[str, str]:
    """Return (color_code, label) for a safety level."""
    level = (level or "").upper()
    if level == "DESTRUCTIVE":
        return RED_BOLD, "DESTRUCTIVE"
    if level == "CAUTION":
        return AMBER_BOLD, "CAUTION"
    if level == "SAFE":
        return DIM, "SAFE"
    return DIM, "UNKNOWN"


def render_verdict(command: str, level: str, matched_rules: list[str]) -> str:
    """Render a single safety verdict block as ANSI text."""
    color, label = level_style(level)
    lines: list[str] = []
    lines.append("")
    if label == "DESTRUCTIVE":
        lines.extend(colorize(line, RED) for line in DESTRUCTIVE_SPLASH)
    lines.append(colorize(f"[{label}]", color))
    lines.append(f"command: {command}")
    if matched_rules:
        rules = ", ".join(matched_rules)
        lines.append(colorize(f"rules:   {rules}", DIM))
    return "\n".join(lines)


def render_flavor(level: str) -> str:
    """Return one brief, in-character aside for a warning; SAFE stays plain."""
    level = (level or "").upper()
    if level == "DESTRUCTIVE":
        return colorize(f"{next(_DESTRUCTIVE_FLAVORS)}", RED)
    if level == "CAUTION":
        return colorize(f"{next(_CAUTION_FLAVORS)}", AMBER)
    return ""


def render_waiting() -> str:
    """Choose an ambient line for an active request."""
    return colorize(f"[analyzing] {random.choice(WAITING_MESSAGES)}", DIM)


def render_explanation(explanation: str, level: str) -> str:
    """Render wrapped explanation paragraphs with level-appropriate styling."""
    color, _ = level_style(level)
    out: list[str] = []
    width = max(20, shutil.get_terminal_size(fallback=(80, 24)).columns - 2)
    for para in explanation.splitlines():
        para = para.strip()
        if not para:
            out.append("")
            continue
        wrapped = textwrap.fill(
            para,
            width=width,
            initial_indent="",
            subsequent_indent="",
            break_long_words=False,
            break_on_hyphens=False,
        )
        out.append(colorize(wrapped, color if supports_color() else ""))
    return "\n".join(out)


def render_evidence(evidence: list[dict]) -> str:
    """Render source references returned by the backend's evidence retrieval."""
    references = [
        f"{item['source_type']}:{item['source_ref']}"
        for item in evidence
        if item.get("source_type") and item.get("source_ref")
    ]
    if not references:
        return colorize("context: no repository evidence returned", DIM)
    return colorize(f"context: {', '.join(references)}", DIM)


def render_startup(api_url: str, repo_id: str) -> None:
    """Print the startup banner: logo + connection info."""
    print()
    print_logo(delay=0.03)
    print()
    print(colorize("  ghosttrace + repo-seance", BOLD))
    print(colorize(f"  {random.choice(STARTUP_MESSAGES)}", DIM))
    print(f"  api:     {api_url}")
    print(colorize(f"  repo:    {repo_id}", DIM))
    print(colorize("  type '? <question>', 'history', 'gap', 'roadmap', a shell command, or 'help'", ITALIC))
    print()


def render_error(message: str) -> str:
    return colorize(f"  [error] {message}", RED if supports_color() else "")


def render_connected() -> str:
    return colorize("  [connected] ready.", GREEN if supports_color() else "")


def render_seance_answer(question: str, answer: str, citations: list[dict]) -> str:
    """Render a grounded Q&A answer with inline source tags and citations."""
    lines: list[str] = []
    lines.append("")
    lines.append(colorize("  [SÉANCE RESPONSE]", CYAN_BOLD))
    lines.append(colorize(f"  question: {question}", DIM))
    lines.append("")

    width = max(20, shutil.get_terminal_size(fallback=(80, 24)).columns - 2)
    for para in answer.splitlines():
        para = para.strip()
        if not para:
            continue
        wrapped = textwrap.fill(
            para,
            width=width,
            initial_indent="  ",
            subsequent_indent="  ",
            break_long_words=False,
            break_on_hyphens=False,
        )
        lines.append(wrapped)

    if citations:
        lines.append("")
        refs = [f"{c.get('source_type')}:{c.get('source_ref')}" for c in citations if c.get("source_type")]
        lines.append(colorize(f"  citations: {', '.join(refs)}", CYAN))
    lines.append("")
    return "\n".join(lines)


def render_history(contributors: list[dict], log: list[dict], gap: dict) -> str:
    """Render repository commit history, top contributors, and activity gap."""
    lines: list[str] = []
    lines.append("")
    lines.append(colorize("  [REPOSITORY HISTORY]", CYAN_BOLD))

    # Activity gap
    if gap and gap.get("message"):
        lines.append(colorize(f"  gap: {gap['message']}", PURPLE))
    lines.append("")

    # Contributors
    lines.append(colorize("  Top Contributors:", BOLD))
    for c in contributors[:5]:
        author = c.get("author", "unknown")
        count = c.get("commit_count", 0)
        lines.append(f"    - {author}: {count} commit{'s' if count != 1 else ''}")
    lines.append("")

    # Recent commits
    lines.append(colorize(f"  Recent Commits ({len(log[:5])} of {len(log)}):", BOLD))
    for commit in log[:5]:
        sh = commit.get("short_hash", "")[:8]
        msg = (commit.get("message", "") or "").splitlines()[0][:60]
        author = commit.get("author", "")
        lines.append(f"    {colorize(sh, DIM)} {msg} {colorize(f'({author})', DIM)}")
    lines.append("")
    return "\n".join(lines)


def render_gap(gap: dict) -> str:
    """Render development gap analysis."""
    lines: list[str] = []
    lines.append("")
    lines.append(colorize("  [ACTIVITY GAP]", PURPLE_BOLD))
    msg = gap.get("message", "No activity gap detected.")
    days = gap.get("days", 0)
    lines.append(f"  {msg}")
    if days and days > 0:
        lines.append(colorize(f"  (Repository was dormant for approximately {days:.1f} days)", DIM))
    lines.append("")
    return "\n".join(lines)


def render_roadmap(roadmap: str, citations: list[dict]) -> str:
    """Render repository recovery roadmap."""
    lines: list[str] = []
    lines.append("")
    lines.append(colorize("  [RECOVERY ROADMAP]", PURPLE_BOLD))
    lines.append("")

    width = max(20, shutil.get_terminal_size(fallback=(80, 24)).columns - 2)
    for para in roadmap.splitlines():
        para = para.strip()
        if not para:
            continue
        wrapped = textwrap.fill(
            para,
            width=width,
            initial_indent="  ",
            subsequent_indent="  ",
            break_long_words=False,
            break_on_hyphens=False,
        )
        lines.append(wrapped)

    if citations:
        lines.append("")
        refs = [f"{c.get('source_type')}:{c.get('source_ref')}" for c in citations if c.get("source_type")]
        lines.append(colorize(f"  evidence cited: {', '.join(refs)}", DIM))
    lines.append("")
    return "\n".join(lines)


def render_help() -> str:
    """Render CLI command guide."""
    lines: list[str] = []
    lines.append("")
    lines.append(colorize("  GHOSTTRACE + REPO SÉANCE COMMANDS", BOLD))
    lines.append("")
    lines.append(f"  {colorize('? <question>', CYAN)} or {colorize('ask <question>', CYAN)}")
    lines.append("      Summon repository ghosts — Ask forensic questions grounded in git memory.")
    lines.append(f"  {colorize('history', CYAN)} or {colorize('contributors', CYAN)}")
    lines.append("      View commit log, contributor leaderboard, and active timeline.")
    lines.append(f"  {colorize('gap', PURPLE)}")
    lines.append("      Inspect detected development dormancy and activity gaps.")
    lines.append(f"  {colorize('roadmap', PURPLE)}")
    lines.append("      Generate an AI-driven project revival and recovery roadmap.")
    lines.append(f"  {colorize('<shell command>', RED)}")
    lines.append("      Test any shell command (e.g. 'rm -rf ./build') for pre-flight safety verdicts.")
    lines.append(f"  {colorize('exit', DIM)} or {colorize('quit', DIM)}")
    lines.append("      Exit the session.")
    lines.append("")
    return "\n".join(lines)

