"""Link daily task reports to PostgreSQL-native portal tasks.

Revision ID: 20260801_0002
Revises: 20260731_0001
"""
from alembic import op
import sqlalchemy as sa

revision = "20260801_0002"
down_revision = "20260731_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("daily_tasks")}
    # The historical baseline creates tables from current model metadata. On a
    # completely fresh database the new column may therefore already exist.
    # Existing Release 20.6 databases do not have it and are upgraded here.
    if "portal_task_id" in columns:
        return

    with op.batch_alter_table("daily_tasks") as batch_op:
        batch_op.add_column(sa.Column("portal_task_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_daily_tasks_portal_task_id",
            "portal_tasks",
            ["portal_task_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_daily_tasks_portal_task_id",
            ["portal_task_id"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("daily_tasks")}
    if "portal_task_id" not in columns:
        return
    with op.batch_alter_table("daily_tasks") as batch_op:
        indexes = {item["name"] for item in sa.inspect(bind).get_indexes("daily_tasks")}
        if "ix_daily_tasks_portal_task_id" in indexes:
            batch_op.drop_index("ix_daily_tasks_portal_task_id")
        foreign_keys = {
            item.get("name")
            for item in sa.inspect(bind).get_foreign_keys("daily_tasks")
        }
        if "fk_daily_tasks_portal_task_id" in foreign_keys:
            batch_op.drop_constraint(
                "fk_daily_tasks_portal_task_id",
                type_="foreignkey",
            )
        batch_op.drop_column("portal_task_id")
