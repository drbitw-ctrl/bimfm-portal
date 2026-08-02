from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common import utc_now


class TaskWorkSession(Base):
    """A freelancer's timed work interval against one portal task.

    Snapshot fields keep the record understandable even if an old task or
    project is later removed. A stopped session is also mirrored into a
    ``DailyTask`` row so existing DTR and utilization reporting continue to use
    one trusted source of actual minutes.
    """

    __tablename__ = "task_work_sessions"
    __table_args__ = (
        Index("ix_work_sessions_freelancer_status", "freelancer_id", "status"),
        Index("ix_work_sessions_task_started", "portal_task_id", "started_at"),
        Index("ix_work_sessions_started_at", "started_at"),
        Index(
            "uq_work_sessions_one_active",
            "freelancer_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE' AND stopped_at IS NULL"),
            sqlite_where=text("status = 'ACTIVE' AND stopped_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    freelancer_id: Mapped[int] = mapped_column(
        ForeignKey("freelancers.id", ondelete="RESTRICT"), nullable=False
    )
    portal_task_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("portal_tasks.id", ondelete="SET NULL"), nullable=True
    )
    project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("portal_projects.id", ondelete="SET NULL"), nullable=True
    )
    daily_task_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("daily_tasks.id", ondelete="SET NULL"), nullable=True
    )
    project_code: Mapped[str] = mapped_column(String(120), nullable=False)
    project_name: Mapped[str] = mapped_column(String(300), nullable=False)
    task_title: Mapped[str] = mapped_column(String(300), nullable=False)
    discipline: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    stopped_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )


class TaskReminder(Base):
    """Email-style task reminder delivered to one freelancer."""

    __tablename__ = "task_reminders"
    __table_args__ = (
        Index("ix_task_reminders_recipient_created", "freelancer_id", "created_at"),
        Index("ix_task_reminders_unread", "freelancer_id", "read_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    freelancer_id: Mapped[int] = mapped_column(
        ForeignKey("freelancers.id", ondelete="RESTRICT"), nullable=False
    )
    portal_task_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("portal_tasks.id", ondelete="SET NULL"), nullable=True
    )
    sender_admin_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("hr_admin_accounts.id", ondelete="SET NULL"), nullable=True
    )
    subject: Mapped[str] = mapped_column(String(240), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    recipient_email: Mapped[Optional[str]] = mapped_column(String(320), nullable=True)
    email_attempted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    email_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    email_sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    email_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
