"""BUG-001: счётчик занятых мест на время, чтобы вместимость не превышалась при одновременных запросах.

Существующие брони переносятся в счётчик. Какие сайты считают места по занятию, а какие по заведению,
записано здесь снимком правил на момент миграции: будущие правки sites.py не должны менять её смысл.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PER_RESOURCE = ("fitness",)                  # места на каждом занятии
PER_VENUE = ("restaurant", "gastrobar", "bar")  # столы на всё заведение


def upgrade() -> None:
    counters = op.create_table(
        "slot_counters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("site", sa.String(40), nullable=False),
        sa.Column("resource_key", sa.String(100), nullable=False),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("taken", sa.Integer(), nullable=False),
        sa.UniqueConstraint("site", "resource_key", "starts_at", name="uq_slot_counters_slot"),
    )
    bookings = sa.table("bookings", sa.column("site", sa.String), sa.column("resource", sa.String),
                        sa.column("starts_at", sa.DateTime), sa.column("status", sa.String))
    active = bookings.c.status != "cancelled"
    conn = op.get_bind()
    rows = []
    # Места на занятии — по занятию, столы — по всему заведению (ключ пустой). Группировать по константе
    # PostgreSQL не умеет, поэтому пустой ключ подставляем уже в Python
    per_resource = (sa.select(bookings.c.site, bookings.c.resource, bookings.c.starts_at, sa.func.count())
                    .where(active, bookings.c.site.in_(PER_RESOURCE))
                    .group_by(bookings.c.site, bookings.c.resource, bookings.c.starts_at))
    per_venue = (sa.select(bookings.c.site, bookings.c.starts_at, sa.func.count())
                 .where(active, bookings.c.site.in_(PER_VENUE))
                 .group_by(bookings.c.site, bookings.c.starts_at))
    rows += [{"site": s, "resource_key": k, "starts_at": t, "taken": n} for s, k, t, n in conn.execute(per_resource)]
    rows += [{"site": s, "resource_key": "", "starts_at": t, "taken": n} for s, t, n in conn.execute(per_venue)]
    if rows:
        op.bulk_insert(counters, rows)


def downgrade() -> None:
    op.drop_table("slot_counters")
