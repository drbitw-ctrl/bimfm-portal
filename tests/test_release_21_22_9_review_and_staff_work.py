from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app import models  # noqa: F401
from app.models import HRAdminAccount, PortalProject, PortalTask, PortalTaskAssignment
from app.review_work_service import assign_review, ensure_reviewer_freelancer, start_review, stop_review
from app.portal_project_service import current_freelancer_portal_tasks
from app.work_order_service import active_work_session, start_work_session, stop_work_session


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine, Session(engine)


def _seed_staff_task(db: Session):
    admin = HRAdminAccount(username="don", display_name="Don", role="ADMIN", password_hash="x", is_active=True)
    project = PortalProject(project_code="P-1", name="Project One", status="ACTIVE")
    db.add_all([admin, project]); db.flush()
    member = ensure_reviewer_freelancer(db, admin)
    task = PortalTask(project_id=project.id, title="Admin assigned coordination", description="Coordinate and check model", status="IN_PROGRESS", priority="NORMAL", progress=20, start_date=date(2026,8,1), due_date=date(2026,8,20))
    db.add(task); db.flush()
    db.add(PortalTaskAssignment(task_id=task.id, freelancer_id=member.id, assignment_role="ASSIGNEE")); db.flush()
    return admin, member, project, task


def test_staff_assigned_task_can_start_and_stop_normal_work_order():
    engine, db = _session()
    try:
        admin, member, project, task = _seed_staff_task(db)
        assigned = current_freelancer_portal_tasks(db, freelancer_id=member.id)
        assert [row.id for row in assigned] == [task.id]
        session = start_work_session(db, freelancer=member, task_id=task.id)
        assert active_work_session(db, member.id).id == session.id
        # make elapsed time long enough to produce a normal minute result
        session.started_at = session.started_at - timedelta(minutes=17)
        stopped, daily = stop_work_session(db, freelancer=member, notes="Reviewed assigned coordination model and comments")
        assert stopped.status == "STOPPED"
        assert stopped.duration_minutes >= 17
        assert daily.portal_task_id == task.id
        assert daily.freelancer_id == member.id
        assert task.status == "IN_PROGRESS"
        assert task.progress == 20
    finally:
        db.close(); engine.dispose()


def test_review_timer_remains_separate_from_staff_assigned_task_timer():
    engine, db = _session()
    try:
        admin, member, project, task = _seed_staff_task(db)
        review_task = PortalTask(project_id=project.id, title="Freelancer model review", status="FOR_REVIEW", priority="NORMAL", progress=100, start_date=date(2026,8,1), due_date=date(2026,8,20))
        db.add(review_task); db.flush()
        assign_review(db, task=review_task, reviewer=admin, actor=admin)
        review_session = start_review(db, admin=admin, task=review_task)
        assert review_session.portal_task_id == review_task.id
        assert str(review_session.notes).startswith("[[REVIEW_ACTIVE]]")
        try:
            start_work_session(db, freelancer=member, task_id=task.id)
            raise AssertionError("ordinary staff Work Order should be blocked while review timer is active")
        except ValueError:
            pass
        stop_review(db, admin=admin, notes="Checked model before project engineer submission")
        normal = start_work_session(db, freelancer=member, task_id=task.id)
        assert normal.portal_task_id == task.id
        assert not str(normal.notes or "").startswith("[[REVIEW_ACTIVE]]")
    finally:
        db.close(); engine.dispose()


def test_review_queue_template_no_longer_calls_missing_datetime_helper():
    text = Path("templates/admin_review_queue.html").read_text(encoding="utf-8")
    assert "format_local_datetime" not in text
    assert "active_review.started_at.strftime" in text


def test_dashboard_wraps_cards_without_manual_horizontal_scroll():
    css = Path("static/css/ui-refresh.css").read_text(encoding="utf-8")
    assert "grid-template-columns:repeat(4,minmax(0,1fr))" in css
    assert "grid-template-columns:repeat(3,minmax(0,1fr))" in css
    assert "grid-template-columns:repeat(2,minmax(0,1fr))" in css
    release_css = css.split("Release 21.22.8", 1)[-1]
    assert "overflow-x:auto" not in release_css


def test_admin_my_work_has_assigned_and_review_timer_controls():
    text = Path("templates/staff_my_work.html").read_text(encoding="utf-8")
    route = Path("app/routers/portal.py").read_text(encoding="utf-8")
    assert "My Assigned Tasks" in text
    assert "/portal/my-work/assigned/{{ row.id }}/start" in text
    assert "/portal/my-work/assigned/stop" in text
    assert "/admin/review-queue/{{ row.task_id }}/start" in text
    assert "return_to" in text
    assert "staff_assigned_work_start" in route
    assert "staff_assigned_work_stop" in route
