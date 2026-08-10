"""Separate staff review queue and timed review work.

Review work is intentionally separate from freelancer production work.  This
module reuses the existing PortalTaskUpdate and TaskWorkSession tables, so the
feature requires no schema migration.  Staff review timers never create
DailyTask rows and never change the freelancer task assignee, task status, or
progress.
"""
from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Freelancer,
    HRAdminAccount,
    PortalProject,
    PortalTask,
    PortalTaskUpdate,
    TaskWorkSession,
)
from app.models.common import utc_now

REVIEWABLE = {"IN_PROGRESS", "FOR_REVIEW"}
ASSIGN_PREFIX = "[[REVIEW_ASSIGNMENT]]"
ACTIVE_PREFIX = "[[REVIEW_ACTIVE]]"
STOPPED_PREFIX = "[[REVIEW]]"
STAFF_MEMBER_PREFIX = "TS-"


def _aware(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _staff_member_code(admin_id: int) -> str:
    return f"{STAFF_MEMBER_PREFIX}{int(admin_id):03d}"


def is_staff_task_member(member: Freelancer | None) -> bool:
    return bool(member and str(member.freelancer_code or "").upper().startswith(STAFF_MEMBER_PREFIX))


def reviewer_freelancer(db: Session, admin: HRAdminAccount) -> Freelancer | None:
    """Return the deterministic task/review identity for a staff account.

    Do not reference HRAdminAccount.task_freelancer_id here.  Production has
    previously run model definitions where that optional ORM attribute was not
    present even though the database was otherwise healthy.
    """
    if admin is None or getattr(admin, "id", None) is None:
        return None
    return db.scalar(
        select(Freelancer).where(Freelancer.freelancer_code == _staff_member_code(int(admin.id)))
    )


def ensure_reviewer_freelancer(db: Session, admin: HRAdminAccount) -> Freelancer:
    """Create/reuse an internal timer identity for review work.

    This is a normal row insert only when the deterministic TS-* identity does
    not yet exist; it performs no schema change and is hidden from DTR
    generation.  It also means review work does not depend on the separate
    'Enable Task Assignment' UI.
    """
    member = reviewer_freelancer(db, admin)
    if member is None:
        member = Freelancer(
            freelancer_code=_staff_member_code(int(admin.id)),
            full_name=str(admin.display_name or admin.username or f"Staff {admin.id}"),
            email=None,
            join_date=None,
            is_active=bool(getattr(admin, "is_active", True)),
        )
        db.add(member)
        db.flush()
    else:
        member.full_name = str(admin.display_name or admin.username or member.full_name)
        member.is_active = bool(getattr(admin, "is_active", True))
    return member


def reviewer_choices(db: Session, *, current_admin: HRAdminAccount | None = None) -> list[HRAdminAccount]:
    """Return active Admin/Supervisor reviewer choices without duplicate names.

    If historical staff accounts share the exact same visible name/role, keep
    the signed-in account when it is one of the duplicates; otherwise keep the
    lowest account id.  This removes the duplicate 'Don' experience without
    deleting or mutating any staff account.
    """
    accounts = list(
        db.scalars(
            select(HRAdminAccount)
            .where(
                HRAdminAccount.is_active.is_(True),
                HRAdminAccount.role.in_(("ADMIN", "SUPERVISOR")),
            )
            .order_by(HRAdminAccount.display_name, HRAdminAccount.id)
        ).all()
    )
    grouped: dict[tuple[str, str], HRAdminAccount] = {}
    current_id = int(current_admin.id) if current_admin is not None else None
    for account in accounts:
        key = (
            " ".join(str(account.display_name or account.username or "").split()).casefold(),
            str(account.role or "").upper(),
        )
        existing = grouped.get(key)
        if existing is None or (current_id is not None and int(account.id) == current_id):
            grouped[key] = account
    return sorted(grouped.values(), key=lambda row: (str(row.display_name or "").casefold(), int(row.id)))


def assign_review(db: Session, *, task: PortalTask, reviewer: HRAdminAccount, actor: HRAdminAccount) -> None:
    if task is None:
        raise ValueError("Review task not found.")
    if reviewer is None or not bool(getattr(reviewer, "is_active", False)):
        raise ValueError("Reviewer account is unavailable.")
    if str(getattr(reviewer, "role", "") or "").upper() not in {"ADMIN", "SUPERVISOR"}:
        raise ValueError("Review work can only be assigned to an Administrator or Supervisor.")
    if str(task.status or "").upper() not in REVIEWABLE:
        raise ValueError("Only In Progress or Completed — For Review tasks can enter the review queue.")
    db.add(
        PortalTaskUpdate(
            task_id=task.id,
            admin_id=reviewer.id,
            status=task.status,
            note=f"{ASSIGN_PREFIX} reviewer={reviewer.id}; assigned_by={actor.id}",
        )
    )
    db.flush()


def latest_review_assignments(db: Session) -> dict[int, int]:
    rows = db.scalars(
        select(PortalTaskUpdate)
        .where(PortalTaskUpdate.note.like(f"{ASSIGN_PREFIX}%"))
        .order_by(PortalTaskUpdate.id)
    ).all()
    result: dict[int, int] = {}
    for row in rows:
        if row.admin_id is not None and row.task_id is not None:
            result[int(row.task_id)] = int(row.admin_id)
    return result


def active_review_session(db: Session, admin: HRAdminAccount) -> TaskWorkSession | None:
    member = reviewer_freelancer(db, admin)
    if member is None:
        return None
    return db.scalar(
        select(TaskWorkSession)
        .where(
            TaskWorkSession.freelancer_id == member.id,
            TaskWorkSession.status == "ACTIVE",
            TaskWorkSession.stopped_at.is_(None),
            TaskWorkSession.notes.like(f"{ACTIVE_PREFIX}%"),
        )
        .order_by(TaskWorkSession.started_at.desc())
        .limit(1)
    )


def start_review(db: Session, *, admin: HRAdminAccount, task: PortalTask | None) -> TaskWorkSession:
    if task is None:
        raise ValueError("Review task not found.")
    if str(task.status or "").upper() not in REVIEWABLE:
        raise ValueError("This task is no longer available for review work.")

    assignments = latest_review_assignments(db)
    if assignments.get(int(task.id)) != int(admin.id):
        raise ValueError("This review is assigned to another reviewer.")

    # Review work is separate from ordinary task assignment.  Ensure the
    # staff-only timer identity automatically instead of requiring a separate
    # task-assignment setup step.
    member = ensure_reviewer_freelancer(db, admin)

    existing = db.scalar(
        select(TaskWorkSession)
        .where(
            TaskWorkSession.freelancer_id == member.id,
            TaskWorkSession.status == "ACTIVE",
            TaskWorkSession.stopped_at.is_(None),
        )
        .order_by(TaskWorkSession.started_at.desc())
        .limit(1)
    )
    if existing:
        if str(existing.notes or "").startswith(ACTIVE_PREFIX):
            raise ValueError("A review timer is already running. Stop it before starting another review.")
        raise ValueError("Stop your current Work Order before starting review work.")

    project = db.get(PortalProject, task.project_id)
    if project is None:
        raise ValueError("Project not found.")

    now = _aware(utc_now())
    session = TaskWorkSession(
        freelancer_id=member.id,
        portal_task_id=task.id,
        project_id=project.id,
        project_code=str(project.project_code or "REVIEW"),
        project_name=str(project.name or "Project"),
        task_title=str(task.title or "Review work"),
        discipline=task.discipline or project.discipline,
        status="ACTIVE",
        started_at=now,
        duration_minutes=0,
        notes=f"{ACTIVE_PREFIX} reviewer={admin.id}; task={task.id}",
    )
    db.add(session)
    db.flush()
    return session


def stop_review(db: Session, *, admin: HRAdminAccount, notes: str) -> TaskWorkSession:
    session = active_review_session(db, admin)
    if session is None:
        raise ValueError("There is no active review timer to stop.")
    clean = " ".join(str(notes or "").split())
    if len(clean) < 5:
        raise ValueError("Enter a short review activity note before stopping.")
    now = _aware(utc_now())
    start = _aware(session.started_at)
    session.status = "STOPPED"
    session.stopped_at = now
    session.duration_minutes = max(1, int(math.ceil((now - start).total_seconds() / 60.0)))
    session.notes = f"{STOPPED_PREFIX} reviewer={admin.id}; {clean[:900]}"
    session.updated_at = now
    db.add(
        PortalTaskUpdate(
            task_id=session.portal_task_id,
            admin_id=admin.id,
            note=f"{STOPPED_PREFIX} {clean[:900]}",
        )
    )
    db.flush()
    return session


def _session_reviewer_id(session: TaskWorkSession) -> int | None:
    note = str(session.notes or "")
    marker = "reviewer="
    pos = note.find(marker)
    if pos < 0:
        return None
    value = note[pos + len(marker):].split(";", 1)[0].strip()
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def review_minutes_by_task(db: Session, admin_id: int | None = None) -> dict[int, int]:
    """Aggregate stopped review time without staff/freelancer ORM joins."""
    sessions = db.scalars(
        select(TaskWorkSession).where(
            TaskWorkSession.status == "STOPPED",
            TaskWorkSession.notes.like(f"{STOPPED_PREFIX}%"),
        )
    ).all()
    totals: dict[int, int] = {}
    for session in sessions:
        reviewer_id = _session_reviewer_id(session)
        if admin_id is not None and reviewer_id != int(admin_id):
            continue
        if session.portal_task_id is None:
            continue
        task_id = int(session.portal_task_id)
        totals[task_id] = totals.get(task_id, 0) + max(0, int(session.duration_minutes or 0))
    return totals


def queue_rows(db: Session, *, admin: HRAdminAccount | None = None, all_reviewers: bool = False) -> list[dict]:
    assignments = latest_review_assignments(db)
    accounts = list(db.scalars(select(HRAdminAccount).where(HRAdminAccount.is_active.is_(True))).all())
    names = {int(a.id): str(a.display_name or a.username or f"Staff {a.id}") for a in accounts}
    totals = review_minutes_by_task(db)

    active_task_by_reviewer: dict[int, int] = {}
    for account in accounts:
        session = active_review_session(db, account)
        if session is not None and session.portal_task_id is not None:
            active_task_by_reviewer[int(account.id)] = int(session.portal_task_id)

    tasks = db.scalars(
        select(PortalTask)
        .where(PortalTask.status.in_(tuple(REVIEWABLE)))
        .order_by(PortalTask.due_date, PortalTask.id)
    ).all()
    rows: list[dict] = []
    for task in tasks:
        reviewer_id = assignments.get(int(task.id))
        if not all_reviewers and admin is not None and reviewer_id != int(admin.id):
            continue
        project = db.get(PortalProject, task.project_id)
        minutes = totals.get(int(task.id), 0)
        if reviewer_id is None:
            review_state = "UNASSIGNED"
        elif active_task_by_reviewer.get(int(reviewer_id)) == int(task.id):
            review_state = "REVIEWING"
        elif minutes > 0:
            review_state = "REVIEWED"
        else:
            review_state = "ASSIGNED"
        rows.append(
            {
                "task_id": int(task.id),
                "task_title": str(task.title or "—"),
                "project_name": str(project.name if project else "—"),
                "status": str(task.status or "NOT_STARTED"),
                "review_status": review_state,
                "priority": str(task.priority or "NORMAL"),
                "due_date": task.due_date.isoformat() if task.due_date else "—",
                "reviewer_id": reviewer_id,
                "reviewer_name": names.get(int(reviewer_id), "Unassigned") if reviewer_id is not None else "Unassigned",
                "review_minutes": minutes,
            }
        )
    return rows
