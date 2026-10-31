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
    """Thin client over the /ws/ghosttrace WebSocket and Repo Séance REST API.

    Safety verdicts come from the backend's deterministic engine; forensic
    Q&A and history queries connect to the Repo Séance agent endpoints.
    """

    def __init__(self, api_url: str = "ws://localhost:8000", repo_id: str = "8") -> None:
        self.api_url = api_url.rstrip("/")
        self.repo_id = repo_id
        self.uri = f"{self.api_url}/ws/ghosttrace?repo_id={self.repo_id}"
        self._ws: Optional[websockets.ClientConnection] = None

    @property
    def http_base(self) -> str:
        return self.api_url.replace("ws://", "http://").replace("wss://", "https://")

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

    async def ask(self, question: str) -> dict:
        """Query the forensic Q&A endpoint grounded in vector evidence."""
        import asyncio
        import urllib.request

        url = f"{self.http_base}/repos/{self.repo_id}/ask"
        data = json.dumps({"question": question}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        def _fetch():
            with urllib.request.urlopen(req, timeout=90) as resp:
                return json.loads(resp.read().decode("utf-8"))

        return await asyncio.to_thread(_fetch)

    async def get_history(self) -> dict:
        """Fetch git commit log, contributor stats, and activity gap."""
        import asyncio
        import urllib.request

        url = f"{self.http_base}/repos/{self.repo_id}/history"

        def _fetch():
            with urllib.request.urlopen(url, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))

        return await asyncio.to_thread(_fetch)

    async def get_roadmap(self) -> dict:
        """Generate a recovery roadmap for the repository."""
        import asyncio
        import urllib.request

        url = f"{self.http_base}/repos/{self.repo_id}/roadmap"
        req = urllib.request.Request(
            url,
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        def _fetch():
            with urllib.request.urlopen(req, timeout=90) as resp:
                return json.loads(resp.read().decode("utf-8"))

        return await asyncio.to_thread(_fetch)
