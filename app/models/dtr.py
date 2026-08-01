from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import DEFAULT_TIMEZONE
from app.database import Base
from app.models.common import utc_now

class MonthlyDTR(Base):
    __tablename__ = "monthly_dtr"
    __table_args__ = (
        UniqueConstraint(
            "freelancer_id",
            "month_key",
            name="uq_monthly_dtr_freelancer_month",
        ),
        Index("ix_monthly_dtr_month", "month_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    freelancer_id: Mapped[int] = mapped_column(
        ForeignKey("freelancers.id", ondelete="RESTRICT"), nullable=False
    )
    month_key: Mapped[str] = mapped_column(String(7), nullable=False)
    schedule_name: Mapped[str] = mapped_column(String(120), nullable=False)
    scheduled_start_text: Mapped[str] = mapped_column(String(5), nullable=False)
    scheduled_end_text: Mapped[str] = mapped_column(String(5), nullable=False)
    timezone_name: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="DRAFT"
    )

    calendar_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    scheduled_workdays: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    present_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    late_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    absent_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    leave_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    holiday_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rest_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    incomplete_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    scheduled_future_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    rendered_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    late_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    undertime_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    potential_overtime_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    approved_overtime_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    comp_leave_earned_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    comp_leave_used_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    comp_leave_opening_balance_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    comp_leave_closing_balance_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    daily_task_entries: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    daily_task_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    task_missing_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    task_variance_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    task_review_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="UNREVIEWED"
    )
    pending_overtime_claims: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    pending_leave_requests: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    generated_by_admin_id: Mapped[int] = mapped_column(
        ForeignKey("hr_admin_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    generation_reason: Mapped[str] = mapped_column(Text, nullable=False)

    reviewed_by_admin_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("hr_admin_accounts.id", ondelete="RESTRICT"), nullable=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    review_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    finalized_by_admin_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("hr_admin_accounts.id", ondelete="RESTRICT"), nullable=True
    )
    finalized_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finalization_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

class DTRDailyLine(Base):
    __tablename__ = "dtr_daily_lines"
    __table_args__ = (
        UniqueConstraint(
            "monthly_dtr_id",
            "attendance_date",
            name="uq_dtr_daily_line_dtr_date",
        ),
        Index(
            "ix_dtr_daily_lines_freelancer_date",
            "freelancer_id",
            "attendance_date",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    monthly_dtr_id: Mapped[int] = mapped_column(
        ForeignKey("monthly_dtr.id", ondelete="CASCADE"), nullable=False
    )
    freelancer_id: Mapped[int] = mapped_column(
        ForeignKey("freelancers.id", ondelete="RESTRICT"), nullable=False
    )
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False)
    day_name: Mapped[str] = mapped_column(String(12), nullable=False)
    day_type: Mapped[str] = mapped_column(String(30), nullable=False)
    attendance_status: Mapped[str] = mapped_column(String(40), nullable=False)
    scheduled_start_text: Mapped[str] = mapped_column(String(5), nullable=False)
    scheduled_end_text: Mapped[str] = mapped_column(String(5), nullable=False)
    time_in_utc: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    time_out_utc: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rendered_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    late_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    undertime_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    potential_overtime_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    approved_overtime_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    comp_leave_earned_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    comp_leave_used_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    task_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    task_entry_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    task_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    task_variance_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    attendance_review_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="UNREVIEWED"
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

class DTRTaskLine(Base):
    __tablename__ = "dtr_task_lines"
    __table_args__ = (
        Index("ix_dtr_task_line_dtr_date", "monthly_dtr_id", "task_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    monthly_dtr_id: Mapped[int] = mapped_column(
        ForeignKey("monthly_dtr.id", ondelete="CASCADE"), nullable=False
    )
    source_task_id: Mapped[int] = mapped_column(Integer, nullable=False)
    task_date: Mapped[date] = mapped_column(Date, nullable=False)
    project_code: Mapped[str] = mapped_column(String(80), nullable=False)
    project_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    discipline: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    task_description: Mapped[str] = mapped_column(Text, nullable=False)
    accomplishment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    task_status: Mapped[str] = mapped_column(String(30), nullable=False)
    minutes_spent: Mapped[int] = mapped_column(Integer, nullable=False)
    completion_percentage: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

class DTRCompLine(Base):
    __tablename__ = "dtr_comp_lines"
    __table_args__ = (
        Index("ix_dtr_comp_line_dtr_date", "monthly_dtr_id", "transaction_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    monthly_dtr_id: Mapped[int] = mapped_column(
        ForeignKey("monthly_dtr.id", ondelete="CASCADE"), nullable=False
    )
    source_transaction_id: Mapped[int] = mapped_column(Integer, nullable=False)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(30), nullable=False)
    amount_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

class DTRLeaveLine(Base):
    __tablename__ = "dtr_leave_lines"
    __table_args__ = (
        Index("ix_dtr_leave_line_dtr_date", "monthly_dtr_id", "leave_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    monthly_dtr_id: Mapped[int] = mapped_column(
        ForeignKey("monthly_dtr.id", ondelete="CASCADE"), nullable=False
    )
    source_leave_id: Mapped[int] = mapped_column(Integer, nullable=False)
    leave_date: Mapped[date] = mapped_column(Date, nullable=False)
    leave_type: Mapped[str] = mapped_column(String(60), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    comp_leave_minutes_used: Mapped[int] = mapped_column(Integer, nullable=False)
    is_paid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
