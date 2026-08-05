from datetime import date, datetime, timezone
from pathlib import Path
import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.hr_workflow import approve_overtime_claim, adjust_approved_overtime_claim, comp_balance
from app.models import CompLeaveTransaction, Freelancer, HRAdminAccount, HRPolicy, OvertimeClaim

ROOT = Path(__file__).resolve().parents[1]


class OvertimeCreditAdjustmentTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def tearDown(self):
        self.engine.dispose()

    def _seed(self, status="PENDING_FINAL"):
        db = self.Session()
        admin = HRAdminAccount(username="admin", display_name="Admin", role="ADMIN", password_hash="x")
        freelancer = Freelancer(freelancer_code="PH-003", full_name="Carlo Ninoy Nilo")
        policy = HRPolicy(
            name="Test",
            overtime_minimum_minutes=30,
            overtime_rounding_minutes=15,
            max_approved_overtime_per_day=720,
            overtime_to_comp_numerator=1,
            overtime_to_comp_denominator=1,
            is_active=True,
        )
        db.add_all([admin, freelancer, policy])
        db.flush()
        claim = OvertimeClaim(
            freelancer_id=freelancer.id,
            attendance_date=date(2026, 8, 4),
            planned_start_utc=datetime(2026, 8, 4, 10, 0, tzinfo=timezone.utc),
            planned_end_utc=datetime(2026, 8, 4, 15, 0, tzinfo=timezone.utc),
            actual_time_out_utc=datetime(2026, 8, 4, 18, 30, tzinfo=timezone.utc),
            approved_time_out_utc=datetime(2026, 8, 4, 18, 30, tzinfo=timezone.utc),
            requested_minutes=300,
            potential_minutes_snapshot=510,
            work_description="Urgent API work",
            status=status,
        )
        db.add(claim)
        db.flush()
        return db, admin, freelancer, claim

    def test_final_approval_can_exceed_original_plan_when_verified(self):
        db, admin, freelancer, claim = self._seed()
        approve_overtime_claim(
            db,
            claim=claim,
            approved_minutes=510,
            admin_id=admin.id,
            reason="Verified work continued until 02:30.",
        )
        db.commit()
        self.assertEqual(claim.approved_minutes, 510)
        self.assertEqual(claim.comp_leave_minutes_earned, 510)
        self.assertEqual(comp_balance(db, freelancer.id), 510)
        db.close()

    def test_adjust_existing_300_credit_to_510_without_duplicate_transaction(self):
        db, admin, freelancer, claim = self._seed()
        approve_overtime_claim(
            db,
            claim=claim,
            approved_minutes=300,
            admin_id=admin.id,
            reason="Initial approval used planned duration.",
        )
        db.commit()
        adjust_approved_overtime_claim(
            db,
            claim=claim,
            approved_minutes=510,
            admin_id=admin.id,
            reason="Corrected to verified actual end at 02:30.",
        )
        db.commit()
        txs = list(db.scalars(select(CompLeaveTransaction)).all())
        self.assertEqual(len(txs), 1)
        self.assertEqual(txs[0].amount_minutes, 510)
        self.assertEqual(claim.approved_minutes, 510)
        self.assertEqual(comp_balance(db, freelancer.id), 510)
        db.close()

    def test_credit_balance_page_and_adjustment_controls_exist(self):
        router = (ROOT / "app" / "routers" / "overtime.py").read_text(encoding="utf-8")
        template = (ROOT / "templates" / "admin_overtime.html").read_text(encoding="utf-8")
        credits = (ROOT / "templates" / "admin_overtime_credits.html").read_text(encoding="utf-8")
        self.assertIn('@router.get("/admin/overtime/credits"', router)
        self.assertIn('@router.post("/admin/overtime/{claim_id}/adjust")', router)
        self.assertIn("Adjust approved overtime", template)
        self.assertIn("Overtime Credit Balances", credits)


if __name__ == "__main__":
    unittest.main()
