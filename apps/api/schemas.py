"""Pydantic request/response schemas."""

from datetime import datetime
from pydantic import BaseModel


class IngestRequest(BaseModel):
    url: str


class IngestResponse(BaseModel):
    repo_id: int
    status: str


class RepoStatus(BaseModel):
    repo_id: int
    url: str
    status: str
    structure_summary: dict | None = None
    error: str | None = None


# --- History -----------------------------------------------------------

class CommitResponse(BaseModel):
    hash: str
    short_hash: str
    author: str
    date: datetime
    message: str
    files_changed: list[str] = []


class ContributorStatResponse(BaseModel):
    author: str
    commit_count: int
    first_commit: datetime | None = None
    last_commit: datetime | None = None


class ActivityGapResponse(BaseModel):
    start_date: datetime | None = None
    end_date: datetime | None = None
    days: float
    message: str


class HistoryResponse(BaseModel):
    repo_id: int
    log: list[CommitResponse]
    contributors: list[ContributorStatResponse]
    gap: ActivityGapResponse


# --- Evidence / Q&A ----------------------------------------------------

class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str
    citations: list[dict] = []


class RoadmapResponse(BaseModel):
    roadmap: str
    citations: list[dict] = []


# --- System ------------------------------------------------------------

class SystemStatus(BaseModel):
    ollama_reachable: bool
    model: str
    inference_mode: str  # "GPU" or "CPU"

