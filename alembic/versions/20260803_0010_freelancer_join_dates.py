"""Add freelancer join dates and backfill the current team roster.

Revision ID: 20260803_0010
Revises: 20260802_0009
Create Date: 2026-08-03
"""
from __future__ import annotations

from datetime import date

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20260803_0010"
down_revision = "20260802_0009"
branch_labels = None
depends_on = None

_JOIN_DATES = {
    "alexsandria santos": date(2026, 6, 8),
    "carlo ninoy nilo": date(2025, 7, 21),
    "gabrielle gameng": date(2025, 4, 7),
    "jonica jomadiao": date(2025, 8, 12),
    "kaizer macatiag": date(2026, 3, 16),
    "lander samson": date(2025, 11, 24),
    "raymond navarro": date(2025, 7, 1),
}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("freelancers")}
    if "join_date" not in columns:
        op.add_column("freelancers", sa.Column("join_date", sa.Date(), nullable=True))

    update_join_date = sa.text(
        "UPDATE freelancers SET join_date = :join_date "
        "WHERE lower(trim(full_name)) = :full_name AND join_date IS NULL"
    )
    for full_name, join_date in _JOIN_DATES.items():
        bind.execute(update_join_date, {"join_date": join_date, "full_name": full_name})

    bind.execute(
        sa.text(
            "UPDATE freelancers SET is_active = :inactive "
            "WHERE lower(trim(full_name)) = :full_name"
        ),
        {"inactive": False, "full_name": "raymond navarro"},
    )
    bind.execute(
        sa.text(
            "UPDATE freelancer_accounts SET is_active = :inactive "
            "WHERE freelancer_id IN ("
            "SELECT id FROM freelancers WHERE lower(trim(full_name)) = :full_name"
            ")"
        ),
        {"inactive": False, "full_name": "raymond navarro"},
    )


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("freelancers")}
    if "join_date" in columns:
        op.drop_column("freelancers", "join_date")
