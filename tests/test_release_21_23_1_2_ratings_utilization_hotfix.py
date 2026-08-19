from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.models import (
    DailyTask,
    Freelancer,
    HRAdminAccount,
    PortalProject,
    PortalTask,
    PortalTaskAssignment,
    TaskWorkSession,
    WorkSchedule,
)
from app.performance_reporting import build_performance_dashboard
from app.task_time_reporting import build_task_time_utilization

ROOT = Path(__file__).resolve().parents[1]


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine, Session(engine)


def test_administrator_identity_is_not_in_ratings_leaderboards():
    engine, db = _session()
    try:
        project = PortalProject(project_code="P-RATE", name="Ratings Project", status="ACTIVE")
        admin_member = Freelancer(freelancer_code="TS-001", full_name="Portal Administrator", is_active=True)
        freelancer = Freelancer(freelancer_code="F-001", full_name="Production Member", is_active=True)
        db.add_all([project, admin_member, freelancer])
        db.flush()
        admin = HRAdminAccount(
            username="admin",
            display_name="Portal Administrator",
            role="ADMIN",
            password_hash="x",
            is_active=True,
            task_freelancer_id=admin_member.id,
        )
        db.add(admin)
        db.flush()
        admin_task = PortalTask(
            project_id=project.id,
            title="Admin coordination",
            status="COMPLETED",
            quality_score=100,
            start_date=date(2026, 8, 1),
            due_date=date(2026, 8, 10),
            completed_at=datetime(2026, 8, 5, tzinfo=timezone.utc),
        )
        member_task = PortalTask(
            project_id=project.id,
            title="Production model",
            status="COMPLETED",
            quality_score=90,
            start_date=date(2026, 8, 1),
            due_date=date(2026, 8, 10),
            completed_at=datetime(2026, 8, 6, tzinfo=timezone.utc),
        )
        db.add_all([admin_task, member_task])
        db.flush()
        db.add_all([
            PortalTaskAssignment(task_id=admin_task.id, freelancer_id=admin_member.id),
            PortalTaskAssignment(task_id=member_task.id, freelancer_id=freelancer.id),
        ])
        db.commit()

        report = build_performance_dashboard(db)
        for key in ("overall_ranked", "quality_ranked", "task_ranked", "speed_ranked"):
            names = [row["name"] for row in report[key]]
            assert "Portal Administrator" not in names
            assert "Production Member" in names
        assert report["overall_summary"]["total_members"] == 1
    finally:
        db.close()
        engine.dispose()


def test_project_utilization_adds_saved_review_time_to_recorded_production():
    engine, db = _session()
    try:
        db.add(WorkSchedule(name="Weekdays", is_active=True))
        project = PortalProject(project_code="P-UTIL", name="Utilization Project", status="ACTIVE")
        freelancer = Freelancer(freelancer_code="F-001", full_name="Production Member", is_active=True)
        reviewer = Freelancer(freelancer_code="TS-001", full_name="Reviewer", is_active=True)
        db.add_all([project, freelancer, reviewer])
        db.flush()
        task = PortalTask(
            project_id=project.id,
            title="Model and review",
            status="IN_PROGRESS",
            start_date=date(2026, 8, 3),
            due_date=date(2026, 8, 3),
        )
        db.add(task)
        db.flush()
        db.add(DailyTask(
            freelancer_id=freelancer.id,
            portal_task_id=task.id,
            task_date=date(2026, 8, 3),
            project_code=project.project_code,
            project_name=project.name,
            task_description=task.title,
            minutes_spent=300,
        ))
        db.add(TaskWorkSession(
            freelancer_id=reviewer.id,
            portal_task_id=task.id,
            project_id=project.id,
            project_code=project.project_code,
            project_name=project.name,
            task_title=task.title,
            status="STOPPED",
            started_at=datetime(2026, 8, 3, 10, 0, tzinfo=timezone.utc),
            stopped_at=datetime(2026, 8, 3, 11, 30, tzinfo=timezone.utc),
            duration_minutes=90,
            notes="[[REVIEW]] reviewer=1; Checked model",
        ))
        db.commit()

        report = build_task_time_utilization(db)
        row = report["projects"][0]["rows"][0]
        project_row = report["projects"][0]
        assert row["target_minutes"] == 480
        assert row["production_recorded_minutes"] == 300
        assert row["review_minutes"] == 90
        assert row["recorded_minutes"] == 390
        assert row["utilization_minutes"] == 390
        assert row["utilization"] == 81.2
        assert project_row["review_minutes"] == 90
        assert project_row["measured_actual_minutes"] == 390
        assert report["summary"]["review_minutes"] == 90
        assert report["summary"]["measured_actual_minutes"] == 390
    finally:
        db.close()
        engine.dispose()


def test_completion_fallback_still_adds_review_time():
    engine, db = _session()
    try:
        db.add(WorkSchedule(name="Weekdays", is_active=True))
        project = PortalProject(project_code="P-FALLBACK", name="Fallback Project", status="ACTIVE")
        reviewer = Freelancer(freelancer_code="TS-002", full_name="Reviewer", is_active=True)
        db.add_all([project, reviewer])
        db.flush()
        task = PortalTask(
            project_id=project.id,
            title="Historical reviewed model",
            status="COMPLETED",
            start_date=date(2026, 8, 3),
            due_date=date(2026, 8, 7),
            completed_at=datetime(2026, 8, 5, 9, 0, tzinfo=timezone.utc),
        )
        db.add(task)
        db.flush()
        db.add(TaskWorkSession(
            freelancer_id=reviewer.id,
            portal_task_id=task.id,
            project_id=project.id,
            project_code=project.project_code,
            project_name=project.name,
            task_title=task.title,
            status="STOPPED",
            started_at=datetime(2026, 8, 5, 9, 0, tzinfo=timezone.utc),
            stopped_at=datetime(2026, 8, 5, 10, 0, tzinfo=timezone.utc),
            duration_minutes=60,
            notes="[[REVIEW]] reviewer=2; Reviewed historical model",
        ))
        db.commit()

        row = build_task_time_utilization(db)["projects"][0]["rows"][0]
        assert row["uses_completion_fallback"] is True
        assert row["completion_fallback_minutes"] == 3 * 480
        assert row["review_minutes"] == 60
        assert row["utilization_minutes"] == 3 * 480 + 60
    finally:
        db.close()
        engine.dispose()


def test_release_21_23_1_2_version_ui_and_no_schema_change():
    config = (ROOT / "app" / "config.py").read_text(encoding="utf-8")
    template = (ROOT / "templates" / "task_time_utilization.html").read_text(encoding="utf-8")
    assert 'APP_VERSION = "v3.0.23.1.2-release21.23.1.2-ratings-utilization-hotfix"' in config
    assert 'APP_VERSION_NUMBER = "3.0.23.1.2"' in config
    assert "Review Time" in template
    assert "project.review_minutes" in template
    assert "row.review_minutes" in template
    migrations = ROOT / "alembic" / "versions"
    assert not any("21_23_1_2" in path.name for path in migrations.glob("*.py"))
