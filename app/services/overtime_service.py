"""Planned/actual overtime and compensatory-credit workflow service."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Callable

from sqlalchemy.exc import IntegrityError

from app.models import OvertimeClaim
from app.repositories.overtime_repository import OvertimeRepository
from app.services.results import ServiceResult


@dataclass(frozen=True, slots=True)
class OvertimeServiceDependencies:
    month_is_locked: Callable[[Any, str], bool]
    local_time_to_utc: Callable[[date, str, str], Any]
    get_policy: Callable[[Any], Any]
    get_daily_attendance: Callable[[Any, int, date], Any]
    invalidate_dtr: Callable[[Any, int, str], None]
    utc_now: Callable[[], Any]
    approve_overtime_claim: Callable[..., None]
    reject_overtime_claim: Callable[..., None]
    write_audit: Callable[..., None]


class OvertimeService:
    def __init__(self, dependencies: OvertimeServiceDependencies, repository_factory=OvertimeRepository):
        self.deps = dependencies
        self.repository_factory = repository_factory

    @staticmethod
    def parse_date(value: str) -> date | None:
        try:
            return date.fromisoformat(value)
        except (TypeError, ValueError):
            return None

    def submit_plan(
        self,
        database: Any,
        *,
        freelancer_id: int,
        attendance_date: str,
        planned_start: str,
        planned_end: str,
        work_description: str,
    ) -> ServiceResult:
        parsed = self.parse_date(attendance_date)
        month = attendance_date[:7] if attendance_date else None
        if parsed is None:
            return ServiceResult.failure("A valid overtime date is required.", month)
        month_key = parsed.strftime("%Y-%m")
        clean_description = work_description.strip()
        if len(clean_description) < 5:
            return ServiceResult.failure(
                "An overtime work description of at least 5 characters is required.", month_key
            )
        if self.deps.month_is_locked(database, month_key):
            return ServiceResult.failure("This month is locked.", month_key)

        repository = self.repository_factory(database)
        freelancer = repository.get_freelancer(freelancer_id)
        try:
            start_utc = self.deps.local_time_to_utc(parsed, planned_start, freelancer.timezone_name)
            end_utc = self.deps.local_time_to_utc(parsed, planned_end, freelancer.timezone_name)
        except ValueError as exc:
            return ServiceResult.failure(str(exc), month_key)
        if not start_utc or not end_utc or end_utc <= start_utc:
            return ServiceResult.failure(
                "Planned end time must be later than planned start time.", month_key
            )

        planned_minutes = int((end_utc - start_utc).total_seconds() // 60)
        policy = self.deps.get_policy(database)
        if planned_minutes < policy.overtime_minimum_minutes:
            return ServiceResult.failure("Planned overtime is below the policy minimum.", month_key)
        if planned_minutes > policy.max_approved_overtime_per_day:
            return ServiceResult.failure("Planned overtime exceeds the daily policy maximum.", month_key)

        repository.add_claim(OvertimeClaim(
            freelancer_id=freelancer_id,
            attendance_date=parsed,
            potential_minutes_snapshot=0,
            requested_minutes=planned_minutes,
            planned_start_utc=start_utc,
            planned_end_utc=end_utc,
            work_description=clean_description,
            status="PENDING_PLAN",
        ))
        try:
            repository.commit()
        except IntegrityError:
            repository.rollback()
            return ServiceResult.failure(
                "An overtime application already exists for this date.", month_key
            )
        return ServiceResult.success(
            "Planned overtime submitted for supervisor approval.", month_key
        )

    def finalize(
        self,
        database: Any,
        *,
        claim_id: int,
        freelancer_id: int,
        claimed_time_out: str,
        missing_time_out_reason: str,
    ) -> ServiceResult:
        repository = self.repository_factory(database)
        claim = repository.get_claim(claim_id)
        if claim is None or claim.freelancer_id != freelancer_id:
            return ServiceResult.failure("Overtime application not found.")
        month_key = claim.attendance_date.strftime("%Y-%m")
        if claim.status != "PLAN_APPROVED":
            return ServiceResult.failure(
                "Only an approved overtime plan can be finalized.", month_key
            )

        record = self.deps.get_daily_attendance(database, freelancer_id, claim.attendance_date)
        freelancer = repository.get_freelancer(freelancer_id)
        if record is not None and bool(getattr(record, "overtime_unavailable", False)):
            return ServiceResult.failure("Overtime is unavailable until an Administrator corrects the missed overnight attendance.", month_key)
        actual_end = record.time_out_utc if record else None
        if actual_end is None:
            clean_reason = missing_time_out_reason.strip()
            if len(clean_reason) < 5:
                return ServiceResult.failure(
                    "Explain the missing logout using at least 5 characters.", month_key
                )
            try:
                actual_end = self.deps.local_time_to_utc(
                    claim.attendance_date, claimed_time_out, freelancer.timezone_name
                )
            except ValueError as exc:
                return ServiceResult.failure(str(exc), month_key)
            if actual_end is None:
                return ServiceResult.failure("Enter the claimed actual end time.", month_key)
            claim.claimed_time_out_utc = actual_end
            claim.missing_time_out_reason = clean_reason
            claim.status = "PENDING_FINAL_MISSING"
        else:
            claim.actual_time_out_utc = actual_end
            claim.status = "PENDING_FINAL"

        if claim.planned_start_utc is None or actual_end <= claim.planned_start_utc:
            return ServiceResult.failure(
                "Actual or claimed end time must be later than the planned OT start.", month_key
            )
        claim.potential_minutes_snapshot = max(
            0, int((actual_end - claim.planned_start_utc).total_seconds() // 60)
        )
        claim.final_submitted_at = self.deps.utc_now()
        self.deps.invalidate_dtr(database, freelancer_id, month_key)
        repository.commit()
        return ServiceResult.success(
            "Actual overtime submitted for final verification.", month_key
        )

    def review(
        self,
        database: Any,
        *,
        claim_id: int,
        admin_id: int,
        decision: str,
        approved_minutes: str,
        approved_time_out: str,
        reason: str,
        audit_request: Any,
    ) -> ServiceResult:
        repository = self.repository_factory(database)
        claim = repository.get_claim(claim_id)
        if claim is None:
            return ServiceResult.failure("Overtime application not found.")
        month_key = claim.attendance_date.strftime("%Y-%m")
        if self.deps.month_is_locked(database, month_key):
            return ServiceResult.failure("Unlock the month before reviewing overtime.", month_key)

        normalized = decision.strip().upper()
        clean_reason = reason.strip()
        try:
            if normalized == "APPROVE_PLAN":
                if claim.status != "PENDING_PLAN":
                    raise ValueError("Only a pending overtime plan can be approved.")
                if len(clean_reason) < 5:
                    raise ValueError("A review reason of at least 5 characters is required.")
                claim.status = "PLAN_APPROVED"
                claim.reviewed_by_admin_id = admin_id
                claim.reviewed_at = self.deps.utc_now()
                claim.review_reason = clean_reason
            elif normalized == "APPROVE_FINAL":
                freelancer = repository.get_freelancer(claim.freelancer_id)
                if approved_time_out.strip():
                    approved_end = self.deps.local_time_to_utc(
                        claim.attendance_date, approved_time_out, freelancer.timezone_name
                    )

                    # A time-only value such as 02:30 can represent the following day
                    # when the planned overtime started the previous evening. First try
                    # the attendance date, then roll forward one calendar day when that
                    # value would otherwise be before (or equal to) the planned OT start.
                    if (
                        claim.planned_start_utc is not None
                        and approved_end is not None
                        and approved_end <= claim.planned_start_utc
                    ):
                        approved_end = self.deps.local_time_to_utc(
                            claim.attendance_date + timedelta(days=1),
                            approved_time_out,
                            freelancer.timezone_name,
                        )

                    if (
                        claim.planned_start_utc is None
                        or approved_end is None
                        or approved_end <= claim.planned_start_utc
                    ):
                        raise ValueError("Approved end time must be later than planned OT start.")
                    claim.approved_time_out_utc = approved_end
                    verified_minutes = int(
                        (approved_end - claim.planned_start_utc).total_seconds() // 60
                    )
                else:
                    verified_minutes = int(approved_minutes)
                self.deps.approve_overtime_claim(
                    database,
                    claim=claim,
                    approved_minutes=verified_minutes,
                    admin_id=admin_id,
                    reason=clean_reason,
                )
            elif normalized == "REJECT":
                self.deps.reject_overtime_claim(
                    database, claim, admin_id=admin_id, reason=clean_reason
                )
            else:
                raise ValueError("Invalid overtime review decision.")

            self.deps.write_audit(
                database,
                actor_type="HR_ADMIN",
                actor_id=admin_id,
                action=f"{normalized}_OVERTIME",
                request=audit_request,
                target_type="OVERTIME_CLAIM",
                target_id=claim.id,
                details=clean_reason,
            )
            repository.commit()
        except (ValueError, IntegrityError) as exc:
            repository.rollback()
            return ServiceResult.failure(str(exc), month_key)
        return ServiceResult.success("Overtime application reviewed.", month_key)
