from datetime import date
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import DailyTask, Freelancer, PortalProject
from app.performance_reporting import build_project_reports

ROOT = Path(__file__).resolve().parents[1]


def _db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return engine, Session(engine)


def test_release_version_and_additive_bank_fields():
    config = (ROOT / "app" / "config.py").read_text(encoding="utf-8")
    identity = (ROOT / "app" / "models" / "identity.py").read_text(encoding="utf-8")
    migration = (ROOT / "alembic" / "versions" / "20260819_0018_freelancer_bank_details.py").read_text(encoding="utf-8")
    assert 'APP_VERSION = "v3.0.24.0-release21.24.0-finance-reporting-bank-details"' in config
    for field in ("bank_account_name", "bank_account_number", "bank_name", "bank_swift_code", "bank_branch_address"):
        assert field in identity
        assert field in migration
    assert 'down_revision = "20260806_0017"' in migration
    assert "UPDATE freelancers" not in migration
    assert "DELETE" not in migration.upper()


def test_project_report_groups_month_project_and_member_time():
    engine, db = _db()
    try:
        a = Freelancer(freelancer_code="F-001", full_name="Member One", timezone_name="Asia/Manila")
        b = Freelancer(freelancer_code="F-002", full_name="Member Two", timezone_name="Asia/Manila")
        project = PortalProject(project_code="P-100", name="Project Alpha", status="ACTIVE", priority="NORMAL", progress=25)
        db.add_all([a, b, project])
        db.flush()
        db.add_all([
            DailyTask(freelancer_id=a.id, task_date=date(2026, 8, 3), project_code="P-100", project_name="Project Alpha", task_description="Model", minutes_spent=120),
            DailyTask(freelancer_id=b.id, task_date=date(2026, 8, 4), project_code="P-100", project_name="Project Alpha", task_description="Coordinate", minutes_spent=90),
            DailyTask(freelancer_id=a.id, task_date=date(2026, 7, 30), project_code="P-100", project_name="Project Alpha", task_description="Earlier", minutes_spent=60),
        ])
        db.commit()
        report = build_project_reports(db, period="month", month_key="2026-08")
        rows = report["monthly_project_time_rows"]
        assert len(rows) == 1
        row = rows[0]
        assert row["month"] == "2026-08"
        assert row["project_name"] == "Project Alpha"
        assert row["total_minutes"] == 210
        assert {member["name"]: member["minutes"] for member in row["members"]} == {
            "Member One": 120,
            "Member Two": 90,
        }
    finally:
        db.close()
        engine.dispose()


def test_leave_approval_reason_is_optional_but_rejection_remains_guarded():
    route = (ROOT / "app" / "routers" / "leave.py").read_text(encoding="utf-8")
    workflow = (ROOT / "app" / "hr_workflow.py").read_text(encoding="utf-8")
    template = (ROOT / "templates" / "admin_leave_requests.html").read_text(encoding="utf-8")
    assert 'reason: str = Form("")' in route
    approve_block = workflow[workflow.index("def approve_leave_request"):workflow.index("def reject_leave_request")]
    reject_block = workflow[workflow.index("def reject_leave_request"):]
    assert "A review reason of at least 5 characters is required." not in approve_block
    assert "A rejection reason of at least 5 characters is required." in reject_block
    assert "Decision reason (optional for approval)" in template
    assert "Optional when approving; required when rejecting." in template


def test_bank_details_are_exposed_only_in_authorized_finance_views():
    accounts = (ROOT / "templates" / "admin_freelancers.html").read_text(encoding="utf-8")
    bank_form = (ROOT / "templates" / "admin_freelancer_bank_details.html").read_text(encoding="utf-8")
    bank_summary = (ROOT / "templates" / "_freelancer_bank_summary.html").read_text(encoding="utf-8")
    finance = (ROOT / "templates" / "admin_finance_center.html").read_text(encoding="utf-8")
    administration = (ROOT / "app" / "routers" / "administration.py").read_text(encoding="utf-8")
    assert "Bank Details" in accounts and "Edit Bank Details" in accounts
    for label in ("Account Name", "Account Number", "Bank Name", "SWIFT Code", "Bank Branch Address"):
        assert label in bank_form
    assert "current_staff_role in ['ADMIN', 'FINANCE']" in bank_summary
    assert "current_staff_role in ['ADMIN', 'FINANCE']" in finance
    assert "UPDATE_FREELANCER_BANK_DETAILS" in administration
    assert "Sensitive values omitted from audit details." in administration


def test_dtr_summary_contains_actual_leave_and_overtime_history():
    standard = (ROOT / "templates" / "admin_dtr_detail.html").read_text(encoding="utf-8")
    hourly = (ROOT / "templates" / "admin_dtr_task_hourly.html").read_text(encoding="utf-8")
    partial = (ROOT / "templates" / "_dtr_actual_leave_overtime_history.html").read_text(encoding="utf-8")
    attendance = (ROOT / "app" / "routers" / "attendance.py").read_text(encoding="utf-8")
    assert '_freelancer_bank_summary.html' in standard
    assert '_freelancer_bank_summary.html' in hourly
    assert '_dtr_actual_leave_overtime_history.html' in standard
    assert '_dtr_actual_leave_overtime_history.html' in hourly
    assert "ACTUAL LEAVE HISTORY" in partial
    assert "ACTUAL OVERTIME HISTORY" in partial
    assert "current_staff_role in ['ADMIN', 'FINANCE']" in partial
    assert "actual_leave_history" in attendance
    assert "actual_overtime_history" in attendance


def test_excel_export_contains_monthly_project_member_time_sheet():
    source = (ROOT / "app" / "excel_exports.py").read_text(encoding="utf-8")
    assert 'wb.create_sheet("Monthly Project Time")' in source
    assert 'headers=["Month", "Project", "Project Code", "Project Total", "Member", "Member Code", "Member Time"]' in source
