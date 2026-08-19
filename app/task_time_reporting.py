"""Clear task and project time-utilization reporting.

Planned time is calculated for tasks with both a Start Date and Deadline. Each
scheduled workday contributes eight hours and active holidays are excluded.
When a task has Work Order / Daily Task time, that recorded time is used as its
actual utilization time. Saved staff review time is added to that production
time. When no production time exists and the task has been completed, the
estimated production time is calculated from Start Date through Completion Date
and saved review time is added on top. Planned time always remains Start Date
through Deadline. This allows early completions to report below 100% and late
completions or review effort to report above 100%.
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
from app.review_work_service import review_minutes_by_task

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


def _time_budget_status(
    target_minutes: Optional[int],
    utilization_minutes: int,
    *,
    uses_completion_fallback: bool = False,
) -> str:
    if target_minutes is None or int(target_minutes) <= 0:
        return "NO_SCHEDULE"
    if uses_completion_fallback:
        return "COMPLETION_FALLBACK"
    if int(utilization_minutes) > int(target_minutes):
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
    review_minutes = review_minutes_by_task(database)
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
        production_recorded_minutes = linked_minutes_by_task.get(int(task.id), 0)
        task_review_minutes = max(0, int(review_minutes.get(int(task.id), 0) or 0))
        recorded_minutes = int(production_recorded_minutes) + task_review_minutes
        included_in_utilization = target_minutes is not None and target_minutes > 0
        completion_date = task.completed_at.date() if task.completed_at else None
        estimated_actual_workdays = (
            _scheduled_workdays(
                task.start_date,
                completion_date,
                workweek=workweek,
                holidays=holidays,
            )
            if production_recorded_minutes <= 0 and completion_date is not None
            else None
        )
        uses_completion_fallback = bool(
            included_in_utilization
            and production_recorded_minutes <= 0
            and estimated_actual_workdays is not None
            and estimated_actual_workdays > 0
        )
        production_utilization_minutes = (
            int(estimated_actual_workdays) * STANDARD_TASK_DAY_MINUTES
            if uses_completion_fallback
            else int(production_recorded_minutes)
        )
        utilization_minutes = production_utilization_minutes + task_review_minutes
        variance_minutes = (
            utilization_minutes - target_minutes
            if included_in_utilization
            else None
        )
        utilization = (
            round(utilization_minutes / target_minutes * 100, 1)
            if included_in_utilization
            else None
        )
        remaining_minutes = (
            max(0, target_minutes - utilization_minutes)
            if included_in_utilization
            else None
        )
        overrun_minutes = (
            max(0, utilization_minutes - target_minutes)
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
            # ``actual_minutes`` remains the compatibility field used by the
            # report templates and exports. It now means effective utilization
            # time: production time (recorded, or completion fallback) plus
            # saved review time.
            "actual_minutes": utilization_minutes,
            "recorded_minutes": recorded_minutes,
            "production_recorded_minutes": int(production_recorded_minutes),
            "review_minutes": task_review_minutes,
            "utilization_minutes": utilization_minutes,
            "planned_fallback_minutes": 0,
            "completion_fallback_minutes": (
                int(production_utilization_minutes) if uses_completion_fallback else 0
            ),
            "uses_planned_fallback": False,
            "uses_completion_fallback": uses_completion_fallback,
            "measured_actual_minutes": utilization_minutes if included_in_utilization else 0,
            "excluded_actual_minutes": utilization_minutes if not included_in_utilization else 0,
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
            "time_budget_status": _time_budget_status(
                target_minutes,
                utilization_minutes,
                uses_completion_fallback=uses_completion_fallback,
            ),
            "included_in_utilization": included_in_utilization,
            "linked_entries": linked_entries,
            "logged_minutes": recorded_minutes,
            "is_estimated_actual": uses_completion_fallback,
            "actual_time_source": (
                "completion_date_fallback_plus_review"
                if uses_completion_fallback and task_review_minutes > 0
                else "completion_date_fallback"
                if uses_completion_fallback
                else "daily_task_entries_plus_review"
                if linked_entries > 0 and task_review_minutes > 0
                else "daily_task_entries"
                if linked_entries > 0
                else "review_time"
                if task_review_minutes > 0
                else "no_time_data"
            ),
            "estimated_workdays": estimated_actual_workdays,
            "completion_date": completion_date.isoformat() if completion_date else "—",
            "contributors": (
                (
                    _contributors_label(linked_member_minutes.get(int(task.id), {}))
                    + (f"; Review: {task_review_minutes // 60}h {task_review_minutes % 60:02d}m" if task_review_minutes >= 60 else f"; Review: {task_review_minutes}m")
                )
                if linked_entries > 0 and task_review_minutes > 0
                else _contributors_label(linked_member_minutes.get(int(task.id), {}))
                if linked_entries > 0
                else (
                    "Completion-date estimate used as production time; "
                    + (f"Review: {task_review_minutes // 60}h {task_review_minutes % 60:02d}m" if task_review_minutes >= 60 else f"Review: {task_review_minutes}m")
                )
                if uses_completion_fallback and task_review_minutes > 0
                else "Completion-date estimate used as production time"
                if uses_completion_fallback
                else (f"Review: {task_review_minutes // 60}h {task_review_minutes % 60:02d}m" if task_review_minutes >= 60 else f"Review: {task_review_minutes}m")
                if task_review_minutes > 0
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
                "recorded_minutes": unlinked_minutes,
                "production_recorded_minutes": unlinked_minutes,
                "review_minutes": 0,
                "utilization_minutes": unlinked_minutes,
                "planned_fallback_minutes": 0,
                "uses_planned_fallback": False,
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

        measured_rows = [
            row for row in task_rows
            if not row["is_unlinked"] and row["included_in_utilization"]
        ]
        target_minutes = sum(int(row["target_minutes"] or 0) for row in measured_rows)
        measured_actual_minutes = sum(
            int(row["utilization_minutes"] or 0) for row in measured_rows
        )
        actual_minutes = sum(
            int(row["utilization_minutes"] or 0) for row in task_rows
        )
        recorded_minutes = sum(
            int(row["recorded_minutes"] or 0) for row in task_rows
        )
        production_recorded_minutes = sum(
            int(row.get("production_recorded_minutes") or 0) for row in task_rows
        )
        project_review_minutes = sum(
            int(row.get("review_minutes") or 0) for row in task_rows
        )
        planned_fallback_minutes = sum(
            int(row["planned_fallback_minutes"] or 0) for row in task_rows
        )
        excluded_actual_minutes = sum(
            int(row["excluded_actual_minutes"] or 0) for row in task_rows
        )
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
            "recorded_minutes": recorded_minutes,
            "production_recorded_minutes": production_recorded_minutes,
            "review_minutes": project_review_minutes,
            "planned_fallback_minutes": planned_fallback_minutes,
            "completion_fallback_minutes": sum(
                int(row.get("completion_fallback_minutes") or 0) for row in task_rows
            ),
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
            "estimated_actual_task_count": sum(
                1 for row in task_rows
                if not row["is_unlinked"] and row.get("uses_completion_fallback")
            ),
            "rows": task_rows,
        })

    # The project overview is ranked by total all-time project effort. This
    # includes recorded time and planned-time substitutions for historical tasks.
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
    total_recorded_project_minutes = sum(
        int(row["recorded_minutes"] or 0) for row in project_rows
    )
    total_production_recorded_minutes = sum(
        int(row.get("production_recorded_minutes") or 0) for row in project_rows
    )
    total_review_minutes = sum(
        int(row.get("review_minutes") or 0) for row in project_rows
    )
    total_planned_fallback_minutes = sum(
        int(row["planned_fallback_minutes"] or 0) for row in project_rows
    )
    total_excluded_actual_minutes = sum(
        int(row["excluded_actual_minutes"] or 0) for row in project_rows
    )
    for rank, row in enumerate(project_rows, start=1):
        row["actual_rank"] = rank

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
            "recorded_project_minutes": total_recorded_project_minutes,
            "production_recorded_minutes": total_production_recorded_minutes,
            "review_minutes": total_review_minutes,
            "planned_fallback_minutes": total_planned_fallback_minutes,
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
            "estimated_actual_task_count": sum(
                int(row["estimated_actual_task_count"] or 0) for row in project_rows
            ),
        },
        "method": {
            "minutes_per_day": STANDARD_TASK_DAY_MINUTES,
            "hours_per_day": 8,
            "holiday_count": len(holidays),
            "workweek": workweek,
            "formula": "Actual time (production recorded, or Start-to-Completion estimate when no production record exists, plus saved review time) ÷ Planned time (Start-to-Deadline) × 100",
        },
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
