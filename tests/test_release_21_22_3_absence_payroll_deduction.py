from app.payroll_engine import calculate_payroll_multiplier


def test_absence_reduces_monthly_percentage_like_direct_unpaid_time():
    result = calculate_payroll_multiplier(
        calendar_days=30,
        approved_leave_minutes=0,
        comp_credit_minutes_available=0,
        standard_day_minutes=480,
        absent_days=1,
    )
    assert result.absent_minutes == 480
    assert result.effective_unpaid_leave_minutes == 0
    assert result.total_deduction_minutes == 480
    assert result.salary_basis_minutes == 14400
    assert result.salary_covered_minutes == 13920
    assert result.percentage_display == "96.67%"


def test_comp_credit_does_not_cancel_absence():
    result = calculate_payroll_multiplier(
        calendar_days=30,
        approved_leave_minutes=480,
        comp_credit_minutes_available=960,
        standard_day_minutes=480,
        absent_days=1,
    )
    # One day of comp credit covers the approved leave only. The absence stays.
    assert result.comp_credit_minutes_applied == 480
    assert result.effective_unpaid_leave_minutes == 0
    assert result.absent_minutes == 480
    assert result.total_deduction_minutes == 480
    assert result.percentage_display == "96.67%"


def test_unpaid_leave_and_absence_both_reduce_percentage():
    result = calculate_payroll_multiplier(
        calendar_days=31,
        approved_leave_minutes=960,
        comp_credit_minutes_available=480,
        standard_day_minutes=480,
        absent_days=2,
    )
    # 1 uncovered leave day + 2 absent days = 3 direct deduction days.
    assert result.effective_unpaid_leave_minutes == 480
    assert result.absent_minutes == 960
    assert result.total_deduction_minutes == 1440
    expected = (31 * 480 - 1440) / (31 * 480)
    assert abs(result.payroll_multiplier - expected) < 1e-12
    assert "unpaid leave" in result.payroll_treatment_display
    assert "absence" in result.payroll_treatment_display


def test_no_absence_preserves_existing_calculation():
    result = calculate_payroll_multiplier(
        calendar_days=30,
        approved_leave_minutes=480,
        comp_credit_minutes_available=240,
        standard_day_minutes=480,
    )
    assert result.absent_minutes == 0
    assert result.effective_unpaid_leave_minutes == 240
    assert result.total_deduction_minutes == 240
    assert result.salary_covered_minutes == (30 * 480) - 240
