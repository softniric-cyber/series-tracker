"""episodes: índice compuesto (series_tmdb_id, air_date)

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-15 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Acelera el calendario (rango de air_date por series seguidas) y el cálculo
    # de progreso, que filtran por (series_tmdb_id, air_date).
    op.create_index(
        "ix_episodes_series_air_date",
        "episodes",
        ["series_tmdb_id", "air_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_episodes_series_air_date", table_name="episodes")
