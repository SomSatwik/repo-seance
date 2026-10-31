"""Repository ingestion endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from jobs import start_ingestion_job
from models import Repository
from schemas import IngestRequest, IngestResponse, RepoStatus

router = APIRouter(prefix="/repos", tags=["repos"])


@router.post("/ingest", response_model=IngestResponse, status_code=202)
def ingest(payload: IngestRequest, db: Session = Depends(get_db)):
    """Kick off ingestion for a public git URL; returns immediately with a repo id."""
    repo = Repository(url=payload.url.strip(), status="pending")
    db.add(repo)
    db.commit()
    db.refresh(repo)
    start_ingestion_job(repo.id)
    return IngestResponse(repo_id=repo.id, status="pending")


@router.get("/{repo_id}/status", response_model=RepoStatus)
def repo_status(repo_id: int, db: Session = Depends(get_db)):
    """Return ingestion status and, when complete, the structure summary."""
    repo = db.get(Repository, repo_id)
    if repo is None:
        raise HTTPException(status_code=404, detail="repository not found")
    return RepoStatus(
        repo_id=repo.id,
        url=repo.url,
        status=repo.status,
        structure_summary=repo.structure_summary,
        error=repo.error,
    )
