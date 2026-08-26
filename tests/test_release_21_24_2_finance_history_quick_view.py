from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_release_version_and_no_new_migration():
    config = (ROOT / "app" / "config.py").read_text(encoding="utf-8")
    assert 'APP_VERSION = "v3.0.24.3.1-release21.24.3.1-dashboard-leave-availability-hotfix"' in config
    assert 'APP_VERSION_NUMBER = "3.0.24.3.1"' in config
    versions = sorted((ROOT / "alembic" / "versions").glob("*.py"))
    assert any(path.name == "20260819_0018_freelancer_bank_details.py" for path in versions)
    assert not any("0019" in path.name for path in versions)


def test_dtr_finance_history_is_all_time_and_has_credit_summary():
    attendance = (ROOT / "app" / "routers" / "attendance.py").read_text(encoding="utf-8")
    partial = (ROOT / "templates" / "_dtr_actual_leave_overtime_history.html").read_text(encoding="utf-8")
    quick = (ROOT / "templates" / "_finance_history_quick_nav.html").read_text(encoding="utf-8")
    assert "LeaveRecord.freelancer_id == freelancer.id" in attendance
    assert 'LeaveRecord.status == "APPROVED"' in attendance
    assert "LeaveRecord.leave_date >= range_start" not in attendance
    assert "OvertimeClaim.freelancer_id == freelancer.id" in attendance
    assert "OvertimeClaim.attendance_date >= range_start" not in attendance
    assert "CompLeaveTransaction.freelancer_id == freelancer.id" in attendance
    assert "current_comp_credit_label" in attendance
    assert 'id="overtime-credit-balance"' in partial
    assert 'id="leave-history"' in partial
    assert 'id="overtime-history"' in partial
    assert "comp_credit_transactions" in partial
    assert '#overtime-history' in quick
    assert '#overtime-credit-balance' in quick
    assert '#leave-history' in quick


def test_finance_center_uses_grouped_columns_and_quick_history_actions():
    finance = (ROOT / "templates" / "admin_finance_center.html").read_text(encoding="utf-8")
    route = (ROOT / "app" / "routers" / "finance.py").read_text(encoding="utf-8")
    for heading in ["Work", "Leave / Absence", "OT Credit", "Salary", "Quick View"]:
        assert f"t('{heading}')" in finance
    assert "row.current_credit_label" in finance
    assert '#overtime-history' in finance
    assert '#overtime-credit-balance' in finance
    assert '#leave-history' in finance
    assert 'row["current_credit_label"]' in route
    assert "comp_balance(database, dtr.freelancer_id)" in route


def test_bilingual_labels_exist():
    en = (ROOT / "app" / "locales" / "en.json").read_text(encoding="utf-8")
    zh = (ROOT / "app" / "locales" / "zh_TW.json").read_text(encoding="utf-8")
    for key in ["All-Time Finance History", "OT History", "OT Credit Balance", "Leave History", "Quick View"]:
        assert f'"{key}"' in en
        assert f'"{key}"' in zh
    assert "歷史財務紀錄" in zh
    assert "加班補休餘額" in zh
    assert "請假歷史" in zh
