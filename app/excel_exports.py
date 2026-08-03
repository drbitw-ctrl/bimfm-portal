"""Professional Excel exports for operational, attendance, DTR, and project reports."""
from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timezone
from io import BytesIO
from typing import Any, Iterable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import DEFAULT_TIMEZONE
from app.models import (
    DailyAttendance,
    DTRDailyLine,
    Freelancer,
    LeaveRequest,
    MonthlyDTR,
    OvertimeClaim,
    PortalProject,
)
from app.performance_reporting import build_performance_dashboard, build_project_reports
from app.portal_project_service import project_overview_rows, task_overview_rows, team_assignment_rows
from app.task_time_reporting import build_task_time_utilization
from app.work_order_service import live_work_rows

NAVY = "17365D"
BLUE = "2F6FA5"
LIGHT_BLUE = "EAF3FB"
LIGHT_GRAY = "F3F6F9"
WHITE = "FFFFFF"
GREEN = "E7F6ED"
YELLOW = "FFF4CC"
RED = "FDECEC"
PURPLE = "EFE7FA"
TEXT = "243447"
BORDER_COLOR = "D6DEE6"
THIN = Side(style="thin", color=BORDER_COLOR)


def _zone(name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(str(name or DEFAULT_TIMEZONE))
    except ZoneInfoNotFoundError:
        return ZoneInfo(DEFAULT_TIMEZONE)


def _local_time(value: datetime | None, timezone_name: str | None) -> str:
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(_zone(timezone_name)).strftime("%H:%M")


def _month_bounds(month_key: str) -> tuple[str, date, date]:
    try:
        start = datetime.strptime(str(month_key or ""), "%Y-%m").date().replace(day=1)
    except ValueError:
        start = date.today().replace(day=1)
    days = monthrange(start.year, start.month)[1]
    end = date(start.year + (1 if start.month == 12 else 0), 1 if start.month == 12 else start.month + 1, 1)
    return start.strftime("%Y-%m"), start, end


def _duration(minutes: int | None) -> str:
    value = max(0, int(minutes or 0))
    hours, remainder = divmod(value, 60)
    return f"{hours}h {remainder:02d}m"


def _new_workbook() -> Workbook:
    wb = Workbook()
    default = wb.active
    wb.remove(default)
    return wb


def _title(sheet, title: str, subtitle: str, last_column: int) -> int:
    sheet.sheet_view.showGridLines = False
    sheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=last_column)
    title_cell = sheet.cell(1, 1, title)
    title_cell.font = Font(size=16, bold=True, color=WHITE)
    title_cell.fill = PatternFill("solid", fgColor=NAVY)
    title_cell.alignment = Alignment(horizontal="left", vertical="center")
    sheet.row_dimensions[1].height = 28
    sheet.merge_cells(start_row=2, start_column=1, end_row=2, end_column=last_column)
    sub = sheet.cell(2, 1, subtitle)
    sub.font = Font(size=9, italic=True, color=TEXT)
    sub.fill = PatternFill("solid", fgColor=LIGHT_BLUE)
    sub.alignment = Alignment(horizontal="left", vertical="center")
    sheet.row_dimensions[2].height = 22
    return 4


def _header(sheet, row: int, headers: list[str]) -> None:
    for column, header in enumerate(headers, 1):
        cell = sheet.cell(row, column, header)
        cell.font = Font(bold=True, color=WHITE)
        cell.fill = PatternFill("solid", fgColor=BLUE)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = Border(top=THIN, bottom=THIN, left=THIN, right=THIN)
    sheet.row_dimensions[row].height = 28


