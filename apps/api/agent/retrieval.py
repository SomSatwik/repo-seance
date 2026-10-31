"""Evidence retrieval: embed + pgvector cosine similarity search."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import select

from models import Evidence
from agent.client import client


@dataclass
class EvidenceHit:
    """A single retrieved evidence chunk with its similarity score."""

    source_type: str  # "commit" | "readme" | "file"
    source_ref: str  # commit hash or file path
    content: str
    distance: float  # cosine distance (lower = more similar)


def retrieve_evidence(
    db: Session,
    repo_id: int,
    query: str,
    k: int = 5,
    model: Optional[str] = None,
) -> list[EvidenceHit]:
    """Retrieve the top-``k`` most similar evidence chunks for ``query``.

    Embeds the query with Ollama, then orders stored evidence rows by cosine
    distance (pgvector `<=>`) and returns the closest matches.
    """
    query_emb = client.embed(query, model=model)
    stmt = (
        select(Evidence)
        .where(Evidence.repo_id == repo_id)
        .order_by(Evidence.embedding.cosine_distance(query_emb))
        .limit(k)
    )
    rows = db.execute(stmt).scalars().all()
    return [
        EvidenceHit(
            source_type=r.source_type,
            source_ref=r.source_ref,
            content=r.content,
            distance=float(r.embedding.distance) if hasattr(r, "distance") else 0.0,
        )
        for r in rows
    ]


def index_text(
    db: Session,
    repo_id: int,
    source_type: str,
    source_ref: str,
    content: str,
    model: Optional[str] = None,
) -> None:
    """Embed ``content`` and store it as an evidence row."""
    embedding = client.embed(content, model=model)
    db.add(
        Evidence(
            repo_id=repo_id,
            source_type=source_type,
            source_ref=source_ref,
            content=content,
            embedding=embedding,
        )
    )
