"""Overnight attendance, Work Order, and OT exception safeguards."""
from __future__ import annotations
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.config import DEFAULT_TIMEZONE
from app.models import AuditLog, DailyAttendance, Freelancer, TaskWorkSession
from app.models.common import utc_now

FLAGGED_STATUS = "FLAGGED_MISSED_STOP"

def _zone(name: str):
    try: return ZoneInfo(name or DEFAULT_TIMEZONE)
    except ZoneInfoNotFoundError: return ZoneInfo(DEFAULT_TIMEZONE)

def reconcile_overnight_exceptions(database: Session, *, now: datetime | None = None) -> int:
    current = now or utc_now()
    if current.tzinfo is None: current = current.replace(tzinfo=timezone.utc)
    changed = 0
    freelancers = list(database.scalars(select(Freelancer).where(Freelancer.is_active.is_(True))).all())
    for freelancer in freelancers:
        zone = _zone(freelancer.timezone_name)
        local_now = current.astimezone(zone)
        if local_now.time() < time(6, 0):
            continue
        prior_date = local_now.date() - timedelta(days=1)
        cutoff_local = datetime.combine(local_now.date(), time(6, 0), tzinfo=zone)
        cutoff_utc = cutoff_local.astimezone(timezone.utc)
        record = database.scalar(select(DailyAttendance).where(
            DailyAttendance.freelancer_id == freelancer.id,
            DailyAttendance.attendance_date == prior_date,
            DailyAttendance.time_in_utc.is_not(None),
            DailyAttendance.time_out_utc.is_(None),
        ))
        sessions = list(database.scalars(select(TaskWorkSession).where(
            TaskWorkSession.freelancer_id == freelancer.id,
            TaskWorkSession.status == "ACTIVE",
            TaskWorkSession.stopped_at.is_(None),
            TaskWorkSession.started_at < cutoff_utc,
        )).all())
        if record is None and not sessions:
            continue
        if record is not None and not record.exception_flagged_at:
            record.status = "MISSING_TIME_OUT"
            record.review_status = "REQUIRES_CORRECTION"
            record.missed_time_out_flag = True
            record.missed_work_order_stop_flag = bool(sessions)
            record.overtime_unavailable = True
            record.overtime_minutes = 0
            record.exception_flagged_at = current
            changed += 1
        for session in sessions:
            session.status = FLAGGED_STATUS
            session.stopped_at = cutoff_utc
            session.duration_minutes = 0
            session.missed_stop_flag = True
            session.exception_flagged_at = current
            session.updated_at = current
            database.add(AuditLog(actor_type="SYSTEM", actor_id=None, action="FLAG_OVERNIGHT_MISSED_STOP", target_type="TASK_WORK_SESSION", target_id=session.id, details=f"Flagged at 06:00 local time for {prior_date.isoformat()}; OT unavailable pending Administrator correction.", ip_address=None))
            changed += 1
    if changed:
        database.flush()
    return changed
