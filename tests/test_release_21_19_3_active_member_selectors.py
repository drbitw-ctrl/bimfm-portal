from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.member_directory import get_active_freelancer, get_active_freelancers
from app.models import Freelancer, FreelancerAccount


class ActiveMemberSelectorTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "members.db"
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(self.engine)

    def tearDown(self):
        self.engine.dispose()
        self.temp_dir.cleanup()

    def _freelancer(self, session: Session, code: str, name: str, *, active=True):
        row = Freelancer(freelancer_code=code, full_name=name, is_active=active)
        session.add(row)
        session.flush()
        return row

    def test_only_active_account_linked_members_are_returned(self):
        with Session(self.engine) as session:
            mapped = self._freelancer(session, "PH-001", "Mapped Member")
            legacy = self._freelancer(session, "LEG-001", "Legacy Member")
            inactive_member = self._freelancer(session, "PH-002", "Inactive Member", active=False)
            inactive_account = self._freelancer(session, "PH-003", "Disabled Account")
            session.add_all([
                FreelancerAccount(freelancer_id=mapped.id, username="mapped", password_hash="x", is_active=True),
                FreelancerAccount(freelancer_id=inactive_member.id, username="inactive", password_hash="x", is_active=True),
                FreelancerAccount(freelancer_id=inactive_account.id, username="disabled", password_hash="x", is_active=False),
            ])
            session.commit()

            rows = get_active_freelancers(session)
            self.assertEqual([row.id for row in rows], [mapped.id])
            self.assertNotIn(legacy.id, [row.id for row in rows])

    def test_single_lookup_rejects_unmapped_or_inactive_rows(self):
        with Session(self.engine) as session:
            mapped = self._freelancer(session, "PH-011", "Active Portal Member")
            legacy = self._freelancer(session, "LEG-011", "Legacy Only")
            session.add(FreelancerAccount(freelancer_id=mapped.id, username="active11", password_hash="x", is_active=True))
            session.commit()

            self.assertEqual(get_active_freelancer(session, mapped.id).id, mapped.id)
            self.assertIsNone(get_active_freelancer(session, legacy.id))

    def test_results_are_sorted_by_name(self):
        with Session(self.engine) as session:
            zed = self._freelancer(session, "PH-021", "Zed Member")
            amy = self._freelancer(session, "PH-022", "Amy Member")
            session.add_all([
                FreelancerAccount(freelancer_id=zed.id, username="zed", password_hash="x", is_active=True),
                FreelancerAccount(freelancer_id=amy.id, username="amy", password_hash="x", is_active=True),
            ])
            session.commit()
            self.assertEqual([row.full_name for row in get_active_freelancers(session)], ["Amy Member", "Zed Member"])


if __name__ == "__main__":
    unittest.main()
