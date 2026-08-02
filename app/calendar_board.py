"""Modern deadline and holiday reminder calendar data builder."""
from __future__ import annotations

from calendar import Calendar, month_name
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Holiday, PortalProject, PortalTask

_MONTH_FORMAT = "%Y-%m"
_CLOSED_STATUSES = {"COMPLETED", "CANCELLED"}


def _month_start(month_key: str, today: date) -> date:
    try:
        parsed = date.fromisoformat(f"{month_key}-01")
        return parsed.replace(day=1)
    except (TypeError, ValueError):
        return today.replace(day=1)


def _shift_month(value: date, offset: int) -> date:
    absolute = value.year * 12 + (value.month - 1) + offset
    year, month_zero = divmod(absolute, 12)
    return date(year, month_zero + 1, 1)


def _task_event_state(task: PortalTask, today: date) -> str:
    status = str(task.status or "NOT_STARTED").upper()
    if status == "COMPLETED":
        return "completed"
    if task.due_date and task.due_date < today and status not in _CLOSED_STATUSES:
        return "overdue"
    if status == "FOR_REVIEW":
        return "review"
    if str(task.priority or "").upper() == "URGENT":
        return "urgent"
    return "deadline"


def build_reminder_calendar(
    database: Session,
    *,
    month_key: str = "",
    today: date | None = None,
) -> dict[str, Any]:
    """Return a Monday-first month board containing task deadlines and holidays."""
    current_day = today or date.today()
    first_day = _month_start(month_key, current_day)
    next_month = _shift_month(first_day, 1)
    previous_month = _shift_month(first_day, -1)

    weeks = Calendar(firstweekday=0).monthdatescalendar(first_day.year, first_day.month)
    while len(weeks) < 6:
        next_start = weeks[-1][-1] + timedelta(days=1)
        weeks.append([next_start + timedelta(days=index) for index in range(7)])
    grid_start = weeks[0][0]
    grid_end = weeks[-1][-1] + timedelta(days=1)

    projects = {
        int(project.id): project
        for project in database.scalars(select(PortalProject)).all()
    }
    tasks = list(
        database.scalars(
            select(PortalTask)
            .where(
                PortalTask.due_date.is_not(None),
                PortalTask.due_date >= grid_start,
                PortalTask.due_date < grid_end,
                PortalTask.status != "CANCELLED",
            )
            .order_by(PortalTask.due_date, PortalTask.priority.desc(), PortalTask.title)
        ).all()
    )
    holidays = list(
        database.scalars(
            select(Holiday)
            .where(
                Holiday.holiday_date >= grid_start,
                Holiday.holiday_date < grid_end,
                Holiday.is_active.is_(True),
            )
            .order_by(Holiday.holiday_date, Holiday.name)
        ).all()
    )

    events_by_date: dict[date, list[dict[str, Any]]] = {}
    all_events: list[dict[str, Any]] = []

    for holiday in holidays:
        event = {
            "date": holiday.holiday_date,
            "kind": "holiday",
            "state": "holiday",
            "title": str(holiday.name),
            "subtitle": str(holiday.holiday_type or "COMPANY").replace("_", " ").title(),
            "href": "/admin/hr/calendar?month=" + holiday.holiday_date.strftime(_MONTH_FORMAT),
            "is_holiday": True,
            "is_deadline": False,
        }
        events_by_date.setdefault(holiday.holiday_date, []).append(event)
        all_events.append(event)

    for task in tasks:
        project = projects.get(int(task.project_id))
        due_date = task.due_date
        if due_date is None:
            continue
        state = _task_event_state(task, current_day)
        event = {
            "date": due_date,
            "kind": "deadline",
            "state": state,
            "title": str(task.title),
            "subtitle": str(project.name if project else "Project"),
            "project_name": str(project.name if project else "Project"),
            "status": str(task.status or "NOT_STARTED"),
            "priority": str(task.priority or "NORMAL"),
            "progress": int(task.progress or 0),
            "href": "/portal/tasks?view=" + ("completed" if state == "completed" else "active"),
            "is_holiday": False,
            "is_deadline": True,
        }
        events_by_date.setdefault(due_date, []).append(event)
        all_events.append(event)

    state_order = {
        "holiday": 0,
        "overdue": 1,
        "urgent": 2,
        "review": 3,
        "deadline": 4,
        "completed": 5,
    }
    for event_rows in events_by_date.values():
        event_rows.sort(
            key=lambda row: (
                state_order.get(str(row["state"]), 9),
                str(row["title"]).casefold(),
            )
        )

    cells: list[dict[str, Any]] = []
    for week_index, week in enumerate(weeks):
        for day_value in week:
            day_events = events_by_date.get(day_value, [])
            cells.append({
                "date": day_value,
                "date_key": day_value.isoformat(),
                "day_number": day_value.day,
                "week_index": week_index,
                "in_month": day_value.month == first_day.month,
                "is_today": day_value == current_day,
                "is_weekend": day_value.weekday() >= 5,
                "events": day_events,
                "event_count": len(day_events),
                "states": sorted({str(row["state"]) for row in day_events}),
            })

    month_events = [row for row in all_events if first_day <= row["date"] < next_month]
    month_events.sort(key=lambda row: (row["date"], state_order.get(str(row["state"]), 9), str(row["title"]).casefold()))
    upcoming = [row for row in all_events if row["date"] >= current_day]
    upcoming.sort(key=lambda row: (row["date"], state_order.get(str(row["state"]), 9), str(row["title"]).casefold()))
    overdue = [row for row in all_events if row["state"] == "overdue"]
    overdue.sort(key=lambda row: (row["date"], str(row["title"]).casefold()))

    return {
        "month_key": first_day.strftime(_MONTH_FORMAT),
        "month_label": f"{month_name[first_day.month]} {first_day.year}",
        "previous_month": previous_month.strftime(_MONTH_FORMAT),
        "next_month": next_month.strftime(_MONTH_FORMAT),
        "today_month": current_day.strftime(_MONTH_FORMAT),
        "weekdays": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
        "cells": cells,
        "month_events": month_events,
        "upcoming_events": upcoming[:10],
        "overdue_events": overdue[:6],
        "summary": {
            "deadline_count": sum(1 for row in month_events if row["is_deadline"]),
            "holiday_count": sum(1 for row in month_events if row["is_holiday"]),
            "overdue_count": sum(1 for row in month_events if row["state"] == "overdue"),
            "event_days": len({row["date"] for row in month_events}),
        },
        "generated_on": current_day.isoformat(),
    }
