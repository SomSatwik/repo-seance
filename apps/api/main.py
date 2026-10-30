"""Repo Séance API — FastAPI entry point.

Phase 1 skeleton: a single /health endpoint that probes live database
connectivity so we can verify the Postgres + pgvector stack end to end.
"""

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text

load_dotenv()

app = FastAPI(title="Repo Séance API", version="0.1.0")

# Allow the Next.js dev server (localhost:3000) to call this API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5434/reposeance",
)


def _sqlalchemy_url(url: str) -> str:
    """Point SQLAlchemy at the psycopg (v3) driver.

    ``.env.example`` uses a driver-less ``postgresql://`` URL (the de-facto
    standard), but SQLAlchemy defaults that scheme to psycopg2. We install
    ``psycopg[binary]`` (psycopg 3), so rewrite the scheme for the engine only.
    """
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


engine = create_engine(_sqlalchemy_url(DATABASE_URL), pool_pre_ping=True)


@app.get("/health")
def health() -> dict:
    """Liveness + DB connectivity probe."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as exc:  # noqa: BLE001 - report the failure in the body
        db_status = f"error: {exc.__class__.__name__}"
    return {"status": "ok", "db": db_status}
