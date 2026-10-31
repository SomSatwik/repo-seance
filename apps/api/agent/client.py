"""Ollama-powered agent client for local LLM inference."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional

import sentry_sdk

from config import settings


@dataclass
class OllamaStatus:
    reachable: bool
    model: str
    inference_mode: str  # "GPU" or "CPU"
    error: Optional[str] = None


class OllamaClient:
    """Thin wrapper around Ollama's local REST API.

    Defaults to ``/api/generate`` (single-turn). Model name is taken from
    the ``OLLAMA_MODEL`` env var (``gemma2:2b`` by default).
    """

    def __init__(self, host: Optional[str] = None, model: Optional[str] = None):
        configured_host = (host or settings.ollama_host).rstrip("/")
        self.host = (
            configured_host
            if "://" in configured_host
            else f"http://{configured_host}"
        )
        self.model = model or settings.ollama_model
        self._timeout = 120

    # -- low-level -----------------------------------------------------

    def _post(self, path: str, payload: dict) -> dict:
        url = f"{self.host}{path}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                body = resp.read().decode("utf-8")
        except urllib.error.URLError as exc:  # noqa: BLE001 - surface to caller
            return {
                "_error": f"Ollama unreachable at {self.host}: {exc}",
                "_error_type": type(exc).__name__,
            }
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {
                "_error": f"Invalid JSON from Ollama: {body[:200]}",
                "_error_type": "JSONDecodeError",
            }

    # -- public API ----------------------------------------------------

    def generate(self, prompt: str, context: Optional[list] = None) -> str:
        """Generate a completion for ``prompt`` using the configured model.

        Returns the generated text (or an error string prefixed with "[error]").
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if context:
            payload["context"] = context
        started = time.perf_counter()
        with sentry_sdk.start_span(op="ai.inference", name="ollama.generate") as span:
            span.set_data("model", self.model)
            span.set_data("success", False)
            try:
                result = self._post("/api/generate", payload)
            except Exception as exc:
                latency_ms = round((time.perf_counter() - started) * 1000, 2)
                span.set_data("latency_ms", latency_ms)
                self._capture_generate_failure(latency_ms, type(exc).__name__)
                raise

            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            span.set_data("latency_ms", latency_ms)
            for field, key in (
                ("prompt_tokens", "prompt_eval_count"),
                ("completion_tokens", "eval_count"),
            ):
                if isinstance(result.get(key), int):
                    span.set_data(field, result[key])
            if isinstance(result.get("total_duration"), int):
                span.set_data(
                    "ollama_total_duration_ms",
                    result["total_duration"] / 1_000_000,
                )

            if "_error" in result:
                self._capture_generate_failure(
                    latency_ms,
                    result.get("_error_type", "OllamaRequestError"),
                )
                return f"[error] {result['_error']}"

            span.set_data("success", True)
            return result.get("response", "")

    def _capture_generate_failure(self, latency_ms: float, failure_type: str) -> None:
        """Capture a sanitized model-call failure without recording the prompt."""
        try:
            raise RuntimeError(f"Ollama generate request failed ({failure_type})")
        except RuntimeError as exc:
            with sentry_sdk.push_scope() as scope:
                scope.set_tag("ai.provider", "ollama")
                scope.set_tag("ai.model", self.model)
                scope.set_tag("ai.failure_type", failure_type)
                scope.set_context(
                    "ai.call",
                    {
                        "operation": "generate",
                        "success": False,
                        "latency_ms": latency_ms,
                        "failure_type": failure_type,
                    },
                )
                sentry_sdk.capture_exception(exc)

    def embed(self, text: str, model: Optional[str] = None) -> list[float]:
        """Return an embedding vector for ``text`` via Ollama's embeddings API."""
        model = model or settings.ollama_embed_model
        payload = {"model": model, "prompt": text}
        result = self._post("/api/embeddings", payload)
        if "_error" in result:
            raise RuntimeError(result["_error"])
        return result.get("embedding", [])

    def status(self) -> OllamaStatus:
        """Probe Ollama: reachability, model, and inference mode (GPU/CPU)."""
        # Reachability + model via a cheap generate call with num_predict=0.
        result = self._post(
            "/api/generate",
            {"model": self.model, "prompt": "", "stream": False, "num_predict": 0},
        )
        if "_error" in result:
            return OllamaStatus(
                reachable=False,
                model=self.model,
                inference_mode="unknown",
                error=result["_error"],
            )

        # Inference mode: query /api/ps which reports the processor used.
        mode = self._inference_mode()
        return OllamaStatus(
            reachable=True,
            model=self.model,
            inference_mode=mode,
        )

    def _inference_mode(self) -> str:
        """Best-effort GPU/CPU detection via Ollama /api/ps."""
        try:
            req = urllib.request.Request(
                f"{self.host.rstrip('/')}/api/ps",
                method="GET",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception:  # noqa: BLE001 - fall back to CPU assumption
            return "CPU"
        models = data.get("models", [])
        for m in models:
            if m.get("name") == self.model or m.get("name", "").startswith(self.model.split(":")[0]):
                proc = str(m.get("processor", "")).lower()
                if "gpu" in proc:
                    return "GPU"
                return "CPU"
        return "CPU"


# Module-level singleton (configured from env).
client = OllamaClient()


def generate(prompt: str, context: Optional[list] = None) -> str:
    """Convenience wrapper around the module-level Ollama client."""
    return client.generate(prompt, context)


def status() -> OllamaStatus:
    """Convenience wrapper around the module-level client status probe."""
    return client.status()
