import json
from pathlib import Path


def test_attendance_history_supports_recent_month_and_all_time_ranges():
    route = Path("app/routers/attendance.py").read_text(encoding="utf-8")
    assert '@router.get("/attendance/history"' in route
    assert 'period == "all"' in route
    assert 'period == "this_month"' in route
    assert 'period == "last_month"' in route
    assert 'parse_month_key(selected_month)' in route
    assert 'attendance_query = attendance_query.limit(31)' in route


def test_attendance_history_lists_only_signed_in_freelancers_dtrs():
    route = Path("app/routers/attendance.py").read_text(encoding="utf-8")
    assert 'MonthlyDTR.freelancer_id == account.freelancer_id' in route
    assert '@router.get("/attendance/dtr/{dtr_id}"' in route
    assert 'int(dtr.freelancer_id) != int(account.freelancer_id)' in route


def test_freelancer_history_page_contains_dtr_archive_and_all_time_access():
    template = Path("templates/attendance_history.html").read_text(encoding="utf-8")
    assert "Monthly DTR Archive" in template
    assert "?period=all" in template
    assert 'type="month"' in template
    assert '/attendance/dtr/{{ dtr.id }}' in template
    assert "freelancer_code" not in template


def test_freelancer_dtr_is_read_only_and_separates_daily_time_from_task_reports():
    template = Path("templates/freelancer_dtr_detail.html").read_text(encoding="utf-8")
    assert "PERSONAL DAILY TIME RECORD" in template
    assert "DAILY TASK REPORTS" in template
    assert "Task activity is shown separately from the Daily Time Record" in template
    assert '/admin/dtr/' not in template
    assert 'method="post"' not in template.lower()
    assert "freelancer_code" not in template


def test_sidebar_and_localization_expose_personal_dtr_history():
    base = Path("templates/base.html").read_text(encoding="utf-8")
    assert "Attendance History & DTR" in base
    en = json.loads(Path("app/locales/en.json").read_text(encoding="utf-8"))
    zh = json.loads(Path("app/locales/zh_TW.json").read_text(encoding="utf-8"))
    assert set(en) == set(zh)
    assert en["Attendance History & DTR"] == "Attendance History & DTR"
    assert zh["Attendance History & DTR"] == "出勤紀錄與 DTR"
