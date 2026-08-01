"""Leave persistence adapter."""
from __future__ import annotations

from app.models import LeaveRequest
from app.repositories.base import SQLAlchemyRepository


class LeaveRepository(SQLAlchemyRepository[LeaveRequest]):
    def get_request(self, request_id: int) -> LeaveRequest | None:
        return self.get(LeaveRequest, request_id)

    def add_request(self, request: LeaveRequest) -> LeaveRequest:
        return self.add(request)
