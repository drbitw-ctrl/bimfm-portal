from datetime import date
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.database import Base
from app import models  # noqa: F401
from app.models import DailyTask, Freelancer, HRAdminAccount, PortalProject, PortalTask, PortalTaskAssignment
from app.review_work_service import (
    assign_review,
    queue_rows,
    reviewer_choices,
    start_review,
    stop_review,
)


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine, Session(engine)


def test_review_timer_is_separate_and_auto_creates_staff_timer_identity():
    engine, db = _session()
    try:
        admin = HRAdminAccount(
            username="don",
            display_name="Don",
            role="ADMIN",
            password_hash="x",
            is_active=True,
        )
        worker = Freelancer(freelancer_code="PH-001", full_name="Worker", is_active=True)
        project = PortalProject(project_code="P-1", name="Project One", status="ACTIVE")
        db.add_all([admin, worker, project])
        db.flush()
        task = PortalTask(
            project_id=project.id,
            title="Model review task",
            status="FOR_REVIEW",
            priority="NORMAL",
            progress=100,
            start_date=date(2026, 8, 1),
            due_date=date(2026, 8, 12),
        )
        db.add(task)
        db.flush()
        db.add(PortalTaskAssignment(task_id=task.id, freelancer_id=worker.id, assignment_role="ASSIGNEE"))
        db.flush()

        assign_review(db, task=task, reviewer=admin, actor=admin)
        original_assignment = db.scalar(select(PortalTaskAssignment).where(PortalTaskAssignment.task_id == task.id))
        session = start_review(db, admin=admin, task=task)
        db.flush()

        assert session.freelancer_id != worker.id
        staff_member = db.get(Freelancer, session.freelancer_id)
        assert staff_member.freelancer_code == f"TS-{admin.id:03d}"
        assert task.status == "FOR_REVIEW"
        assert task.progress == 100
        assert original_assignment.freelancer_id == worker.id
        assert db.query(DailyTask).count() == 0

        stopped = stop_review(db, admin=admin, notes="Reviewed model coordination and comments")
        assert stopped.status == "STOPPED"
        assert stopped.duration_minutes >= 1
        assert db.query(DailyTask).count() == 0
        rows = queue_rows(db, admin=admin)
        assert len(rows) == 1
        assert rows[0]["reviewer_name"] == "Don"
        assert rows[0]["review_status"] == "REVIEWED"
    finally:
        db.close()
        engine.dispose()


def test_duplicate_visible_admin_names_are_collapsed_in_reviewer_picker():
    engine, db = _session()
    try:
        current = HRAdminAccount(username="don.current", display_name="Don", role="ADMIN", password_hash="x", is_active=True)
        duplicate = HRAdminAccount(username="don.old", display_name="Don", role="ADMIN", password_hash="x", is_active=True)
        supervisor = HRAdminAccount(username="supervisor", display_name="Supervisor", role="SUPERVISOR", password_hash="x", is_active=True)
        db.add_all([duplicate, current, supervisor])
        db.flush()
        choices = reviewer_choices(db, current_admin=current)
        don_rows = [row for row in choices if row.display_name == "Don" and row.role == "ADMIN"]
        assert len(don_rows) == 1
        assert don_rows[0].id == current.id
        assert any(row.role == "SUPERVISOR" for row in choices)
    finally:
        db.close()
        engine.dispose()


def test_dashboard_keeps_full_member_cards_in_horizontal_lanes():
    text = Path("templates/admin_dashboard.html").read_text(encoding="utf-8")
    css = Path("static/css/ui-refresh.css").read_text(encoding="utf-8")
    assert "availability-board-horizontal-details" in text
    assert "availability_cards(assigned_member_rows" in text
    assert "row.current_tasks" in text
    assert "grid-auto-flow:column" in css


def test_my_work_includes_review_queue_and_statuses():
    text = Path("templates/staff_my_work.html").read_text(encoding="utf-8")
    route = Path("app/routers/portal.py").read_text(encoding="utf-8")
    assert "My Review Work" in text
    assert "row.review_status" in text
    assert "my_review_rows = queue_rows" in route


def test_staff_timer_identities_are_excluded_from_dtr_generation():
    route = Path("app/routers/attendance.py").read_text(encoding="utf-8")
    page = Path("templates/admin_dtr_dashboard.html").read_text(encoding="utf-8")
    sidebar = Path("templates/base.html").read_text(encoding="utf-8")
    assert route.count('startswith("TS-")') >= 3
    assert "Daily Time Record (DTR) · Monthly Generation" in page
    assert "Daily Task Reports (Work Activities)" in sidebar
    assert "Daily Time Record (DTR)" in sidebar


def test_review_queue_routes_have_non_500_failure_handling():
    route = Path("app/routers/administration.py").read_text(encoding="utf-8")
    template = Path("templates/admin_review_queue.html").read_text(encoding="utf-8")
    assert "review_timer_start_failed" in route
    assert "review_queue_load_failed" in route
    assert "current_admin_id" in template
    assert "admin.id" not in template
