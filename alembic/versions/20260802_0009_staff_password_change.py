"""Add forced password-change flag for staff accounts.

Revision ID: 20260802_0009
Revises: 20260802_0008
Create Date: 2026-08-02
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20260802_0009"
down_revision = "20260802_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("hr_admin_accounts")}
    if "must_change_password" not in columns:
        op.add_column(
            "hr_admin_accounts",
            sa.Column(
                "must_change_password",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("hr_admin_accounts")}
    if "must_change_password" in columns:
        op.drop_column("hr_admin_accounts", "must_change_password")