def _write_rows(
    sheet,
    *,
    title: str,
    subtitle: str,
    headers: list[str],
    rows: Iterable[Iterable[Any]],
    widths: list[int] | None = None,
    status_column: int | None = None,
    due_column: int | None = None,
) -> None:
    header_row = _title(sheet, title, subtitle, len(headers))
    _header(sheet, header_row, headers)
    today = date.today()
    for row_index, values in enumerate(rows, header_row + 1):
        values = list(values)
        for col_index, value in enumerate(values, 1):
            cell = sheet.cell(row_index, col_index, value)
            cell.font = Font(size=9, color=TEXT)
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = Border(bottom=THIN)
        fill = None
        if status_column is not None and status_column <= len(values):
            status = str(values[status_column - 1] or "").strip().upper()
            if status == "COMPLETED":
                fill = GREEN
            elif status in {"IN_PROGRESS", "FOR_REVIEW", "PENDING", "PENDING_PLAN", "PENDING_FINAL"}:
                fill = YELLOW
        if due_column is not None and due_column <= len(values):
            due_value = values[due_column - 1]
            if isinstance(due_value, str) and due_value and due_value != "—":
                try:
                    due = date.fromisoformat(due_value)
                except ValueError:
                    due = None
                status = str(values[status_column - 1] or "").strip().upper() if status_column else ""
                if due and due < today and status not in {"COMPLETED", "CANCELLED", "FINALIZED"}:
                    fill = RED
        if fill:
            for cell in sheet[row_index]:
                cell.fill = PatternFill("solid", fgColor=fill)
    sheet.freeze_panes = f"A{header_row + 1}"
    sheet.auto_filter.ref = f"A{header_row}:{get_column_letter(len(headers))}{sheet.max_row}"
    if widths:
        for index, width in enumerate(widths, 1):
            sheet.column_dimensions[get_column_letter(index)].width = width
    else:
        for index in range(1, len(headers) + 1):
            longest = max(
                (len(str(sheet.cell(row, index).value or "")) for row in range(1, min(sheet.max_row, 200) + 1)),
                default=10,
            )
            sheet.column_dimensions[get_column_letter(index)].width = max(10, min(35, longest + 2))


def _add_summary_sheet(wb: Workbook, month_key: str, database: Session) -> None:
    sheet = wb.create_sheet("Export Summary")
    tasks = task_overview_rows(database, status_mode="all", limit=1000)
    projects = project_overview_rows(database, limit=500)
    team = team_assignment_rows(database)
    dtrs = list(database.scalars(select(MonthlyDTR).where(MonthlyDTR.month_key == month_key)).all())
    cards = [
        ("Selected Month", month_key),
        ("Projects", len(projects)),
        ("All Tasks", len(tasks)),
        ("Open Tasks", sum(str(row["status"]).upper() not in {"COMPLETED", "CANCELLED"} for row in tasks)),
        ("Completed Tasks", sum(str(row["status"]).upper() == "COMPLETED" for row in tasks)),
        ("Unassigned Open Tasks", sum(str(row.get("assignees") or "") == "Unassigned" and str(row["status"]).upper() not in {"COMPLETED", "CANCELLED"} for row in tasks)),
        ("Active Team Members", len(team)),
        ("DTR Records", len(dtrs)),
    ]
    _title(sheet, "BIMFM PORTAL — EXCEL EXPORT PACKAGE", f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}", 4)
    _header(sheet, 4, ["Metric", "Value", "Purpose", "Scope"])
    purpose = {
        "Selected Month": "Monthly attendance and DTR period",
        "Projects": "Current project register",
        "All Tasks": "Complete task register",
        "Open Tasks": "Tasks requiring action",
        "Completed Tasks": "Completed task history",
        "Unassigned Open Tasks": "Tasks requiring assignment",
        "Active Team Members": "Current team availability population",
        "DTR Records": "Generated DTR records for selected month",
    }
    for idx, (label, value) in enumerate(cards, 5):
        sheet.cell(idx, 1, label)
        sheet.cell(idx, 2, value)
        sheet.cell(idx, 3, purpose[label])
        sheet.cell(idx, 4, "Portal records")
        for cell in sheet[idx]:
            cell.border = Border(bottom=THIN)
            cell.alignment = Alignment(vertical="center", wrap_text=True)
        sheet.cell(idx, 1).font = Font(bold=True, color=NAVY)
        sheet.cell(idx, 2).font = Font(bold=True, size=13, color=BLUE)
    for col, width in enumerate([26, 16, 42, 24], 1):
        sheet.column_dimensions[get_column_letter(col)].width = width
    sheet.freeze_panes = "A5"


