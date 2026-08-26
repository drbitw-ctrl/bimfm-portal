import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_release_version_and_no_new_database_revision():
    config = (ROOT / "app" / "config.py").read_text(encoding="utf-8")
    assert 'APP_VERSION = "v3.0.24.3.1-release21.24.3.1-dashboard-leave-availability-hotfix"' in config
    assert 'APP_VERSION_NUMBER = "3.0.24.3.1"' in config
    versions = sorted((ROOT / "alembic" / "versions").glob("*.py"))
    assert any(path.name == "20260819_0018_freelancer_bank_details.py" for path in versions)
    assert not any("0019" in path.name for path in versions)


def test_overtime_claims_support_all_time_history_and_credit_ledger():
    route = (ROOT / "app" / "routers" / "overtime.py").read_text(encoding="utf-8")
    template = (ROOT / "templates" / "admin_overtime.html").read_text(encoding="utf-8")
    credits = (ROOT / "templates" / "admin_overtime_credits.html").read_text(encoding="utf-8")
    assert 'period: str = "month"' in route
    assert 'selected_period = "all"' in route
    assert 'if selected_period == "month"' in route
    assert 'period=all&status=ALL' in template
    assert "All-Time OT History" in template
    assert "OT Credit Ledger" in template
    assert 'name="period"' in template
    assert "View Full OT Credit Ledger" in credits
    assert "Balance After" in credits
    assert '"ledger_rows": ledger_rows' in route


def test_operations_overviews_and_completed_periods_are_present():
    route = (ROOT / "app" / "routers" / "portal.py").read_text(encoding="utf-8")
    template = (ROOT / "templates" / "portal_module.html").read_text(encoding="utf-8")
    js = (ROOT / "static" / "js" / "ui.js").read_text(encoding="utf-8")
    for period in ["week", "2w", "month", "6m", "12m", "all"]:
        assert f'"value": "{period}"' in route
    for title in ["Completed Task Overview", "Task Register Overview", "Active Task Overview", "Team Availability Overview"]:
        assert title in route
    assert "operations-overview-panel" in template
    assert "data-overview-filter-key" in template
    assert 'id="task-register-filters"' in template
    assert "data-filter-key=\"availability\"" in template
    assert "data-filter-key=\"risk\"" in template
    assert "data-overview-filter-key" in js


def test_task_completed_row_visual_fix_and_bilingual_labels():
    css = (ROOT / "static" / "css" / "ui-refresh.css").read_text(encoding="utf-8")
    assert "Completed tasks keep one continuous green row" in css
    assert ".task-register-table tbody tr.task-row-completed > td:first-child" in css
    assert ".task-register-table tbody tr.task-row-completed .task-quick-control" in css
    en = json.loads((ROOT / "app" / "locales" / "en.json").read_text(encoding="utf-8"))
    zh = json.loads((ROOT / "app" / "locales" / "zh_TW.json").read_text(encoding="utf-8"))
    for key in [
        "All-Time OT History",
        "OT Credit Ledger",
        "Completed Task Overview",
        "Active Task Overview",
        "Team Availability Overview",
        "Last 12 Months",
    ]:
        assert key in en
        assert key in zh
    assert zh["All-Time OT History"] == "全部期間加班歷史"
    assert zh["Team Availability Overview"] == "團隊可用狀態概覽"
