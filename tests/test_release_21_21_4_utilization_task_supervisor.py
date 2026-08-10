from datetime import date, datetime, timezone
import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.database import Base
from app.models import Freelancer, HRAdminAccount, PortalProject, PortalTask, ProjectMember, WorkSchedule
from app.portal_project_service import ensure_hr_project_members
from app.task_time_reporting import build_task_time_utilization


class Release2114Tests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.db.add(WorkSchedule(name="Weekdays", is_active=True))
        self.project = PortalProject(project_code="P-1", name="Project One")
        self.db.add(self.project)
        self.db.flush()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_completed_early_without_actual_hours_is_below_100_percent(self):
        task = PortalTask(
            project_id=self.project.id,
            title="Early task",
            status="COMPLETED",
            start_date=date(2026, 8, 3),
            due_date=date(2026, 8, 14),
            completed_at=datetime(2026, 8, 5, 9, 0, tzinfo=timezone.utc),
        )
        self.db.add(task)
        self.db.commit()

        report = build_task_time_utilization(self.db)
        row = report["projects"][0]["rows"][0]
        self.assertEqual(row["target_minutes"], 10 * 480)
        self.assertEqual(row["utilization_minutes"], 3 * 480)
        self.assertEqual(row["utilization"], 30.0)
        self.assertTrue(row["uses_completion_fallback"])

    def test_completed_late_without_actual_hours_can_exceed_100_percent(self):
        task = PortalTask(
            project_id=self.project.id,
            title="Late task",
            status="COMPLETED",
            start_date=date(2026, 8, 3),
            due_date=date(2026, 8, 5),
            completed_at=datetime(2026, 8, 7, 9, 0, tzinfo=timezone.utc),
        )
        self.db.add(task)
        self.db.commit()

        report = build_task_time_utilization(self.db)
        row = report["projects"][0]["rows"][0]
        self.assertEqual(row["target_minutes"], 3 * 480)
        self.assertEqual(row["utilization_minutes"], 5 * 480)
        self.assertEqual(row["utilization"], 166.7)

    def test_staff_account_can_map_to_assignable_task_member(self):
        freelancer = Freelancer(
            freelancer_code="TS-001",
            full_name="Don",
            is_active=True,
        )
        self.db.add(freelancer)
        self.db.flush()
        admin = HRAdminAccount(
            username="don",
            display_name="Don",
            role="ADMIN",
            password_hash="test",
            is_active=True,
            task_freelancer_id=freelancer.id,
        )
        self.db.add(admin)
        self.db.flush()
        changed = ensure_hr_project_members(
            self.db,
            admin_id=admin.id,
            freelancer_ids={freelancer.id},
        )
        self.db.commit()

        member = self.db.scalar(
            select(ProjectMember).where(ProjectMember.freelancer_id == freelancer.id)
        )
        self.assertEqual(changed, 1)
        self.assertIsNotNone(member)
        self.assertEqual(member.member_name, "Don")
        self.assertEqual(admin.task_freelancer_id, freelancer.id)


if __name__ == "__main__":
    unittest.main()
