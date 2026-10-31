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

app = FastAPI(title="Repo Séance API", version="0.2.0")

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

app.include_router(repos.router)
app.include_router(history.router)
app.include_router(agent.router)
app.include_router(ghosttrace_router)


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
