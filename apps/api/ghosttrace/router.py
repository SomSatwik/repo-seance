"""GhostTrace terminal-companion router (WebSocket command interception).

Design constraints (safety-critical):

* The safety VERDICT is computed by the deterministic engine
  (``ghosttrace.safety_rules.classify``) BEFORE any LLM call. Gemma is used
  ONLY to produce the explanation text — it is never asked to second-guess
  or override the verdict.
* The feature is opt-in via ``GHOSTTRACE_ENABLED`` and project-scoped via
  ``GHOSTTRACE_PROJECT_SCOPE_ONLY`` — evidence is retrieved only for the
  current repo_id, never the user's broader shell history or machine.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from agent.client import client as ollama_client
from agent.retrieval import retrieve_evidence
from config import settings
from database import SessionLocal
from ghosttrace.safety_rules import CAUTION, DESTRUCTIVE, SAFE, classify

logger = logging.getLogger("ghosttrace")

router = APIRouter(tags=["ghosttrace"])


# --- Explanation prompt (LLM explains the verdict, never second-guesses it) ---

_EXPLANATION_PROMPT_TEMPLATE = """You are explaining a safety classification for a shell command a user is about to run.

The safety verdict below was computed by a separate, deterministic rule engine. Treat it as a fact:
- Do NOT second-guess, override, or reclassify it.
- Your job is only to explain WHY it received that classification, using the project context.

Command: {command}
Deterministic safety verdict: {level}
Rules matched: {matched_rules}

Project context from this repository's actual history (commit messages, README, file docstrings):
{evidence}

Write a concise, clear explanation that:
1. States what the command does.
2. Explains why it is classified "{level}", referencing specific file paths or commit hashes from the project context above where relevant.
3. Notes what the user should double-check before running it (for CAUTION/DESTRUCTIVE).
Do not invent file paths or commit hashes that do not appear in the context. Keep it under 120 words.

Explanation:"""


def _format_evidence(hits) -> str:
    if not hits:
        return "(no project context found for this repository)"
    blocks = []
    for h in hits[:5]:
        blocks.append(f"[{h.source_type}:{h.source_ref}] {h.content[:300]}")
    return "\n".join(blocks)


def _fallback_explanation(command: str, level: str, matched_rules: list[str]) -> str:
    """Deterministic fallback explanation used when Gemma is unavailable."""
    rules = "; ".join(matched_rules) if matched_rules else "none"
    return (
        f"The command '{command}' was classified as {level} by the deterministic "
        f"safety engine (rules matched: {rules}). "
        f"{'This is potentially destructive — review carefully before running.' if level == DESTRUCTIVE else ''}"
        f"{'Exercise caution — this can modify files or history.' if level == CAUTION else ''}"
    )


@router.websocket("/ws/ghosttrace")
async def ghosttrace_websocket(
    websocket: WebSocket,
    repo_id: int = Query(..., description="ID of the current project repository"),
) -> None:
    """WebSocket endpoint: classify a command + return a Gemma explanation.

    Message format (client -> server):
        {"command": "rm -rf ./build"}

    Response (server -> client):
        {"command": "...", "level": "DESTRUCTIVE", "explanation": "...", "evidence": [...]}
    """
    # --- Opt-in gate -------------------------------------------------------
    if not settings.ghosttrace_enabled:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="GhostTrace is not enabled. Set GHOSTTRACE_ENABLED=true.",
        )
        return

    await websocket.accept()

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(
                    json.dumps({"error": "invalid JSON", "detail": "expected {\"command\": \"...\"}"})
                )
                continue

            command: str = payload.get("command", "")
            if not isinstance(command, str) or not command.strip():
                await websocket.send_text(
                    json.dumps({"error": "missing command", "detail": "provide a non-empty \"command\""})
                )
                continue

            # --- Step 1: deterministic safety verdict (BEFORE any LLM) -----
            result = classify(command)
            logger.info(
                "ghosttrace: repo_id=%s command=%r level=%s rules=%s",
                repo_id,
                command,
                result.level,
                result.matched_rules,
            )

            # --- Step 2: project-scoped evidence retrieval (Sprint 1 layer) ---
            evidence_hits = []
            if settings.ghosttrace_project_scope_only:
                db = SessionLocal()
                try:
                    evidence_hits = retrieve_evidence(db, repo_id, command, k=5)
                finally:
                    db.close()
            evidence_text = _format_evidence(evidence_hits)

            # --- Step 3: Gemma explains the verdict (LLM only for text) ----
            # The verdict is already fixed; the prompt is told not to second-guess it.
            prompt = _EXPLANATION_PROMPT_TEMPLATE.format(
                command=command,
                level=result.level,
                matched_rules=", ".join(result.matched_rules) or "none",
                evidence=evidence_text,
            )
            try:
                explanation = ollama_client.generate(prompt)
                if explanation.startswith("[error]"):
                    explanation = _fallback_explanation(command, result.level, result.matched_rules)
            except Exception as exc:  # noqa: BLE001 - Gemma down is not fatal
                logger.warning("ghosttrace: Gemma explanation failed: %s", exc)
                explanation = _fallback_explanation(command, result.level, result.matched_rules)

            response = {
                "command": command,
                "level": result.level,
                "matched_rules": result.matched_rules,
                "explanation": explanation,
                "evidence": [
                    {
                        "source_type": h.source_type,
                        "source_ref": h.source_ref,
                        "content": h.content[:200],
                    }
                    for h in evidence_hits
                ],
            }
            await websocket.send_text(json.dumps(response))

    except WebSocketDisconnect:  # noqa: BLE001 - normal client disconnect
        logger.info("ghosttrace: repo_id=%s disconnected", repo_id)
