"""Clear task time-budget reporting.

Planned time is calculated only for tasks with both a Start Date and Deadline.
Each scheduled workday contributes eight hours and active holidays are excluded.
Recorded time comes only from linked Daily Task / Work Order records. The
utilization percentage compares the same measurable population on both sides:
recorded time on scheduled tasks divided by planned time for those scheduled
tasks. Unscheduled, unlinked, and unmatched work remains visible but is excluded
from the percentage so it cannot silently inflate the result.
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


def _time_budget_status(target_minutes: Optional[int], actual_minutes: int) -> str:
    if target_minutes is None or int(target_minutes) <= 0:
        return "NO_SCHEDULE"
    if int(actual_minutes) <= 0:
        return "NO_TIME"
    if int(actual_minutes) > int(target_minutes):
        return "OVER_PLAN"
    return "WITHIN_PLAN"


def build_task_time_utilization(
    database: Session,
    *,
    project_id: int = 0,
) -> dict[str, Any]:
    """Build project and task time-budget reporting with a transparent formula."""
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

    for row in database.scalars(select(DailyTask)).all():
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
            if workdays is not None and workdays > 0
            else None
        )
        linked_entries = linked_entries_by_task.get(int(task.id), 0)
        actual_minutes = linked_minutes_by_task.get(int(task.id), 0)
        included_in_utilization = target_minutes is not None and target_minutes > 0
        variance_minutes = (
            actual_minutes - target_minutes
            if included_in_utilization
            else None
        )
        utilization = (
            round(actual_minutes / target_minutes * 100, 1)
            if included_in_utilization
            else None
        )
        remaining_minutes = (
            max(0, target_minutes - actual_minutes)
            if included_in_utilization
            else None
        )
        overrun_minutes = (
            max(0, actual_minutes - target_minutes)
            if included_in_utilization
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
            "measured_actual_minutes": actual_minutes if included_in_utilization else 0,
            "excluded_actual_minutes": actual_minutes if not included_in_utilization else 0,
            "variance_minutes": variance_minutes,
            "variance_absolute_minutes": abs(variance_minutes) if variance_minutes is not None else None,
            "variance_direction": (
                "over" if variance_minutes is not None and variance_minutes > 0
                else "under" if variance_minutes is not None and variance_minutes < 0
                else "target" if variance_minutes == 0
                else "none"
            ),
            "variance_label": _variance_label(variance_minutes),
            "remaining_minutes": remaining_minutes,
            "overrun_minutes": overrun_minutes,
            "utilization": utilization,
            "time_budget_status": _time_budget_status(target_minutes, actual_minutes),
            "included_in_utilization": included_in_utilization,
            "linked_entries": linked_entries,
            "logged_minutes": actual_minutes,
            "is_estimated_actual": False,
            "actual_time_source": "daily_task_entries" if linked_entries > 0 else "no_time_data",
            "estimated_workdays": None,
            "completion_date": task.completed_at.date().isoformat() if task.completed_at else "—",
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
                "measured_actual_minutes": 0,
                "excluded_actual_minutes": unlinked_minutes,
                "variance_minutes": None,
                "variance_absolute_minutes": None,
                "variance_direction": "none",
                "variance_label": "Excluded from utilization",
                "remaining_minutes": None,
                "overrun_minutes": None,
                "utilization": None,
                "time_budget_status": "NO_SCHEDULE",
                "included_in_utilization": False,
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

        measured_rows = [
            row for row in task_rows
            if not row["is_unlinked"] and row["included_in_utilization"]
        ]
        target_minutes = sum(int(row["target_minutes"] or 0) for row in measured_rows)
        measured_actual_minutes = sum(int(row["actual_minutes"] or 0) for row in measured_rows)
        actual_minutes = sum(int(row["actual_minutes"] or 0) for row in task_rows)
        excluded_actual_minutes = max(0, actual_minutes - measured_actual_minutes)
        variance_minutes = (
            measured_actual_minutes - target_minutes
            if target_minutes > 0
            else None
        )
        utilization = (
            round(measured_actual_minutes / target_minutes * 100, 1)
            if target_minutes > 0
            else None
        )
        remaining_minutes = (
            max(0, target_minutes - measured_actual_minutes)
            if target_minutes > 0
            else None
        )
        overrun_minutes = (
            max(0, measured_actual_minutes - target_minutes)
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
            "targeted_task_count": len(measured_rows),
            "measured_task_count": len(measured_rows),
            "missing_target_count": sum(
                1 for row in task_rows
                if not row["is_unlinked"] and not row["included_in_utilization"]
            ),
            "target_minutes": target_minutes if target_minutes > 0 else None,
            "measured_actual_minutes": measured_actual_minutes,
            "actual_minutes": actual_minutes,
            "excluded_actual_minutes": excluded_actual_minutes,
            "variance_minutes": variance_minutes,
            "variance_absolute_minutes": abs(variance_minutes) if variance_minutes is not None else None,
            "variance_direction": (
                "over" if variance_minutes is not None and variance_minutes > 0
                else "under" if variance_minutes is not None and variance_minutes < 0
                else "target" if variance_minutes == 0
                else "none"
            ),
            "variance_label": _variance_label(variance_minutes),
            "remaining_minutes": remaining_minutes,
            "overrun_minutes": overrun_minutes,
            "utilization": utilization,
            "unlinked_minutes": unlinked_minutes,
            "estimated_actual_task_count": 0,
            "rows": task_rows,
        })

    # The project overview is intentionally ranked by total recorded effort.
    project_rows.sort(
        key=lambda item: (
            -int(item["actual_minutes"] or 0),
            item["name"].casefold(),
        )
    )

    total_target_minutes = sum(
        int(row["target_minutes"] or 0)
        for row in project_rows
        if row["target_minutes"] is not None
    )
    total_measured_actual_minutes = sum(
        int(row["measured_actual_minutes"] or 0) for row in project_rows
    )
    total_actual_project_minutes = sum(
        int(row["actual_minutes"] or 0) for row in project_rows
    )
    total_excluded_actual_minutes = max(
        0, total_actual_project_minutes - total_measured_actual_minutes
    )
    maximum_project_actual_minutes = max(
        (int(row["actual_minutes"] or 0) for row in project_rows),
        default=0,
    )
    for rank, row in enumerate(project_rows, start=1):
        actual_minutes = int(row["actual_minutes"] or 0)
        row["actual_rank"] = rank
        row["actual_share_percent"] = (
            round(actual_minutes / total_actual_project_minutes * 100, 1)
            if total_actual_project_minutes > 0
            else 0.0
        )
        row["actual_bar_percent"] = (
            round(actual_minutes / maximum_project_actual_minutes * 100, 1)
            if maximum_project_actual_minutes > 0
            else 0.0
        )

    top_project = project_rows[0] if project_rows else None
    total_variance_minutes = (
        total_measured_actual_minutes - total_target_minutes
        if total_target_minutes > 0
        else None
    )
    overall_utilization = (
        round(total_measured_actual_minutes / total_target_minutes * 100, 1)
        if total_target_minutes > 0
        else None
    )
    remaining_minutes = (
        max(0, total_target_minutes - total_measured_actual_minutes)
        if total_target_minutes > 0
        else None
    )
    overrun_minutes = (
        max(0, total_measured_actual_minutes - total_target_minutes)
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
            "targeted_task_count": sum(row["targeted_task_count"] for row in project_rows),
            "missing_target_task_count": sum(row["missing_target_count"] for row in project_rows),
            "target_minutes": total_target_minutes if total_target_minutes > 0 else None,
            "measured_actual_minutes": total_measured_actual_minutes,
            "actual_project_minutes": total_actual_project_minutes,
            "excluded_actual_minutes": total_excluded_actual_minutes,
            "top_project_name": top_project["name"] if top_project else "—",
            "top_project_actual_minutes": int(top_project["actual_minutes"] or 0) if top_project else 0,
            "variance_minutes": total_variance_minutes,
            "variance_absolute_minutes": abs(total_variance_minutes) if total_variance_minutes is not None else None,
            "variance_direction": (
                "over" if total_variance_minutes is not None and total_variance_minutes > 0
                else "under" if total_variance_minutes is not None and total_variance_minutes < 0
                else "target" if total_variance_minutes == 0
                else "none"
            ),
            "variance_label": _variance_label(total_variance_minutes),
            "remaining_minutes": remaining_minutes,
            "overrun_minutes": overrun_minutes,
            "utilization": overall_utilization,
            "unlinked_project_minutes": sum(int(row["unlinked_minutes"] or 0) for row in project_rows),
            "unmatched_minutes": unmatched_minutes,
            "unmatched_entries": unmatched_entries,
            "estimated_actual_task_count": 0,
        },
        "method": {
            "minutes_per_day": STANDARD_TASK_DAY_MINUTES,
            "hours_per_day": 8,
            "holiday_count": len(holidays),
            "workweek": workweek,
            "formula": "Recorded time on scheduled tasks ÷ Planned time for those same tasks × 100",
        },
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
