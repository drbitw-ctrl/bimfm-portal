import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_release_version_and_database_boundary_remains_0018():
    config = (ROOT / "app" / "config.py").read_text(encoding="utf-8")
    assert 'APP_VERSION = "v3.0.24.3.1-release21.24.3.1-dashboard-leave-availability-hotfix"' in config
    assert 'APP_VERSION_NUMBER = "3.0.24.3.1"' in config
    versions = sorted((ROOT / "alembic" / "versions").glob("*.py"))
    assert any(path.name == "20260819_0018_freelancer_bank_details.py" for path in versions)
    assert not any("0019" in path.name for path in versions)


def test_dashboard_uses_approved_leave_for_current_local_date():
    route = (ROOT / "app" / "routers" / "administration.py").read_text(encoding="utf-8")
    assert 'select(LeaveRecord).where(' in route
    assert 'LeaveRecord.status == "APPROVED"' in route
    assert 'LeaveRecord.leave_date.in_(leave_dates)' in route
    assert 'leave.leave_date == current_date_by_member.get(freelancer_id)' in route
    assert 'else "on_leave" if leave_today is not None' in route
    assert '"on_leave": on_leave_rows' in route


def test_dashboard_has_on_leave_lane_and_clear_status_design():
    template = (ROOT / "templates" / "admin_dashboard.html").read_text(encoding="utf-8")
    css = (ROOT / "static" / "css" / "ui-refresh.css").read_text(encoding="utf-8")
    assert "On Leave Today" in template
    assert "Approved leave today" in template
    assert "on_leave_member_rows" in template
    assert "availability-legend on-leave" in template
    assert ".availability-board-horizontal-details .leave-group" in css
    assert ".member-availability-card.state-on_leave" in css
    assert ".availability-badge.on_leave" in css
    assert ".attendance-mini.status-on-leave" in css


def test_on_leave_labels_are_bilingual():
    en = json.loads((ROOT / "app" / "locales" / "en.json").read_text(encoding="utf-8"))
    zh = json.loads((ROOT / "app" / "locales" / "zh_TW.json").read_text(encoding="utf-8"))
    for key in ["On Leave", "On Leave Today", "Approved leave today", "No members are on approved leave today."]:
        assert key in en
        assert key in zh
    assert zh["On Leave"] == "請假中"
    assert zh["On Leave Today"] == "今日請假"
