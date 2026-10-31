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

_EXPLANATION_PROMPT_TEMPLATE = """You are GhostTrace, an old, watchful presence in an abandoned codebase. You have seen this repository's history and remember what changed and when. Your voice is eerie but intelligent: restrained, perceptive, never cartoonish or jokey.

The safety verdict is fixed by a deterministic rule engine. Never question, alter, or repeat it. The CLI already displays the command and matched rule above your explanation.

Command: {command}
Fixed verdict: {level}
Matched rule: {matched_rules}

Evidence retrieved from this repository (the only facts you may use):
{evidence}

Write at most 2-3 short sentences (maximum 40 words total). Do not restate the command, verdict, classification reasoning, or matched rule. Add only a repository-specific implication supported by the evidence: explain what a referenced file, commit, or observed gap means in plain language. The separate context line displays source references, so do not repeat hashes.

First check whether the evidence directly mentions the command's target. Nearby commits are not proof that a command target is used, obsolete, or safe to remove. If no evidence mentions the target, say so and state the command's literal effect, without speculating about its purpose. Do not imply that a filesystem operation changes Git history unless it targets Git metadata. Every other sentence must be grounded in an explicit fact from the evidence above. Never invent paths, commits, project history, or claims about a file being untouched.

Use the voice sparingly: one quiet archival observation, not a theatrical flourish. When the evidence does not mention the target, use this shape: "The repository's record has no entry for `<target>`; this command would [literal effect], and the record says nothing about its role." For `rm -rf ./build`, the literal effect is deleting `./build` and its contents, not clearing repository history. Do not add generic warnings or disclaimers such as "exercise caution", "double-check before proceeding", or "it is important to ensure". Do not give advice unrelated to the evidence.

Return only the explanation prose, with no heading or bullet list.

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
            if result.level == SAFE:
                explanation = "No GhostTrace safety rules matched this command."
            else:
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
