from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import json
import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    ProjectSourceMember,
    ProjectSyncRun,
    SyncedProjectTask,
)


INACTIVE_PROJECT_STATUSES = {
    "completed",
    "complete",
    "closed",
    "cancelled",
    "canceled",
    "archived",
    "inactive",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_member_name(value: str) -> str:
    """Create a stable comparison value without changing the display name."""
    return re.sub(r"\s+", " ", value.strip()).casefold()


def task_status_is_active(status: Optional[str]) -> bool:
    normalized = (status or "").strip().casefold()
    return normalized not in INACTIVE_PROJECT_STATUSES


class ProjectTaskSyncItem(BaseModel):
    source_project_id: str = Field(min_length=1, max_length=120)
    source_member_name: str = Field(min_length=1, max_length=200)
    project_code: str = Field(min_length=1, max_length=200)
    project_name: Optional[str] = Field(default=None, max_length=300)
    deadline: Optional[date] = None
    status: Optional[str] = Field(default=None, max_length=80)
    engineer: Optional[str] = Field(default=None, max_length=200)
    priority: Optional[str] = Field(default=None, max_length=80)
    discipline: Optional[str] = Field(default=None, max_length=100)
    progress: int = Field(default=0, ge=0, le=100)
    task_description: Optional[str] = None
    source_updated_at: Optional[datetime] = None
    is_active: Optional[bool] = None

    @field_validator(
        "source_project_id",
        "source_member_name",
        "project_code",
        mode="before",
    )
    @classmethod
    def strip_required_text(cls, value):
        if value is None:
            return value
        return str(value).strip()

    @field_validator(
        "project_name",
        "status",
        "engineer",
        "priority",
        "discipline",
        "task_description",
        mode="before",
    )
    @classmethod
    def clean_optional_text(cls, value):
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None


class ProjectTaskSyncPayload(BaseModel):
    source_system: str = Field(
        default="BIMFM_TASK_MANAGER",
        min_length=1,
        max_length=80,
    )
    source_database_label: Optional[str] = Field(
        default="projects.db",
        max_length=200,
    )
    full_snapshot: bool = True
    sync_started_at_utc: Optional[datetime] = None
    tasks: list[ProjectTaskSyncItem] = Field(default_factory=list)

    @field_validator("source_system", mode="before")
    @classmethod
    def normalize_source_system(cls, value):
        return str(value or "BIMFM_TASK_MANAGER").strip().upper()


def _payload_hash(item: ProjectTaskSyncItem) -> str:
    payload = item.model_dump(mode="json")
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _ensure_source_member(
    database: Session,
    *,
    source_system: str,
    source_member_name: str,
    seen_at: datetime,
) -> ProjectSourceMember:
    normalized = normalize_member_name(source_member_name)
    source_member = database.scalar(
        select(ProjectSourceMember).where(
            ProjectSourceMember.source_system == source_system,
            ProjectSourceMember.normalized_member_name == normalized,
        )
    )

    if source_member is None:
        source_member = ProjectSourceMember(
            source_system=source_system,
            source_member_name=source_member_name.strip(),
            normalized_member_name=normalized,
            is_active=True,
            active_task_count=0,
            last_seen_at=seen_at,
        )
        database.add(source_member)
        database.flush()
    else:
        source_member.source_member_name = source_member_name.strip()
        source_member.is_active = True
        source_member.last_seen_at = seen_at

    return source_member


def apply_project_task_snapshot(
    database: Session,
    *,
    payload: ProjectTaskSyncPayload,
    request_ip: Optional[str],
) -> dict[str, object]:
    """Apply a read-only snapshot received from the project sync agent.

    The source SQLite file is never modified. This function only updates
    the HR-side synchronized copy.
    """
    started_at = payload.sync_started_at_utc or utc_now()
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)

    sync_run = ProjectSyncRun(
        source_system=payload.source_system,
        source_database_label=payload.source_database_label,
        started_at_utc=started_at,
        status="RUNNING",
        received_count=len(payload.tasks),
        request_ip=request_ip,
    )
    database.add(sync_run)
    database.flush()

    try:
        existing_tasks = {
            task.source_project_id: task
            for task in database.scalars(
                select(SyncedProjectTask).where(
                    SyncedProjectTask.source_system
                    == payload.source_system
                )
            ).all()
        }

        if payload.full_snapshot:
            for existing in existing_tasks.values():
                existing.is_active = False

        received_ids: set[str] = set()
        mapped_count = 0
        unmapped_count = 0
        active_count = 0

        for item in payload.tasks:
            source_project_id = str(item.source_project_id).strip()
            received_ids.add(source_project_id)

            source_member = _ensure_source_member(
                database,
                source_system=payload.source_system,
                source_member_name=item.source_member_name,
                seen_at=utc_now(),
            )

            effective_active = (
                item.is_active
                if item.is_active is not None
                else task_status_is_active(item.status)
            )
            if effective_active:
                active_count += 1

            freelancer_id = source_member.freelancer_id
            if freelancer_id is None:
                unmapped_count += 1
            else:
                mapped_count += 1

            synced_task = existing_tasks.get(source_project_id)
            if synced_task is None:
                synced_task = SyncedProjectTask(
                    source_system=payload.source_system,
                    source_project_id=source_project_id,
                )
                database.add(synced_task)
                existing_tasks[source_project_id] = synced_task

            synced_task.source_member_name = (
                item.source_member_name.strip()
            )
            synced_task.normalized_member_name = normalize_member_name(
                item.source_member_name
            )
            synced_task.freelancer_id = freelancer_id
            synced_task.project_code = item.project_code.strip()
            synced_task.project_name = (
                item.project_name or item.project_code
            )
            synced_task.deadline = item.deadline
            synced_task.project_status = item.status
            synced_task.engineer = item.engineer
            synced_task.priority = item.priority
            synced_task.discipline = item.discipline
            synced_task.progress = item.progress
            synced_task.task_description = item.task_description
            synced_task.source_updated_at = item.source_updated_at
            synced_task.synced_at = utc_now()
            synced_task.is_active = bool(effective_active)
            synced_task.payload_hash = _payload_hash(item)
            synced_task.last_sync_run_id = sync_run.id

        database.flush()

        source_members = list(
            database.scalars(
                select(ProjectSourceMember).where(
                    ProjectSourceMember.source_system
                    == payload.source_system
                )
            ).all()
        )
        for source_member in source_members:
            source_member.active_task_count = int(
                database.scalar(
                    select(func.count(SyncedProjectTask.id)).where(
                        SyncedProjectTask.source_system
                        == payload.source_system,
                        SyncedProjectTask.normalized_member_name
                        == source_member.normalized_member_name,
                        SyncedProjectTask.is_active.is_(True),
                    )
                )
                or 0
            )

        inactive_count = int(
            database.scalar(
                select(func.count(SyncedProjectTask.id)).where(
                    SyncedProjectTask.source_system
                    == payload.source_system,
                    SyncedProjectTask.is_active.is_(False),
                )
            )
            or 0
        )

        sync_run.status = "SUCCESS"
        sync_run.completed_at_utc = utc_now()
        sync_run.active_count = active_count
        sync_run.inactive_count = inactive_count
        sync_run.mapped_count = mapped_count
        sync_run.unmapped_count = unmapped_count
        sync_run.message = (
            f"Received {len(payload.tasks)} tasks; "
            f"{mapped_count} mapped; {unmapped_count} unmapped."
        )

        database.commit()

        return {
            "status": "success",
            "sync_run_id": sync_run.id,
            "received_count": len(payload.tasks),
            "active_count": active_count,
            "inactive_count": inactive_count,
            "mapped_count": mapped_count,
            "unmapped_count": unmapped_count,
        }
    except Exception as exc:
        database.rollback()

        failed_run = ProjectSyncRun(
            source_system=payload.source_system,
            source_database_label=payload.source_database_label,
            started_at_utc=started_at,
            completed_at_utc=utc_now(),
            status="FAILED",
            received_count=len(payload.tasks),
            request_ip=request_ip,
            message=str(exc)[:1000],
        )
        database.add(failed_run)
        database.commit()
        raise


