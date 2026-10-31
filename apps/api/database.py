"""SQLAlchemy engine, session factory, and declarative base."""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config import settings


def _sqlalchemy_url(url: str) -> str:
    """Point SQLAlchemy at the psycopg (v3) driver.

    ``.env.example`` uses a driver-less ``postgresql://`` URL, but SQLAlchemy
    defaults that scheme to psycopg2. We install ``psycopg[binary]`` (psycopg 3),
    so rewrite the scheme for the engine only.
    """
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


engine = create_engine(_sqlalchemy_url(settings.database_url), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
