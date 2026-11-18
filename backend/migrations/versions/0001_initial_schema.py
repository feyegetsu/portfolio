"""Базовая схема: таблицы, которые раньше создавал create_all при старте.

Базы, созданные до появления миграций, app.migrate помечает этой ревизией (stamp) и обновляет дальше.

Revision ID: 0001
Revises:
Create Date: 2026-11-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(200), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("password_hash", sa.String(200), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("sites", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "leads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("site", sa.String(40), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("phone", sa.String(30), nullable=False),
        sa.Column("email", sa.String(200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_leads_site", "leads", ["site"])
    op.create_index("ix_leads_site_created", "leads", ["site", "created_at"])

    op.create_table(
        "bookings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("site", sa.String(40), nullable=False),
        sa.Column("resource", sa.String(100), nullable=False),
        sa.Column("service", sa.String(100), nullable=False),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("phone", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("slot_lock", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("slot_lock"),
    )
    op.create_index("ix_bookings_site", "bookings", ["site"])
    op.create_index("ix_bookings_starts_at", "bookings", ["starts_at"])

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("token", sa.String(32), nullable=False),
        sa.Column("site", sa.String(40), nullable=False),
        sa.Column("items", sa.JSON(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("phone", sa.String(30), nullable=False),
        sa.Column("address", sa.String(300), nullable=False),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_orders_site", "orders", ["site"])
    op.create_index("ix_orders_token", "orders", ["token"], unique=True)

    op.create_table(
        "catalog",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("site", sa.String(40), nullable=False),
        sa.Column("ref", sa.String(60), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(60), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("site", "ref", name="uq_catalog_site_ref"),
    )
    op.create_index("ix_catalog_site", "catalog", ["site"])


def downgrade() -> None:
    for table in ("catalog", "orders", "bookings", "leads", "users"):
        op.drop_table(table)