def map_source_member(
    database: Session,
    *,
    source_member: ProjectSourceMember,
    freelancer_id: Optional[int],
) -> int:
    """Apply an HR freelancer mapping to current synchronized tasks."""
    source_member.freelancer_id = freelancer_id
    source_member.updated_at = utc_now()

    tasks = list(
        database.scalars(
            select(SyncedProjectTask).where(
                SyncedProjectTask.source_system
                == source_member.source_system,
                SyncedProjectTask.normalized_member_name
                == source_member.normalized_member_name,
            )
        ).all()
    )
    for task in tasks:
        task.freelancer_id = freelancer_id

    database.commit()
    return len(tasks)


def current_freelancer_project_tasks(
    database: Session,
    *,
    freelancer_id: int,
    limit: Optional[int] = None,
) -> list[SyncedProjectTask]:
    query = (
        select(SyncedProjectTask)
        .where(
            SyncedProjectTask.freelancer_id == freelancer_id,
            SyncedProjectTask.is_active.is_(True),
        )
        .order_by(
            SyncedProjectTask.deadline.is_(None),
            SyncedProjectTask.deadline,
            SyncedProjectTask.priority,
            SyncedProjectTask.project_code,
        )
    )

    if limit is not None:
        query = query.limit(limit)

    return list(database.scalars(query).all())


def last_successful_sync(
    database: Session,
    source_system: str = "BIMFM_TASK_MANAGER",
) -> Optional[ProjectSyncRun]:
    return database.scalar(
        select(ProjectSyncRun)
        .where(
            ProjectSyncRun.source_system == source_system,
            ProjectSyncRun.status == "SUCCESS",
        )
        .order_by(ProjectSyncRun.completed_at_utc.desc())
        .limit(1)
    )
