"""Separate staff review queue and timed review work.

Uses existing PortalTaskUpdate and TaskWorkSession storage so Release 21.22.5
requires no schema migration. Review sessions never create DailyTask rows and
never alter freelancer task assignments/status/progress.
"""
from __future__ import annotations
from datetime import datetime, timezone
import math
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Freelancer, HRAdminAccount, PortalProject, PortalTask, PortalTaskUpdate, TaskWorkSession
from app.models.common import utc_now

REVIEWABLE = {"IN_PROGRESS", "FOR_REVIEW"}
ASSIGN_PREFIX = "[[REVIEW_ASSIGNMENT]]"
ACTIVE_PREFIX = "[[REVIEW_ACTIVE]]"
STOPPED_PREFIX = "[[REVIEW]]"


def _aware(v: datetime) -> datetime:
    return v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v.astimezone(timezone.utc)


def reviewer_freelancer(db: Session, admin: HRAdminAccount) -> Freelancer | None:
    fid = getattr(admin, "task_freelancer_id", None)
    return db.get(Freelancer, fid) if fid else None


def assign_review(db: Session, *, task: PortalTask, reviewer: HRAdminAccount, actor: HRAdminAccount) -> None:
    if str(task.status or "").upper() not in REVIEWABLE:
        raise ValueError("Only In Progress or Completed — For Review tasks can enter the review queue.")
    db.add(PortalTaskUpdate(task_id=task.id, admin_id=reviewer.id, status=task.status,
                            note=f"{ASSIGN_PREFIX} reviewer={reviewer.id}; assigned_by={actor.id}"))
    db.flush()


def latest_review_assignments(db: Session) -> dict[int, int]:
    rows = db.scalars(select(PortalTaskUpdate).where(PortalTaskUpdate.note.like(f"{ASSIGN_PREFIX}%")).order_by(PortalTaskUpdate.id)).all()
    result: dict[int, int] = {}
    for row in rows:
        if row.admin_id:
            result[int(row.task_id)] = int(row.admin_id)
    return result


def active_review_session(db: Session, admin: HRAdminAccount) -> TaskWorkSession | None:
    member = reviewer_freelancer(db, admin)
    if not member:
        return None
    return db.scalar(select(TaskWorkSession).where(
        TaskWorkSession.freelancer_id == member.id,
        TaskWorkSession.status == "ACTIVE",
        TaskWorkSession.stopped_at.is_(None),
        TaskWorkSession.notes.like(f"{ACTIVE_PREFIX}%"),
    ).order_by(TaskWorkSession.started_at.desc()).limit(1))


def start_review(db: Session, *, admin: HRAdminAccount, task: PortalTask) -> TaskWorkSession:
    member = reviewer_freelancer(db, admin)
    if member is None:
        raise ValueError("Enable Task Assignment for this staff account before starting review work.")
    if str(task.status or "").upper() not in REVIEWABLE:
        raise ValueError("This task is no longer available for review work.")
    assignments = latest_review_assignments(db)
    if assignments.get(task.id) != admin.id:
        raise ValueError("This review is assigned to another reviewer.")
    existing = db.scalar(select(TaskWorkSession).where(TaskWorkSession.freelancer_id == member.id, TaskWorkSession.status == "ACTIVE", TaskWorkSession.stopped_at.is_(None)).limit(1))
    if existing:
        raise ValueError("Stop your current work/review timer before starting another review.")
    project = db.get(PortalProject, task.project_id)
    if project is None:
        raise ValueError("Project not found.")
    now = _aware(utc_now())
    session = TaskWorkSession(freelancer_id=member.id, portal_task_id=task.id, project_id=project.id,
        project_code=project.project_code, project_name=project.name, task_title=task.title,
        discipline=task.discipline or project.discipline, status="ACTIVE", started_at=now,
        duration_minutes=0, notes=f"{ACTIVE_PREFIX} reviewer={admin.id}")
    db.add(session); db.flush(); return session


def stop_review(db: Session, *, admin: HRAdminAccount, notes: str) -> TaskWorkSession:
    session = active_review_session(db, admin)
    if session is None:
        raise ValueError("There is no active review timer to stop.")
    clean = " ".join(str(notes or "").split())
    if len(clean) < 5:
        raise ValueError("Enter a short review activity note before stopping.")
    now = _aware(utc_now()); start = _aware(session.started_at)
    session.status = "STOPPED"; session.stopped_at = now
    session.duration_minutes = max(1, int(math.ceil((now-start).total_seconds()/60.0)))
    session.notes = f"{STOPPED_PREFIX} reviewer={admin.id}; {clean[:900]}"; session.updated_at = now
    db.add(PortalTaskUpdate(task_id=session.portal_task_id, admin_id=admin.id, note=f"{STOPPED_PREFIX} {clean[:900]}"))
    db.flush(); return session


def review_minutes_by_task(db: Session, admin_id: int | None = None) -> dict[int, int]:
    q = select(TaskWorkSession, HRAdminAccount).join(Freelancer, Freelancer.id == TaskWorkSession.freelancer_id).join(HRAdminAccount, HRAdminAccount.task_freelancer_id == Freelancer.id).where(TaskWorkSession.status == "STOPPED", TaskWorkSession.notes.like(f"{STOPPED_PREFIX}%"))
    if admin_id:
        q = q.where(HRAdminAccount.id == admin_id)
    totals: dict[int,int] = {}
    for session, _ in db.execute(q).all():
        if session.portal_task_id:
            totals[int(session.portal_task_id)] = totals.get(int(session.portal_task_id),0) + int(session.duration_minutes or 0)
    return totals


def queue_rows(db: Session, *, admin: HRAdminAccount | None = None, all_reviewers: bool = False) -> list[dict]:
    assignments = latest_review_assignments(db)
    names = {a.id:a.display_name for a in db.scalars(select(HRAdminAccount).where(HRAdminAccount.is_active.is_(True))).all()}
    totals = review_minutes_by_task(db)
    tasks = db.scalars(select(PortalTask).where(PortalTask.status.in_(tuple(REVIEWABLE))).order_by(PortalTask.due_date, PortalTask.id)).all()
    rows=[]
    for task in tasks:
        reviewer_id=assignments.get(task.id)
        if not all_reviewers and admin is not None and reviewer_id != admin.id: continue
        project=db.get(PortalProject, task.project_id)
        rows.append({"task_id":task.id,"task_title":task.title,"project_name":project.name if project else "—","status":task.status,
          "priority":task.priority,"due_date":task.due_date.isoformat() if task.due_date else "—","reviewer_id":reviewer_id,
          "reviewer_name":names.get(reviewer_id,"Unassigned"),"review_minutes":totals.get(task.id,0)})
    return rows
