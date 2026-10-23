"""Kategoriyaga tavsif ustunini qo‘shadi.

Revision ID: 20261023_0002
Oldingi migratsiya: 20261023_0001
Yaratilgan sana: 2026-10-23
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261023_0002"
down_revision: str | None = "20261023_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Kategoriya tavsifini qo‘shadi va nom uzunligini yangilaydi."""
    with op.batch_alter_table("categories") as batch_op:
        batch_op.add_column(sa.Column("description", sa.Text(), nullable=True))
        batch_op.alter_column(
            "name",
            existing_type=sa.String(length=120),
            type_=sa.String(length=100),
            existing_nullable=False,
        )


def downgrade() -> None:
    """O‘zgarishlarni orqaga qaytaradi."""
    with op.batch_alter_table("categories") as batch_op:
        batch_op.drop_column("description")
        batch_op.alter_column(
            "name",
            existing_type=sa.String(length=100),
            type_=sa.String(length=120),
            existing_nullable=False,
        )
