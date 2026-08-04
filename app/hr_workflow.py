from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.models import (
    CompLeaveTransaction,
    DailyTask,
    HRPolicy,
    LeaveRecord,
    LeaveRequest,
    OvertimeClaim,
    TaskMonthReview,
    MonthlyDTR,
)


COMP_LEAVE_DAY_MINUTES = 8 * 60


def whole_comp_days(minutes: int) -> int:
    """Compatibility display helper for complete-day equivalents.

    Credit eligibility is hourly; this value is never used to block partial
    credit redemption.
    """
    return max(0, int(minutes or 0)) // COMP_LEAVE_DAY_MINUTES


def redeemable_comp_minutes(minutes: int) -> int:
    """Return all positive credit minutes; partial hours are immediately usable."""
    return max(0, int(minutes or 0))


def comp_remainder_minutes(minutes: int) -> int:
    """Retained for compatibility; hourly policy has no blocked remainder."""
    return 0


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def month_bounds(month_key: str) -> tuple[date, date]:
    year, month = (int(part) for part in month_key.split("-"))
    first = date(year, month, 1)
    next_month = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return first, next_month


def ensure_default_policy(database: Session) -> HRPolicy:
    policy = database.scalar(
        select(HRPolicy).where(HRPolicy.is_active.is_(True)).order_by(HRPolicy.id)
    )
    if policy is not None:
        return policy
    policy = HRPolicy(
        name="BIMFM Standard HR Policy",
        standard_leave_day_minutes=480,
        overtime_minimum_minutes=30,
        overtime_rounding_minutes=15,
        overtime_to_comp_numerator=1,
        overtime_to_comp_denominator=1,
        max_approved_overtime_per_day=480,
        require_task_for_overtime=True,
        require_daily_task_for_dtr=True,
        task_variance_warning_minutes=60,
        allow_negative_comp_balance=False,
        show_project_engineer_to_freelancers=False,
        is_active=True,
    )
    database.add(policy)
    database.commit()
    database.refresh(policy)
    return policy


def get_policy(database: Session) -> HRPolicy:
    return ensure_default_policy(database)