def _add_tasks_sheet(wb: Workbook, database: Session) -> None:
    rows = task_overview_rows(database, status_mode="all", limit=1000)
    _write_rows(
        wb.create_sheet("All Tasks"),
        title="ALL TASKS",
        subtitle="Complete task register including current assignment, schedule, progress, and Quality Score.",
        headers=[
            "Task ID", "Project", "Project Engineer", "Task", "Description", "Assigned Member",
            "Status", "Priority", "Discipline", "Progress %", "Quality Score", "Start Date",
            "Deadline", "Completed Date", "Updated At",
        ],
        rows=[[
            row["id"], row["project_name"], row["project_engineer"], row["title"], row["description"],
            row["assignees"], row["status"], row["priority"], row["discipline"], row["progress"],
            row["quality_score"] if row["quality_score"] is not None else "", row["start_date"],
            row["due_date"], row["completion_date"],
            row["updated_at"].strftime("%Y-%m-%d %H:%M") if row.get("updated_at") else "",
        ] for row in rows],
        widths=[10, 28, 22, 30, 42, 28, 18, 12, 16, 12, 14, 13, 13, 15, 18],
        status_column=7,
        due_column=13,
    )


def _add_projects_sheet(wb: Workbook, database: Session) -> None:
    rows = project_overview_rows(database, limit=500)
    _write_rows(
        wb.create_sheet("Projects"),
        title="PROJECT REGISTER",
        subtitle="Current project-level status, progress, team coverage, and active workload.",
        headers=["Project ID", "Project", "Project Engineer", "Status", "Priority", "Progress %", "Members", "Active Tasks", "Deadline"],
        rows=[[
            row["id"], row["name"], row["project_engineer"], row["status"], row["priority"],
            row["progress"], row["member_count"], row["active_task_count"], row["deadline"],
        ] for row in rows],
        widths=[11, 32, 24, 16, 12, 13, 11, 13, 14],
        status_column=4,
        due_column=9,
    )


def _add_team_sheet(wb: Workbook, database: Session) -> None:
    live = {int(row["freelancer_id"]): row for row in live_work_rows(database)}
    rows = []
    for row in team_assignment_rows(database):
        current = live.get(int(row["freelancer_id"]))
        if int(row["overdue_task_count"] or 0) > 0:
            state = "Overdue"
        elif current:
            state = "Working Now"
        elif int(row["active_task_count"] or 0) > 0:
            state = "Assigned"
        else:
            state = "Available"
        rows.append([
            row["name"], row["code"], row.get("join_date", "—"), state,
            current["project_name"] if current else "", current["task_title"] if current else "",
            row["project_count"], row["active_task_count"], row["overdue_task_count"], row["completed_task_count"],
            row["assignment_status"],
        ])
    _write_rows(
        wb.create_sheet("Team Availability"),
        title="TEAM AVAILABILITY",
        subtitle="Green = available, blue = working now, yellow = assigned, red = overdue.",
        headers=["Member", "Code", "Join Date", "Availability", "Current Project", "Working Task", "Projects", "Active Tasks", "Overdue", "Completed", "Assignment Status"],
        rows=rows,
        widths=[26, 14, 13, 16, 28, 32, 10, 12, 10, 11, 28],
    )
    sheet = wb["Team Availability"]
    for row in range(5, sheet.max_row + 1):
        state = str(sheet.cell(row, 4).value or "")
        fill = {"Available": GREEN, "Working Now": LIGHT_BLUE, "Assigned": YELLOW, "Overdue": RED}.get(state)
        if fill:
            for cell in sheet[row]:
                cell.fill = PatternFill("solid", fgColor=fill)


def _add_attendance_sheet(wb: Workbook, database: Session, month_key: str) -> None:
    _, start, end = _month_bounds(month_key)
    results = list(database.execute(
        select(DailyAttendance, Freelancer)
        .join(Freelancer, Freelancer.id == DailyAttendance.freelancer_id)
        .where(DailyAttendance.attendance_date >= start, DailyAttendance.attendance_date < end)
        .order_by(DailyAttendance.attendance_date, Freelancer.full_name)
    ).all())
    _write_rows(
        wb.create_sheet("Monthly Attendance"),
        title=f"MONTHLY ATTENDANCE — {month_key}",
        subtitle="Daily attendance records for the selected month.",
        headers=["Date", "Member", "Code", "Join Date", "Active", "Time In", "Time Out", "Break Minutes", "Rendered", "Late", "Undertime", "Overtime", "Status", "Review Status", "Locked"],
        rows=[[
            record.attendance_date.isoformat(), freelancer.full_name, freelancer.freelancer_code,
            freelancer.join_date.isoformat() if freelancer.join_date else "—", "Yes" if freelancer.is_active else "No",
            _local_time(record.time_in_utc, freelancer.timezone_name), _local_time(record.time_out_utc, freelancer.timezone_name),
            record.break_minutes, _duration(record.rendered_minutes), _duration(record.late_minutes),
            _duration(record.undertime_minutes), _duration(record.overtime_minutes), record.status,
            record.review_status, "Yes" if record.is_locked else "No",
        ] for record, freelancer in results],
        widths=[13, 26, 14, 13, 10, 11, 11, 14, 13, 12, 13, 12, 16, 16, 10],
        status_column=13,
    )


