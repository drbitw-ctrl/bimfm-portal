from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import DEFAULT_TIMEZONE
from app.database import Base
from app.models.common import utc_now

class HRPolicy(Base):
    __tablename__ = "hr_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    standard_leave_day_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=480
    )
    overtime_minimum_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=30
    )
    overtime_rounding_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=15
    )
    overtime_to_comp_numerator: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )
    overtime_to_comp_denominator: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )
    max_approved_overtime_per_day: Mapped[int] = mapped_column(
        Integer, nullable=False, default=480
    )
    require_task_for_overtime: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    require_daily_task_for_dtr: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    task_variance_warning_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=60
    )
    allow_negative_comp_balance: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    show_project_engineer_to_freelancers: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
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
