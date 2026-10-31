"""Repo Séance API — FastAPI entry point."""

import sentry_sdk
from config import settings
from database import engine
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ghosttrace.router import router as ghosttrace_router
from routers import agent
from routers import history
from routers import repos
from sqlalchemy import text

if settings.sentry_dsn and settings.sentry_dsn.strip():
    sentry_sdk.init(
        dsn=settings.sentry_dsn.strip(),
        traces_sample_rate=1.0,
        send_default_pii=False,
        include_local_variables=False,
    )

app = FastAPI(
    title="Repo Séance API — Occult Code Forensics",
    description="The digital necromancer gateway for git codebases. Summon dormant commits, interrogate repository ghosts, and enforce deterministic shell safety via GhostTrace.",
    version="0.3.0",
)

# Allow the Next.js dev server and external tunnels to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(repos.router)
app.include_router(history.router)
app.include_router(agent.router)
app.include_router(ghosttrace_router)


@app.get("/")
def root() -> dict:
    """The gateway to the digital underworld."""
    return {
        "realm": "Repo Séance",
        "tagline": "Summon the spirit of any git repository.",
        "presence": "A dormant spirit stirs in the vector memory.",
        "status": "haunted",
        "ascii": "  .-.\n ( o o )\n  | O |\n",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "repos": "/repos",
            "ghosttrace_ws": "/ws/ghosttrace",
        },
    }


@app.get("/health")
def health() -> dict:
    """Liveness + DB connectivity probe with ambient occult telemetry."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as exc:  # noqa: BLE001 - report the failure in the body
        db_status = f"error: {exc.__class__.__name__}"
    return {
        "status": "haunted" if db_status == "connected" else "severed",
        "db": db_status,
        "presence": "active" if db_status == "connected" else "dormant",
    }
