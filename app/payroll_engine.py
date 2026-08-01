from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PayrollCalculation:
    calendar_days: int
    approved_leave_days: int
    comp_credit_days_available: int
    comp_credit_days_applied: int
    effective_unpaid_leave_days: int
    payroll_numerator_days: int
    payroll_multiplier: float

    @property
    def multiplier_display(self) -> str:
        return f"{self.payroll_multiplier:.4f}×"

    @property
    def percentage_display(self) -> str:
        return f"{self.payroll_multiplier * 100:.2f}%"

    @property
    def formula_display(self) -> str:
        return (
            f"({self.calendar_days} - {self.effective_unpaid_leave_days}) "
            f"/ {self.calendar_days}"
        )

    @property
    def salary_coverage_display(self) -> str:
        return f"{self.payroll_numerator_days} of {self.calendar_days} days"

    @property
    def payroll_treatment_display(self) -> str:
        if self.effective_unpaid_leave_days == 0:
            return "Full Monthly Rate"
        day_word = "day" if self.effective_unpaid_leave_days == 1 else "days"
        return f"Reduced by {self.effective_unpaid_leave_days} calendar {day_word}"

    @property
    def deduction_display(self) -> str:
        day_word = "day" if self.effective_unpaid_leave_days == 1 else "days"
        return f"{self.effective_unpaid_leave_days} {day_word}"


def calculate_payroll_multiplier(
    *,
    calendar_days: int,
    approved_leave_days: int,
    comp_credit_days_available: int,
) -> PayrollCalculation:
    """Calculate the monthly-rate freelancer payroll multiplier.

    Approved overtime never raises salary. Whole-day compensatory credits may
    offset approved leave, and the final multiplier is always between 0 and 1.
    """
    normalized_calendar_days = max(1, int(calendar_days or 0))
    normalized_leave_days = max(0, int(approved_leave_days or 0))
    normalized_comp_days = max(0, int(comp_credit_days_available or 0))

    comp_applied = min(normalized_leave_days, normalized_comp_days)
    effective_unpaid = max(0, normalized_leave_days - comp_applied)
    numerator = max(0, normalized_calendar_days - effective_unpaid)
    multiplier = min(1.0, max(0.0, numerator / normalized_calendar_days))

    return PayrollCalculation(
        calendar_days=normalized_calendar_days,
        approved_leave_days=normalized_leave_days,
        comp_credit_days_available=normalized_comp_days,
        comp_credit_days_applied=comp_applied,
        effective_unpaid_leave_days=effective_unpaid,
        payroll_numerator_days=numerator,
        payroll_multiplier=multiplier,
    )
