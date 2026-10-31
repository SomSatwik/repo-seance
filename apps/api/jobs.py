"""In-process background ingestion jobs (simple thread runner for the MVP)."""

import threading
from datetime import datetime, timezone

from database import SessionLocal
from ingestion.pipeline import run_ingestion
from models import Repository


def start_ingestion_job(repo_id: int) -> None:
    """Launch ingestion for ``repo_id`` on a daemon thread."""
    t = threading.Thread(
        target=_run_job, args=(repo_id,), daemon=True, name=f"ingest-{repo_id}"
    )
    t.start()


def _run_job(repo_id: int) -> None:
    db = SessionLocal()
    try:
        repo = db.get(Repository, repo_id)
        if repo is None:
            return
        repo.status = "running"
        db.commit()

        summary = run_ingestion(repo_id, repo.url, db)

        repo = db.get(Repository, repo_id)
        repo.status = "completed"
        repo.structure_summary = summary
        repo.cloned_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as exc:  # noqa: BLE001 - record the failure on the row
        db.rollback()
        repo = db.get(Repository, repo_id)
        if repo is not None:
            repo.status = "failed"
            repo.error = str(exc)
            db.commit()
    finally:
        db.close()
