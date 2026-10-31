"""Git history analysis engine (GitPython-backed)."""

from .analyzer import (
    blame_file,
    detect_activity_gaps,
    get_commit_log,
    get_contributor_stats,
)

__all__ = [
    "blame_file",
    "detect_activity_gaps",
    "get_commit_log",
    "get_contributor_stats",
]
