"""Pydantic request/response schemas."""

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
