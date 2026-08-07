"""Task-hourly member mode without attendance punches.

Release 21.22 intentionally keeps this configuration in application code so the
production database schema is not changed while no restorable managed backup is
available. Belinda is identified by the stable portal freelancer code imported
from the legacy directory.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import DEFAULT_TIMEZONE
from app.models import Freelancer, TaskWorkSession

TASK_HOURLY_MEMBER_CODES = frozenset({"LEGACY-00008"})
TASK_HOURLY_MEMBER_NAMES = frozenset({"belinda"})


def is_task_hourly_member(freelancer: Freelancer | None) -> bool:
    if freelancer is None:
        return False
    code = str(getattr(freelancer, "freelancer_code", "") or "").strip().upper()
    name = " ".join(str(getattr(freelancer, "full_name", "") or "").split()).casefold()
    return code in TASK_HOURLY_MEMBER_CODES or name in TASK_HOURLY_MEMBER_NAMES


def _zone(name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(name or DEFAULT_TIMEZONE)
    except ZoneInfoNotFoundError:
        return ZoneInfo(DEFAULT_TIMEZONE)


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def format_duration_seconds(total_seconds: int) -> dict[str, Any]:
    seconds = max(0, int(total_seconds or 0))
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return {
        "seconds_total": seconds,
        "hours": hours,
        "minutes": minutes,
        "seconds": secs,
        "label": f"{hours:02d}:{minutes:02d}:{secs:02d}",
    }


def task_hourly_month_ledger(
    database: Session,
    *,
    freelancer: Freelancer,
    month_key: str,
) -> dict[str, Any]:
    """Return exact per-day task time from stopped Work Order timestamps.

    Sessions that cross midnight are split at local midnight so each calendar
    day receives only the time actually worked on that day. Flagged/incomplete
    sessions are excluded until an Administrator verifies and closes them.
    """
    year, month = (int(part) for part in month_key.split("-", 1))
    zone = _zone(freelancer.timezone_name)
    month_start_local = datetime.combine(date(year, month, 1), time.min, tzinfo=zone)
    if month == 12:
        next_month_local = datetime.combine(date(year + 1, 1, 1), time.min, tzinfo=zone)
    else:
        next_month_local = datetime.combine(date(year, month + 1, 1), time.min, tzinfo=zone)
    start_utc = month_start_local.astimezone(timezone.utc)
    end_utc = next_month_local.astimezone(timezone.utc)

    sessions = list(database.scalars(
        select(TaskWorkSession).where(
            TaskWorkSession.freelancer_id == freelancer.id,
            TaskWorkSession.stopped_at.is_not(None),
            TaskWorkSession.started_at < end_utc,
            TaskWorkSession.stopped_at > start_utc,
            TaskWorkSession.status == "STOPPED",
            TaskWorkSession.missed_stop_flag.is_(False),
        ).order_by(TaskWorkSession.started_at, TaskWorkSession.id)
    ).all())

    rows: list[dict[str, Any]] = []
    daily_seconds: dict[date, int] = defaultdict(int)
    grand_seconds = 0

    for session in sessions:
        session_start = max(_aware_utc(session.started_at), start_utc)
        session_stop = min(_aware_utc(session.stopped_at), end_utc)
        if session_stop <= session_start:
            continue
        cursor_local = session_start.astimezone(zone)
        final_local = session_stop.astimezone(zone)
        while cursor_local < final_local:
            next_midnight = datetime.combine(
                cursor_local.date() + timedelta(days=1), time.min, tzinfo=zone
            )
            segment_stop = min(final_local, next_midnight)
            seconds = max(0, int((segment_stop - cursor_local).total_seconds()))
            if seconds:
                duration = format_duration_seconds(seconds)
                rows.append({
                    "date": cursor_local.date(),
                    "day_name": cursor_local.strftime("%A"),
                    "project": session.project_name,
                    "project_code": session.project_code,
                    "task": session.task_title,
                    "discipline": session.discipline or "—",
                    "description": session.notes or "—",
                    "started": cursor_local.strftime("%I:%M:%S %p").lstrip("0"),
                    "stopped": segment_stop.strftime("%I:%M:%S %p").lstrip("0"),
                    **duration,
                })
                daily_seconds[cursor_local.date()] += seconds
                grand_seconds += seconds
            cursor_local = segment_stop

    daily = [
        {"date": day, **format_duration_seconds(seconds)}
        for day, seconds in sorted(daily_seconds.items())
    ]
    return {
        "rows": rows,
        "daily": daily,
        "total": format_duration_seconds(grand_seconds),
        "session_count": len(sessions),
        "worked_day_count": len(daily_seconds),
    }
