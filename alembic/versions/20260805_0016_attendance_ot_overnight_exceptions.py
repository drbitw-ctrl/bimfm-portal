"""Add attendance correction requests and overnight exception flags.

Revision ID: 20260805_0016
Revises: 20260804_0015
"""
from alembic import op
import sqlalchemy as sa
revision="20260805_0016"
down_revision="20260804_0015"
branch_labels=None
depends_on=None

def _has_column(bind, table, column):
    return any(c["name"] == column for c in sa.inspect(bind).get_columns(table))

def upgrade():
    bind=op.get_bind()
    additions = [
        ("daily_attendance", "missed_time_out_flag", sa.Column("missed_time_out_flag", sa.Boolean(), nullable=False, server_default=sa.false())),
        ("daily_attendance", "missed_work_order_stop_flag", sa.Column("missed_work_order_stop_flag", sa.Boolean(), nullable=False, server_default=sa.false())),
        ("daily_attendance", "overtime_unavailable", sa.Column("overtime_unavailable", sa.Boolean(), nullable=False, server_default=sa.false())),
        ("daily_attendance", "exception_flagged_at", sa.Column("exception_flagged_at", sa.DateTime(timezone=True), nullable=True)),
        ("task_work_sessions", "missed_stop_flag", sa.Column("missed_stop_flag", sa.Boolean(), nullable=False, server_default=sa.false())),
        ("task_work_sessions", "exception_flagged_at", sa.Column("exception_flagged_at", sa.DateTime(timezone=True), nullable=True)),
    ]
    for table, name, column in additions:
        if not _has_column(bind, table, name): op.add_column(table, column)
    if "attendance_correction_requests" not in sa.inspect(bind).get_table_names():
        op.create_table(
            "attendance_correction_requests",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("freelancer_id", sa.Integer(), sa.ForeignKey("freelancers.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("daily_attendance_id", sa.Integer(), sa.ForeignKey("daily_attendance.id", ondelete="SET NULL"), nullable=True),
            sa.Column("attendance_date", sa.Date(), nullable=False),
            sa.Column("requested_time_in_utc", sa.DateTime(timezone=True), nullable=True),
            sa.Column("requested_time_out_utc", sa.DateTime(timezone=True), nullable=True),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
            sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("reviewed_by_admin_id", sa.Integer(), sa.ForeignKey("hr_admin_accounts.id", ondelete="RESTRICT"), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("review_reason", sa.Text(), nullable=True),
        )
        op.create_index("ix_attendance_correction_requests_status", "attendance_correction_requests", ["status", "requested_at"])
        op.create_index("ix_attendance_correction_requests_member_date", "attendance_correction_requests", ["freelancer_id", "attendance_date"])

def downgrade():
    bind=op.get_bind()
    if "attendance_correction_requests" in sa.inspect(bind).get_table_names():
        op.drop_index("ix_attendance_correction_requests_member_date", table_name="attendance_correction_requests")
        op.drop_index("ix_attendance_correction_requests_status", table_name="attendance_correction_requests")
        op.drop_table("attendance_correction_requests")
    for table, name in [("task_work_sessions","exception_flagged_at"),("task_work_sessions","missed_stop_flag"),("daily_attendance","exception_flagged_at"),("daily_attendance","overtime_unavailable"),("daily_attendance","missed_work_order_stop_flag"),("daily_attendance","missed_time_out_flag")]:
        if _has_column(bind, table, name): op.drop_column(table,name)
