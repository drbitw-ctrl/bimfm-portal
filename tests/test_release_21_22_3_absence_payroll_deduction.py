from app.payroll_engine import calculate_payroll_multiplier


def test_absence_reduces_monthly_percentage_when_no_comp_credit_exists():
    result = calculate_payroll_multiplier(
        calendar_days=30,
        approved_leave_minutes=0,
        comp_credit_minutes_available=0,
        standard_day_minutes=480,
        absent_days=1,
    )
    assert result.absent_minutes == 480
    assert result.absence_comp_credit_minutes_applied == 0
    assert result.effective_absent_minutes == 480
    assert result.total_deduction_minutes == 480
    assert result.percentage_display == "96.67%"


def test_approved_comp_credit_can_cancel_absence_after_covering_leave():
    result = calculate_payroll_multiplier(
        calendar_days=30,
        approved_leave_minutes=480,
        comp_credit_minutes_available=960,
        standard_day_minutes=480,
        absent_days=1,
    )
    assert result.comp_credit_minutes_applied == 960
    assert result.effective_unpaid_leave_minutes == 0
    assert result.absence_comp_credit_minutes_applied == 480
    assert result.effective_absent_minutes == 0
    assert result.total_deduction_minutes == 0
    assert result.percentage_display == "100.00%"


def test_partial_remaining_comp_credit_partially_covers_absence():
    result = calculate_payroll_multiplier(
        calendar_days=31,
        approved_leave_minutes=480,
        comp_credit_minutes_available=720,
        standard_day_minutes=480,
        absent_days=1,
    )
    assert result.effective_unpaid_leave_minutes == 0
    assert result.absence_comp_credit_minutes_applied == 240
    assert result.effective_absent_minutes == 240
    assert result.total_deduction_minutes == 240
    expected = (31 * 480 - 240) / (31 * 480)
    assert abs(result.payroll_multiplier - expected) < 1e-12


def test_no_absence_preserves_existing_leave_calculation():
    result = calculate_payroll_multiplier(
        calendar_days=30,
        approved_leave_minutes=480,
        comp_credit_minutes_available=240,
        standard_day_minutes=480,
    )
    assert result.absent_minutes == 0
    assert result.effective_absent_minutes == 0
    assert result.effective_unpaid_leave_minutes == 240
    assert result.total_deduction_minutes == 240
