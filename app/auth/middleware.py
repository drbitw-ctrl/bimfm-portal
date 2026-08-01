"""Central policy enforcement for HTML routes.

Release 20.14 separates read permissions from write permissions so a Supervisor
can inspect the complete operational workspace without being able to change
records.
"""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.auth.dependencies import principal_from_request
from app.auth.permissions import Permission, Role, has_permission
from app.database import SessionLocal


@dataclass(frozen=True)
class RoutePolicy:
    prefix: str
    view_permission: Permission
    write_permission: Permission | None = None


ROUTE_POLICIES = (
    RoutePolicy("/portal/tasks/new", Permission.PROJECT_EDIT, Permission.PROJECT_EDIT),
    RoutePolicy("/portal", Permission.PROJECT_VIEW, Permission.PROJECT_EDIT),
    RoutePolicy("/admin/staff-accounts", Permission.STAFF_MANAGE, Permission.STAFF_MANAGE),
    RoutePolicy("/admin/settings", Permission.SETTINGS_MANAGE, Permission.SETTINGS_MANAGE),
    RoutePolicy("/admin/integration", Permission.INTEGRATION_MANAGE, Permission.INTEGRATION_MANAGE),
    RoutePolicy("/admin/finance", Permission.FINANCE_VIEW, Permission.FINANCE_EXPORT),
    RoutePolicy("/admin/leave-requests", Permission.LEAVE_VIEW_ALL, Permission.LEAVE_APPROVE),
    RoutePolicy("/admin/overtime", Permission.OVERTIME_VIEW_ALL, Permission.OVERTIME_APPROVE),
    RoutePolicy("/admin/attendance", Permission.ATTENDANCE_VIEW_ALL, Permission.ATTENDANCE_EDIT),
    RoutePolicy("/admin/dtr", Permission.ATTENDANCE_VIEW_ALL, Permission.ATTENDANCE_EDIT),
    RoutePolicy("/admin/freelancers", Permission.STAFF_MANAGE, Permission.STAFF_MANAGE),
)

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
READ_ONLY_STAFF_ROLES = {Role.SUPERVISOR, Role.FINANCE}


class AuthorizationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in {"/admin/login", "/admin/logout", "/login", "/setup", "/language"}:
            return await call_next(request)

        matched = next(
            (policy for policy in ROUTE_POLICIES if path.startswith(policy.prefix)),
            None,
        )
        staff_write = (
            request.method not in SAFE_METHODS
            and path.startswith(("/admin", "/portal"))
        )
        if matched is None and not staff_write:
            return await call_next(request)

        with SessionLocal() as database:
            principal = principal_from_request(request, database)
            if principal is None:
                target = "/admin/login" if path.startswith(("/admin", "/portal")) else "/login"
                return RedirectResponse(target, status_code=303)

            # Defense in depth for every current and future staff route,
            # including routes not yet listed in ROUTE_POLICIES.
            if principal.role in READ_ONLY_STAFF_ROLES and staff_write:
                request.session["flash"] = {
                    "message": (
                        "Supervisor access is read-only."
                        if principal.role == Role.SUPERVISOR
                        else "Finance access is read-only."
                    ),
                    "category": "error",
                }
                return RedirectResponse("/access-denied", status_code=303)

            if matched is not None:
                required_permission = (
                    matched.view_permission
                    if request.method in SAFE_METHODS
                    else (matched.write_permission or matched.view_permission)
                )
                if not has_permission(principal.role, required_permission):
                    request.session["flash"] = {
                        "message": "permission_required",
                        "message_key": True,
                        "category": "error",
                    }
                    return RedirectResponse("/access-denied", status_code=303)

        return await call_next(request)
