"""Add timed work sessions and task reminders.

Revision ID: 20260802_0008
Revises: 20260802_0007
Create Date: 2026-08-02
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20260802_0008"
down_revision = "20260802_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    tables = set(inspector.get_table_names())

    if "task_work_sessions" not in tables:
        op.create_table(
            "task_work_sessions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("freelancer_id", sa.Integer(), sa.ForeignKey("freelancers.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("portal_task_id", sa.Integer(), sa.ForeignKey("portal_tasks.id", ondelete="SET NULL"), nullable=True),
            sa.Column("project_id", sa.Integer(), sa.ForeignKey("portal_projects.id", ondelete="SET NULL"), nullable=True),
            sa.Column("daily_task_id", sa.Integer(), sa.ForeignKey("daily_tasks.id", ondelete="SET NULL"), nullable=True),
            sa.Column("project_code", sa.String(length=120), nullable=False),
            sa.Column("project_name", sa.String(length=300), nullable=False),
            sa.Column("task_title", sa.String(length=300), nullable=False),
            sa.Column("discipline", sa.String(length=100), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="ACTIVE"),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_work_sessions_freelancer_status", "task_work_sessions", ["freelancer_id", "status"])
        op.create_index("ix_work_sessions_task_started", "task_work_sessions", ["portal_task_id", "started_at"])
        op.create_index("ix_work_sessions_started_at", "task_work_sessions", ["started_at"])
        op.create_index(
            "uq_work_sessions_one_active",
            "task_work_sessions",
            ["freelancer_id"],
            unique=True,
            postgresql_where=sa.text("status = 'ACTIVE' AND stopped_at IS NULL"),
            sqlite_where=sa.text("status = 'ACTIVE' AND stopped_at IS NULL"),
        )

    inspector = inspect(op.get_bind())
    if "task_reminders" not in set(inspector.get_table_names()):
        op.create_table(
            "task_reminders",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("freelancer_id", sa.Integer(), sa.ForeignKey("freelancers.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("portal_task_id", sa.Integer(), sa.ForeignKey("portal_tasks.id", ondelete="SET NULL"), nullable=True),
            sa.Column("sender_admin_id", sa.Integer(), sa.ForeignKey("hr_admin_accounts.id", ondelete="SET NULL"), nullable=True),
            sa.Column("subject", sa.String(length=240), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("recipient_email", sa.String(length=320), nullable=True),
            sa.Column("email_attempted", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("email_sent", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("email_sent_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("email_error", sa.Text(), nullable=True),
            sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_task_reminders_recipient_created", "task_reminders", ["freelancer_id", "created_at"])
        op.create_index("ix_task_reminders_unread", "task_reminders", ["freelancer_id", "read_at"])


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "task_reminders" in tables:
        op.drop_index("ix_task_reminders_unread", table_name="task_reminders")
        op.drop_index("ix_task_reminders_recipient_created", table_name="task_reminders")
        op.drop_table("task_reminders")
    inspector = inspect(op.get_bind())
    if "task_work_sessions" in set(inspector.get_table_names()):
        op.drop_index("uq_work_sessions_one_active", table_name="task_work_sessions")
        op.drop_index("ix_work_sessions_started_at", table_name="task_work_sessions")
        op.drop_index("ix_work_sessions_task_started", table_name="task_work_sessions")
        op.drop_index("ix_work_sessions_freelancer_status", table_name="task_work_sessions")
        op.drop_table("task_work_sessions")
