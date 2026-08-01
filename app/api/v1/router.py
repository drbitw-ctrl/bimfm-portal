"""Versioned, language-neutral JSON API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import config
from app.api.v1.dependencies import get_database, require_api_permission
from app.auth.dependencies import Principal, require_authenticated_user
from app.auth.permissions import Permission, has_permission, permissions_for_role
from app.database import database_is_available
from app.models import Freelancer, LeaveRequest, OvertimeClaim, PortalProject, PortalTask
from app.schemas.api import (
    ApiMeta, ApiResponse, FreelancerRead, HealthData, LeaveRequestRead,
    OvertimeClaimRead, PaginationMeta, PrincipalRead, ProjectRead, TaskRead,
)

router = APIRouter(prefix="/api/v1", tags=["API v1"])


def _meta(request: Request) -> ApiMeta:
    return ApiMeta(request_id=request.state.request_id)


def _pagination(request: Request, *, limit: int, offset: int, count: int, total: int) -> PaginationMeta:
    return PaginationMeta(
        request_id=request.state.request_id,
        limit=limit,
        offset=offset,
        count=count,
        total=total,
    )


def _freelancer_id(principal: Principal) -> int | None:
    return getattr(principal.account, "freelancer_id", None)


@router.get("/health", response_model=ApiResponse[HealthData], summary="API liveness and database health")
def health(request: Request):
    database_ok = database_is_available()
    return ApiResponse(
        data=HealthData(
            status="ok" if database_ok else "degraded",
            database="available" if database_ok else "unavailable",
            application=config.APP_NAME,
            version=config.APP_VERSION,
        ),
        meta=_meta(request),
    )


@router.get("/me", response_model=ApiResponse[PrincipalRead], summary="Current authenticated principal")
def me(request: Request, principal: Principal = Depends(require_authenticated_user)):
    account = principal.account
    display_name = getattr(account, "display_name", None)
    if not display_name and getattr(account, "freelancer", None):
        display_name = account.freelancer.full_name
    display_name = display_name or getattr(account, "username", "")
    return ApiResponse(
        data=PrincipalRead(
            kind=principal.kind,
            account_id=principal.id,
            role=principal.role.value,
            display_name=display_name,
            freelancer_id=_freelancer_id(principal),
            permissions=sorted(permission.value for permission in permissions_for_role(principal.role)),
        ),
        meta=_meta(request),
    )


@router.get("/freelancers", response_model=ApiResponse[list[FreelancerRead]])
def list_freelancers(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    active_only: bool = True,
    database: Session = Depends(get_database),
    principal: Principal = Depends(require_api_permission(Permission.ATTENDANCE_VIEW_ALL)),
):
    del principal
    filters = [Freelancer.is_active.is_(True)] if active_only else []
    total = int(database.scalar(select(func.count(Freelancer.id)).where(*filters)) or 0)
    records = list(database.scalars(select(Freelancer).where(*filters).order_by(Freelancer.full_name).limit(limit).offset(offset)))
    return ApiResponse(data=[FreelancerRead.model_validate(item) for item in records], meta=_pagination(request, limit=limit, offset=offset, count=len(records), total=total))


@router.get("/leave-requests", response_model=ApiResponse[list[LeaveRequestRead]])
def list_leave_requests(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: str | None = Query(None, max_length=30),
    database: Session = Depends(get_database),
    principal: Principal = Depends(require_api_permission(Permission.LEAVE_SUBMIT)),
):
    filters = []
    if status:
        filters.append(LeaveRequest.status == status.strip().upper())
    if not has_permission(principal.role, Permission.LEAVE_APPROVE):
        freelancer_id = _freelancer_id(principal)
        filters.append(LeaveRequest.freelancer_id == freelancer_id)
    total = int(database.scalar(select(func.count(LeaveRequest.id)).where(*filters)) or 0)
    records = list(database.scalars(select(LeaveRequest).where(*filters).order_by(LeaveRequest.leave_date.desc(), LeaveRequest.id.desc()).limit(limit).offset(offset)))
    return ApiResponse(data=[LeaveRequestRead.model_validate(item) for item in records], meta=_pagination(request, limit=limit, offset=offset, count=len(records), total=total))


@router.get("/overtime-claims", response_model=ApiResponse[list[OvertimeClaimRead]])
def list_overtime_claims(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: str | None = Query(None, max_length=30),
    database: Session = Depends(get_database),
    principal: Principal = Depends(require_api_permission(Permission.OVERTIME_SUBMIT)),
):
    filters = []
    if status:
        filters.append(OvertimeClaim.status == status.strip().upper())
    if not has_permission(principal.role, Permission.OVERTIME_APPROVE):
        filters.append(OvertimeClaim.freelancer_id == _freelancer_id(principal))
    total = int(database.scalar(select(func.count(OvertimeClaim.id)).where(*filters)) or 0)
    records = list(database.scalars(select(OvertimeClaim).where(*filters).order_by(OvertimeClaim.attendance_date.desc(), OvertimeClaim.id.desc()).limit(limit).offset(offset)))
    return ApiResponse(data=[OvertimeClaimRead.model_validate(item) for item in records], meta=_pagination(request, limit=limit, offset=offset, count=len(records), total=total))


@router.get("/projects", response_model=ApiResponse[list[ProjectRead]])
def list_projects(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: str | None = Query(None, max_length=40),
    database: Session = Depends(get_database),
    principal: Principal = Depends(require_api_permission(Permission.PROJECT_VIEW)),
):
    del principal
    filters = [PortalProject.status == status.strip().upper()] if status else []
    total = int(database.scalar(select(func.count(PortalProject.id)).where(*filters)) or 0)
    records = list(database.scalars(select(PortalProject).where(*filters).order_by(PortalProject.updated_at.desc()).limit(limit).offset(offset)))
    return ApiResponse(data=[ProjectRead.model_validate(item) for item in records], meta=_pagination(request, limit=limit, offset=offset, count=len(records), total=total))


@router.get("/tasks", response_model=ApiResponse[list[TaskRead]])
def list_tasks(
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    project_id: int | None = Query(None, ge=1),
    status: str | None = Query(None, max_length=40),
    database: Session = Depends(get_database),
    principal: Principal = Depends(require_api_permission(Permission.PROJECT_VIEW)),
):
    del principal
    filters = []
    if project_id is not None:
        filters.append(PortalTask.project_id == project_id)
    if status:
        filters.append(PortalTask.status == status.strip().upper())
    total = int(database.scalar(select(func.count(PortalTask.id)).where(*filters)) or 0)
    records = list(database.scalars(select(PortalTask).where(*filters).order_by(PortalTask.updated_at.desc()).limit(limit).offset(offset)))
    return ApiResponse(data=[TaskRead.model_validate(item) for item in records], meta=_pagination(request, limit=limit, offset=offset, count=len(records), total=total))


@router.get("/readiness", response_model=ApiResponse[HealthData], summary="Deployment readiness")
def readiness(request: Request):
    database_ok = database_is_available()
    app_ready = bool(getattr(request.app.state, "ready", False))
    if not (database_ok and app_ready):
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail={"code": "service_not_ready"})
    return ApiResponse(
        data=HealthData(status="ready", database="available", application=config.APP_NAME, version=config.APP_VERSION),
        meta=_meta(request),
    )
