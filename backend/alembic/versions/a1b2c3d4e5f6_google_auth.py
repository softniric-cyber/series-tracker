"""google auth: password_hash nullable + google_sub

Revision ID: a1b2c3d4e5f6
Revises: 5f6a776329d1
Create Date: 2026-07-12 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "5f6a776329d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Los usuarios que solo se autentican con Google no tienen contraseña.
    op.alter_column("users", "password_hash", existing_type=sa.String(), nullable=True)
    # `sub` estable de Google para vincular/identificar la cuenta.
    op.add_column("users", sa.Column("google_sub", sa.String(), nullable=True))
    op.create_unique_constraint("uq_users_google_sub", "users", ["google_sub"])


def downgrade() -> None:
    op.drop_constraint("uq_users_google_sub", "users", type_="unique")
    op.drop_column("users", "google_sub")
    op.alter_column("users", "password_hash", existing_type=sa.String(), nullable=False)
