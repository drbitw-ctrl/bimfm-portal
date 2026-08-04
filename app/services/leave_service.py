"""Leave-request business workflow.

No FastAPI request/response or localization rendering belongs in this module.
The service returns stable message keys; the presentation layer translates them.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable, Any

from sqlalchemy.exc import IntegrityError

from app.models import LeaveRequest
from app.repositories.leave_repository import LeaveRepository
from app.services.results import ServiceResult


@dataclass(frozen=True, slots=True)
class LeaveServiceDependencies:
    comp_balance: Callable[..., int]
    whole_comp_days: Callable[[int], int]
    month_is_locked: Callable[[Any, str], bool]
    invalidate_dtr: Callable[[Any, int, str], None]
    approve_leave_request: Callable[..., None]
    reject_leave_request: Callable[..., None]
    write_audit: Callable[..., None]
    comp_leave_day_minutes: int


class LeaveService:
    VALID_TYPES = frozenset({"COMPENSATORY_LEAVE", "UNPAID_LEAVE", "OTHER_APPROVED_LEAVE"})
    VALID_DECISIONS = frozenset({"APPROVE", "REJECT"})

    def __init__(self, dependencies: LeaveServiceDependencies, repository_factory=LeaveRepository):
        self.deps = dependencies
        self.repository_factory = repository_factory

    @staticmethod
    def parse_leave_date(value: str) -> date | None:
        try:
            return date.fromisoformat(value)
        except (TypeError, ValueError):
            return None

    def submit(
        self,
        database: Any,
        *,
        freelancer_id: int,
        leave_date: str,
        leave_type: str,
        reason: str,
    ) -> ServiceResult:
        parsed = self.parse_leave_date(leave_date)
        month = leave_date[:7] if leave_date else None
        if parsed is None:
            return ServiceResult.failure("Invalid leave date.", month)

        normalized_type = leave_type.strip().upper()
        if normalized_type not in self.VALID_TYPES:
            return ServiceResult.failure("Invalid leave type.", parsed.strftime("%Y-%m"))

        clean_reason = reason.strip()
        if len(clean_reason) < 5:
            return ServiceResult.failure(
                "A leave reason of at least 5 characters is required.",
                parsed.strftime("%Y-%m"),
            )

        month_key = parsed.strftime("%Y-%m")
        if self.deps.month_is_locked(database, month_key):
            return ServiceResult.failure("This month is locked.", month_key)

        if normalized_type == "COMPENSATORY_LEAVE":
            available = self.deps.comp_balance(database, freelancer_id, parsed)
            if available <= 0:
                return ServiceResult.failure(
                    "No compensatory credit is available for this leave date.",
                    month_key,
                )

        record = LeaveRequest(
            freelancer_id=freelancer_id,
            leave_date=parsed,
            leave_type=normalized_type,
            requested_minutes=self.deps.comp_leave_day_minutes,
            reason=clean_reason,
            status="PENDING",
        )
        repository = self.repository_factory(database)
        repository.add_request(record)
        self.deps.invalidate_dtr(database, freelancer_id, month_key)
        try:
            repository.commit()
        except IntegrityError:
            repository.rollback()
            return ServiceResult.failure("A leave request already exists for this date.", month_key)
        return ServiceResult.success("Leave request submitted for HR review.", month_key)

    def cancel(self, database: Any, *, request_id: int, freelancer_id: int) -> ServiceResult:
        repository = self.repository_factory(database)
        record = repository.get_request(request_id)
        if record is None or record.freelancer_id != freelancer_id:
            return ServiceResult.failure("Leave request not found.")
        month_key = record.leave_date.strftime("%Y-%m")
        if record.status != "PENDING":
            return ServiceResult.failure("Only pending leave requests can be cancelled.", month_key)
        record.status = "CANCELLED"
        self.deps.invalidate_dtr(database, freelancer_id, month_key)
        repository.commit()
        return ServiceResult.success("Leave request cancelled.", month_key)

    def review(
        self,
        database: Any,
        *,
        request_id: int,
        admin_id: int,
        decision: str,
        reason: str,
        audit_request: Any,
    ) -> ServiceResult:
        repository = self.repository_factory(database)
        record = repository.get_request(request_id)
        if record is None:
            return ServiceResult.failure("Leave request not found.")
        month_key = record.leave_date.strftime("%Y-%m")
        if self.deps.month_is_locked(database, month_key):
            return ServiceResult.failure("Unlock the month before reviewing leave.", month_key)

        normalized = decision.strip().upper()
        if normalized not in self.VALID_DECISIONS:
            return ServiceResult.failure("Invalid leave review decision.", month_key)

        clean_reason = reason.strip()
        try:
            if normalized == "APPROVE":
                self.deps.approve_leave_request(
                    database, request_record=record, admin_id=admin_id, reason=clean_reason
                )
            else:
                self.deps.reject_leave_request(
                    database, record, admin_id=admin_id, reason=clean_reason
                )
            self.deps.write_audit(
                database,
                actor_type="HR_ADMIN",
                actor_id=admin_id,
                action=f"{normalized}_LEAVE_REQUEST",
                request=audit_request,
                target_type="LEAVE_REQUEST",
                target_id=record.id,
                details=clean_reason,
            )
            repository.commit()
        except (ValueError, IntegrityError) as exc:
            repository.rollback()
            return ServiceResult.failure(str(exc), month_key)
        return ServiceResult.success("Leave request reviewed.", month_key)
