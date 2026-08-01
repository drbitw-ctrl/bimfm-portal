"""Central policy enforcement for legacy HTML routes.

Routers are being migrated incrementally.  This middleware gives all existing
routes one policy source immediately, while new routes can use dependencies.
"""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.auth.dependencies import principal_from_request
from app.auth.permissions import Permission, has_permission
from app.database import SessionLocal


@dataclass(frozen=True)
class RoutePolicy:
    prefix: str
    permission: Permission
    write_only: bool = False


ROUTE_POLICIES = (
    RoutePolicy("/admin/staff-accounts", Permission.STAFF_MANAGE),
    RoutePolicy("/admin/settings", Permission.SETTINGS_MANAGE),
    RoutePolicy("/admin/integration", Permission.INTEGRATION_MANAGE),
    RoutePolicy("/admin/finance", Permission.FINANCE_VIEW),
    RoutePolicy("/admin/leave-requests", Permission.LEAVE_APPROVE),
    RoutePolicy("/admin/overtime", Permission.OVERTIME_APPROVE),
    RoutePolicy("/admin/attendance", Permission.ATTENDANCE_VIEW_ALL),
    RoutePolicy("/admin/dtr", Permission.ATTENDANCE_VIEW_ALL),
    RoutePolicy("/admin/freelancers", Permission.STAFF_MANAGE, write_only=True),
)

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


class AuthorizationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in {"/admin/login", "/admin/logout", "/login", "/setup"}:
            return await call_next(request)

        matched = next((policy for policy in ROUTE_POLICIES if path.startswith(policy.prefix)), None)
        if matched is None:
            return await call_next(request)
        if matched.write_only and request.method in SAFE_METHODS:
            return await call_next(request)

        with SessionLocal() as database:
            principal = principal_from_request(request, database)
            if principal is None:
                target = "/admin/login" if path.startswith("/admin") else "/login"
                return RedirectResponse(target, status_code=303)
            if not has_permission(principal.role, matched.permission):
                request.session["flash"] = {
                    "message": "permission_required",
                    "message_key": True,
                    "category": "error",
                }
                return RedirectResponse("/access-denied", status_code=303)

        return await call_next(request)
