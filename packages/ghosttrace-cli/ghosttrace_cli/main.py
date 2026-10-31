"""GhostTrace CLI entry point.

Installs as the `ghosttrace` command via [project.scripts] in pyproject.toml.
Reuses the existing /ws/ghosttrace WebSocket endpoint from the Repo Séance
API — no safety engine or Gemma logic is reimplemented here.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

import colorama

from .client import GhostTraceClient
from .render import (
    DIM,
    ITALIC,
    BOLD,
    CYAN,
    PURPLE,
    colorize,
    render_error,
    render_connected,
    render_startup,
    render_verdict,
    render_flavor,
    render_explanation,
    render_evidence,
    render_waiting,
    render_seance_answer,
    render_history,
    render_gap,
    render_roadmap,
    render_help,
)


def _check_backend(api_url: str) -> None:
    """Best-effort check that the backend is reachable before we enter the REPL."""
    import urllib.request

    health_url = api_url.replace("ws://", "http://").replace("wss://", "https://") + "/health"
    try:
        with urllib.request.urlopen(health_url, timeout=3) as resp:  # noqa: S310 - local dev URL
            if resp.status != 200:
                print(render_error(f"backend returned HTTP {resp.status}"))
                sys.exit(1)
    except Exception as exc:  # noqa: BLE001 - report and exit cleanly
        print(render_error(f"cannot reach backend at {api_url} ({exc})"))
        print(colorize("  start the Repo Séance API first: uvicorn main:app --port 8000", DIM))
        sys.exit(1)


async def _repl(client: GhostTraceClient) -> None:
    """REPL loop: handle forensic questions, repo history/roadmap, or shell safety."""
    print(render_connected())
    print()
    while True:
        try:
            try:
                command = input("> ").strip()
            except EOFError:
                print()
                break
        except KeyboardInterrupt:
            print()
            break
        if not command:
            continue
        if command.lower() in {"exit", "quit", ":q"}:
            break

        # --- Help command ---
        if command.lower() in {"help", "--help", "-h"}:
            print(render_help())
            continue

        # --- Séance Forensic Q&A ---
        if command.startswith("?") or command.lower().startswith("ask ") or command.lower().startswith("seance "):
            if command.startswith("?"):
                question = command[1:].strip()
            elif command.lower().startswith("ask "):
                question = command[4:].strip()
            else:
                question = command[7:].strip()

            if not question:
                print(colorize("  provide a question, e.g. '? who worked on this project?'", DIM))
                continue

            show_waiting = sys.stdout.isatty()
            if show_waiting:
                print(colorize("  [summoning] interrogating the repository's ghosts...", CYAN), end="", flush=True)
            try:
                res = await client.ask(question)
                if show_waiting:
                    print("\r\033[2K", end="", flush=True)
                print(render_seance_answer(question, res.get("answer", ""), res.get("citations", [])))
            except Exception as exc:
                if show_waiting:
                    print("\r\033[2K", end="", flush=True)
                print(render_error(f"séance query failed: {exc}"))
            continue

        # --- History & Contributor Stats ---
        if command.lower() in {"history", "commits", "contributors"}:
            show_waiting = sys.stdout.isatty()
            if show_waiting:
                print(colorize("  [searching] reading git logs and contributors...", CYAN), end="", flush=True)
            try:
                res = await client.get_history()
                if show_waiting:
                    print("\r\033[2K", end="", flush=True)
                print(render_history(res.get("contributors", []), res.get("log", []), res.get("gap", {})))
            except Exception as exc:
                if show_waiting:
                    print("\r\033[2K", end="", flush=True)
                print(render_error(f"failed to fetch history: {exc}"))
            continue

        # --- Activity Gap / Dormancy ---
        if command.lower() in {"gap", "dormancy", "dormant"}:
            show_waiting = sys.stdout.isatty()
            if show_waiting:
                print(colorize("  [analyzing] computing activity gaps...", PURPLE), end="", flush=True)
            try:
                res = await client.get_history()
                if show_waiting:
                    print("\r\033[2K", end="", flush=True)
                print(render_gap(res.get("gap", {})))
            except Exception as exc:
                if show_waiting:
                    print("\r\033[2K", end="", flush=True)
                print(render_error(f"failed to check activity gap: {exc}"))
            continue

        # --- Recovery Roadmap ---
        if command.lower() in {"roadmap", "revive", "recovery"}:
            show_waiting = sys.stdout.isatty()
            if show_waiting:
                print(colorize("  [planning] generating project recovery roadmap...", PURPLE), end="", flush=True)
            try:
                res = await client.get_roadmap()
                if show_waiting:
                    print("\r\033[2K", end="", flush=True)
                print(render_roadmap(res.get("roadmap", ""), res.get("citations", [])))
            except Exception as exc:
                if show_waiting:
                    print("\r\033[2K", end="", flush=True)
                print(render_error(f"failed to generate roadmap: {exc}"))
            continue

        # --- GhostTrace Shell Safety Classification ---
        show_waiting = sys.stdout.isatty()
        if show_waiting:
            print(render_waiting(), end="", flush=True)
        try:
            verdict = await client.classify(command)
        except Exception as exc:  # noqa: BLE001 - surface connection issues clearly
            print(render_error(str(exc)))
            print(colorize("  the WebSocket may have closed; restart ghosttrace to reconnect", DIM))
            break
        finally:
            if show_waiting:
                print("\r\033[2K", end="", flush=True)
        print(render_verdict(verdict.command, verdict.level, verdict.matched_rules))
        flavor = render_flavor(verdict.level)
        if flavor:
            print(flavor)
        print(render_explanation(verdict.explanation, verdict.level))
        print(render_evidence(verdict.evidence))
        print()


def run() -> None:
    colorama.just_fix_windows_console()
    colorama.init(autoreset=True)

    parser = argparse.ArgumentParser(
        prog="ghosttrace",
        description="GhostTrace terminal companion — deterministic shell safety classifications.",
    )
    parser.add_argument(
        "--api-url",
        default=os.environ.get("GHOSTTRACE_API_URL", "ws://localhost:8000"),
        help="Backend WebSocket URL (default: ws://localhost:8000, or GHOSTTRACE_API_URL)",
    )
    parser.add_argument(
        "--repo",
        default=os.environ.get("GHOSTTRACE_REPO_ID"),
        help="Repository id (or GHOSTTRACE_REPO_ID)",
    )
    args = parser.parse_args()
    if not args.repo:
        parser.error("--repo is required unless GHOSTTRACE_REPO_ID is set")

    print()
    render_startup(args.api_url, args.repo)

    _check_backend(args.api_url.replace("ws://", "http://").replace("wss://", "https://"))

    client = GhostTraceClient(api_url=args.api_url, repo_id=args.repo)
    try:
        asyncio.run(_run_client(client))
    except KeyboardInterrupt:
        print()
    except Exception as exc:
        print(render_error(f"cannot connect to GhostTrace WebSocket at {client.uri} ({exc})"))
        print(colorize("  confirm GhostTrace is enabled and the API URL is correct", DIM))
        sys.exit(1)
    finally:
        print(colorize("  ghosttrace session ended.", ITALIC))
        print()


async def _run_client(client: GhostTraceClient) -> None:
    try:
        await client.connect()
        await _repl(client)
    finally:
        await client.close()


if __name__ == "__main__":
    run()
