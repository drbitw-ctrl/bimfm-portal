"""Timed work orders, live-work visibility, and email-style reminders."""
from __future__ import annotations

from datetime import date, datetime, timezone
from email.message import EmailMessage
import math
import smtplib
from typing import Any, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import (
    DEFAULT_TIMEZONE,
    SMTP_FROM_EMAIL,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_USERNAME,
    SMTP_USE_TLS,
)
from app.models import (
    DailyTask,
    Freelancer,
    HRAdminAccount,
    PortalProject,
    PortalTask,
    TaskReminder,
    TaskWorkSession,
)
from app.models.common import utc_now
from app.portal_project_service import current_freelancer_portal_tasks, portal_task_for_freelancer

ACTIVE_SESSION_STATUS = "ACTIVE"
STOPPED_SESSION_STATUS = "STOPPED"
CLOSED_TASK_STATUSES = {"COMPLETED", "CANCELLED"}


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _local_date(value: datetime, timezone_name: str) -> date:
    try:
        zone = ZoneInfo(timezone_name or DEFAULT_TIMEZONE)
    except ZoneInfoNotFoundError:
        zone = ZoneInfo(DEFAULT_TIMEZONE)
    return _aware(value).astimezone(zone).date()


def active_work_session(database: Session, freelancer_id: int) -> Optional[TaskWorkSession]:
    return database.scalar(
        select(TaskWorkSession)
        .where(
            TaskWorkSession.freelancer_id == freelancer_id,
            TaskWorkSession.status == ACTIVE_SESSION_STATUS,
            TaskWorkSession.stopped_at.is_(None),
        )
        .order_by(TaskWorkSession.started_at.desc(), TaskWorkSession.id.desc())
        .limit(1)
    )


def start_work_session(
    database: Session,
    *,
    freelancer: Freelancer,
    task_id: int,
    started_at: Optional[datetime] = None,
) -> TaskWorkSession:
    existing = active_work_session(database, freelancer.id)
    if existing is not None:
        raise ValueError("Stop your current work order before starting another task.")

    assigned = portal_task_for_freelancer(
        database,
        task_id=task_id,
        freelancer_id=freelancer.id,
    )
    if assigned is None:
        raise ValueError("This task is not available in your active assignments.")

    task = database.get(PortalTask, task_id)
    if task is None or str(task.status or "").upper() in CLOSED_TASK_STATUSES:
        raise ValueError("This task is already closed and cannot be started.")
    project = database.get(PortalProject, task.project_id)
    if project is None:
        raise ValueError("The task project could not be found.")

    now = _aware(started_at or utc_now())
    session = TaskWorkSession(
        freelancer_id=freelancer.id,
        portal_task_id=task.id,
        project_id=project.id,
        project_code=project.project_code,
        project_name=project.name,
        task_title=task.title,
        discipline=task.discipline or project.discipline,
        status=ACTIVE_SESSION_STATUS,
        started_at=now,
        duration_minutes=0,
    )
    database.add(session)
    database.flush()
    return session


def stop_work_session(
    database: Session,
    *,
    freelancer: Freelancer,
    notes: str = "",
    stopped_at: Optional[datetime] = None,
) -> tuple[TaskWorkSession, DailyTask]:
    session = active_work_session(database, freelancer.id)
    if session is None:
        raise ValueError("There is no active work order to stop.")

    stop_time = _aware(stopped_at or utc_now())
    start_time = _aware(session.started_at)
    if stop_time <= start_time:
        raise ValueError("The stop time must be later than the start time.")

    elapsed_seconds = (stop_time - start_time).total_seconds()
    # Record every genuine session and round partial minutes upward so short
    # checks do not disappear from the operational record.
    duration_minutes = max(1, int(math.ceil(elapsed_seconds / 60.0)))

    task = database.get(PortalTask, session.portal_task_id) if session.portal_task_id else None
    project = database.get(PortalProject, session.project_id) if session.project_id else None
    portal_status = str(getattr(task, "status", "IN_PROGRESS") or "IN_PROGRESS").upper()
    daily_status = "COMPLETED" if portal_status == "COMPLETED" else "IN_PROGRESS"
    progress = max(0, min(100, int(getattr(task, "progress", 0) or 0)))

    daily_task = DailyTask(
        freelancer_id=freelancer.id,
        portal_task_id=session.portal_task_id,
        synced_project_task_id=None,
        task_date=_local_date(stop_time, freelancer.timezone_name),
        project_code=(project.project_code if project else session.project_code),
        project_name=(project.name if project else session.project_name),
        discipline=(getattr(task, "discipline", None) or getattr(project, "discipline", None) or session.discipline),
        task_description=(getattr(task, "title", None) or session.task_title),
        # Accomplishment and project progress remain management-controlled.
        accomplishment=None,
        task_status=daily_status,
        minutes_spent=duration_minutes,
        completion_percentage=progress,
        notes=notes.strip() or None,
    )
    database.add(daily_task)
    database.flush()

    session.status = STOPPED_SESSION_STATUS
    session.stopped_at = stop_time
    session.duration_minutes = duration_minutes
    session.notes = notes.strip() or None
    session.daily_task_id = daily_task.id
    session.updated_at = stop_time
    database.flush()
    return session, daily_task


