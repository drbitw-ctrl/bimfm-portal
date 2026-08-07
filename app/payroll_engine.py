from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PayrollCalculation:
    """Hourly monthly-salary calculation while retaining workday reporting.

    The monthly salary basis follows the approved company example:
    monthly salary / calendar days / standard work hours per day. Approved
    overtime credit offsets approved leave minute-for-minute and can never
    increase salary above the full monthly rate.
    """

    calendar_days: int
    standard_day_minutes: int
    approved_leave_minutes: int
    comp_credit_minutes_available: int
    comp_credit_minutes_applied: int
    effective_unpaid_leave_minutes: int
    absence_comp_credit_minutes_applied: int
    absent_minutes: int
    effective_absent_minutes: int
    salary_basis_minutes: int
    salary_covered_minutes: int
    payroll_multiplier: float

    @property
    def approved_leave_hours(self) -> float:
        return self.approved_leave_minutes / 60

    @property
    def comp_credit_hours_available(self) -> float:
        return self.comp_credit_minutes_available / 60

    @property
    def comp_credit_hours_applied(self) -> float:
        return self.comp_credit_minutes_applied / 60

    @property
    def effective_unpaid_leave_hours(self) -> float:
        return self.effective_unpaid_leave_minutes / 60

    @property
    def absent_hours(self) -> float:
        return self.absent_minutes / 60

    @property
    def absent_days(self) -> float:
        return self.absent_minutes / self.standard_day_minutes

    @property
    def absence_comp_credit_hours_applied(self) -> float:
        return self.absence_comp_credit_minutes_applied / 60

    @property
    def effective_absent_hours(self) -> float:
        return self.effective_absent_minutes / 60

    @property
    def effective_absent_days(self) -> float:
        return self.effective_absent_minutes / self.standard_day_minutes

    @property
    def total_deduction_minutes(self) -> int:
        return self.effective_unpaid_leave_minutes + self.effective_absent_minutes

    @property
    def total_deduction_hours(self) -> float:
        return self.total_deduction_minutes / 60

    @property
    def approved_leave_days(self) -> float:
        return self.approved_leave_minutes / self.standard_day_minutes

    @property
    def comp_credit_days_available(self) -> float:
        return self.comp_credit_minutes_available / self.standard_day_minutes

    @property
    def comp_credit_days_applied(self) -> float:
        return self.comp_credit_minutes_applied / self.standard_day_minutes

    @property
    def effective_unpaid_leave_days(self) -> float:
        return self.effective_unpaid_leave_minutes / self.standard_day_minutes

    @property
    def payroll_numerator_days(self) -> float:
        return self.salary_covered_minutes / self.standard_day_minutes

    @property
    def multiplier_display(self) -> str:
        return f"{self.payroll_multiplier:.4f}×"

    @property
    def percentage_display(self) -> str:
        return f"{self.payroll_multiplier * 100:.2f}%"

    @property
    def formula_display(self) -> str:
        return (
            f"({self.salary_basis_minutes} - {self.effective_unpaid_leave_minutes} "
            f"- {self.effective_absent_minutes}) / {self.salary_basis_minutes}"
        )

    @property
    def salary_coverage_display(self) -> str:
        covered_hours = self.salary_covered_minutes / 60
        basis_hours = self.salary_basis_minutes / 60
        return f"{covered_hours:g} of {basis_hours:g} salary-basis hours"

    @property
    def payroll_treatment_display(self) -> str:
        if self.total_deduction_minutes == 0:
            return "Full Monthly Rate"
        parts = []
        if self.effective_unpaid_leave_minutes:
            parts.append(f"{self.effective_unpaid_leave_hours:g} unpaid leave hours")
        if self.effective_absent_minutes:
            parts.append(f"{self.effective_absent_hours:g} uncovered absence hours")
        return "Reduced by " + " + ".join(parts)

    @property
    def deduction_display(self) -> str:
        return f"{self.total_deduction_hours:g} hours"


def calculate_payroll_multiplier(
    *,
    calendar_days: int,
    approved_leave_minutes: int,
    comp_credit_minutes_available: int,
    standard_day_minutes: int = 480,
    absent_days: int = 0,
) -> PayrollCalculation:
    """Calculate hourly leave deduction against a calendar-day monthly salary."""
    normalized_calendar_days = max(1, int(calendar_days or 0))
    normalized_standard_day = max(1, int(standard_day_minutes or 0))
    normalized_leave = max(0, int(approved_leave_minutes or 0))
    normalized_comp = max(0, int(comp_credit_minutes_available or 0))
    normalized_absent_days = max(0, int(absent_days or 0))

    # Approved compensatory credit first offsets approved leave, then any
    # remaining approved credit offsets ABSENT time. This supports the common
    # case where a leave request was missed but the member already has approved
    # comp credit. Credit can never increase salary above the full monthly rate.
    leave_comp_applied = min(normalized_leave, normalized_comp)
    effective_unpaid = max(0, normalized_leave - leave_comp_applied)
    remaining_comp = max(0, normalized_comp - leave_comp_applied)
    absent_minutes = normalized_absent_days * normalized_standard_day
    absence_comp_applied = min(absent_minutes, remaining_comp)
    effective_absent = max(0, absent_minutes - absence_comp_applied)
    comp_applied = leave_comp_applied + absence_comp_applied
    salary_basis = normalized_calendar_days * normalized_standard_day
    salary_covered = max(0, salary_basis - effective_unpaid - effective_absent)
    multiplier = min(1.0, max(0.0, salary_covered / salary_basis))

    return PayrollCalculation(
        calendar_days=normalized_calendar_days,
        standard_day_minutes=normalized_standard_day,
        approved_leave_minutes=normalized_leave,
        comp_credit_minutes_available=normalized_comp,
        comp_credit_minutes_applied=comp_applied,
        effective_unpaid_leave_minutes=effective_unpaid,
        absence_comp_credit_minutes_applied=absence_comp_applied,
        absent_minutes=absent_minutes,
        effective_absent_minutes=effective_absent,
        salary_basis_minutes=salary_basis,
        salary_covered_minutes=salary_covered,
        payroll_multiplier=multiplier,
    )