def _add_dtr_sheets(wb: Workbook, database: Session, month_key: str) -> None:
    records = list(database.execute(
        select(MonthlyDTR, Freelancer)
        .join(Freelancer, Freelancer.id == MonthlyDTR.freelancer_id)
        .where(MonthlyDTR.month_key == month_key)
        .order_by(Freelancer.full_name)
    ).all())
    _write_rows(
        wb.create_sheet("Monthly DTR Summary"),
        title=f"MONTHLY DTR SUMMARY — {month_key}",
        subtitle="Generated DTR status and monthly totals for all members.",
        headers=["DTR ID", "Member", "Code", "Join Date", "Status", "Calendar Days", "Scheduled Workdays", "Present", "Late Days", "Absent", "Leave", "Holiday", "Rest Days", "Incomplete", "Rendered", "Late", "Undertime", "Approved OT", "Task Entries", "Task Time", "Task Review"],
        rows=[[
            dtr.id, freelancer.full_name, freelancer.freelancer_code,
            freelancer.join_date.isoformat() if freelancer.join_date else "—", dtr.status,
            dtr.calendar_days, dtr.scheduled_workdays, dtr.present_days, dtr.late_days, dtr.absent_days,
            dtr.leave_days, dtr.holiday_days, dtr.rest_days, dtr.incomplete_days, _duration(dtr.rendered_minutes),
            _duration(dtr.late_minutes), _duration(dtr.undertime_minutes), _duration(dtr.approved_overtime_minutes),
            dtr.daily_task_entries, _duration(dtr.daily_task_minutes), dtr.task_review_status,
        ] for dtr, freelancer in records],
        widths=[10, 26, 14, 13, 13, 13, 17, 10, 11, 10, 10, 10, 11, 12, 13, 12, 13, 13, 12, 13, 15],
        status_column=5,
    )
    dtr_ids = [int(dtr.id) for dtr, _ in records]
    names = {int(dtr.id): (freelancer.full_name, freelancer.freelancer_code, freelancer.timezone_name) for dtr, freelancer in records}
    lines = list(database.scalars(
        select(DTRDailyLine)
        .where(DTRDailyLine.monthly_dtr_id.in_(tuple(dtr_ids)) if dtr_ids else DTRDailyLine.id.is_(None))
        .order_by(DTRDailyLine.attendance_date, DTRDailyLine.monthly_dtr_id)
    ).all())
    _write_rows(
        wb.create_sheet("DTR Daily Details"),
        title=f"DTR DAILY DETAILS — {month_key}",
        subtitle="Day-by-day attendance and task totals supporting the monthly DTR.",
        headers=["Date", "Member", "Code", "Day", "Day Type", "Attendance Status", "Scheduled Start", "Scheduled End", "Time In", "Time Out", "Rendered", "Late", "Undertime", "Potential OT", "Approved OT", "Task Time", "Task Entries", "Task Summary", "Review Status", "Notes"],
        rows=[[
            line.attendance_date.isoformat(), names.get(int(line.monthly_dtr_id), ("—", "—", DEFAULT_TIMEZONE))[0],
            names.get(int(line.monthly_dtr_id), ("—", "—", DEFAULT_TIMEZONE))[1], line.day_name, line.day_type,
            line.attendance_status, line.scheduled_start_text, line.scheduled_end_text,
            _local_time(line.time_in_utc, names.get(int(line.monthly_dtr_id), ("", "", DEFAULT_TIMEZONE))[2]),
            _local_time(line.time_out_utc, names.get(int(line.monthly_dtr_id), ("", "", DEFAULT_TIMEZONE))[2]),
            _duration(line.rendered_minutes), _duration(line.late_minutes), _duration(line.undertime_minutes),
            _duration(line.potential_overtime_minutes), _duration(line.approved_overtime_minutes),
            _duration(line.task_minutes), line.task_entry_count, line.task_summary or "", line.attendance_review_status, line.notes or "",
        ] for line in lines],
        widths=[13, 26, 14, 11, 15, 18, 14, 14, 11, 11, 13, 12, 13, 13, 13, 13, 12, 42, 16, 36],
        status_column=6,
    )


