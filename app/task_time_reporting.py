"""Task target-versus-actual time utilization reporting.

Target time is a management planning estimate calculated from scheduled
workdays between a task's start date and deadline, inclusive. Each counted
workday contributes a fixed eight hours (480 minutes). Active company holidays
are excluded. Actual time comes from freelancer Daily Task records linked to the portal task.
When a completed task has no Daily Task time yet, the report uses an explicitly
labelled estimate from Start Date through Completion Date at eight scheduled
hours per workday. Unlinked daily work is retained at project level so
management can still see the full amount of effort logged against a project.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    DailyTask,
    Freelancer,
    Holiday,
    PortalProject,
    PortalTask,
    PortalTaskAssignment,
    ProjectMember,
    WorkSchedule,
)

CLOSED_TASK_STATUSES = {"COMPLETED", "CANCELLED"}
STANDARD_TASK_DAY_MINUTES = 480
DAY_FIELDS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


def _normalized(value: object) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _active_workweek(database: Session) -> tuple[bool, ...]:
    schedule = database.scalar(
        select(WorkSchedule)
        .where(WorkSchedule.is_active.is_(True))
        .order_by(WorkSchedule.id)
    )
    if schedule is None:
        return (True, True, True, True, True, False, False)
    return tuple(bool(getattr(schedule, field)) for field in DAY_FIELDS)


def _active_holidays(database: Session) -> set[date]:
    return {
        row.holiday_date
        for row in database.scalars(
            select(Holiday).where(Holiday.is_active.is_(True))
        ).all()
    }


def _scheduled_workdays(
    start: Optional[date],
    deadline: Optional[date],
    *,
    workweek: tuple[bool, ...],
    holidays: set[date],
) -> Optional[int]:
    if start is None or deadline is None or deadline < start:
        return None
    days = 0
    cursor = start
    while cursor <= deadline:
        if workweek[cursor.weekday()] and cursor not in holidays:
            days += 1
        cursor += timedelta(days=1)
    return days


def _member_display_maps(database: Session) -> tuple[dict[int, str], dict[int, str]]:
    freelancers = {
        int(row.id): str(row.full_name or row.freelancer_code or f"Member {row.id}")
        for row in database.scalars(select(Freelancer)).all()
    }
    assignment_names = dict(freelancers)
    for member in database.scalars(select(ProjectMember)).all():
        if member.source_freelancer_id is None:
            continue
        source_id = int(member.source_freelancer_id)
        if member.freelancer_id is not None and int(member.freelancer_id) in freelancers:
            assignment_names[source_id] = freelancers[int(member.freelancer_id)]
        else:
            assignment_names[source_id] = str(
                member.member_name or member.member_code or f"Member {source_id}"
            )
    return freelancers, assignment_names


def _duration_parts(minutes: Optional[int]) -> dict[str, Any]:
    if minutes is None:
        return {"minutes": None, "hours": None}
    value = int(minutes)
    return {"minutes": value, "hours": round(value / 60, 1)}


def _variance_label(minutes: Optional[int]) -> str:
    if minutes is None:
        return "—"
    value = int(minutes)
    if value == 0:
        return "On target"
    absolute = abs(value)
    hours, remainder = divmod(absolute, 60)
    duration = f"{hours}h {remainder:02d}m" if hours else f"{remainder}m"
    return f"{duration} over" if value > 0 else f"{duration} under"


def _contributors_label(values: dict[str, int]) -> str:
    if not values:
        return "—"
    ordered = sorted(values.items(), key=lambda item: (-item[1], item[0].casefold()))
    parts: list[str] = []
    for name, minutes in ordered:
        hours, remainder = divmod(max(0, int(minutes)), 60)
        duration = f"{hours}h {remainder:02d}m" if hours else f"{remainder}m"
        parts.append(f"{name}: {duration}")
    return "; ".join(parts)


def build_task_time_utilization(
    database: Session,
    *,
    project_id: int = 0,
) -> dict[str, Any]:
    """Build project > task > target time > actual time reporting data."""
    workweek = _active_workweek(database)
    holidays = _active_holidays(database)
    freelancer_names, assignment_names = _member_display_maps(database)

    projects = {
        int(row.id): row
        for row in database.scalars(select(PortalProject)).all()
    }
    tasks = list(
        database.scalars(
            select(PortalTask).order_by(
                PortalTask.project_id,
                PortalTask.status,
                PortalTask.due_date,
                PortalTask.id,
            )
        ).all()
    )
    if project_id and project_id in projects:
        tasks = [task for task in tasks if int(task.project_id) == int(project_id)]

    task_ids = {int(task.id) for task in tasks}
    assignment_values: dict[int, list[str]] = defaultdict(list)
    if task_ids:
        for task_id, freelancer_id in database.execute(
            select(
                PortalTaskAssignment.task_id,
                PortalTaskAssignment.freelancer_id,
            ).where(PortalTaskAssignment.task_id.in_(tuple(task_ids)))
        ).all():
            name = assignment_names.get(int(freelancer_id), f"Member {int(freelancer_id)}")
            if name not in assignment_values[int(task_id)]:
                assignment_values[int(task_id)].append(name)

    project_by_code = {
        _normalized(row.project_code): int(row.id)
        for row in projects.values()
        if _normalized(row.project_code)
    }
    project_by_name = {
        _normalized(row.name): int(row.id)
        for row in projects.values()
        if _normalized(row.name)
    }

    linked_minutes_by_task: dict[int, int] = defaultdict(int)
    linked_entries_by_task: dict[int, int] = defaultdict(int)
    linked_member_minutes: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    unlinked_project_minutes: dict[int, int] = defaultdict(int)
    unlinked_project_entries: dict[int, int] = defaultdict(int)
    unlinked_project_members: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    unmatched_minutes = 0
    unmatched_entries = 0

    daily_rows = list(database.scalars(select(DailyTask)).all())
    for row in daily_rows:
        minutes = max(0, int(row.minutes_spent or 0))
        member_name = freelancer_names.get(int(row.freelancer_id), f"Member {int(row.freelancer_id)}")
        if row.portal_task_id is not None and int(row.portal_task_id) in task_ids:
            task_id = int(row.portal_task_id)
            linked_minutes_by_task[task_id] += minutes
            linked_entries_by_task[task_id] += 1
            linked_member_minutes[task_id][member_name] += minutes
            continue

        matched_project_id = project_by_code.get(_normalized(row.project_code))
        if matched_project_id is None:
            matched_project_id = project_by_name.get(_normalized(row.project_name))
        if matched_project_id is not None and (not project_id or matched_project_id == project_id):
            unlinked_project_minutes[matched_project_id] += minutes
            unlinked_project_entries[matched_project_id] += 1
            unlinked_project_members[matched_project_id][member_name] += minutes
        elif not project_id:
            unmatched_minutes += minutes
            unmatched_entries += 1

    rows_by_project: dict[int, list[dict[str, Any]]] = defaultdict(list)
    today = date.today()
    for task in tasks:
        status = str(task.status or "NOT_STARTED").upper()
        workdays = _scheduled_workdays(
            task.start_date,
            task.due_date,
            workweek=workweek,
            holidays=holidays,
        )
        target_minutes = (
            workdays * STANDARD_TASK_DAY_MINUTES
            if workdays is not None
            else None
        )
        linked_entries = linked_entries_by_task.get(int(task.id), 0)
        logged_minutes = linked_minutes_by_task.get(int(task.id), 0)
        completion_date = task.completed_at.date() if task.completed_at is not None else None
        estimated_workdays = None
        is_estimated_actual = False
        if linked_entries == 0 and task.start_date is not None and completion_date is not None:
            estimated_workdays = _scheduled_workdays(
                task.start_date,
                completion_date,
                workweek=workweek,
                holidays=holidays,
            )
            if estimated_workdays is not None:
                actual_minutes = estimated_workdays * STANDARD_TASK_DAY_MINUTES
                is_estimated_actual = True
            else:
                actual_minutes = 0
        else:
            actual_minutes = logged_minutes
        variance_minutes = (
            actual_minutes - target_minutes
            if target_minutes is not None
            else None
        )
        utilization = (
            round(actual_minutes / target_minutes * 100, 1)
            if target_minutes and target_minutes > 0
            else None
        )
        rows_by_project[int(task.project_id)].append({
            "id": int(task.id),
            "title": str(task.title or f"Task {task.id}"),
            "status": status,
            "is_closed": status in CLOSED_TASK_STATUSES,
            "is_delayed": (
                status not in CLOSED_TASK_STATUSES
                and task.due_date is not None
                and task.due_date < today
            ),
            "assignees": ", ".join(sorted(assignment_values.get(int(task.id), []), key=str.casefold)) or "Unassigned",
            "start_date": task.start_date.isoformat() if task.start_date else "—",
            "deadline": task.due_date.isoformat() if task.due_date else "—",
            "scheduled_workdays": workdays,
            "target_minutes": target_minutes,
            "actual_minutes": actual_minutes,
            "variance_minutes": variance_minutes,
            "variance_absolute_minutes": abs(variance_minutes) if variance_minutes is not None else None,
            "variance_direction": ("over" if variance_minutes is not None and variance_minutes > 0 else ("under" if variance_minutes is not None and variance_minutes < 0 else "target" if variance_minutes == 0 else "none")),
            "variance_label": _variance_label(variance_minutes),
            "utilization": utilization,
            "linked_entries": linked_entries,
            "logged_minutes": logged_minutes,
            "is_estimated_actual": is_estimated_actual,
            "actual_time_source": (
                "completion_date_estimate" if is_estimated_actual
                else ("daily_task_entries" if linked_entries > 0 else "no_time_data")
            ),
            "estimated_workdays": estimated_workdays,
            "completion_date": completion_date.isoformat() if completion_date else "—",
            "contributors": (
                _contributors_label(linked_member_minutes.get(int(task.id), {}))
                if linked_entries > 0
                else "—"
            ),
            "is_unlinked": False,
        })

    project_rows: list[dict[str, Any]] = []
    selected_project_ids = (
        [int(project_id)]
        if project_id and int(project_id) in projects
        else sorted(projects)
    )
    for current_project_id in selected_project_ids:
        project = projects[current_project_id]
        task_rows = rows_by_project.get(current_project_id, [])
        task_rows.sort(
            key=lambda item: (
                item["is_closed"],
                not item["is_delayed"],
                item["deadline"] == "—",
                item["deadline"],
                item["title"].casefold(),
            )
        )

        unlinked_minutes = unlinked_project_minutes.get(current_project_id, 0)
        if unlinked_minutes > 0:
            task_rows.append({
                "id": 0,
                "title": "Unlinked / General Project Work",
                "status": "UNLINKED_WORK",
                "is_closed": True,
                "is_delayed": False,
                "assignees": "—",
                "start_date": "—",
                "deadline": "—",
                "scheduled_workdays": None,
                "target_minutes": None,
                "actual_minutes": unlinked_minutes,
                "variance_minutes": None,
                "variance_absolute_minutes": None,
                "variance_direction": "none",
                "variance_label": "No task target",
                "utilization": None,
                "linked_entries": unlinked_project_entries.get(current_project_id, 0),
                "logged_minutes": unlinked_minutes,
                "is_estimated_actual": False,
                "actual_time_source": "unlinked_daily_task_entries",
                "estimated_workdays": None,
                "completion_date": "—",
                "contributors": _contributors_label(unlinked_project_members.get(current_project_id, {})),
                "is_unlinked": True,
            })

        if not task_rows:
            continue

        known_target_rows = [row for row in task_rows if row["target_minutes"] is not None]
        target_minutes = sum(int(row["target_minutes"] or 0) for row in known_target_rows)
        actual_minutes = sum(int(row["actual_minutes"] or 0) for row in task_rows)
        variance_minutes = actual_minutes - target_minutes if known_target_rows else None
        utilization = (
            round(actual_minutes / target_minutes * 100, 1)
            if target_minutes > 0
            else None
        )
        project_rows.append({
            "id": current_project_id,
            "name": str(project.name or project.project_code),
            "code": str(project.project_code or ""),
            "discipline": str(project.discipline or "—"),
            "status": str(project.status or "ACTIVE"),
            "task_count": sum(1 for row in task_rows if not row["is_unlinked"]),
            "active_task_count": sum(1 for row in task_rows if not row["is_unlinked"] and not row["is_closed"]),
            "targeted_task_count": len(known_target_rows),
            "missing_target_count": sum(1 for row in task_rows if not row["is_unlinked"] and row["target_minutes"] is None),
            "target_minutes": target_minutes if known_target_rows else None,
            "actual_minutes": actual_minutes,
            "variance_minutes": variance_minutes,
            "variance_absolute_minutes": abs(variance_minutes) if variance_minutes is not None else None,
            "variance_direction": ("over" if variance_minutes is not None and variance_minutes > 0 else ("under" if variance_minutes is not None and variance_minutes < 0 else "target" if variance_minutes == 0 else "none")),
            "variance_label": _variance_label(variance_minutes),
            "utilization": utilization,
            "unlinked_minutes": unlinked_minutes,
            "estimated_actual_task_count": sum(
                1 for row in task_rows if row.get("is_estimated_actual")
            ),
            "rows": task_rows,
        })

    project_rows.sort(
        key=lambda item: (
            item["active_task_count"] == 0,
            -int(item["actual_minutes"] or 0),
            item["name"].casefold(),
        )
    )

    total_target_minutes = sum(
        int(row["target_minutes"] or 0)
        for row in project_rows
        if row["target_minutes"] is not None
    )
    total_actual_project_minutes = sum(int(row["actual_minutes"] or 0) for row in project_rows)
    total_variance_minutes = (
        total_actual_project_minutes - total_target_minutes
        if total_target_minutes > 0
        else None
    )
    overall_utilization = (
        round(total_actual_project_minutes / total_target_minutes * 100, 1)
        if total_target_minutes > 0
        else None
    )

    project_options = [
        {"id": int(project.id), "name": str(project.name or project.project_code)}
        for project in sorted(projects.values(), key=lambda item: str(item.name).casefold())
    ]

    return {
        "selected_project_id": int(project_id or 0),
        "project_options": project_options,
        "projects": project_rows,
        "summary": {
            "project_count": len(project_rows),
            "task_count": sum(row["task_count"] for row in project_rows),
            "target_minutes": total_target_minutes if total_target_minutes > 0 else None,
            "actual_project_minutes": total_actual_project_minutes,
            "variance_minutes": total_variance_minutes,
            "variance_absolute_minutes": abs(total_variance_minutes) if total_variance_minutes is not None else None,
            "variance_direction": ("over" if total_variance_minutes is not None and total_variance_minutes > 0 else ("under" if total_variance_minutes is not None and total_variance_minutes < 0 else "target" if total_variance_minutes == 0 else "none")),
            "variance_label": _variance_label(total_variance_minutes),
            "utilization": overall_utilization,
            "unmatched_minutes": unmatched_minutes,
            "unmatched_entries": unmatched_entries,
            "estimated_actual_task_count": sum(
                row.get("estimated_actual_task_count", 0) for row in project_rows
            ),
        },
        "method": {
            "minutes_per_day": STANDARD_TASK_DAY_MINUTES,
            "hours_per_day": 8,
            "holiday_count": len(holidays),
            "workweek": workweek,
        },
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
