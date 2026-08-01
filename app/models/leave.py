from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import DEFAULT_TIMEZONE
from app.database import Base
from app.models.common import utc_now

class Holiday(Base):
    __tablename__ = "holidays"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    holiday_date: Mapped[date] = mapped_column(
        Date, unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    holiday_type: Mapped[str] = mapped_column(
        String(40), nullable=False, default="COMPANY"
    )
    is_paid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by_admin_id: Mapped[int] = mapped_column(
        ForeignKey("hr_admin_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

class LeaveRecord(Base):
    __tablename__ = "leave_records"
    __table_args__ = (
        UniqueConstraint(
            "freelancer_id",
            "leave_date",
            name="uq_leave_record_freelancer_date",
        ),
        Index("ix_leave_records_date", "leave_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    freelancer_id: Mapped[int] = mapped_column(
        ForeignKey("freelancers.id", ondelete="RESTRICT"), nullable=False
    )
    leave_date: Mapped[date] = mapped_column(Date, nullable=False)
    leave_type: Mapped[str] = mapped_column(
        String(60), nullable=False, default="APPROVED_LEAVE"
    )
    is_paid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="APPROVED"
    )
    duration_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=480
    )
    comp_leave_minutes_used: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    source_request_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approved_by_admin_id: Mapped[int] = mapped_column(
        ForeignKey("hr_admin_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

class LeaveRequest(Base):
    __tablename__ = "leave_requests"
    __table_args__ = (
        UniqueConstraint(
            "freelancer_id", "leave_date", name="uq_leave_request_freelancer_date"
        ),
        Index("ix_leave_request_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    freelancer_id: Mapped[int] = mapped_column(
        ForeignKey("freelancers.id", ondelete="RESTRICT"), nullable=False
    )
    leave_date: Mapped[date] = mapped_column(Date, nullable=False)
    leave_type: Mapped[str] = mapped_column(String(60), nullable=False)
    requested_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="PENDING"
    )
    approved_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    reviewed_by_admin_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("hr_admin_accounts.id", ondelete="RESTRICT"), nullable=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    review_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

class CompLeaveTransaction(Base):
    __tablename__ = "comp_leave_transactions"
    __table_args__ = (
        UniqueConstraint("source_key", name="uq_comp_leave_source_key"),
        Index("ix_comp_leave_freelancer_date", "freelancer_id", "transaction_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    freelancer_id: Mapped[int] = mapped_column(
        ForeignKey("freelancers.id", ondelete="RESTRICT"), nullable=False
    )
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(30), nullable=False)
    amount_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    source_key: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_admin_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("hr_admin_accounts.id", ondelete="RESTRICT"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

class MonthlyCompLeaveBalance(Base):
    __tablename__ = "monthly_comp_leave_balance"
    __table_args__ = (
        UniqueConstraint("freelancer_id", "month_key", name="uq_comp_balance_freelancer_month"),
        Index("ix_comp_balance_month", "month_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    freelancer_id: Mapped[int] = mapped_column(ForeignKey("freelancers.id", ondelete="RESTRICT"), nullable=False)
    month_key: Mapped[str] = mapped_column(String(7), nullable=False)
    opening_balance_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    earned_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    used_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    adjustment_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    closing_balance_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
