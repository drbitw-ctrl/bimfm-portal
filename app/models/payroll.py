from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import DEFAULT_TIMEZONE
from app.database import Base
from app.models.common import utc_now

class PayrollMonthSummary(Base):
    __tablename__ = "payroll_month_summary"
    __table_args__ = (
        UniqueConstraint("freelancer_id", "month_key", name="uq_payroll_summary_freelancer_month"),
        Index("ix_payroll_summary_month", "month_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    freelancer_id: Mapped[int] = mapped_column(ForeignKey("freelancers.id", ondelete="RESTRICT"), nullable=False)
    monthly_dtr_id: Mapped[int] = mapped_column(ForeignKey("monthly_dtr.id", ondelete="CASCADE"), nullable=False)
    month_key: Mapped[str] = mapped_column(String(7), nullable=False)
    regular_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    approved_overtime_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    potential_overtime_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    paid_leave_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unpaid_leave_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    comp_leave_used_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    opening_balance_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    earned_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    closing_balance_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payroll_review_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attendance_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tasks_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    overtime_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    leave_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    comp_ledger_balanced: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    payroll_status: Mapped[str] = mapped_column(String(30), nullable=False, default="NOT_READY")
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
