"""Add optional task quality score for the editable task register.

Revision ID: 20260801_0005
Revises: 20260801_0004
Create Date: 2026-08-01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20260801_0005"
down_revision = "20260801_0004"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str]:
    return {column["name"] for column in inspect(op.get_bind()).get_columns(table_name)}


def upgrade() -> None:
    if "portal_tasks" not in inspect(op.get_bind()).get_table_names():
        return
    if "quality_score" in _columns("portal_tasks"):
        return
    with op.batch_alter_table("portal_tasks") as batch_op:
        batch_op.add_column(sa.Column("quality_score", sa.Integer(), nullable=True))


def downgrade() -> None:
    if "portal_tasks" not in inspect(op.get_bind()).get_table_names():
        return
    if "quality_score" not in _columns("portal_tasks"):
        return
    with op.batch_alter_table("portal_tasks") as batch_op:
        batch_op.drop_column("quality_score")
