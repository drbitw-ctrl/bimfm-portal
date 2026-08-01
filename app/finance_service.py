from __future__ import annotations

from datetime import timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.hr_workflow import COMP_LEAVE_DAY_MINUTES
from app.payroll_engine import calculate_payroll_multiplier

from app.hr_workflow import month_bounds
from app.models import (
    DTRDailyLine, DTRLeaveLine, Freelancer, HRPolicy, MonthlyCompLeaveBalance, MonthlyDTR, PayrollMonthSummary
)


def _leave_totals(database: Session, dtr_id: int) -> tuple[int, int, int]:
    rows = list(database.scalars(select(DTRLeaveLine).where(DTRLeaveLine.monthly_dtr_id == dtr_id)).all())
    paid = sum(int(x.duration_minutes or 0) for x in rows if x.is_paid and x.leave_type != "COMPENSATORY")
    unpaid = sum(int(x.duration_minutes or 0) for x in rows if not x.is_paid)
    comp = sum(int(x.comp_leave_minutes_used or 0) for x in rows)
    return paid, unpaid, comp


def sync_finance_summary(database: Session, dtr: MonthlyDTR) -> PayrollMonthSummary:
    paid, unpaid, comp_taken = _leave_totals(database, dtr.id)
    expected_close = int(dtr.comp_leave_opening_balance_minutes or 0) + int(dtr.comp_leave_earned_minutes or 0) - int(dtr.comp_leave_used_minutes or 0)
    balanced = expected_close == int(dtr.comp_leave_closing_balance_minutes or 0)
    attendance_complete = not dtr.incomplete_days and not dtr.scheduled_future_days
    tasks_complete = dtr.task_missing_days == 0 and dtr.task_review_status in {"REVIEWED", "NOT_REQUIRED"}
    overtime_complete = dtr.pending_overtime_claims == 0
    leave_complete = dtr.pending_leave_requests == 0
    ready = all((attendance_complete, tasks_complete, overtime_complete, leave_complete, balanced))
    # Monthly-rate model: approved OT earns compensatory credits only.
    # It never increases payable salary time.
    payroll_review = int(dtr.rendered_minutes or 0) + paid + comp_taken

    balance = database.scalar(select(MonthlyCompLeaveBalance).where(
        MonthlyCompLeaveBalance.freelancer_id == dtr.freelancer_id,
        MonthlyCompLeaveBalance.month_key == dtr.month_key,
    ))
    if balance is None:
        balance = MonthlyCompLeaveBalance(freelancer_id=dtr.freelancer_id, month_key=dtr.month_key)
        database.add(balance)
    balance.opening_balance_minutes = dtr.comp_leave_opening_balance_minutes
    balance.earned_minutes = dtr.comp_leave_earned_minutes
    balance.used_minutes = dtr.comp_leave_used_minutes
    balance.adjustment_minutes = int(dtr.comp_leave_closing_balance_minutes or 0) - expected_close
    balance.closing_balance_minutes = dtr.comp_leave_closing_balance_minutes

    summary = database.scalar(select(PayrollMonthSummary).where(
        PayrollMonthSummary.freelancer_id == dtr.freelancer_id,
        PayrollMonthSummary.month_key == dtr.month_key,
    ))
    if summary is None:
        summary = PayrollMonthSummary(freelancer_id=dtr.freelancer_id, monthly_dtr_id=dtr.id, month_key=dtr.month_key)
        database.add(summary)
    summary.monthly_dtr_id = dtr.id
    summary.regular_minutes = dtr.rendered_minutes
    summary.approved_overtime_minutes = dtr.approved_overtime_minutes
    summary.potential_overtime_minutes = dtr.potential_overtime_minutes
    summary.paid_leave_minutes = paid
    summary.unpaid_leave_minutes = unpaid
    summary.comp_leave_used_minutes = comp_taken
    summary.opening_balance_minutes = dtr.comp_leave_opening_balance_minutes
    summary.earned_minutes = dtr.comp_leave_earned_minutes
    summary.closing_balance_minutes = dtr.comp_leave_closing_balance_minutes
    summary.payroll_review_minutes = payroll_review
    summary.attendance_complete = attendance_complete
    summary.tasks_complete = tasks_complete
    summary.overtime_complete = overtime_complete
    summary.leave_complete = leave_complete
    summary.comp_ledger_balanced = balanced
    summary.payroll_status = "READY" if ready else "NOT_READY"
    database.flush()
    return summary