def rounded_down(minutes: int, unit: int) -> int:
    minutes = max(0, int(minutes or 0))
    unit = max(1, int(unit or 1))
    return (minutes // unit) * unit


def comp_minutes_from_overtime(approved_minutes: int, policy: HRPolicy) -> int:
    numerator = max(1, policy.overtime_to_comp_numerator)
    denominator = max(1, policy.overtime_to_comp_denominator)
    raw = (max(0, approved_minutes) * numerator) // denominator
    return rounded_down(raw, policy.overtime_rounding_minutes)


def comp_balance(
    database: Session,
    freelancer_id: int,
    through_date: Optional[date] = None,
) -> int:
    query = select(func.coalesce(func.sum(CompLeaveTransaction.amount_minutes), 0)).where(
        CompLeaveTransaction.freelancer_id == freelancer_id
    )
    if through_date is not None:
        query = query.where(CompLeaveTransaction.transaction_date <= through_date)
    return int(database.scalar(query) or 0)


def task_minutes_for_date(database: Session, freelancer_id: int, task_date: date) -> int:
    return int(
        database.scalar(
            select(func.coalesce(func.sum(DailyTask.minutes_spent), 0)).where(
                DailyTask.freelancer_id == freelancer_id,
                DailyTask.task_date == task_date,
            )
        )
        or 0
    )


def invalidate_dtr(database: Session, freelancer_id: int, month_key: str) -> None:
    """Delete non-finalized snapshots so stale data cannot be reviewed/exported."""
    database.execute(
        delete(MonthlyDTR).where(
            MonthlyDTR.freelancer_id == freelancer_id,
            MonthlyDTR.month_key == month_key,
            MonthlyDTR.status != "FINALIZED",
        )
    )


def invalidate_task_review(database: Session, freelancer_id: int, month_key: str) -> None:
    database.execute(
        delete(TaskMonthReview).where(
            TaskMonthReview.freelancer_id == freelancer_id,
            TaskMonthReview.month_key == month_key,
        )
    )
    invalidate_dtr(database, freelancer_id, month_key)


def get_task_review(database: Session, freelancer_id: int, month_key: str):
    return database.scalar(
        select(TaskMonthReview).where(
            TaskMonthReview.freelancer_id == freelancer_id,
            TaskMonthReview.month_key == month_key,
        )
    )


def approve_overtime_claim(
    database: Session,
    *,
    claim: OvertimeClaim,
    approved_minutes: int,
    admin_id: int,
    reason: str,
) -> None:
    policy = get_policy(database)
    reason = reason.strip()
    if len(reason) < 5:
        raise ValueError("A review reason of at least 5 characters is required.")
    if claim.status not in {"PENDING", "PENDING_FINAL", "PENDING_FINAL_MISSING"}:
        raise ValueError("Only overtime claims pending final verification can be approved.")
    approved = max(0, int(approved_minutes))
    approved = min(
        approved,
        claim.requested_minutes,
        claim.potential_minutes_snapshot,
        policy.max_approved_overtime_per_day,
    )
    approved = rounded_down(approved, policy.overtime_rounding_minutes)
    if approved < policy.overtime_minimum_minutes:
        raise ValueError("Approved overtime is below the policy minimum.")
    earned = comp_minutes_from_overtime(approved, policy)
    if earned <= 0:
        raise ValueError("The overtime approval does not earn compensatory leave.")

    claim.status = "APPROVED"
    claim.approved_minutes = approved
    claim.comp_leave_minutes_earned = earned
    claim.reviewed_by_admin_id = admin_id
    claim.reviewed_at = utc_now()
    claim.review_reason = reason

    invalidate_dtr(database, claim.freelancer_id, claim.attendance_date.strftime("%Y-%m"))

    database.add(
        CompLeaveTransaction(
            freelancer_id=claim.freelancer_id,
            transaction_date=claim.attendance_date,
            transaction_type="EARNED_OVERTIME",
            amount_minutes=earned,
            source_key=f"OVERTIME_CLAIM:{claim.id}",
            description=(
                f"Approved {approved} overtime minutes; "
                f"earned {earned} compensatory-leave minutes."
            ),
            created_by_admin_id=admin_id,
        )
    )


def reject_overtime_claim(
    database: Session,
    claim: OvertimeClaim,
    *,
    admin_id: int,
    reason: str,
) -> None:
    reason = reason.strip()
    if len(reason) < 5:
        raise ValueError("A rejection reason of at least 5 characters is required.")
    if claim.status not in {"PENDING", "PENDING_PLAN", "PLAN_APPROVED", "PENDING_FINAL", "PENDING_FINAL_MISSING"}:
        raise ValueError("This overtime claim is no longer pending review.")
    claim.status = "REJECTED"
    claim.approved_minutes = 0
    claim.comp_leave_minutes_earned = 0
    claim.reviewed_by_admin_id = admin_id
    claim.reviewed_at = utc_now()
    claim.review_reason = reason
    invalidate_dtr(database, claim.freelancer_id, claim.attendance_date.strftime("%Y-%m"))


def approve_leave_request(
    database: Session,
    *,
    request_record: LeaveRequest,
    admin_id: int,
    reason: str,
) -> LeaveRecord:
    policy = get_policy(database)
    reason = reason.strip()
    if len(reason) < 5:
        raise ValueError("A review reason of at least 5 characters is required.")
    if request_record.status != "PENDING":
        raise ValueError("Only pending leave requests can be reviewed.")

    # Leave requests remain full working days for attendance reporting, while
    # overtime credits are applied hour-for-hour. Partial credit balances are
    # usable immediately and may cover part of a leave day.
    full_day_minutes = int(policy.standard_leave_day_minutes or COMP_LEAVE_DAY_MINUTES)
    if int(request_record.requested_minutes or 0) != full_day_minutes:
        raise ValueError("Leave requests must be exactly one standard workday.")
    approved = full_day_minutes

    existing = database.scalar(
        select(LeaveRecord).where(
            LeaveRecord.freelancer_id == request_record.freelancer_id,
            LeaveRecord.leave_date == request_record.leave_date,
        )
    )
    if existing is not None:
        raise ValueError("An approved leave record already exists for this date.")

    comp_used = 0
    paid = False
    if request_record.leave_type == "COMPENSATORY_LEAVE":
        available = comp_balance(
            database,
            request_record.freelancer_id,
            request_record.leave_date,
        )
        if available <= 0:
            raise ValueError("No compensatory credit is available for this leave date.")
        comp_used = min(approved, max(0, int(available)))
        paid = comp_used >= approved

    leave = LeaveRecord(
        freelancer_id=request_record.freelancer_id,
        leave_date=request_record.leave_date,
        leave_type=request_record.leave_type,
        is_paid=paid,
        status="APPROVED",
        duration_minutes=approved,
        comp_leave_minutes_used=comp_used,
        source_request_id=request_record.id,
        notes=request_record.reason,
        approved_by_admin_id=admin_id,
    )
    database.add(leave)
    database.flush()

    if comp_used:
        database.add(
            CompLeaveTransaction(
                freelancer_id=request_record.freelancer_id,
                transaction_date=request_record.leave_date,
                transaction_type="USED_LEAVE",
                amount_minutes=-comp_used,
                source_key=f"LEAVE_REQUEST:{request_record.id}",
                description=(
                    f"Used {comp_used} compensatory-leave minutes for "
                    f"{request_record.leave_date.isoformat()}."
                ),
                created_by_admin_id=admin_id,
            )
        )

    request_record.status = "APPROVED"
    request_record.approved_minutes = approved
    request_record.reviewed_by_admin_id = admin_id
    request_record.reviewed_at = utc_now()
    request_record.review_reason = reason
    invalidate_dtr(database, request_record.freelancer_id, request_record.leave_date.strftime("%Y-%m"))
    return leave


def reject_leave_request(
    database: Session,
    request_record: LeaveRequest,
    *,
    admin_id: int,
    reason: str,
) -> None:
    reason = reason.strip()
    if len(reason) < 5:
        raise ValueError("A rejection reason of at least 5 characters is required.")
    if request_record.status != "PENDING":
        raise ValueError("Only pending leave requests can be reviewed.")
    request_record.status = "REJECTED"
    request_record.approved_minutes = 0
    request_record.reviewed_by_admin_id = admin_id
    request_record.reviewed_at = utc_now()
    request_record.review_reason = reason
    invalidate_dtr(database, request_record.freelancer_id, request_record.leave_date.strftime("%Y-%m"))


def pending_counts(database: Session, freelancer_id: int, month_key: str) -> tuple[int, int]:
    first, next_month = month_bounds(month_key)
    pending_ot = int(
        database.scalar(
            select(func.count(OvertimeClaim.id)).where(
                OvertimeClaim.freelancer_id == freelancer_id,
                OvertimeClaim.attendance_date >= first,
                OvertimeClaim.attendance_date < next_month,
                OvertimeClaim.status == "PENDING",
            )
        )
        or 0
    )
    pending_leave = int(
        database.scalar(
            select(func.count(LeaveRequest.id)).where(
                LeaveRequest.freelancer_id == freelancer_id,
                LeaveRequest.leave_date >= first,
                LeaveRequest.leave_date < next_month,
                LeaveRequest.status == "PENDING",
            )
        )
        or 0
    )
    return pending_ot, pending_leave