def _add_requests_sheets(wb: Workbook, database: Session, month_key: str) -> None:
    _, start, end = _month_bounds(month_key)
    names = {int(row.id): row for row in database.scalars(select(Freelancer)).all()}
    leave = list(database.scalars(
        select(LeaveRequest)
        .where(LeaveRequest.leave_date >= start, LeaveRequest.leave_date < end)
        .order_by(LeaveRequest.leave_date, LeaveRequest.id)
    ).all())
    _write_rows(
        wb.create_sheet("Leave Requests"),
        title=f"LEAVE REQUESTS — {month_key}",
        subtitle="Leave requests submitted for the selected month.",
        headers=["Date", "Member", "Code", "Type", "Requested", "Approved", "Status", "Reason", "Review Reason", "Submitted At"],
        rows=[[
            item.leave_date.isoformat(), names.get(int(item.freelancer_id)).full_name if names.get(int(item.freelancer_id)) else "—",
            names.get(int(item.freelancer_id)).freelancer_code if names.get(int(item.freelancer_id)) else "—",
            item.leave_type, _duration(item.requested_minutes), _duration(item.approved_minutes), item.status,
            item.reason, item.review_reason or "", item.submitted_at.strftime("%Y-%m-%d %H:%M"),
        ] for item in leave],
        widths=[13, 26, 14, 18, 13, 13, 15, 40, 36, 18],
        status_column=7,
    )
    overtime = list(database.scalars(
        select(OvertimeClaim)
        .where(OvertimeClaim.attendance_date >= start, OvertimeClaim.attendance_date < end)
        .order_by(OvertimeClaim.attendance_date, OvertimeClaim.id)
    ).all())
    _write_rows(
        wb.create_sheet("Overtime Claims"),
        title=f"OVERTIME CLAIMS — {month_key}",
        subtitle="Overtime claims and approved time for the selected month.",
        headers=["Date", "Member", "Code", "Potential", "Requested", "Approved", "Comp Credit", "Status", "Work Description", "Missing Time Out Reason", "Review Reason", "Submitted At"],
        rows=[[
            item.attendance_date.isoformat(), names.get(int(item.freelancer_id)).full_name if names.get(int(item.freelancer_id)) else "—",
            names.get(int(item.freelancer_id)).freelancer_code if names.get(int(item.freelancer_id)) else "—",
            _duration(item.potential_minutes_snapshot), _duration(item.requested_minutes), _duration(item.approved_minutes),
            _duration(item.comp_leave_minutes_earned), item.status, item.work_description, item.missing_time_out_reason or "",
            item.review_reason or "", item.submitted_at.strftime("%Y-%m-%d %H:%M"),
        ] for item in overtime],
        widths=[13, 26, 14, 13, 13, 13, 14, 18, 42, 36, 36, 18],
        status_column=8,
    )


