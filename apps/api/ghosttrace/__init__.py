"""GhostTrace: terminal-companion safety engine package."""

from .safety_rules import (
    SAFE,
    CAUTION,
    DESTRUCTIVE,
    SafetyResult,
    classify,
)

__all__ = ["SAFE", "CAUTION", "DESTRUCTIVE", "SafetyResult", "classify"]
