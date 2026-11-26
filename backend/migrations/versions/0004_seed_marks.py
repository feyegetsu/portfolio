"""BUG-003: отметки о залитых начальных данных, чтобы удалённый каталог не возвращался после перезапуска.

Сайты, у которых уже есть позиции каталога, сразу помечаются: их каталог заливался раньше.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    marks = op.create_table("seed_marks", sa.Column("key", sa.String(100), primary_key=True))
    catalog = sa.table("catalog", sa.column("site", sa.String))
    sites = op.get_bind().execute(sa.select(catalog.c.site).distinct()).scalars().all()
    if sites:
        op.bulk_insert(marks, [{"key": f"catalog:{s}"} for s in sites])


def downgrade() -> None:
    op.drop_table("seed_marks")
