from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_hotfix_version_marker():
    config = (ROOT / "app" / "config.py").read_text(encoding="utf-8")
    assert 'APP_VERSION = "v3.0.24.2-release21.24.2-finance-history-quick-view"' in config
    assert 'APP_VERSION_NUMBER = "3.0.24.2"' in config


def test_dtr_route_passes_local_datetime_formatter_to_template_context():
    source = (ROOT / "app" / "routers" / "attendance.py").read_text(encoding="utf-8")
    partial = (ROOT / "templates" / "_dtr_actual_leave_overtime_history.html").read_text(encoding="utf-8")
    assert "format_local_datetime=format_local_datetime" in source
    assert "format_local_datetime(item.actual_time_out_utc or item.claimed_time_out_utc" in partial


def test_hotfix_has_no_new_database_revision():
    versions = sorted((ROOT / "alembic" / "versions").glob("*.py"))
    names = [p.name for p in versions]
    assert "20260819_0018_freelancer_bank_details.py" in names
    assert not any("0019" in name for name in names)
