"""add commits and evidence tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-31
"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "commits",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("repo_id", sa.Integer(), nullable=False),
        sa.Column("hash", sa.String(), nullable=False),
        sa.Column("short_hash", sa.String(), nullable=False),
        sa.Column("author", sa.String(), nullable=False),
        sa.Column("author_email", sa.String(), nullable=False),
        sa.Column("date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("files_changed", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["repo_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_commits_repo_id", "commits", ["repo_id"])
    op.create_index("ix_commits_hash", "commits", ["hash"])

    op.create_table(
        "evidence",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("repo_id", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("source_ref", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(768), nullable=True),
        sa.ForeignKeyConstraint(["repo_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evidence_repo_id", "evidence", ["repo_id"])


def downgrade() -> None:
    op.drop_index("ix_evidence_repo_id", table_name="evidence")
    op.drop_table("evidence")
    op.drop_index("ix_commits_hash", table_name="commits")
    op.drop_index("ix_commits_repo_id", table_name="commits")
    op.drop_table("commits")
