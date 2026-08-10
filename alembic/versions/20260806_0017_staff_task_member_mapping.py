"""Add optional task-member mapping for staff accounts.

Revision ID: 20260806_0017
Revises: 20260805_0016
"""
from alembic import op
import sqlalchemy as sa

revision = "20260806_0017"
down_revision = "20260805_0016"
branch_labels = None
depends_on = None


def _column_names() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns("hr_admin_accounts")}


def _constraint_names() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    names = {
        item.get("name")
        for item in inspector.get_unique_constraints("hr_admin_accounts")
        if item.get("name")
    }
    names.update(
        item.get("name")
        for item in inspector.get_foreign_keys("hr_admin_accounts")
        if item.get("name")
    )
    return names


def upgrade() -> None:
    columns = _column_names()
    constraints = _constraint_names()
    with op.batch_alter_table("hr_admin_accounts") as batch:
        if "task_freelancer_id" not in columns:
            batch.add_column(sa.Column("task_freelancer_id", sa.Integer(), nullable=True))
        if "uq_hr_admin_task_freelancer" not in constraints:
            batch.create_unique_constraint(
                "uq_hr_admin_task_freelancer",
                ["task_freelancer_id"],
            )
        if "fk_hr_admin_task_freelancer" not in constraints:
            batch.create_foreign_key(
                "fk_hr_admin_task_freelancer",
                "freelancers",
                ["task_freelancer_id"],
                ["id"],
                ondelete="SET NULL",
            )


def downgrade() -> None:
    constraints = _constraint_names()
    columns = _column_names()
    with op.batch_alter_table("hr_admin_accounts") as batch:
        if "fk_hr_admin_task_freelancer" in constraints:
            batch.drop_constraint("fk_hr_admin_task_freelancer", type_="foreignkey")
        if "uq_hr_admin_task_freelancer" in constraints:
            batch.drop_constraint("uq_hr_admin_task_freelancer", type_="unique")
        if "task_freelancer_id" in columns:
            batch.drop_column("task_freelancer_id")
