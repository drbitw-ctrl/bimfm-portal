from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import DEFAULT_TIMEZONE
from app.database import Base
from app.models.common import utc_now

class OvertimeClaim(Base):
    __tablename__ = "overtime_claims"
    __table_args__ = (
        UniqueConstraint(
            "freelancer_id", "attendance_date", name="uq_ot_claim_freelancer_date"
        ),
        Index("ix_ot_claim_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    freelancer_id: Mapped[int] = mapped_column(
        ForeignKey("freelancers.id", ondelete="RESTRICT"), nullable=False
    )
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False)
    potential_minutes_snapshot: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    requested_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    work_description: Mapped[str] = mapped_column(Text, nullable=False)
    planned_start_utc: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    planned_end_utc: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_time_out_utc: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    claimed_time_out_utc: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_time_out_utc: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    missing_time_out_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    final_submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="PENDING"
    )
    approved_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    comp_leave_minutes_earned: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
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
