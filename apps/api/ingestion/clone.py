"""Repository cloning with configurable size/time limits (GitPython)."""

import os
import shutil
import threading
from pathlib import Path
from urllib.parse import urlparse

from git import Repo

from config import settings


class CloneError(Exception):
    """Raised when a repository cannot be cloned (bad URL, auth, network, limits)."""


def clone_repo(
    url: str,
    dest: Path,
    timeout: int | None = None,
    max_size_mb: int | None = None,
) -> Path:
    """Clone ``url`` into ``dest`` using a shallow clone with a size/time guard.

    Limits are configurable via settings/env: ``CLONE_TIMEOUT_SECONDS``,
    ``CLONE_MAX_SIZE_MB``, ``CLONE_DEPTH``. The shallow ``--depth`` clone is the
    primary size control; ``max_size_mb`` is a post-clone guard that deletes the
    result if it is exceeded.
    """
    timeout = timeout or settings.clone_timeout_seconds
    max_size_mb = max_size_mb or settings.clone_max_size_mb

    _validate_url(url)

    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)

    git_env = os.environ.copy()
    # Fail fast (never hang prompting) on private repos without credentials.
    git_env["GIT_TERMINAL_PROMPT"] = "0"
    git_env["GIT_LFS_SKIP_SMUDGE"] = "1"

    err: dict = {}

    def _run() -> None:
        try:
            Repo.clone_from(
                url,
                str(dest),
                multi_options=["--depth", str(settings.clone_depth), "--single-branch"],
                allow_unsafe_protocols=True,
                env=git_env,
            )
        except Exception as exc:  # noqa: BLE001 - re-raised as CloneError below
            err["e"] = exc

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout)

    if t.is_alive():
        shutil.rmtree(dest, ignore_errors=True)
        raise CloneError(
            f"clone timed out after {timeout}s (limit is configurable via CLONE_TIMEOUT_SECONDS)"
        )

    if "e" in err:
        shutil.rmtree(dest, ignore_errors=True)
        raise CloneError(_classify(err["e"], url))

    size = _dir_size(dest)
    if size > max_size_mb * 1024 * 1024:
        shutil.rmtree(dest, ignore_errors=True)
        raise CloneError(
            f"cloned repo is {size // (1024 * 1024)} MB, exceeding the "
            f"{max_size_mb} MB limit (configurable via CLONE_MAX_SIZE_MB)"
        )

    return dest


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme in {"http", "https", "git", "ssh", "file"}:
        return
    if not parsed.scheme and Path(url).exists():
        return  # local path (used by tests)
    raise CloneError(f"unsupported or invalid repository URL: {url!r}")


def _classify(exc: Exception, url: str) -> str:
    msg = str(exc)
    low = msg.lower()
    if any(
        token in low
        for token in (
            "authentication failed",
            "could not read username",
            "could not read password",
            "permission denied",
            "access denied",
        )
    ):
        return f"authentication failed (private repo or missing credentials): {url!r}"
    if any(
        token in low
        for token in (
            "not found",
            "does not appear to be a git repository",
            "repository not found",
        )
    ):
        return f"repository not found or invalid URL: {url!r}"
    if any(
        token in low
        for token in (
            "could not resolve host",
            "unable to access",
            "could not resolve",
            "network is unreachable",
            "connection timed out",
        )
    ):
        return f"network error while cloning: {url!r}"
    return f"git clone failed: {msg}"


def _dir_size(path: Path) -> int:
    total = 0
    for p in path.rglob("*"):
        if p.is_file():
            try:
                total += p.stat().st_size
            except OSError:
                pass
    return total
