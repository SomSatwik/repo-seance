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

_EXPLANATION_PROMPT_TEMPLATE = """You are GhostTrace, an AI terminal safety companion with deep knowledge of repository history.

A developer entered the shell command:
`{command}`

Deterministic classification: {level}
Matched safety rules: {matched_rules}

Repository Context (recent commits and file history):
{evidence}

Explain why this command was classified as {level} and provide clear pre-flight guidance.
Follow this structure:
The command `{command}` will [explain what it does]. This action is classified as {level} because [explain why this command and its flags or targets triggered this classification].
**Why {level}:** [Explain the specific risks, targeting issues, and potential data loss].
**Before executing:**
- [Actionable precaution 1]
- [Actionable precaution 2]

Do not output conversational greetings. Return only the explanation prose with markdown formatting."""


def _format_evidence(hits) -> str:
    if not hits:
        return "(no project context found for this repository)"
    blocks = []
    for h in hits[:5]:
        blocks.append(f"[{h.source_type}:{h.source_ref}] {h.content[:300]}")
    return "\n".join(blocks)


def _fallback_explanation(command: str, level: str, matched_rules: list[str]) -> str:
    """Deterministic fallback explanation used when Gemma is unavailable."""
    rules = ", ".join(matched_rules) if matched_rules else "none"
    if level == DESTRUCTIVE:
        return (
            f"The command `{command}` will perform an irreversible or highly sensitive operation. "
            f"This action is classified as DESTRUCTIVE because it matched rule(s): {rules}.\n\n"
            f"**Why DESTRUCTIVE:** This command carries high risk of unintended data loss, irreversible deletion, or corruption.\n\n"
            f"**Before executing:**\n"
            f"- Double-check if you truly intend to run `{command}` as this action cannot be easily undone.\n"
            f"- Ensure you have committed your changes or have a backup before running the command."
        )
    if level == CAUTION:
        return (
            f"The command `{command}` will modify files, dependencies, or git history. "
            f"This action is classified as CAUTION because it matched rule(s): {rules}.\n\n"
            f"**Why CAUTION:** The project history highlights the potential for unintended side-effects or loss of uncommitted work.\n\n"
            f"**Before running this command, always double-check the arguments and target path to ensure safety.**"
        )
    return f"The command `{command}` is safe to run in this repository."


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

    # Ambient presence banner on initial connection
    await websocket.send_text(
        json.dumps({
            "event": "presence",
            "message": f"Spirit link established with repository #{repo_id}. The ghosts are listening...",
            "level": "SAFE",
        })
    )

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

            flavor = ""
            if result.level == DESTRUCTIVE:
                flavor = "This action may leave a mark that cannot be undone. Verify the target."
            elif result.level == CAUTION:
                flavor = "The repository remembers every turn. Check the target before proceeding."

            response = {
                "command": command,
                "level": result.level,
                "matched_rules": result.matched_rules,
                "flavor": flavor,
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
