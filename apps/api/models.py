"""SQLAlchemy ORM models."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

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

    commits = relationship("Commit", back_populates="repo", cascade="all, delete-orphan")
    evidence = relationship("Evidence", back_populates="repo", cascade="all, delete-orphan")


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


class Commit(Base):
    __tablename__ = "commits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    repo_id = Column(
        Integer,
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    hash = Column(String, nullable=False, index=True)
    short_hash = Column(String, nullable=False)
    author = Column(String, nullable=False)
    author_email = Column(String, nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    message = Column(Text, nullable=False)
    files_changed = Column(JSONB, nullable=True)

    repo = relationship("Repository", back_populates="commits")


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True, autoincrement=True)
    repo_id = Column(
        Integer,
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # What this evidence is: "commit", "readme", or "file"
    source_type = Column(String, nullable=False)
    # Reference: commit hash, file path, etc.
    source_ref = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    # 768-dimensional embedding (nomic-embed-text)
    embedding = Column(Vector(768), nullable=True)

    repo = relationship("Repository", back_populates="evidence")
