"""create repositories and files tables

Revision ID: 0001
Revises:
Create Date: 2026-10-31
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "repositories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("cloned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("structure_summary", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "files",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("repo_id", sa.Integer(), nullable=False),
        sa.Column("path", sa.String(), nullable=False),
        sa.Column("language", sa.String(), nullable=True),
        sa.Column("symbols", postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(["repo_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_files_repo_id", "files", ["repo_id"])


def downgrade() -> None:
    op.drop_index("ix_files_repo_id", table_name="files")
    op.drop_table("files")
    op.drop_table("repositories")
