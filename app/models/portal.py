from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import DEFAULT_TIMEZONE
from app.database import Base
from app.models.common import utc_now

class PortalProject(Base):
    __tablename__ = "portal_projects"
    __table_args__ = (
        UniqueConstraint("project_code", name="uq_portal_project_code"),
        Index("ix_portal_projects_status_deadline", "status", "deadline"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_code: Mapped[str] = mapped_column(String(120), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="ACTIVE")
    priority: Mapped[str] = mapped_column(String(40), nullable=False, default="NORMAL")
    discipline: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    deadline: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    completion_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    supervisor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("hr_admin_accounts.id", ondelete="SET NULL"), nullable=True)
    legacy_source_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

class PortalProjectMember(Base):
    __tablename__ = "portal_project_members"
    __table_args__ = (UniqueConstraint("project_id", "freelancer_id", name="uq_portal_project_member"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("portal_projects.id", ondelete="CASCADE"), nullable=False)
    freelancer_id: Mapped[int] = mapped_column(ForeignKey("freelancers.id", ondelete="CASCADE"), nullable=False)
    member_role: Mapped[str] = mapped_column(String(40), nullable=False, default="MEMBER")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

class PortalTask(Base):
    __tablename__ = "portal_tasks"
    __table_args__ = (
        Index("ix_portal_tasks_project_status", "project_id", "status"),
        Index("ix_portal_tasks_due_status", "due_date", "status"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("portal_projects.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="NOT_STARTED")
    priority: Mapped[str] = mapped_column(String(40), nullable=False, default="NORMAL")
    discipline: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    legacy_source_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    created_by_admin_id: Mapped[Optional[int]] = mapped_column(ForeignKey("hr_admin_accounts.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

class PortalTaskAssignment(Base):
    __tablename__ = "portal_task_assignments"
    __table_args__ = (UniqueConstraint("task_id", "freelancer_id", name="uq_portal_task_assignment"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("portal_tasks.id", ondelete="CASCADE"), nullable=False)
    freelancer_id: Mapped[int] = mapped_column(ForeignKey("freelancers.id", ondelete="CASCADE"), nullable=False)
    assignment_role: Mapped[str] = mapped_column(String(40), nullable=False, default="ASSIGNEE")
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

class PortalTaskUpdate(Base):
    __tablename__ = "portal_task_updates"
    __table_args__ = (Index("ix_portal_task_updates_task_created", "task_id", "created_at"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("portal_tasks.id", ondelete="CASCADE"), nullable=False)
    freelancer_id: Mapped[Optional[int]] = mapped_column(ForeignKey("freelancers.id", ondelete="SET NULL"), nullable=True)
    admin_id: Mapped[Optional[int]] = mapped_column(ForeignKey("hr_admin_accounts.id", ondelete="SET NULL"), nullable=True)
    progress: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
