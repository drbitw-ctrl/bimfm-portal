"""Central policy enforcement for HTML routes.

Release 20.14 separates read permissions from write permissions so a Supervisor
can inspect the complete operational workspace without being able to change
records.
"""
from __future__ import annotations

from dataclasses import dataclass
import logging
import threading
import time

from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.auth.dependencies import principal_from_request
from app.auth.permissions import Permission, Role, has_permission
from app.config import WORK_ORDER_RECONCILE_INTERVAL_SECONDS
from app.database import SessionLocal
from app.models import FreelancerAccount, HRAdminAccount
from app.work_order_service import reconcile_stale_work_sessions


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
    RoutePolicy("/admin/dtr/generate", Permission.ATTENDANCE_VIEW_ALL, Permission.DTR_GENERATE),
    RoutePolicy("/admin/dtr", Permission.ATTENDANCE_VIEW_ALL, Permission.ATTENDANCE_EDIT),
    RoutePolicy("/admin/freelancers", Permission.STAFF_MANAGE, Permission.STAFF_MANAGE),
)

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
READ_ONLY_STAFF_ROLES = {Role.SUPERVISOR, Role.FINANCE}
FINANCE_WRITE_EXCEPTIONS = {"/admin/dtr/generate"}
STAFF_SELF_SERVICE_WRITE_PATHS = {"/admin/change-password"}
_safeguard_lock = threading.Lock()
_last_work_order_reconcile = 0.0
_logger = logging.getLogger(__name__)


def _run_work_order_safeguard_if_due() -> None:
    """Reconcile forgotten timers at a low frequency without delaying requests."""
    global _last_work_order_reconcile
    now_monotonic = time.monotonic()
    if now_monotonic - _last_work_order_reconcile < WORK_ORDER_RECONCILE_INTERVAL_SECONDS:
        return
    if not _safeguard_lock.acquire(blocking=False):
        return
    try:
        now_monotonic = time.monotonic()
        if now_monotonic - _last_work_order_reconcile < WORK_ORDER_RECONCILE_INTERVAL_SECONDS:
            return
        with SessionLocal() as database:
            try:
                closed = reconcile_stale_work_sessions(database)
                if closed:
                    database.commit()
                else:
                    database.rollback()
            except Exception:
                database.rollback()
                _logger.exception("Work Order safeguard reconciliation failed")
        _last_work_order_reconcile = time.monotonic()
    finally:
        _safeguard_lock.release()


PASSWORD_CHANGE_ALLOWED_PATHS = {
    "/admin/change-password", "/admin/logout", "/change-password", "/logout",
    "/admin/login", "/login", "/setup", "/language",
}


class AuthorizationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith("/static/"):
            return await call_next(request)

        _run_work_order_safeguard_if_due()

        # Force temporary-password replacement before any operational page is
        # available. Existing production staff accounts migrate with the flag
        # disabled; newly created or reset accounts are flagged explicitly.
        if path not in PASSWORD_CHANGE_ALLOWED_PATHS:
            with SessionLocal() as database:
                staff_id = request.session.get("admin_id")
                if staff_id:
                    staff = database.get(HRAdminAccount, int(staff_id))
                    if staff and staff.is_active and bool(staff.must_change_password):
                        return RedirectResponse("/admin/change-password", status_code=303)
                freelancer_account_id = request.session.get("freelancer_account_id")
                if freelancer_account_id:
                    account = database.get(FreelancerAccount, int(freelancer_account_id))
                    if account and account.is_active and bool(account.must_change_password):
                        return RedirectResponse("/change-password", status_code=303)

        if path in {"/admin/login", "/admin/logout", "/login", "/setup", "/language", "/admin/change-password", "/change-password", "/logout"}:
            return await call_next(request)

        matched = next(
            (policy for policy in ROUTE_POLICIES if path.startswith(policy.prefix)),
            None,
        )
        staff_write = (
            request.method not in SAFE_METHODS
            and path.startswith(("/admin", "/portal"))
            and path not in STAFF_SELF_SERVICE_WRITE_PATHS
        )
        if matched is None and not staff_write:
            return await call_next(request)

        with SessionLocal() as database:
            principal = principal_from_request(request, database)
            if principal is None:
                target = "/admin/login" if path.startswith(("/admin", "/portal")) else "/login"
                return RedirectResponse(target, status_code=303)

            # Supervisors remain fully read-only. Finance is read-only except for
            # the explicit DTR generation operation requested for payroll work.
            if principal.role in READ_ONLY_STAFF_ROLES and staff_write:
                finance_exception = (
                    principal.role == Role.FINANCE
                    and path in FINANCE_WRITE_EXCEPTIONS
                )
                if not finance_exception:
                    request.session["flash"] = {
                        "message": (
                            "Supervisor access is read-only."
                            if principal.role == Role.SUPERVISOR
                            else "Finance access is read-only except for DTR generation."
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
