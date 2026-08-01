"""Overtime persistence adapter."""
from __future__ import annotations

from app.models import Freelancer, OvertimeClaim
from app.repositories.base import SQLAlchemyRepository


class OvertimeRepository(SQLAlchemyRepository[OvertimeClaim]):
    def get_claim(self, claim_id: int) -> OvertimeClaim | None:
        return self.get(OvertimeClaim, claim_id)

    def add_claim(self, claim: OvertimeClaim) -> OvertimeClaim:
        return self.add(claim)

    def get_freelancer(self, freelancer_id: int) -> Freelancer | None:
        return self.get(Freelancer, freelancer_id)
