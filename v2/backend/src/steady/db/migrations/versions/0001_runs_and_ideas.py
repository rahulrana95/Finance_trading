"""Algo runs and the ideas they propose."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None


def upgrade() -> None:
    op.create_table(
        "runs",
        sa.Column("seq", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("id", sa.String(32), nullable=False, unique=True),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("summary", sa.String(200), nullable=False),
        sa.Column("steps", sa.JSON, nullable=False),
    )
    op.create_index("ix_runs_status", "runs", ["status"])
    op.create_table(
        "ideas",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("body", sa.JSON, nullable=False),
    )
    op.create_index("ix_ideas_symbol", "ideas", ["symbol"])
    op.create_index("ix_ideas_status", "ideas", ["status"])


def downgrade() -> None:
    op.drop_table("ideas")
    op.drop_table("runs")
