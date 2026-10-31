"""Ollama agent client package."""

from .client import OllamaClient, OllamaStatus, client, generate, status

__all__ = ["OllamaClient", "OllamaStatus", "client", "generate", "status"]