def finance_rows(database: Session, month_key: str) -> list[dict]:
    freelancers = {f.id: f for f in database.scalars(select(Freelancer).order_by(Freelancer.full_name)).all()}
    summaries = list(database.scalars(select(PayrollMonthSummary).where(PayrollMonthSummary.month_key == month_key)).all())
    policy = database.scalar(select(HRPolicy).order_by(HRPolicy.id))
    standard_day_minutes = max(1, int(policy.standard_leave_day_minutes if policy else 480))
    rows = []
    for x in summaries:
        f = freelancers.get(x.freelancer_id)
        if not f:
            continue
        dtr = database.get(MonthlyDTR, x.monthly_dtr_id)
        if dtr is None:
            continue
        leave_lines = list(database.scalars(select(DTRLeaveLine).where(DTRLeaveLine.monthly_dtr_id == dtr.id)).all())

        # Finance reports use calendar-day counts, never hour-derived decimal days.
        # A day with attendance is one physically worked day regardless of OT,
        # late minutes, or undertime. Approved OT is credited separately and must
        # never inflate the number of days worked or payable.
        worked_statuses = {"PRESENT", "LATE", "HOLIDAY_WORK", "REST_DAY_WORK", "WORKED_ON_LEAVE", "PARTIAL_LEAVE_WORK"}
        daily_lines = list(database.scalars(
            select(DTRDailyLine).where(DTRDailyLine.monthly_dtr_id == dtr.id)
        ).all())
        worked_days = len({line.attendance_date for line in daily_lines if line.attendance_status in worked_statuses})
        regular_leave_taken_days = len({line.leave_date for line in leave_lines})

        # Payroll multiplier policy (calendar-day monthly salary model):
        #   multiplier = (calendar days - effective unpaid leave days) / calendar days
        #   effective unpaid leave = max(0, approved leave days - comp credits applied)
        # Compensatory credits can only offset approved leave and can never push
        # the multiplier above 1.0000. Any unused balance remains in the ledger.
        comp_credit_days_used = int(x.comp_leave_used_minutes or 0) // COMP_LEAVE_DAY_MINUTES
        payroll = calculate_payroll_multiplier(
            calendar_days=int(dtr.calendar_days or 0),
            approved_leave_days=regular_leave_taken_days,
            comp_credit_days_available=comp_credit_days_used,
        )
        comp_credit_days_applied = payroll.comp_credit_days_applied
        effective_unpaid_leave_days = payroll.effective_unpaid_leave_days
        calendar_days = payroll.calendar_days
        payroll_numerator_days = payroll.payroll_numerator_days
        payroll_multiplier = payroll.payroll_multiplier

        # Retain the older attendance reconciliation figures for drill-down pages,
        # but do not use them as the salary basis.
        regular_leave_days = effective_unpaid_leave_days
        comp_leave_days = comp_credit_days_applied
        payable_days = worked_days + comp_leave_days
        non_payable_days = effective_unpaid_leave_days + int(dtr.absent_days or 0)
        rows.append({
            "id": x.id, "dtr_id": x.monthly_dtr_id, "code": f.freelancer_code, "name": f.full_name,
            "calendar_days": calendar_days,
            "leave_days": regular_leave_taken_days,
            "comp_credit_days_applied": comp_credit_days_applied,
            "effective_unpaid_leave_days": effective_unpaid_leave_days,
            "payroll_numerator_days": payroll_numerator_days,
            "payroll_multiplier": payroll_multiplier,
            # Retained for API/backward compatibility; the Finance UI no longer
            # displays decimal multipliers or percentages.
            "payroll_multiplier_display": payroll.multiplier_display,
            "payroll_percentage_display": payroll.percentage_display,
            "payroll_formula_display": payroll.formula_display,
            "salary_covered_days": payroll_numerator_days,
            "salary_coverage_display": payroll.salary_coverage_display,
            "payroll_treatment_display": payroll.payroll_treatment_display,
            "deduction_display": payroll.deduction_display,
            "worked_days": worked_days,
            "regular_leave_taken_days": regular_leave_taken_days,
            "regular_leave_days": regular_leave_days,
            "comp_leave_days": comp_leave_days,
            "payable_days": payable_days,
            "payable_workday_equivalents": payable_days,
            "non_payable_days": non_payable_days,
            "rest_days": int(dtr.rest_days or 0), "holiday_days": int(dtr.holiday_days or 0),
            "approved_ot_minutes": int(x.approved_overtime_minutes or 0),
            "comp_earned_minutes": int(x.earned_minutes or 0),
            "comp_used_minutes": int(x.comp_leave_used_minutes or 0),
            "opening_minutes": int(x.opening_balance_minutes or 0),
            "closing_minutes": int(x.closing_balance_minutes or 0),
            "status": x.payroll_status, "attendance": x.attendance_complete, "tasks": x.tasks_complete,
            "overtime": x.overtime_complete, "leave": x.leave_complete, "balanced": x.comp_ledger_balanced,
        })
    return rows
