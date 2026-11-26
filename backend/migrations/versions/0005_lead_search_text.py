"""BUG-009: поисковое поле заявки в нижнем регистре, чтобы поиск по кириллице не зависел от регистра в SQLite.

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("leads") as batch:
        batch.add_column(sa.Column("search_text", sa.Text(), server_default="", nullable=False))
    leads = sa.table("leads", sa.column("id", sa.Integer), sa.column("name", sa.String), sa.column("phone", sa.String),
                     sa.column("email", sa.String), sa.column("message", sa.Text), sa.column("search_text", sa.Text))
    conn = op.get_bind()
    rows = conn.execute(sa.select(leads.c.id, leads.c.name, leads.c.phone, leads.c.email, leads.c.message)).all()
    for lead_id, *parts in rows:
        text = " ".join(p for p in parts if p).casefold()  # как Lead.make_search_text
        conn.execute(leads.update().where(leads.c.id == lead_id).values(search_text=text))


def downgrade() -> None:
    with op.batch_alter_table("leads") as batch:
        batch.drop_column("search_text")
