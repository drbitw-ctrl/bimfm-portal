from pathlib import Path


def test_dtr_generation_reconciles_one_idempotent_absence_credit_transaction():
    text = Path("app/dtr_service.py").read_text(encoding="utf-8")
    assert 'AUTO_ABSENCE_COMP:{freelancer.id}:{month_key}' in text
    assert 'transaction_type="USED_ABSENCE"' in text
    assert 'desired_absence_comp = min(max(0, base_month_end_balance), absence_minutes_required)' in text
    assert 'database.delete(existing_auto_absence)' in text


def test_finance_uses_total_dtr_comp_usage_not_leave_only():
    text = Path("app/finance_service.py").read_text(encoding="utf-8")
    assert 'total_comp_applied_minutes' in text
    assert 'int(dtr.comp_leave_used_minutes or 0)' in text
    assert 'payroll.effective_absent_days' in text
