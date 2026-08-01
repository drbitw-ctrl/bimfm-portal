"""FastAPI authorization dependencies and shared access helpers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.permissions import Permission, Role, has_permission, normalize_role
from app.database import SessionLocal
from app.models import FreelancerAccount, HRAdminAccount


@dataclass(frozen=True)
class Principal:
    kind: str
    id: int
    role: Role
    account: HRAdminAccount | FreelancerAccount


def principal_from_request(request: Request, database: Session) -> Principal | None:
    admin_id = request.session.get("admin_id")
    if admin_id:
        account = database.get(HRAdminAccount, int(admin_id))
        if account and account.is_active:
            return Principal("staff", account.id, normalize_role(account.role), account)
        request.session.pop("admin_id", None)

    freelancer_id = request.session.get("freelancer_account_id")
    if freelancer_id:
        account = database.get(FreelancerAccount, int(freelancer_id))
        if account and account.is_active:
            return Principal("employee", account.id, Role.EMPLOYEE, account)
        request.session.pop("freelancer_account_id", None)
    return None


def require_permission_in_session(
    request: Request,
    database: Session,
    permission: Permission | str,
) -> Principal | None:
    principal = principal_from_request(request, database)
    if principal is None or not has_permission(principal.role, permission):
        return None
    return principal


def database_session():
    with SessionLocal() as database:
        yield database


def require_authenticated_user(
    request: Request,
    database: Session = Depends(database_session),
) -> Principal:
    principal = principal_from_request(request, database)
    if principal is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication_required")
    return principal


def require_permission(permission: Permission | str) -> Callable:
    def dependency(
        principal: Principal = Depends(require_authenticated_user),
    ) -> Principal:
        if not has_permission(principal.role, permission):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="permission_required")
        return principal
    return dependency


require_admin = require_permission(Permission.STAFF_MANAGE)
require_finance = require_permission(Permission.FINANCE_VIEW)
require_supervisor = require_permission(Permission.LEAVE_VIEW_ALL)
require_employee = require_permission(Permission.ATTENDANCE_VIEW_OWN)
