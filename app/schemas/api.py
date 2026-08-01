"""Language-neutral Pydantic contracts for API v1."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ApiMeta(BaseModel):
    request_id: str
    api_version: str = "v1"


class PaginationMeta(ApiMeta):
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    count: int = Field(ge=0)
    total: int = Field(ge=0)


class ApiResponse(BaseModel, Generic[T]):
    data: T
    meta: ApiMeta | PaginationMeta


class ApiError(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ApiErrorResponse(BaseModel):
    error: ApiError
    meta: ApiMeta


class HealthData(BaseModel):
    status: str
    database: str
    application: str
    version: str


class PrincipalRead(BaseModel):
    kind: str
    account_id: int
    role: str
    display_name: str
    freelancer_id: int | None = None
    permissions: list[str]


class FreelancerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    freelancer_code: str
    full_name: str
    email: str | None
    timezone_name: str
    is_active: bool


class LeaveRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    freelancer_id: int
    leave_date: date
    leave_type: str
    requested_minutes: int
    reason: str
    status: str
    approved_minutes: int
    submitted_at: datetime
    reviewed_by_admin_id: int | None
    reviewed_at: datetime | None
    review_reason: str | None


class OvertimeClaimRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    freelancer_id: int
    attendance_date: date
    requested_minutes: int
    approved_minutes: int
    comp_leave_minutes_earned: int
    work_description: str
    status: str
    planned_start_utc: datetime | None
    planned_end_utc: datetime | None
    actual_time_out_utc: datetime | None
    claimed_time_out_utc: datetime | None
    approved_time_out_utc: datetime | None
    submitted_at: datetime
    reviewed_at: datetime | None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_code: str
    name: str
    description: str | None
    status: str
    priority: str
    discipline: str | None
    start_date: date | None
    deadline: date | None
    completion_date: date | None
    progress: int
    supervisor_id: int | None
    updated_at: datetime


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    title: str
    description: str | None
    status: str
    priority: str
    discipline: str | None
    progress: int
    start_date: date | None
    due_date: date | None
    completed_at: datetime | None
    updated_at: datetime
