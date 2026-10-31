"""SQLAlchemy ORM models."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from database import Base


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String, nullable=False)
    cloned_at = Column(DateTime(timezone=True), nullable=True)
    structure_summary = Column(JSONB, nullable=True)
    # Async job state (pending -> running -> completed | failed)
    status = Column(String, nullable=False, default="pending", server_default="pending")
    error = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class File(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    repo_id = Column(
        Integer,
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    path = Column(String, nullable=False)
    language = Column(String, nullable=True)
    symbols = Column(JSONB, nullable=True)
