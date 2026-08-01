"""Persistence adapters for BIMFM Portal domain services."""

from app.repositories.leave_repository import LeaveRepository
from app.repositories.overtime_repository import OvertimeRepository

__all__ = ["LeaveRepository", "OvertimeRepository"]
