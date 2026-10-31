"""Agent endpoints: grounded Q&A (ask), recovery roadmap, and system status."""

from __future__ import annotations

import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from agent.client import client, status as ollama_status
from agent.retrieval import retrieve_evidence
from database import get_db
from models import Repository, Evidence
from schemas import AskRequest, AskResponse, RoadmapResponse, SystemStatus
from config import settings

router = APIRouter(tags=["agent"])

# --- Grounded Q&A -------------------------------------------------------

_ASK_PROMPT_TEMPLATE = """You are a forensic code assistant answering questions about a software repository.

Answer the user's question using ONLY the evidence below. Each evidence item is tagged with its source:
- [commit:<short_hash>] a commit message (author: message)
- [readme:<name>] README file content
- [file:<path>] a source file's docstring/summary

Rules:
1. Ground every claim in the evidence. Cite your sources inline using the tags above, e.g. [commit:a1b2c3d] or [file:src/main.py].
2. If the evidence does not contain enough information to answer, say so explicitly rather than guessing.
3. Do not invent file paths, commit hashes, or authors that do not appear in the evidence.
4. Be concise.

Question: {question}

Evidence:
{evidence}

Answer:"""


def _format_evidence(hits) -> str:
    if not hits:
        return "(no relevant evidence found)"
    blocks = []
    for h in hits:
        blocks.append(f"[{h.source_type}:{h.source_ref}] {h.content}")
    return "\n\n".join(blocks)


@router.post("/repos/{repo_id}/ask", response_model=AskResponse)
def ask(repo_id: int, payload: AskRequest, db: Session = Depends(get_db)):
    """Answer a question about a repo, grounded in retrieved evidence with citations."""
    repo = db.get(Repository, repo_id)
    if repo is None:
        raise HTTPException(status_code=404, detail="repository not found")

    hits = retrieve_evidence(db, repo_id, payload.question, k=5)
    evidence_text = _format_evidence(hits)
    prompt = _ASK_PROMPT_TEMPLATE.format(question=payload.question, evidence=evidence_text)

    t0 = time.perf_counter()
    answer = client.generate(prompt)
    latency_ms = (time.perf_counter() - t0) * 1000

    if answer.startswith("[error]"):
        raise HTTPException(status_code=502, detail=answer)

    citations = [
        {"source_type": h.source_type, "source_ref": h.source_ref}
        for h in hits
    ]
    return AskResponse(answer=answer, citations=citations)


# --- Recovery roadmap ---------------------------------------------------

_ROADMAP_PROMPT_TEMPLATE = """You are a recovery lead for an abandoned or stagnant software repository.

Produce a prioritized recovery roadmap based on the evidence below. Each item is tagged with its source.

Evidence (activity gap, contributors, and TODOs/FIXMEs found in the repo):
{evidence}

Rules:
1. Ground every recommendation in the evidence. Cite sources inline using [commit:...] / [file:...] tags.
2. Address the activity gap explicitly: when development stopped, who the top contributors were, and what that implies.
3. Surface concrete next steps (e.g. "revive the X module", "address FIXME in src/foo.py:line").
4. Be concise and actionable.

Roadmap:"""


def _collect_roadmap_evidence(db: Session, repo_id: int, structure_summary: dict | None) -> str:
    blocks = []

    # Activity gap + top contributors from local git history (cheap on a clone).
    from history.analyzer import get_contributor_stats, detect_activity_gaps
    from pathlib import Path
    repo_path = settings.data_dir / "repos" / str(repo_id)
    if repo_path.exists():
        stats = get_contributor_stats(repo_path)
        gap = detect_activity_gaps(repo_path)
        blocks.append(f"ACTIVITY_GAP: {gap.message}")
        top = stats[:5]
        blocks.append("TOP_CONTRIBUTORS: " + "; ".join(
            f"{s.author} ({s.commit_count} commits)" for s in top
        ))

    # TODO/FIXME hints from the structure scan (manifests + file list).
    if structure_summary:
        manifests = structure_summary.get("manifests", {})
        if manifests:
            blocks.append("MANIFESTS: " + str(manifests)[:800])
        files = structure_summary.get("file_tree", {})
        if files:
            blocks.append("FILE_TREE_PREVIEW: " + str(files)[:600])

    return "\n".join(blocks)


@router.post("/repos/{repo_id}/roadmap", response_model=RoadmapResponse)
def roadmap(repo_id: int, db: Session = Depends(get_db)):
    """Return a prioritized, evidence-grounded recovery roadmap for the repo."""
    repo = db.get(Repository, repo_id)
    if repo is None:
        raise HTTPException(status_code=404, detail="repository not found")

    evidence_text = _collect_roadmap_evidence(db, repo_id, repo.structure_summary)
    # Also pull relevant commit/file evidence via retrieval for grounding.
    hits = retrieve_evidence(db, repo_id, "recovery roadmap abandoned TODO FIXME", k=5)
    if hits:
        retrieval_text = "\n".join(f"[{h.source_type}:{h.source_ref}] {h.content}" for h in hits)
        evidence_text += "\n\nRETRIEVED:\n" + retrieval_text
        citations = [{"source_type": h.source_type, "source_ref": h.source_ref} for h in hits]
    else:
        citations = []

    prompt = _ROADMAP_PROMPT_TEMPLATE.format(evidence=evidence_text)
    answer = client.generate(prompt)

    if answer.startswith("[error]"):
        raise HTTPException(status_code=502, detail=answer)

    return RoadmapResponse(roadmap=answer, citations=citations)


# --- System status ------------------------------------------------------

@router.get("/system/status", response_model=SystemStatus)
def system_status():
    """Report Ollama reachability, model in use, and inferred execution mode (GPU/CPU)."""
    st = ollama_status()
    return SystemStatus(
        ollama_reachable=st.reachable,
        model=st.model,
        inference_mode=st.inference_mode,
    )
