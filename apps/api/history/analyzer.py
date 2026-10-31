"""Git history analysis using GitPython on an already-cloned repo path.

All functions operate on a local, already-cloned repository. They do not
perform any network access — the caller (ingestion pipeline) is responsible
for having cloned the repo first.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from git import Repo


@dataclass
class CommitRecord:
    """A single commit as read from the local git history."""

    hash: str
    short_hash: str
    author: str
    author_email: str
    date: datetime
    message: str
    files_changed: list[str]


@dataclass
class ContributorStat:
    """Aggregated stats for a single author."""

    author: str
    email: str
    commit_count: int
    first_commit: Optional[datetime]
    last_commit: Optional[datetime]


@dataclass
class ActivityGap:
    """The largest detected gap between consecutive commits."""

    start_date: Optional[datetime]
    end_date: Optional[datetime]
    days: float
    message: str


def _open_repo(repo_path: Path | str) -> Repo:
    """Open the repository at ``repo_path`` (must already be cloned)."""
    return Repo(str(repo_path))


def _files_changed(repo: Repo, commit) -> list[str]:
    """Files changed in a commit, robust to shallow clones (no parent diff)."""
    try:
        output = repo.git.diff_tree(
            "--no-commit-id", "--name-only", "-r", commit.hexsha
        )
    except Exception:  # noqa: BLE001 - fall back to empty
        return []
    return sorted([l for l in output.splitlines() if l])


def get_commit_log(repo_path: Path | str, limit: int | None = 500) -> list[CommitRecord]:
    """Return commits (newest first) with hash, author, date, message.

    ``limit`` caps how many commits are read; pass ``None`` for the full
    history. Each record also includes the list of files changed in that
    commit (via ``git diff-tree``, which works even on shallow clones).
    """
    repo = _open_repo(repo_path)
    commits: list[CommitRecord] = []
    for commit in repo.iter_commits(max_count=limit):
        commits.append(
            CommitRecord(
                hash=commit.hexsha,
                short_hash=commit.hexsha[:8],
                author=commit.author.name,
                author_email=commit.author.email,
                date=commit.committed_datetime,
                message=commit.message.strip(),
                files_changed=_files_changed(repo, commit),
            )
        )
    return commits


def get_contributor_stats(repo_path: Path | str) -> list[ContributorStat]:
    """Return per-author commit counts with first/last commit dates."""
    repo = _open_repo(repo_path)
    by_author: dict[str, dict] = {}
    for commit in repo.iter_commits():
        key = commit.author.email
        entry = by_author.setdefault(
            key,
            {
                "author": commit.author.name,
                "email": commit.author.email,
                "commit_count": 0,
                "first_commit": commit.committed_datetime,
                "last_commit": commit.committed_datetime,
            },
        )
        entry["commit_count"] += 1
        dt = commit.committed_datetime
        if dt < entry["first_commit"]:
            entry["first_commit"] = dt
        if dt > entry["last_commit"]:
            entry["last_commit"] = dt

    return [
        ContributorStat(
            author=e["author"],
            email=e["email"],
            commit_count=e["commit_count"],
            first_commit=e["first_commit"],
            last_commit=e["last_commit"],
        )
        for e in sorted(by_author.values(), key=lambda x: -x["commit_count"])
    ]


def detect_activity_gaps(repo_path: Path | str) -> ActivityGap:
    """Find the largest gap between consecutive commits (newest first).

    Returns an ``ActivityGap`` describing the window where development
    stopped — the commit before the gap and the commit after it, plus the
    gap in days. Returns an empty gap if fewer than two commits exist.
    """
    repo = _open_repo(repo_path)
    commits = list(repo.iter_commits())
    if len(commits) < 2:
        return ActivityGap(None, None, 0.0, "Not enough history to detect a gap.")

    # iter_commits yields newest first. Compute gaps between consecutive ones.
    max_gap_seconds = 0.0
    gap_start: Optional[datetime] = None  # older commit (end of gap)
    gap_end: Optional[datetime] = None  # newer commit (start of gap)
    prev_dt: Optional[datetime] = None
    for commit in commits:
        dt = commit.committed_datetime
        if prev_dt is not None:
            delta = (prev_dt - dt).total_seconds()
            if delta > max_gap_seconds:
                max_gap_seconds = delta
                gap_end = prev_dt  # newer commit
                gap_start = dt  # older commit
        prev_dt = dt

    days = max_gap_seconds / 86400.0
    if gap_start and gap_end:
        message = (
            f"Development gap of {days:.1f} days between "
            f"{gap_end:%Y-%m-%d} and {gap_start:%Y-%m-%d}."
        )
    else:
        message = "No activity gap detected."
    return ActivityGap(gap_start, gap_end, days, message)


def blame_file(repo_path: Path | str, path: str) -> list[dict]:
    """Return git blame output for ``path`` as a list of line dicts.

    Each dict: ``{"commit": short_hash, "author": name, "line": text}``.
    Returns an empty list if the file doesn't exist or blame fails.
    """
    repo = _open_repo(repo_path)
    try:
        blame = repo.blame("HEAD", path)
    except Exception:  # noqa: BLE001 - file may not exist or be binary
        return []
    out: list[dict] = []
    for commit, lines in blame:
        for line in lines:
            out.append(
                {
                    "commit": commit.hexsha[:8],
                    "author": commit.author.name,
                    "line": line.rstrip("\n"),
                }
            )
    return out
