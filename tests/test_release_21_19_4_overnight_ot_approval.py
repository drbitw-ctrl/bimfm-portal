import unittest
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

from app.services.overtime_service import OvertimeService, OvertimeServiceDependencies


@dataclass
class FakeFreelancer:
    id: int = 1
    timezone_name: str = "Asia/Manila"


@dataclass
class FakeClaim:
    id: int = 10
    freelancer_id: int = 1
    attendance_date: date = date(2026, 8, 4)
    planned_start_utc: datetime = datetime(2026, 8, 4, 10, 0, tzinfo=timezone.utc)  # 18:00 Manila
    status: str = "PENDING_FINAL"
    approved_time_out_utc: datetime | None = None


class FakeRepository:
    claim = FakeClaim()
    freelancer = FakeFreelancer()
    committed = False
    rolled_back = False

    def __init__(self, database):
        self.database = database

    def get_claim(self, claim_id):
        return self.claim if claim_id == self.claim.id else None

    def get_freelancer(self, freelancer_id):
        return self.freelancer

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


def local_time_to_utc(work_date, value, timezone_name):
    parsed = time.fromisoformat(value)
    local = datetime.combine(work_date, parsed, tzinfo=ZoneInfo(timezone_name))
    return local.astimezone(timezone.utc)


class OvernightOvertimeApprovalTests(unittest.TestCase):
    def setUp(self):
        FakeRepository.claim = FakeClaim()
        FakeRepository.freelancer = FakeFreelancer()
        FakeRepository.committed = False
        FakeRepository.rolled_back = False
        self.approved_minutes = None

        def approve_overtime_claim(database, *, claim, approved_minutes, admin_id, reason):
            self.approved_minutes = approved_minutes
            claim.status = "APPROVED"

        deps = OvertimeServiceDependencies(
            month_is_locked=lambda database, month: False,
            local_time_to_utc=local_time_to_utc,
            get_policy=lambda database: None,
            get_daily_attendance=lambda database, freelancer_id, work_date: None,
            invalidate_dtr=lambda database, freelancer_id, month: None,
            utc_now=lambda: datetime(2026, 8, 5, 0, 0, tzinfo=timezone.utc),
            approve_overtime_claim=approve_overtime_claim,
            reject_overtime_claim=lambda *args, **kwargs: None,
            write_audit=lambda *args, **kwargs: None,
        )
        self.service = OvertimeService(deps, repository_factory=FakeRepository)

    def test_approved_0230_is_next_day_after_1800_start(self):
        result = self.service.review(
            object(),
            claim_id=10,
            admin_id=1,
            decision="APPROVE_FINAL",
            approved_minutes="",
            approved_time_out="02:30",
            reason="Verified against work records.",
            audit_request=None,
        )

        self.assertTrue(result.ok)
        self.assertEqual(self.approved_minutes, 510)
        self.assertEqual(
            FakeRepository.claim.approved_time_out_utc,
            datetime(2026, 8, 4, 18, 30, tzinfo=timezone.utc),  # 02:30 Manila on Aug 5
        )

    def test_same_day_2300_remains_same_day(self):
        result = self.service.review(
            object(),
            claim_id=10,
            admin_id=1,
            decision="APPROVE_FINAL",
            approved_minutes="",
            approved_time_out="23:00",
            reason="Verified against work records.",
            audit_request=None,
        )

        self.assertTrue(result.ok)
        self.assertEqual(self.approved_minutes, 300)
        self.assertEqual(
            FakeRepository.claim.approved_time_out_utc,
            datetime(2026, 8, 4, 15, 0, tzinfo=timezone.utc),
        )


if __name__ == "__main__":
    unittest.main()
