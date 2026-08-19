"""Add optional freelancer bank details for finance review.

Revision ID: 20260819_0018
Revises: 20260806_0017
Create Date: 2026-08-19

This migration is additive only. Existing freelancer, attendance, DTR, leave,
overtime, project, and payroll records are not modified.
"""
from alembic import op
import sqlalchemy as sa

revision = "20260819_0018"
down_revision = "20260806_0017"
branch_labels = None
depends_on = None


def _column_names() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns("freelancers")}


def upgrade() -> None:
    columns = _column_names()
    with op.batch_alter_table("freelancers") as batch:
        if "bank_account_name" not in columns:
            batch.add_column(sa.Column("bank_account_name", sa.String(length=200), nullable=True))
        if "bank_account_number" not in columns:
            batch.add_column(sa.Column("bank_account_number", sa.String(length=120), nullable=True))
        if "bank_name" not in columns:
            batch.add_column(sa.Column("bank_name", sa.String(length=200), nullable=True))
        if "bank_swift_code" not in columns:
            batch.add_column(sa.Column("bank_swift_code", sa.String(length=50), nullable=True))
        if "bank_branch_address" not in columns:
            batch.add_column(sa.Column("bank_branch_address", sa.Text(), nullable=True))


def downgrade() -> None:
    columns = _column_names()
    with op.batch_alter_table("freelancers") as batch:
        for name in (
            "bank_branch_address",
            "bank_swift_code",
            "bank_name",
            "bank_account_number",
            "bank_account_name",
        ):
            if name in columns:
                batch.drop_column(name)
