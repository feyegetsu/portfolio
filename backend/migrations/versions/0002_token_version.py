"""SEC-002: версия токена у пользователя и запрет переиспользования id в SQLite.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ("users", "leads", "bookings", "orders", "catalog")


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("token_version", sa.Integer(), server_default="0", nullable=False))
    if op.get_bind().dialect.name == "sqlite":
        # Без AUTOINCREMENT SQLite отдаёт новой строке id удалённой; таблицу приходится пересоздать
        for table in TABLES:
            with op.batch_alter_table(table, recreate="always", table_kwargs={"sqlite_autoincrement": True}):
                pass


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_column("token_version")