def freelancer_work_order_view(database: Session, freelancer: Freelancer) -> dict[str, Any]:
    assigned = current_freelancer_portal_tasks(
        database,
        freelancer_id=freelancer.id,
        limit=200,
    )
    active = active_work_session(database, freelancer.id)
    today = _local_date(utc_now(), freelancer.timezone_name)
    # Filter in Python using the freelancer's configured timezone. This avoids
    # PostgreSQL's DATE(timestamptz) comparison/casting differences and also
    # prevents a UTC database session from assigning near-midnight work to the
    # wrong local day. The bounded candidate query keeps the page efficient.
    candidates = list(
        database.scalars(
            select(TaskWorkSession)
            .where(TaskWorkSession.freelancer_id == freelancer.id)
            .order_by(TaskWorkSession.started_at.desc(), TaskWorkSession.id.desc())
            .limit(250)
        ).all()
    )
    today_sessions = [
        row for row in candidates
        if _local_date(row.started_at, freelancer.timezone_name) == today
    ]

    total_minutes = sum(int(row.duration_minutes or 0) for row in today_sessions if row.status == STOPPED_SESSION_STATUS)
    active_started_iso = _aware(active.started_at).isoformat() if active else ""
    return {
        "assigned_tasks": assigned,
        "active_session": active,
        "active_started_iso": active_started_iso,
        "today_sessions": today_sessions,
        "today_total_minutes": total_minutes,
        "today": today,
    }


