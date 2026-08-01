from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import DEFAULT_TIMEZONE
from app.database import Base
from app.models.common import utc_now

class AttendanceEvent(Base):
    __tablename__ = "attendance_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('TIME_IN', 'TIME_OUT')",
            name="ck_attendance_event_type",
        ),
        Index(
            "ix_attendance_events_freelancer_date",
            "freelancer_id",
            "attendance_date",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    freelancer_id: Mapped[int] = mapped_column(
        ForeignKey("freelancers.id", ondelete="RESTRICT"), nullable=False
    )
    account_id: Mapped[int] = mapped_column(
        ForeignKey("freelancer_accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False)
    timezone_name: Mapped[str] = mapped_column(
        String(80), nullable=False, default=DEFAULT_TIMEZONE
    )
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )
    source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="FREELANCER_PORTAL"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

class DailyAttendance(Base):
    __tablename__ = "daily_attendance"
    __table_args__ = (
        UniqueConstraint(
            "freelancer_id",
            "attendance_date",
            name="uq_daily_attendance_freelancer_date",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    freelancer_id: Mapped[int] = mapped_column(
        ForeignKey("freelancers.id", ondelete="RESTRICT"), nullable=False
    )
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False)
    time_in_utc: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    time_out_utc: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    break_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=60
    )
    rendered_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    late_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    undertime_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    overtime_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="PENDING"
    )
    review_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="UNREVIEWED"
    )
    is_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

class AttendanceCorrection(Base):
    __tablename__ = "attendance_corrections"
    __table_args__ = (
        Index(
            "ix_attendance_corrections_freelancer_date",
            "freelancer_id",
            "attendance_date",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    daily_attendance_id: Mapped[int] = mapped_column(
        ForeignKey("daily_attendance.id", ondelete="RESTRICT"), nullable=False
    )
    freelancer_id: Mapped[int] = mapped_column(
        ForeignKey("freelancers.id", ondelete="RESTRICT"), nullable=False
    )
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False)
    original_time_in_utc: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    original_time_out_utc: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    corrected_time_in_utc: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    corrected_time_out_utc: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    corrected_by_admin_id: Mapped[int] = mapped_column(
        ForeignKey("hr_admin_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

class AttendanceMonthLock(Base):
    __tablename__ = "attendance_month_locks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    month_key: Mapped[str] = mapped_column(
        String(7), unique=True, nullable=False, index=True
    )
    is_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    locked_by_admin_id: Mapped[int] = mapped_column(
        ForeignKey("hr_admin_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    locked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    lock_reason: Mapped[str] = mapped_column(Text, nullable=False)
    unlocked_by_admin_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("hr_admin_accounts.id", ondelete="RESTRICT"), nullable=True
    )
    unlocked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    unlock_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

class WorkSchedule(Base):
    __tablename__ = "work_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    timezone_name: Mapped[str] = mapped_column(
        String(80), nullable=False, default=DEFAULT_TIMEZONE
    )
    start_time_text: Mapped[str] = mapped_column(
        String(5), nullable=False, default="09:00"
    )
    end_time_text: Mapped[str] = mapped_column(
        String(5), nullable=False, default="18:00"
    )
    grace_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=15
    )
    break_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=60
    )
    break_trigger_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=300
    )
    monday: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    tuesday: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    wednesday: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    thursday: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    friday: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    saturday: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sunday: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_by_admin_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("hr_admin_accounts.id", ondelete="RESTRICT"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

class AttendanceCalculation(Base):
    __tablename__ = "attendance_calculations"
    __table_args__ = (
        UniqueConstraint(
            "daily_attendance_id",
            name="uq_attendance_calculation_daily_attendance",
        ),
        Index(
            "ix_attendance_calculations_freelancer_date",
            "freelancer_id",
            "attendance_date",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    daily_attendance_id: Mapped[int] = mapped_column(
        ForeignKey("daily_attendance.id", ondelete="CASCADE"), nullable=False
    )
    freelancer_id: Mapped[int] = mapped_column(
        ForeignKey("freelancers.id", ondelete="RESTRICT"), nullable=False
    )
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False)
    schedule_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("work_schedules.id", ondelete="SET NULL"), nullable=True
    )
    schedule_name: Mapped[str] = mapped_column(String(120), nullable=False)
    scheduled_start_text: Mapped[str] = mapped_column(String(5), nullable=False)
    scheduled_end_text: Mapped[str] = mapped_column(String(5), nullable=False)
    grace_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    scheduled_break_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    applied_break_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    is_workday: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    gross_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rendered_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    late_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    undertime_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    overtime_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    calculation_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="INCOMPLETE"
    )
    calculation_source: Mapped[str] = mapped_column(
        String(40), nullable=False, default="AUTOMATIC"
    )
    calculated_by_admin_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("hr_admin_accounts.id", ondelete="RESTRICT"), nullable=True
    )
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
