"""Central role and permission policy.

Database role values remain stable while route code checks capabilities. This
keeps authorization extensible and prevents role-name comparisons from being
scattered throughout the application.
"""
from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from typing import Iterable


class Role(StrEnum):
    ADMIN = "ADMIN"
    SUPERVISOR = "SUPERVISOR"
    FINANCE = "FINANCE"
    EMPLOYEE = "EMPLOYEE"


class Permission(StrEnum):
    DASHBOARD_VIEW = "dashboard.view"
    ATTENDANCE_VIEW_OWN = "attendance.view_own"
    ATTENDANCE_VIEW_ALL = "attendance.view_all"
    ATTENDANCE_EDIT = "attendance.edit"
    LEAVE_SUBMIT = "leave.submit"
    LEAVE_VIEW_ALL = "leave.view_all"
    LEAVE_APPROVE = "leave.approve"
    OVERTIME_SUBMIT = "overtime.submit"
    OVERTIME_VIEW_ALL = "overtime.view_all"
    OVERTIME_APPROVE = "overtime.approve"
    FINANCE_VIEW = "finance.view"
    FINANCE_EXPORT = "finance.export"
    DTR_GENERATE = "dtr.generate"
    PROJECT_VIEW = "project.view"
    PROJECT_EDIT = "project.edit"
    STAFF_MANAGE = "staff.manage"
    SETTINGS_MANAGE = "settings.manage"
    INTEGRATION_MANAGE = "integration.manage"
    TASK_REMINDER_SEND = "task_reminder.send"
    REPORT_EXPORT = "report.export"


_ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.ADMIN: frozenset(Permission),
    # Release 20.14: Supervisor is a true read-only management role. It can
    # inspect operational, project, attendance, request, DTR and finance data,
    # but it cannot create, approve, edit, delete or configure records. It may
    # download read-only operational Excel reports. Finance remains narrowly
    # scoped to reporting plus monthly DTR generation.
    Role.SUPERVISOR: frozenset({
        Permission.DASHBOARD_VIEW,
        Permission.ATTENDANCE_VIEW_ALL,
        Permission.LEAVE_VIEW_ALL,
        Permission.OVERTIME_VIEW_ALL,
        Permission.FINANCE_VIEW,
        Permission.PROJECT_VIEW,
        Permission.TASK_REMINDER_SEND,
        Permission.REPORT_EXPORT,
    }),
    Role.FINANCE: frozenset({
        Permission.DASHBOARD_VIEW,
        Permission.ATTENDANCE_VIEW_ALL,
        Permission.FINANCE_VIEW,
        Permission.FINANCE_EXPORT,
        Permission.DTR_GENERATE,
        Permission.PROJECT_VIEW,
        Permission.REPORT_EXPORT,
    }),
    Role.EMPLOYEE: frozenset({
        Permission.DASHBOARD_VIEW,
        Permission.ATTENDANCE_VIEW_OWN,
        Permission.LEAVE_SUBMIT,
        Permission.OVERTIME_SUBMIT,
        Permission.PROJECT_VIEW,
    }),
}


def normalize_role(value: object, *, default: Role = Role.EMPLOYEE) -> Role:
    raw = str(value or "").strip().upper()
    try:
        return Role(raw)
    except ValueError:
        return default


@lru_cache(maxsize=None)
def permissions_for_role(role: Role | str) -> frozenset[Permission]:
    normalized = normalize_role(role)
    return _ROLE_PERMISSIONS[normalized]


def has_permission(role: Role | str, permission: Permission | str) -> bool:
    try:
        normalized_permission = Permission(str(permission))
    except ValueError:
        return False
    return normalized_permission in permissions_for_role(normalize_role(role))


def has_any_permission(role: Role | str, permissions: Iterable[Permission | str]) -> bool:
    return any(has_permission(role, permission) for permission in permissions)
