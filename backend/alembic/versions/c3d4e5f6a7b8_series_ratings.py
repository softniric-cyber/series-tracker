"""series_ratings: puntuación 1-5 del usuario por serie

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-18 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "series_ratings",
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("series_tmdb_id", sa.Integer(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        # La baja de cuenta (RGPD) debe llevarse también las puntuaciones.
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["series_tmdb_id"], ["series.tmdb_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "series_tmdb_id"),
        sa.CheckConstraint("score BETWEEN 1 AND 5", name="ck_series_ratings_score"),
    )


def downgrade() -> None:
    op.drop_table("series_ratings")
