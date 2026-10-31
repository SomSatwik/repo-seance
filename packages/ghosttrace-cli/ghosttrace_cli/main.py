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

from .client import GhostTraceClient
from .render import (
    DIM,
    ITALIC,
    BOLD,
    colorize,
    render_error,
    render_connected,
    render_startup,
    render_verdict,
    render_explanation,
    render_evidence,
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
    """REPL loop: read command, send to backend, render classification + explanation."""
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
        print(colorize("  [analyzing] waiting for the grounded explanation...", DIM))
        try:
            verdict = await client.classify(command)
        except Exception as exc:  # noqa: BLE001 - surface connection issues clearly
            print(render_error(str(exc)))
            print(colorize("  the WebSocket may have closed; restart ghosttrace to reconnect", DIM))
            break
        print(render_verdict(verdict.command, verdict.level, verdict.matched_rules))
        print(render_explanation(verdict.explanation, verdict.level))
        print(render_evidence(verdict.evidence))
        print()


def run() -> None:
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
        default=os.environ.get("GHOSTTRACE_REPO_ID", "8"),
        help="Repository id (default: 8, or GHOSTTRACE_REPO_ID)",
    )
    args = parser.parse_args()

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
