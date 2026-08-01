from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import DEFAULT_TIMEZONE
from app.database import Base
from app.models.common import utc_now

class DailyTask(Base):
    __tablename__ = "daily_tasks"
    __table_args__ = (
        Index("ix_daily_tasks_freelancer_date", "freelancer_id", "task_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    freelancer_id: Mapped[int] = mapped_column(
        ForeignKey("freelancers.id", ondelete="RESTRICT"), nullable=False
    )
    synced_project_task_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("synced_project_tasks.id", ondelete="SET NULL"), nullable=True
    )
    task_date: Mapped[date] = mapped_column(Date, nullable=False)
    project_code: Mapped[str] = mapped_column(String(80), nullable=False)
    project_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    discipline: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    task_description: Mapped[str] = mapped_column(Text, nullable=False)
    accomplishment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    task_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="COMPLETED"
    )
    minutes_spent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_percentage: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

class TaskMonthReview(Base):
    __tablename__ = "task_month_reviews"
    __table_args__ = (
        UniqueConstraint(
            "freelancer_id", "month_key", name="uq_task_review_freelancer_month"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    freelancer_id: Mapped[int] = mapped_column(
        ForeignKey("freelancers.id", ondelete="RESTRICT"), nullable=False
    )
    month_key: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="REVIEWED"
    )
    reviewed_by_admin_id: Mapped[int] = mapped_column(
        ForeignKey("hr_admin_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    review_reason: Mapped[str] = mapped_column(Text, nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
