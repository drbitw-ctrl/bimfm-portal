"""Add HR policy toggle for freelancer project-engineer visibility.

Revision ID: 20260802_0007
Revises: 20260801_0006
Create Date: 2026-08-02
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20260802_0007"
down_revision = "20260801_0006"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str]:
    return {
        column["name"]
        for column in inspect(op.get_bind()).get_columns(table_name)
    }


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    if "hr_policies" not in inspector.get_table_names():
        return
    if "show_project_engineer_to_freelancers" in _columns("hr_policies"):
        return
    with op.batch_alter_table("hr_policies") as batch_op:
        batch_op.add_column(
            sa.Column(
                "show_project_engineer_to_freelancers",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    if "hr_policies" not in inspector.get_table_names():
        return
    if "show_project_engineer_to_freelancers" not in _columns("hr_policies"):
        return
    with op.batch_alter_table("hr_policies") as batch_op:
        batch_op.drop_column("show_project_engineer_to_freelancers")
