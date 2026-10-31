"""WebSocket client for the GhostTrace backend."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

import websockets


@dataclass
class Verdict:
    command: str
    level: str
    matched_rules: list[str]
    explanation: str
    evidence: list[dict]


class GhostTraceClient:
    """Thin WebSocket client over the /ws/ghosttrace endpoint.

    Safety verdicts come from the backend's deterministic engine; this
    client only transports the command and renders the response.
    """

    def __init__(self, api_url: str = "ws://localhost:8000", repo_id: str = "8") -> None:
        self.api_url = api_url.rstrip("/")
        self.repo_id = repo_id
        self.uri = f"{self.api_url}/ws/ghosttrace?repo_id={self.repo_id}"
        self._ws: Optional[websockets.ClientConnection] = None

    async def connect(self) -> None:
        self._ws = await websockets.connect(self.uri, open_timeout=5)

    async def close(self) -> None:
        if self._ws is not None:
            await self._ws.close()
            self._ws = None

    async def classify(self, command: str) -> Verdict:
        if self._ws is None:
            raise RuntimeError("client not connected")
        await self._ws.send(json.dumps({"command": command}))
        raw = await self._ws.recv()
        data = json.loads(raw)
        if "error" in data:
            raise RuntimeError(data["error"])
        return Verdict(
            command=data.get("command", command),
            level=data.get("level", "UNKNOWN"),
            matched_rules=data.get("matched_rules", []),
            explanation=data.get("explanation", ""),
            evidence=data.get("evidence", []),
        )
