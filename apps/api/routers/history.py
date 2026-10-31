"""Repository history endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, func

from database import get_db
from models import Repository, Commit
from schemas import (
    HistoryResponse,
    CommitResponse,
    ContributorStatResponse,
    ActivityGapResponse,
)

router = APIRouter(prefix="/repos", tags=["history"])


@router.get("/{repo_id}/history", response_model=HistoryResponse)
def repo_history(repo_id: int, db: Session = Depends(get_db)):
    """Return commit log, contributor stats, and the detected activity gap."""
    repo = db.get(Repository, repo_id)
    if repo is None:
        raise HTTPException(status_code=404, detail="repository not found")

    commits = (
        db.execute(
            select(Commit)
            .where(Commit.repo_id == repo_id)
            .order_by(Commit.date.desc())
        )
        .scalars()
        .all()
    )

    log = [
        CommitResponse(
            hash=c.hash,
            short_hash=c.short_hash,
            author=c.author,
            date=c.date,
            message=c.message,
            files_changed=c.files_changed or [],
        )
        for c in commits
    ]

    # Contributor stats aggregated from stored commits.
    by_author: dict[str, dict] = {}
    for c in commits:
        e = by_author.setdefault(
            c.author_email,
            {
                "author": c.author,
                "email": c.author_email,
                "commit_count": 0,
                "first_commit": c.date,
                "last_commit": c.date,
            },
        )
        e["commit_count"] += 1
        if c.date < e["first_commit"]:
            e["first_commit"] = c.date
        if c.date > e["last_commit"]:
            e["last_commit"] = c.date
    contributors = [
        ContributorStatResponse(
            author=e["author"],
            commit_count=e["commit_count"],
            first_commit=e["first_commit"],
            last_commit=e["last_commit"],
        )
        for e in sorted(by_author.values(), key=lambda x: -x["commit_count"])
    ]

    # Activity gap: largest gap between consecutive commit dates.
    gap = _detect_gap([c.date for c in commits])

    return HistoryResponse(
        repo_id=repo_id,
        log=log,
        contributors=contributors,
        gap=gap,
    )


def _detect_gap(dates) -> ActivityGapResponse:
    """Largest gap between consecutive datetimes (newest first)."""
    if len(dates) < 2:
        return ActivityGapResponse(
            days=0.0, message="Not enough history to detect a gap."
        )
    sorted_dates = sorted(dates, reverse=True)
    max_gap = 0.0
    gap_start = gap_end = None
    for i in range(len(sorted_dates) - 1):
        delta = (sorted_dates[i] - sorted_dates[i + 1]).total_seconds()
        if delta > max_gap:
            max_gap = delta
            gap_end = sorted_dates[i]
            gap_start = sorted_dates[i + 1]
    days = max_gap / 86400.0
    return ActivityGapResponse(
        start_date=gap_start,
        end_date=gap_end,
        days=days,
        message=f"Development gap of {days:.1f} days "
        f"({gap_start:%Y-%m-%d} -> {gap_end:%Y-%m-%d})."
        if gap_start and gap_end
        else "No activity gap detected.",
    )