def _add_performance_sheets(wb: Workbook, database: Session, month_key: str) -> None:
    performance = build_performance_dashboard(database)
    _write_rows(
        wb.create_sheet("Performance"),
        title="PERFORMANCE OVERVIEW",
        subtitle="Task output, delivery, and Quality Score as calculated.",
        headers=["Rank", "Member", "Code", "Total Tasks", "Completed", "Active", "Completion %", "Rated Tasks", "Quality Score", "Measured Tasks", "On-time %", "Average Days"],
        rows=[[
            row.get("rank"), row.get("name"), row.get("code"), row.get("total_tasks"), row.get("completed_tasks"),
            row.get("active_tasks"), row.get("completion_rate"), row.get("rated_tasks"), row.get("average_quality"),
            row.get("measured_tasks"), row.get("delivery_rate"), row.get("average_days_label"),
        ] for row in performance.get("task_ranked", [])],
        widths=[9, 26, 14, 12, 12, 10, 13, 12, 14, 14, 12, 18],
    )
    reports = build_project_reports(database, period="month", month_key=month_key)
    _write_rows(
        wb.create_sheet("Project Reports"),
        title=f"PROJECT REPORTS — {reports.get('period_label', month_key)}",
        subtitle="Project delivery, active work, overdue tasks, Quality Score, and logged time.",
        headers=["Project", "Code", "Project Engineer", "Discipline", "Status", "Progress %", "Delivered", "Active", "Overdue", "Rated", "Quality Score", "Measured", "On-time %", "Logged Hours"],
        rows=[[
            row.get("name"), row.get("code"), row.get("project_engineer"), row.get("discipline"), row.get("status"),
            row.get("progress"), row.get("delivered_tasks"), row.get("active_tasks"), row.get("overdue_tasks"),
            row.get("rated_tasks"), row.get("average_quality"), row.get("measured_tasks"), row.get("on_time_rate"), row.get("logged_hours"),
        ] for row in reports.get("project_rows", [])],
        widths=[30, 16, 24, 16, 14, 12, 11, 10, 10, 10, 14, 11, 12, 14],
        status_column=5,
    )


def _add_utilization_sheets(wb: Workbook, database: Session) -> None:
    report = build_task_time_utilization(database)
    _write_rows(
        wb.create_sheet("Project Time Utilization"),
        title="PROJECT TIME UTILIZATION",
        subtitle="Total actual time, target time, variance, and utilization by project.",
        headers=["Rank", "Project", "Code", "Status", "Tasks", "Active Tasks", "Target Time", "Actual Time", "Share %", "Variance", "Utilization %", "Unlinked Time"],
        rows=[[
            row.get("actual_rank"), row.get("name"), row.get("code"), row.get("status"), row.get("task_count"),
            row.get("active_task_count"), _duration(row.get("target_minutes")) if row.get("target_minutes") is not None else "—",
            _duration(row.get("actual_minutes")), row.get("actual_share_percent"), row.get("variance_label"),
            row.get("utilization") if row.get("utilization") is not None else "", _duration(row.get("unlinked_minutes")),
        ] for row in report.get("projects", [])],
        widths=[9, 30, 16, 14, 10, 12, 14, 14, 11, 18, 14, 14],
        status_column=4,
    )
    task_rows = []
    for project in report.get("projects", []):
        for row in project.get("rows", []):
            task_rows.append([
                project.get("name"), row.get("title"), row.get("assignees"), row.get("status"), row.get("start_date"),
                row.get("deadline"), _duration(row.get("target_minutes")) if row.get("target_minutes") is not None else "—",
                _duration(row.get("actual_minutes")), row.get("variance_label"), row.get("utilization") if row.get("utilization") is not None else "",
                row.get("contributors"), "Yes" if row.get("is_estimated_actual") else "No",
            ])
    _write_rows(
        wb.create_sheet("Task Time Details"),
        title="TASK TIME UTILIZATION DETAILS",
        subtitle="Task-level target and actual time supporting the project totals.",
        headers=["Project", "Task", "Assigned Member", "Status", "Start Date", "Deadline", "Target Time", "Actual Time", "Variance", "Utilization %", "Contributors", "Estimated Actual"],
        rows=task_rows,
        widths=[28, 34, 26, 15, 13, 13, 14, 14, 18, 14, 42, 15],
        status_column=4,
        due_column=6,
    )


def build_export_workbook(
    database: Session,
    *,
    month_key: str,
    include_tasks: bool = False,
    include_attendance: bool = False,
    include_dtr: bool = False,
    include_reports: bool = False,
    include_all: bool = False,
) -> bytes:
    month_key, _, _ = _month_bounds(month_key)
    wb = _new_workbook()
    _add_summary_sheet(wb, month_key, database)
    if include_all or include_tasks:
        _add_tasks_sheet(wb, database)
    if include_all or include_reports:
        _add_projects_sheet(wb, database)
        _add_team_sheet(wb, database)
        _add_performance_sheets(wb, database, month_key)
        _add_utilization_sheets(wb, database)
        _add_requests_sheets(wb, database, month_key)
    if include_all or include_attendance:
        _add_attendance_sheet(wb, database, month_key)
    if include_all or include_dtr:
        _add_dtr_sheets(wb, database, month_key)
    output = BytesIO()
    wb.save(output)
    return output.getvalue()