def live_work_rows(database: Session) -> list[dict[str, Any]]:
    statement = (
        select(TaskWorkSession, Freelancer, PortalTask, PortalProject)
        .join(Freelancer, Freelancer.id == TaskWorkSession.freelancer_id)
        .outerjoin(PortalTask, PortalTask.id == TaskWorkSession.portal_task_id)
        .outerjoin(PortalProject, PortalProject.id == TaskWorkSession.project_id)
        .where(
            TaskWorkSession.status == ACTIVE_SESSION_STATUS,
            TaskWorkSession.stopped_at.is_(None),
            Freelancer.is_active.is_(True),
        )
        .order_by(TaskWorkSession.started_at, Freelancer.full_name)
    )
    now = utc_now()
    rows: list[dict[str, Any]] = []
    for session, freelancer, task, project in database.execute(statement).all():
        started = _aware(session.started_at)
        elapsed_minutes = max(0, int((now - started).total_seconds() // 60))
        rows.append({
            "session_id": session.id,
            "freelancer_id": freelancer.id,
            "member_name": freelancer.full_name,
            "member_code": freelancer.freelancer_code,
            "task_id": session.portal_task_id,
            "task_title": (task.title if task else session.task_title),
            "project_name": (project.name if project else session.project_name),
            "project_code": (project.project_code if project else session.project_code),
            "discipline": (getattr(task, "discipline", None) or getattr(project, "discipline", None) or session.discipline or ""),
            "started_at": started,
            "started_at_iso": started.isoformat(),
            "elapsed_minutes": elapsed_minutes,
            "progress": max(0, min(100, int(getattr(task, "progress", 0) or 0))),
            "priority": str(getattr(task, "priority", "NORMAL") or "NORMAL"),
            "due_date": getattr(task, "due_date", None),
        })
    return rows


def unread_reminder_count(database: Session, freelancer_id: int) -> int:
    return int(
        database.scalar(
            select(func.count(TaskReminder.id)).where(
                TaskReminder.freelancer_id == freelancer_id,
                TaskReminder.read_at.is_(None),
            )
        )
        or 0
    )


def reminder_rows(database: Session, freelancer_id: int) -> list[dict[str, Any]]:
    statement = (
        select(TaskReminder, HRAdminAccount, PortalTask, PortalProject)
        .outerjoin(HRAdminAccount, HRAdminAccount.id == TaskReminder.sender_admin_id)
        .outerjoin(PortalTask, PortalTask.id == TaskReminder.portal_task_id)
        .outerjoin(PortalProject, PortalProject.id == PortalTask.project_id)
        .where(TaskReminder.freelancer_id == freelancer_id)
        .order_by(TaskReminder.created_at.desc(), TaskReminder.id.desc())
    )
    rows: list[dict[str, Any]] = []
    for reminder, sender, task, project in database.execute(statement).all():
        rows.append({
            "id": reminder.id,
            "subject": reminder.subject,
            "message": reminder.message,
            "sender": sender.display_name if sender else "BIMFM Operations",
            "created_at": reminder.created_at,
            "is_unread": reminder.read_at is None,
            "task_id": reminder.portal_task_id,
            "task_title": task.title if task else "Task reminder",
            "project_name": project.name if project else "—",
            "email_sent": reminder.email_sent,
            "email_attempted": reminder.email_attempted,
        })
    return rows


def mark_reminder_read(database: Session, reminder_id: int, freelancer_id: int) -> bool:
    reminder = database.scalar(
        select(TaskReminder).where(
            TaskReminder.id == reminder_id,
            TaskReminder.freelancer_id == freelancer_id,
        )
    )
    if reminder is None:
        return False
    if reminder.read_at is None:
        reminder.read_at = utc_now()
    return True


def _send_email(recipient: str, subject: str, body: str) -> tuple[bool, str]:
    if not SMTP_HOST or not SMTP_FROM_EMAIL:
        return False, "SMTP is not configured; the in-app reminder was delivered."

    message = EmailMessage()
    message["From"] = SMTP_FROM_EMAIL
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=12) as client:
            if SMTP_USE_TLS:
                client.starttls()
            if SMTP_USERNAME:
                client.login(SMTP_USERNAME, SMTP_PASSWORD)
            client.send_message(message)
        return True, ""
    except Exception as exc:  # pragma: no cover - external transport varies
        return False, str(exc)[:1000]


def create_task_reminder(
    database: Session,
    *,
    task: PortalTask,
    freelancer: Freelancer,
    sender: HRAdminAccount,
    subject: str,
    message: str,
) -> TaskReminder:
    clean_subject = " ".join(subject.strip().split())
    clean_message = message.strip()
    if not clean_subject:
        raise ValueError("Reminder subject is required.")
    if not clean_message:
        raise ValueError("Reminder message is required.")
    if len(clean_subject) > 240:
        raise ValueError("Reminder subject is too long.")

    reminder = TaskReminder(
        freelancer_id=freelancer.id,
        portal_task_id=task.id,
        sender_admin_id=sender.id,
        subject=clean_subject,
        message=clean_message,
        recipient_email=freelancer.email,
    )
    database.add(reminder)
    database.flush()

    if freelancer.email:
        project = database.get(PortalProject, task.project_id)
        email_body = (
            f"Hello {freelancer.full_name},\n\n"
            f"{clean_message}\n\n"
            f"Project: {project.name if project else '—'}\n"
            f"Task: {task.title}\n"
            f"Deadline: {task.due_date.isoformat() if task.due_date else 'No deadline'}\n\n"
            f"Sent by: {sender.display_name}\n"
            "BIMFM Portal"
        )
        reminder.email_attempted = True
        sent, error = _send_email(freelancer.email, clean_subject, email_body)
        reminder.email_sent = sent
        reminder.email_error = error or None
        reminder.email_sent_at = utc_now() if sent else None
    return reminder
