"""Results of the market-fall screener."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"


def upgrade() -> None:
    op.create_table(
        "screens",
        sa.Column("seq", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("id", sa.String(32), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("body", sa.JSON, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("screens")
