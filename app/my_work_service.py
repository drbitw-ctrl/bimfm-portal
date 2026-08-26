"""Role-aware My Work dashboard data builders.

The staff My Work page is intentionally role-specific:
- Administrators see operational tasks, team availability, and pending requests.
- Supervisors see read-only task and availability registers.
- Finance sees attendance and DTR preparation summaries.
"""
from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.config import DEFAULT_TIMEZONE
from app.finance_service import finance_rows
from app.models import (
    AttendanceCorrection,
    DailyAttendance,
    Freelancer,
    FreelancerAccount,
    LeaveRequest,
    MonthlyDTR,
    OvertimeClaim,
    PortalTask,
)
from app.portal_project_service import (
    active_task_overview_rows,
    team_assignment_rows,
    unassigned_task_overview_rows,
)
from app.work_order_service import live_work_rows

PENDING_OVERTIME_STATES = (
    "PENDING",
    "PENDING_PLAN",
    "PENDING_FINAL",
    "PENDING_FINAL_MISSING",
)


def _zone(name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(str(name or DEFAULT_TIMEZONE))
    except ZoneInfoNotFoundError:
        return ZoneInfo(DEFAULT_TIMEZONE)


def _local_time(value: datetime | None, timezone_name: str | None) -> str:
    if value is None:
        return "—"
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(_zone(timezone_name)).strftime("%H:%M")


def _task_highlight(status: str, due_date_value: object) -> str:
    normalized = str(status or "").strip().upper()
    if normalized == "COMPLETED":
        return "task-row-completed"
    if normalized == "CANCELLED":
        return ""
    due_text = str(due_date_value or "").strip()
    if due_text and due_text != "—":
        try:
            if date.fromisoformat(due_text) < date.today():
                return "task-row-delayed"
        except ValueError:
            pass
    if normalized in {"IN_PROGRESS", "FOR_REVIEW"}:
        return "task-row-attention"
    return ""


def active_task_rows(database: Session, *, limit: int = 500) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source in active_task_overview_rows(database, limit=limit):
        status = str(source.get("status") or "")
        due_date = source.get("due_date") or "—"
        rows.append({
            "id": int(source["id"]),
            "project": str(source.get("project_name") or "—"),
            "task": str(source.get("title") or "—"),
            "member": str(source.get("assignees") or "Unassigned"),
            "status": status,
            "priority": str(source.get("priority") or "NORMAL"),
            "discipline": str(source.get("discipline") or "—"),
            "progress": int(source.get("progress") or 0),
            "deadline": str(due_date),
            "row_class": _task_highlight(status, due_date),
            "task_state": "ongoing",
        })
    return rows


def unassigned_task_rows(database: Session, *, limit: int = 100) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source in unassigned_task_overview_rows(database, limit=limit):
        due_date = str(source.get("due_date") or "—")
        rows.append({
            "id": int(source["id"]),
            "project": str(source.get("project_name") or "—"),
            "task": str(source.get("title") or "—"),
            "status": str(source.get("status") or "NOT_STARTED"),
            "priority": str(source.get("priority") or "NORMAL"),
            "discipline": str(source.get("discipline") or "—"),
            "progress": int(source.get("progress") or 0),
            "start_date": str(source.get("start_date") or "—"),
            "deadline": due_date,
            "row_class": _task_highlight(str(source.get("status") or ""), due_date),
            "href": f"/portal/tasks/{int(source['id'])}/edit",
        })
    return rows


def team_availability_rows(database: Session) -> list[dict[str, Any]]:
    live_by_member = {
        int(row["freelancer_id"]): row
        for row in live_work_rows(database)
    }
    rows: list[dict[str, Any]] = []
    for source in team_assignment_rows(database):
        freelancer_id = int(source["freelancer_id"])
        live = live_by_member.get(freelancer_id)
        active_count = int(source.get("active_task_count") or 0)
        overdue_count = int(source.get("overdue_task_count") or 0)
        if overdue_count:
            state = "overdue"
            availability = "Overdue"
            row_class = "availability-row-overdue"
        elif live:
            state = "working"
            availability = "Working Now"
            row_class = "availability-row-working"
        elif active_count:
            state = "assigned"
            availability = "Assigned"
            row_class = "availability-row-assigned"
        else:
            state = "available"
            availability = "Available"
            row_class = "availability-row-available"
        rows.append({
            "freelancer_id": freelancer_id,
            "name": str(source.get("name") or "—"),
            "code": str(source.get("member_code") or source.get("code") or ""),
            "join_date": str(source.get("join_date") or "—"),
            "availability": availability,
            "state": state,
            "row_class": row_class,
            "working_task": str(live.get("task_title") or "No active task") if live else "No active task",
            "working_project": str(live.get("project_name") or "—") if live else "—",
            "elapsed_minutes": int(live.get("elapsed_minutes") or 0) if live else None,
            "active_tasks": active_count,
            "overdue_tasks": overdue_count,
            "assignment_status": str(source.get("assignment_status") or "—"),
        })
    state_order = {"overdue": 0, "working": 1, "assigned": 2, "available": 3}
    rows.sort(key=lambda row: (state_order[row["state"]], str(row["name"]).casefold()))
    return rows


def administrator_request_overview(database: Session, *, limit: int = 8) -> dict[str, Any]:
    freelancer_names = {
        int(row.id): row.full_name
        for row in database.scalars(select(Freelancer)).all()
    }

    leave_rows = []
    for item in database.scalars(
        select(LeaveRequest)
        .where(LeaveRequest.status == "PENDING")
        .order_by(LeaveRequest.submitted_at.desc())
        .limit(limit)
    ).all():
        leave_rows.append({
            "id": int(item.id),
            "member": freelancer_names.get(int(item.freelancer_id), "—"),
            "date": item.leave_date.isoformat(),
            "type": str(item.leave_type or "Leave"),
            "reason": str(item.reason or ""),
            "href": "/admin/leave-requests",
        })

    overtime_rows = []
    for item in database.scalars(
        select(OvertimeClaim)
        .where(OvertimeClaim.status.in_(PENDING_OVERTIME_STATES))
        .order_by(OvertimeClaim.submitted_at.desc())
        .limit(limit)
    ).all():
        overtime_rows.append({
            "id": int(item.id),
            "member": freelancer_names.get(int(item.freelancer_id), "—"),
            "date": item.attendance_date.isoformat(),
            "type": str(item.status or "PENDING"),
            "reason": str(item.work_description or ""),
            "href": "/admin/overtime",
        })

    cutoff = date.today() - timedelta(days=31)
    issue_rows = []
    correction_counts = {
        int(daily_id): int(count)
        for daily_id, count in database.execute(
            select(
                AttendanceCorrection.daily_attendance_id,
                func.count(AttendanceCorrection.id),
            ).group_by(AttendanceCorrection.daily_attendance_id)
        ).all()
    }
    attendance_items = list(database.scalars(
        select(DailyAttendance)
        .where(
            DailyAttendance.attendance_date >= cutoff,
            DailyAttendance.review_status == "UNREVIEWED",
            or_(
                DailyAttendance.time_in_utc.is_(None),
                DailyAttendance.time_out_utc.is_(None),
                DailyAttendance.time_out_utc <= DailyAttendance.time_in_utc,
            ),
        )
        .order_by(DailyAttendance.attendance_date.desc(), DailyAttendance.id.desc())
        .limit(limit)
    ).all())
    for item in attendance_items:
        if item.time_in_utc is None and item.time_out_utc is None:
            issue = "Missing Time In and Time Out"
        elif item.time_in_utc is None:
            issue = "Missing Time In"
        elif item.time_out_utc is None:
            issue = "Missing Time Out"
        else:
            issue = "Invalid Time Out"
        issue_rows.append({
            "id": int(item.id),
            "member": freelancer_names.get(int(item.freelancer_id), "—"),
            "date": item.attendance_date.isoformat(),
            "issue": issue,
            "corrections": correction_counts.get(int(item.id), 0),
            "href": f"/admin/attendance/{item.freelancer_id}/{item.attendance_date.isoformat()}/correct",
        })

    leave_count = int(database.scalar(
        select(func.count(LeaveRequest.id)).where(LeaveRequest.status == "PENDING")
    ) or 0)
    overtime_count = int(database.scalar(
        select(func.count(OvertimeClaim.id)).where(OvertimeClaim.status.in_(PENDING_OVERTIME_STATES))
    ) or 0)
    attendance_issue_count = int(database.scalar(
        select(func.count(DailyAttendance.id)).where(
            DailyAttendance.attendance_date >= cutoff,
            DailyAttendance.review_status == "UNREVIEWED",
            or_(
                DailyAttendance.time_in_utc.is_(None),
                DailyAttendance.time_out_utc.is_(None),
                DailyAttendance.time_out_utc <= DailyAttendance.time_in_utc,
            ),
        )
    ) or 0)
    return {
        "leave_count": leave_count,
        "overtime_count": overtime_count,
        "attendance_issue_count": attendance_issue_count,
        "total_count": leave_count + overtime_count + attendance_issue_count,
        "leave_rows": leave_rows,
        "overtime_rows": overtime_rows,
        "attendance_issue_rows": issue_rows,
    }


def finance_work_overview(database: Session) -> dict[str, Any]:
    management_now = datetime.now(_zone(DEFAULT_TIMEZONE))
    today = management_now.date()
    month_key = management_now.strftime("%Y-%m")
    month_start = today.replace(day=1)
    month_end = date(today.year, today.month, monthrange(today.year, today.month)[1]) + timedelta(days=1)

    # Finance attendance must represent real, enabled freelancer accounts only.
    # Legacy project-import placeholders are stored in ``freelancers`` for
    # historical foreign-key compatibility, but they do not have login accounts
    # and must never be counted as attendance members. Disabled test/former
    # accounts are excluded by both profile and account status.
    freelancers = list(database.scalars(
        select(Freelancer)
        .join(
            FreelancerAccount,
            FreelancerAccount.freelancer_id == Freelancer.id,
        )
        .where(
            Freelancer.is_active.is_(True),
            FreelancerAccount.is_active.is_(True),
        )
        .order_by(Freelancer.full_name, Freelancer.id)
    ).all())
    eligible_freelancer_ids = tuple(int(row.id) for row in freelancers)
    attendance_by_member = {
        int(row.freelancer_id): row
        for row in database.scalars(
            select(DailyAttendance).where(DailyAttendance.attendance_date == today)
        ).all()
    }
    daily_rows: list[dict[str, Any]] = []
    for freelancer in freelancers:
        record = attendance_by_member.get(int(freelancer.id))
        if record is None or (record.time_in_utc is None and record.time_out_utc is None):
            status = "No Record"
            row_class = "attendance-row-missing"
        elif record.time_in_utc is not None and record.time_out_utc is None:
            status = "Currently Working"
            row_class = "attendance-row-working"
        elif record.time_in_utc is None and record.time_out_utc is not None:
            status = "Invalid Record"
            row_class = "attendance-row-issue"
        else:
            status = "Complete"
            row_class = "attendance-row-complete"
        daily_rows.append({
            "freelancer_id": int(freelancer.id),
            "name": freelancer.full_name,
            "code": freelancer.freelancer_code,
            "status": status,
            "time_in": _local_time(record.time_in_utc if record else None, freelancer.timezone_name),
            "time_out": _local_time(record.time_out_utc if record else None, freelancer.timezone_name),
            "rendered_minutes": int(record.rendered_minutes or 0) if record else 0,
            "late_minutes": int(record.late_minutes or 0) if record else 0,
            "row_class": row_class,
            "href": f"/admin/attendance/{freelancer.id}/{today.isoformat()}/correct",
        })

    monthly_records = list(database.scalars(
        select(DailyAttendance).where(
            DailyAttendance.freelancer_id.in_(eligible_freelancer_ids)
            if eligible_freelancer_ids
            else DailyAttendance.id.is_(None),
            DailyAttendance.attendance_date >= month_start,
            DailyAttendance.attendance_date < month_end,
        )
    ).all())
    complete_month = sum(
        row.time_in_utc is not None and row.time_out_utc is not None
        for row in monthly_records
    )
    incomplete_month = sum(
        (row.time_in_utc is None) != (row.time_out_utc is None)
        for row in monthly_records
    )

    dtrs = list(database.scalars(
        select(MonthlyDTR).where(
            MonthlyDTR.freelancer_id.in_(eligible_freelancer_ids)
            if eligible_freelancer_ids
            else MonthlyDTR.id.is_(None),
            MonthlyDTR.month_key == month_key,
        )
    ).all())
    dtr_status_counts = {
        status: sum(str(row.status).upper() == status for row in dtrs)
        for status in ("DRAFT", "REVIEWED", "FINALIZED")
    }
    generated_ids = {int(row.freelancer_id) for row in dtrs}
    missing_dtr_count = sum(int(row.id) not in generated_ids for row in freelancers)

    # Read-only Finance Center snapshot for Finance Head My Work.  This uses the
    # same finance-row calculation already used by /admin/finance, but does not
    # create, update, or backfill any DTR/finance records.  If Finance Center has
    # not generated summaries for the month yet, the snapshot simply shows the
    # currently available rows and the DTR missing count remains visible.
    center_rows = finance_rows(database, month_key)
    center_summary = {
        "employees": len(center_rows),
        "ready": sum(str(row.get("status") or "").upper() == "READY" for row in center_rows),
        "needs_review": sum(str(row.get("status") or "").upper() != "READY" for row in center_rows),
        "full_month_count": sum(int(row.get("total_deduction_minutes") or 0) == 0 for row in center_rows),
        "worked_days": sum(int(row.get("worked_days") or 0) for row in center_rows),
        "worked_hours": round(sum(float(row.get("worked_hours") or 0) for row in center_rows), 2),
        "comp_credit_hours_applied": round(sum(float(row.get("comp_credit_hours_applied") or 0) for row in center_rows), 2),
        "effective_unpaid_leave_hours": round(sum(float(row.get("effective_unpaid_leave_hours") or 0) for row in center_rows), 2),
        "absent_days": sum(int(row.get("absent_days") or 0) for row in center_rows),
        "effective_absent_hours": round(sum(float(row.get("effective_absent_hours") or 0) for row in center_rows), 2),
    }

    return {
        "today": today.isoformat(),
        "month_key": month_key,
        "freelancers": freelancers,
        "daily_rows": daily_rows,
        "daily_summary": {
            "total": len(freelancers),
            "recorded": sum(row["status"] in {"Complete", "Currently Working"} for row in daily_rows),
            "working": sum(row["status"] == "Currently Working" for row in daily_rows),
            "complete": sum(row["status"] == "Complete" for row in daily_rows),
            "issues": sum(row["status"] in {"Invalid Record", "No Record"} for row in daily_rows),
        },
        "monthly_summary": {
            "records": len(monthly_records),
            "complete": complete_month,
            "incomplete": incomplete_month,
            "rendered_minutes": sum(int(row.rendered_minutes or 0) for row in monthly_records),
            "late_minutes": sum(int(row.late_minutes or 0) for row in monthly_records),
            "undertime_minutes": sum(int(row.undertime_minutes or 0) for row in monthly_records),
            "overtime_minutes": sum(int(row.overtime_minutes or 0) for row in monthly_records),
        },
        "dtr_summary": {
            "generated": len(dtrs),
            "draft": dtr_status_counts["DRAFT"],
            "reviewed": dtr_status_counts["REVIEWED"],
            "finalized": dtr_status_counts["FINALIZED"],
            "missing": missing_dtr_count,
        },
        "finance_center_summary": center_summary,
    }


def build_role_my_work(database: Session, *, role: str) -> dict[str, Any]:
    normalized_role = str(role or "").strip().upper()
    if normalized_role == "FINANCE":
        return {
            "role": normalized_role,
            "finance": finance_work_overview(database),
        }

    task_rows = active_task_rows(database)
    team_rows = team_availability_rows(database)
    unassigned_rows = unassigned_task_rows(database)
    result: dict[str, Any] = {
        "role": normalized_role,
        "task_rows": task_rows,
        "team_rows": team_rows,
        "unassigned_task_rows": unassigned_rows,
        "task_summary": {
            "active": len(task_rows),
            "delayed": sum(row["row_class"] == "task-row-delayed" for row in task_rows),
            "in_progress": sum(str(row["status"]).upper() == "IN_PROGRESS" for row in task_rows),
            "for_review": sum(str(row["status"]).upper() == "FOR_REVIEW" for row in task_rows),
            "unassigned": len(unassigned_rows),
        },
        "team_summary": {
            "available": sum(row["state"] == "available" for row in team_rows),
            "working": sum(row["state"] == "working" for row in team_rows),
            "assigned": sum(row["state"] == "assigned" for row in team_rows),
            "overdue": sum(row["state"] == "overdue" for row in team_rows),
        },
    }
    if normalized_role == "ADMIN":
        result["requests"] = administrator_request_overview(database)
    return result
