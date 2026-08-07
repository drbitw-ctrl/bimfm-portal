from datetime import datetime, timezone
from pathlib import Path
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Freelancer, TaskWorkSession
from app.task_hourly_mode import is_task_hourly_member, task_hourly_month_ledger

ROOT = Path(__file__).resolve().parents[1]


class TaskHourlyMemberTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)

    def tearDown(self):
        self.engine.dispose()

    def test_belinda_is_task_hourly_by_stable_code(self):
        member = Freelancer(
            freelancer_code="LEGACY-00008",
            full_name="Belinda",
            timezone_name="Asia/Manila",
        )
        self.assertTrue(is_task_hourly_member(member))

    def test_other_member_is_not_task_hourly(self):
        member = Freelancer(
            freelancer_code="LEGACY-00003",
            full_name="Carlo",
            timezone_name="Asia/Manila",
        )
        self.assertFalse(is_task_hourly_member(member))

    def test_ledger_preserves_exact_seconds_and_splits_midnight(self):
        with Session(self.engine) as db:
            member = Freelancer(
                freelancer_code="LEGACY-00008",
                full_name="Belinda",
                timezone_name="Asia/Manila",
            )
            db.add(member)
            db.flush()
            # Manila: Aug 5 23:30:15 -> Aug 6 01:15:45 = 1:45:30 total.
            db.add(TaskWorkSession(
                freelancer_id=member.id,
                project_code="P-001",
                project_name="Sample Project",
                task_title="Model Update",
                discipline="AR",
                status="STOPPED",
                started_at=datetime(2026, 8, 5, 15, 30, 15, tzinfo=timezone.utc),
                stopped_at=datetime(2026, 8, 5, 17, 15, 45, tzinfo=timezone.utc),
                duration_minutes=106,
                notes="Updated architectural model",
            ))
            db.commit()
            ledger = task_hourly_month_ledger(db, freelancer=member, month_key="2026-08")
            self.assertEqual(ledger["worked_day_count"], 2)
            self.assertEqual(len(ledger["rows"]), 2)
            self.assertEqual(ledger["total"]["seconds_total"], 6330)
            self.assertEqual(ledger["total"]["label"], "01:45:30")
            self.assertEqual(ledger["rows"][0]["label"], "00:29:45")
            self.assertEqual(ledger["rows"][1]["label"], "01:15:45")

    def test_attendance_buttons_are_green_and_red(self):
        css = (ROOT / "static" / "css" / "ui-refresh.css").read_text(encoding="utf-8")
        self.assertIn(".attendance-action.time-in", css)
        self.assertIn("#15803d", css)
        self.assertIn(".attendance-action.time-out", css)
        self.assertIn("#b42318", css)

    def test_no_database_migration_added(self):
        versions = list((ROOT / "alembic" / "versions").glob("*.py"))
        self.assertFalse(any("21_22" in item.name or "task_hourly" in item.name for item in versions))


if __name__ == "__main__":
    unittest.main()
