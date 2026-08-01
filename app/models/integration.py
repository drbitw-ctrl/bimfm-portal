from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import DEFAULT_TIMEZONE
from app.database import Base
from app.models.common import utc_now

class ProjectSourceMember(Base):
    __tablename__ = "project_source_members"
    __table_args__ = (
        UniqueConstraint(
            "source_system",
            "normalized_member_name",
            name="uq_project_source_member_system_name",
        ),
        Index(
            "ix_project_source_members_freelancer",
            "freelancer_id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_system: Mapped[str] = mapped_column(
        String(80), nullable=False, default="BIMFM_TASK_MANAGER"
    )
    source_member_name: Mapped[str] = mapped_column(
        String(200), nullable=False
    )
    normalized_member_name: Mapped[str] = mapped_column(
        String(200), nullable=False
    )
    freelancer_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("freelancers.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    active_task_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

class ProjectSyncRun(Base):
    __tablename__ = "project_sync_runs"
    __table_args__ = (
        Index(
            "ix_project_sync_runs_source_completed",
            "source_system",
            "completed_at_utc",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_system: Mapped[str] = mapped_column(String(80), nullable=False)
    source_database_label: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True
    )
    started_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at_utc: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="RUNNING"
    )
    received_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    active_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    inactive_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    mapped_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    unmapped_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    request_ip: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

class SyncedProjectTask(Base):
    __tablename__ = "synced_project_tasks"
    __table_args__ = (
        UniqueConstraint(
            "source_system",
            "source_project_id",
            name="uq_synced_project_task_source_id",
        ),
        Index(
            "ix_synced_project_tasks_freelancer_active",
            "freelancer_id",
            "is_active",
        ),
        Index(
            "ix_synced_project_tasks_member",
            "source_system",
            "normalized_member_name",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_system: Mapped[str] = mapped_column(
        String(80), nullable=False, default="BIMFM_TASK_MANAGER"
    )
    source_project_id: Mapped[str] = mapped_column(
        String(120), nullable=False
    )
    freelancer_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("freelancers.id", ondelete="SET NULL"), nullable=True
    )
    source_member_name: Mapped[str] = mapped_column(
        String(200), nullable=False
    )
    normalized_member_name: Mapped[str] = mapped_column(
        String(200), nullable=False
    )
    project_code: Mapped[str] = mapped_column(String(200), nullable=False)
    project_name: Mapped[Optional[str]] = mapped_column(
        String(300), nullable=True
    )
    deadline: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    project_status: Mapped[Optional[str]] = mapped_column(
        String(80), nullable=True
    )
    engineer: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True
    )
    priority: Mapped[Optional[str]] = mapped_column(
        String(80), nullable=True
    )
    discipline: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    progress: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    task_description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    source_updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    payload_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )
    last_sync_run_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("project_sync_runs.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
