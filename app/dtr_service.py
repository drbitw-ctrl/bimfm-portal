from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.attendance_calculations import (
    calculate_attendance_record,
    get_active_schedule,
    get_calculation,
    is_scheduled_workday,
    safe_zone,
)
from app.hr_workflow import (
    comp_balance,
    get_policy,
    get_task_review,
    month_bounds,
    pending_counts,
)
from app.finance_service import sync_finance_summary
from app.models import (
    AttendanceCalculation,
    CompLeaveTransaction,
    DTRCompLine,
    DTRDailyLine,
    DTRLeaveLine,
    DTRTaskLine,
    DailyAttendance,
    DailyTask,
    Freelancer,
    Holiday,
    LeaveRecord,
    MonthlyDTR,
    OvertimeClaim,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def local_today(timezone_name: str) -> date:
    return utc_now().astimezone(safe_zone(timezone_name)).date()


def get_monthly_dtr(database: Session, freelancer_id: int, month_key: str) -> Optional[MonthlyDTR]:
    return database.scalar(
        select(MonthlyDTR).where(
            MonthlyDTR.freelancer_id == freelancer_id,
            MonthlyDTR.month_key == month_key,
        )
    )


def _status_for_day(
    *,
    attendance_date: date,
    record: Optional[DailyAttendance],
    calculation: Optional[AttendanceCalculation],
    holiday: Optional[Holiday],
    leave: Optional[LeaveRecord],
    is_workday: bool,
    today: date,
    standard_day_minutes: int,
) -> tuple[str, str, Optional[str]]:
    has_time_in = bool(record and record.time_in_utc)
    has_time_out = bool(record and record.time_out_utc)
    complete = has_time_in and has_time_out
    partial = has_time_in != has_time_out

    notes: list[str] = []
    if holiday:
        notes.append(f"{holiday.name} ({holiday.holiday_type.replace('_', ' ').title()})")
    if leave:
        leave_note = leave.leave_type.replace("_", " ").title()
        notes.append(leave_note)
        if leave.notes:
            notes.append(leave.notes)

    if partial:
        return "ATTENDANCE", "INCOMPLETE", "; ".join(notes) or "Missing punch"

    if complete:
        if holiday:
            status, day_type = "HOLIDAY_WORK", "HOLIDAY"
        elif leave and leave.duration_minutes < standard_day_minutes:
            status, day_type = "PARTIAL_LEAVE_WORK", "LEAVE"
        elif leave:
            status, day_type = "WORKED_ON_LEAVE", "LEAVE"
        elif not is_workday:
            status, day_type = "REST_DAY_WORK", "REST_DAY"
        elif calculation and calculation.late_minutes > 0:
            status, day_type = "LATE", "WORKDAY"
        else:
            status, day_type = "PRESENT", "WORKDAY"
        return day_type, status, "; ".join(notes) or None

    if holiday:
        return "HOLIDAY", "HOLIDAY", "; ".join(notes)
    if leave:
        comp_used = int(leave.comp_leave_minutes_used or 0)
        duration = int(leave.duration_minutes or 0)
        if comp_used >= duration and duration > 0:
            return "LEAVE", "COMPENSATORY_LEAVE", "; ".join(notes)
        if comp_used > 0:
            return "LEAVE", "PARTIAL_COMPENSATORY_LEAVE", "; ".join(notes)
        status = "REGULAR_LEAVE"
        return "LEAVE", status, "; ".join(notes)
    if not is_workday:
        return "REST_DAY", "REST_DAY", None
    if attendance_date > today:
        return "WORKDAY", "SCHEDULED", None
    return "WORKDAY", "ABSENT", None


def generate_monthly_dtr(
    database: Session,
    *,
    freelancer: Freelancer,
    month_key: str,
    admin_id: int,
    reason: str,
) -> MonthlyDTR:
    first_day, next_month = month_bounds(month_key)
    month_end = next_month - timedelta(days=1)
    schedule = get_active_schedule(database)
    policy = get_policy(database)

    dtr = get_monthly_dtr(database, freelancer.id, month_key)
    if dtr is not None and dtr.status == "FINALIZED":
        raise ValueError("A finalized DTR cannot be regenerated.")

    if dtr is None:
        dtr = MonthlyDTR(
            freelancer_id=freelancer.id,
            month_key=month_key,
            schedule_name=schedule.name,
            scheduled_start_text=schedule.start_time_text,
            scheduled_end_text=schedule.end_time_text,
            timezone_name=freelancer.timezone_name,
            generated_by_admin_id=admin_id,
            generation_reason=reason,
        )
        database.add(dtr)
        database.flush()
    else:
        for model in (DTRDailyLine, DTRTaskLine, DTRCompLine, DTRLeaveLine):
            database.execute(delete(model).where(model.monthly_dtr_id == dtr.id))

    dtr.schedule_name = schedule.name
    dtr.scheduled_start_text = schedule.start_time_text
    dtr.scheduled_end_text = schedule.end_time_text
    dtr.timezone_name = freelancer.timezone_name
    dtr.status = "DRAFT"
    dtr.generated_by_admin_id = admin_id
    dtr.generated_at = utc_now()
    dtr.generation_reason = reason
    dtr.reviewed_by_admin_id = None
    dtr.reviewed_at = None
    dtr.review_reason = None
    dtr.finalized_by_admin_id = None
    dtr.finalized_at = None
    dtr.finalization_reason = None

    records = {
        row.attendance_date: row
        for row in database.scalars(
            select(DailyAttendance).where(
                DailyAttendance.freelancer_id == freelancer.id,
                DailyAttendance.attendance_date >= first_day,
                DailyAttendance.attendance_date < next_month,
            )
        ).all()
    }
    holidays = {
        row.holiday_date: row
        for row in database.scalars(
            select(Holiday).where(
                Holiday.holiday_date >= first_day,
                Holiday.holiday_date < next_month,
                Holiday.is_active.is_(True),
            )
        ).all()
    }
    leaves = {
        row.leave_date: row
        for row in database.scalars(
            select(LeaveRecord).where(
                LeaveRecord.freelancer_id == freelancer.id,
                LeaveRecord.leave_date >= first_day,
                LeaveRecord.leave_date < next_month,
                LeaveRecord.status == "APPROVED",
            )
        ).all()
    }
    tasks = list(
        database.scalars(
            select(DailyTask).where(
                DailyTask.freelancer_id == freelancer.id,
                DailyTask.task_date >= first_day,
                DailyTask.task_date < next_month,
            ).order_by(DailyTask.task_date, DailyTask.id)
        ).all()
    )
    tasks_by_date: dict[date, list[DailyTask]] = {}
    for task in tasks:
        tasks_by_date.setdefault(task.task_date, []).append(task)

    approved_claims = list(
        database.scalars(
            select(OvertimeClaim).where(
                OvertimeClaim.freelancer_id == freelancer.id,
                OvertimeClaim.attendance_date >= first_day,
                OvertimeClaim.attendance_date < next_month,
                OvertimeClaim.status == "APPROVED",
            ).order_by(OvertimeClaim.attendance_date, OvertimeClaim.id)
        ).all()
    )
    claims_by_date: dict[date, list[OvertimeClaim]] = {}
    for claim in approved_claims:
        claims_by_date.setdefault(claim.attendance_date, []).append(claim)
    transactions = list(
        database.scalars(
            select(CompLeaveTransaction).where(
                CompLeaveTransaction.freelancer_id == freelancer.id,
                CompLeaveTransaction.transaction_date >= first_day,
                CompLeaveTransaction.transaction_date < next_month,
            ).order_by(CompLeaveTransaction.transaction_date, CompLeaveTransaction.id)
        ).all()
    )

    pending_ot, pending_leave = pending_counts(database, freelancer.id, month_key)
    task_review = get_task_review(database, freelancer.id, month_key)

    summary = {
        "calendar_days": 0, "scheduled_workdays": 0, "present_days": 0,
        "late_days": 0, "absent_days": 0, "leave_days": 0,
        "holiday_days": 0, "rest_days": 0, "incomplete_days": 0,
        "scheduled_future_days": 0, "rendered_minutes": 0,
        "late_minutes": 0, "undertime_minutes": 0,
        "potential_overtime_minutes": 0, "approved_overtime_minutes": 0,
        "comp_leave_earned_minutes": 0, "comp_leave_used_minutes": 0,
        "daily_task_entries": len(tasks),
        "daily_task_minutes": sum(task.minutes_spent for task in tasks),
        "task_missing_days": 0, "task_variance_days": 0,
    }

    today = local_today(freelancer.timezone_name)
    days_in_month = monthrange(first_day.year, first_day.month)[1]

    for day_number in range(1, days_in_month + 1):
        attendance_date = date(first_day.year, first_day.month, day_number)
        record = records.get(attendance_date)
        holiday = holidays.get(attendance_date)
        leave = leaves.get(attendance_date)
        workday = is_scheduled_workday(schedule, attendance_date)
        calculation = None
        if record is not None:
            calculation = get_calculation(database, record.id)
            if calculation is None:
                calculation = calculate_attendance_record(
                    database, record, freelancer, source="DTR_GENERATION",
                    admin_id=admin_id, schedule=schedule,
                )

        day_type, status, notes = _status_for_day(
            attendance_date=attendance_date, record=record, calculation=calculation,
            holiday=holiday, leave=leave, is_workday=workday, today=today,
            standard_day_minutes=policy.standard_leave_day_minutes,
        )

        rendered = calculation.rendered_minutes if calculation else 0
        late = calculation.late_minutes if calculation else 0
        undertime = calculation.undertime_minutes if calculation else 0
        potential_ot = calculation.overtime_minutes if calculation else 0
        day_claims = claims_by_date.get(attendance_date, [])
        approved_ot = sum(int(claim.approved_minutes or 0) for claim in day_claims)

        # The compensatory-leave ledger is the accounting source of truth.
        # This prevents stale claim/leave snapshots from making the Finance DTR
        # disagree with the auditable balance.
        day_transactions = [
            tx for tx in transactions if tx.transaction_date == attendance_date
        ]
        comp_earned = sum(
            int(tx.amount_minutes or 0)
            for tx in day_transactions if int(tx.amount_minutes or 0) > 0
        )
        comp_used = abs(sum(
            int(tx.amount_minutes or 0)
            for tx in day_transactions if int(tx.amount_minutes or 0) < 0
        ))

        day_tasks = tasks_by_date.get(attendance_date, [])
        task_minutes = sum(task.minutes_spent for task in day_tasks)
        task_summary = "; ".join(
            f"{task.project_name or 'Project'}: {task.task_description}" for task in day_tasks[:3]
        ) or None
        if len(day_tasks) > 3:
            task_summary = f"{task_summary}; +{len(day_tasks) - 3} more"
        task_variance = abs(rendered - task_minutes) if rendered and task_minutes else 0
        attendance_worked = bool(record and record.time_in_utc and record.time_out_utc)
        missing_task = policy.require_daily_task_for_dtr and attendance_worked and not day_tasks
        variance_warning = (
            attendance_worked and bool(day_tasks)
            and task_variance > policy.task_variance_warning_minutes
        )
        if missing_task:
            summary["task_missing_days"] += 1
            notes = "; ".join(filter(None, [notes, "Daily task report missing"]))
        if variance_warning:
            summary["task_variance_days"] += 1
            notes = "; ".join(filter(None, [notes, f"Task/attendance variance {task_variance} minutes"]))

        database.add(DTRDailyLine(
            monthly_dtr_id=dtr.id, freelancer_id=freelancer.id,
            attendance_date=attendance_date, day_name=attendance_date.strftime("%A"),
            day_type=day_type, attendance_status=status,
            scheduled_start_text=schedule.start_time_text,
            scheduled_end_text=schedule.end_time_text,
            time_in_utc=record.time_in_utc if record else None,
            time_out_utc=record.time_out_utc if record else None,
            rendered_minutes=rendered, late_minutes=late,
            undertime_minutes=undertime,
            potential_overtime_minutes=potential_ot,
            approved_overtime_minutes=approved_ot,
            comp_leave_earned_minutes=comp_earned,
            comp_leave_used_minutes=comp_used,
            task_minutes=task_minutes, task_entry_count=len(day_tasks),
            task_summary=task_summary, task_variance_minutes=task_variance,
            attendance_review_status=record.review_status if record else "UNREVIEWED",
            notes=notes,
        ))

        summary["calendar_days"] += 1
        if workday and not holiday and not leave:
            summary["scheduled_workdays"] += 1
        if status in {"PRESENT", "HOLIDAY_WORK", "REST_DAY_WORK", "WORKED_ON_LEAVE", "PARTIAL_LEAVE_WORK"}:
            summary["present_days"] += 1
        elif status == "LATE":
            summary["present_days"] += 1; summary["late_days"] += 1
        elif status == "ABSENT": summary["absent_days"] += 1
        elif status in {"REGULAR_LEAVE", "COMPENSATORY_LEAVE"}: summary["leave_days"] += 1
        elif status == "HOLIDAY": summary["holiday_days"] += 1
        elif status == "REST_DAY": summary["rest_days"] += 1
        elif status == "INCOMPLETE": summary["incomplete_days"] += 1
        elif status == "SCHEDULED": summary["scheduled_future_days"] += 1

        summary["rendered_minutes"] += rendered
        summary["late_minutes"] += late
        summary["undertime_minutes"] += undertime
        summary["potential_overtime_minutes"] += potential_ot
        summary["approved_overtime_minutes"] += approved_ot
        summary["comp_leave_earned_minutes"] += comp_earned
        summary["comp_leave_used_minutes"] += comp_used

    for task in tasks:
        database.add(DTRTaskLine(
            monthly_dtr_id=dtr.id, source_task_id=task.id,
            task_date=task.task_date, project_code=task.project_code,
            project_name=task.project_name, discipline=task.discipline,
            task_description=task.task_description,
            accomplishment=task.accomplishment, task_status=task.task_status,
            minutes_spent=task.minutes_spent,
            completion_percentage=task.completion_percentage, notes=task.notes,
        ))
    for tx in transactions:
        database.add(DTRCompLine(
            monthly_dtr_id=dtr.id, source_transaction_id=tx.id,
            transaction_date=tx.transaction_date,
            transaction_type=tx.transaction_type,
            amount_minutes=tx.amount_minutes, description=tx.description,
        ))
    for leave in leaves.values():
        database.add(DTRLeaveLine(
            monthly_dtr_id=dtr.id, source_leave_id=leave.id,
            leave_date=leave.leave_date, leave_type=leave.leave_type,
            duration_minutes=leave.duration_minutes,
            comp_leave_minutes_used=leave.comp_leave_minutes_used,
            is_paid=leave.is_paid, notes=leave.notes,
        ))

    for key, value in summary.items():
        setattr(dtr, key, value)
    dtr.comp_leave_opening_balance_minutes = comp_balance(
        database, freelancer.id, first_day - timedelta(days=1)
    )
    dtr.comp_leave_closing_balance_minutes = comp_balance(
        database, freelancer.id, month_end
    )
    if not policy.require_daily_task_for_dtr or (summary["present_days"] == 0 and not tasks):
        dtr.task_review_status = "NOT_REQUIRED"
    else:
        dtr.task_review_status = task_review.status if task_review else "UNREVIEWED"
    dtr.pending_overtime_claims = pending_ot
    dtr.pending_leave_requests = pending_leave
    database.flush()
    sync_finance_summary(database, dtr)
    return dtr


def dtr_can_be_reviewed(dtr: MonthlyDTR) -> tuple[bool, str]:
    if dtr.status == "FINALIZED":
        return False, "The DTR is already finalized."
    if dtr.incomplete_days > 0:
        return False, "Resolve all incomplete attendance records first."
    if dtr.scheduled_future_days > 0:
        return False, "The DTR contains future scheduled workdays."
    if dtr.pending_overtime_claims > 0:
        return False, "Review all pending overtime claims first."
    if dtr.pending_leave_requests > 0:
        return False, "Review all pending leave requests first."
    if dtr.task_missing_days > 0:
        return False, "Complete all required daily task reports first."
    if dtr.task_review_status not in {"REVIEWED", "NOT_REQUIRED"}:
        return False, "The monthly daily-task report must be reviewed first."
    return True, ""
