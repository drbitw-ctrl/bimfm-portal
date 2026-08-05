import os
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

_TEST_DB = Path(tempfile.gettempdir()) / "bimfm_21192_tests.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB.as_posix()}"
os.environ["BIMFM_ENV"] = "development"

from sqlalchemy import select
from app.database import Base, SessionLocal, engine
from app.models import DailyAttendance, Freelancer, TaskWorkSession, AttendanceCorrectionRequest
from app.overnight_exception_service import reconcile_overnight_exceptions


class Release21192Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)

    @classmethod
    def tearDownClass(cls):
        engine.dispose()
        _TEST_DB.unlink(missing_ok=True)

    def setUp(self):
        with SessionLocal() as db:
            for table in reversed(Base.metadata.sorted_tables):
                db.execute(table.delete())
            db.commit()

    def test_correction_request_model_persists(self):
        with SessionLocal() as db:
            f = Freelancer(freelancer_code="F001", full_name="Test Member", timezone_name="Asia/Manila")
            db.add(f); db.flush()
            req = AttendanceCorrectionRequest(freelancer_id=f.id, attendance_date=date(2026,8,1), reason="Forgot to record attendance", status="PENDING")
            db.add(req); db.commit()
            saved = db.scalar(select(AttendanceCorrectionRequest))
            self.assertEqual(saved.status, "PENDING")

    def test_overnight_exception_flags_at_six_am(self):
        with SessionLocal() as db:
            f = Freelancer(freelancer_code="F002", full_name="Night Worker", timezone_name="Asia/Manila")
            db.add(f); db.flush()
            attendance = DailyAttendance(freelancer_id=f.id, attendance_date=date(2026,8,1), time_in_utc=datetime(2026,8,1,13,0,tzinfo=timezone.utc), status="PRESENT")
            session = TaskWorkSession(freelancer_id=f.id, project_code="P", project_name="Project", task_title="Task", status="ACTIVE", started_at=datetime(2026,8,1,13,0,tzinfo=timezone.utc))
            db.add_all([attendance, session]); db.commit()
            changed = reconcile_overnight_exceptions(db, now=datetime(2026,8,1,22,0,tzinfo=timezone.utc))  # 06:00 Manila Aug 2
            db.commit(); db.refresh(attendance); db.refresh(session)
            self.assertGreaterEqual(changed, 2)
            self.assertTrue(attendance.missed_time_out_flag)
            self.assertTrue(attendance.missed_work_order_stop_flag)
            self.assertTrue(attendance.overtime_unavailable)
            self.assertEqual(session.status, "FLAGGED_MISSED_STOP")
            self.assertEqual(session.duration_minutes, 0)

    def test_before_six_am_remains_assumed_working(self):
        with SessionLocal() as db:
            f = Freelancer(freelancer_code="F003", full_name="Still Working", timezone_name="Asia/Manila")
            db.add(f); db.flush()
            attendance = DailyAttendance(freelancer_id=f.id, attendance_date=date(2026,8,1), time_in_utc=datetime(2026,8,1,13,0,tzinfo=timezone.utc), status="PRESENT")
            session = TaskWorkSession(freelancer_id=f.id, project_code="P", project_name="Project", task_title="Task", status="ACTIVE", started_at=datetime(2026,8,1,13,0,tzinfo=timezone.utc))
            db.add_all([attendance, session]); db.commit()
            changed = reconcile_overnight_exceptions(db, now=datetime(2026,8,1,21,59,tzinfo=timezone.utc))  # 05:59 Manila
            self.assertEqual(changed, 0)
            self.assertEqual(session.status, "ACTIVE")
            self.assertFalse(attendance.overtime_unavailable)


if __name__ == "__main__":
    unittest.main()
