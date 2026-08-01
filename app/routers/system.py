from contextlib import closing
import sqlite3

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, select

from app.config import APP_NAME, APP_VERSION, DATABASE_DIALECT, DATABASE_PATH, ENVIRONMENT
from app.database import SessionLocal, database_is_available
from app.models import (
    AttendanceCalculation, AttendanceCorrection, AttendanceEvent,
    AttendanceMonthLock, AuditLog, CompLeaveTransaction, DTRCompLine,
    DTRDailyLine, DTRLeaveLine, DTRTaskLine, DailyAttendance, DailyTask,
    Freelancer, FreelancerAccount, HRAdminAccount, HRPolicy, Holiday,
    LeaveRecord, LeaveRequest, MonthlyDTR, OvertimeClaim, ProjectSourceMember,
    ProjectSyncRun, SyncedProjectTask, TaskMonthReview, WorkSchedule,
    PortalProject, PortalProjectMember, PortalTask, PortalTaskAssignment,
    ProjectMember,
)
from app.web_helpers import admin_count, validate_csrf
from app.i18n import SUPPORTED_LOCALES

router = APIRouter(tags=["system"])

@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    with SessionLocal() as database:
        if admin_count(database) == 0:
            return RedirectResponse(
                "/setup",
                status_code=303,
            )

    return RedirectResponse(
        "/login",
        status_code=303,
    )


@router.get("/health")
@router.get("/health/live", include_in_schema=False)
def health() -> dict[str, object]:
    """Liveness probe: confirms that the application process can respond."""
    return {"status": "ok", "application": APP_NAME, "version": APP_VERSION}


@router.get("/health/ready")
def readiness(request: Request):
    """Readiness probe: confirms startup completion and database connectivity."""
    database_ok = database_is_available()
    ready = bool(getattr(request.app.state, "ready", False)) and database_ok
    payload = {
        "status": "ready" if ready else "not_ready",
        "application": APP_NAME,
        "version": APP_VERSION,
        "environment": ENVIRONMENT,
        "database": "available" if database_ok else "unavailable",
        "database_dialect": DATABASE_DIALECT,
    }
    from fastapi.responses import JSONResponse
    return JSONResponse(payload, status_code=200 if ready else 503)


@router.get("/setup-status")
def setup_status() -> dict[str, object]:
    table_counts: dict[str, int] = {}

    with SessionLocal() as database:
        queries = {
            "hr_admin_accounts": select(
                func.count(HRAdminAccount.id)
            ),
            "freelancers": select(func.count(Freelancer.id)),
            "freelancer_accounts": select(
                func.count(FreelancerAccount.id)
            ),
            "attendance_events": select(
                func.count(AttendanceEvent.id)
            ),
            "daily_attendance": select(
                func.count(DailyAttendance.id)
            ),
            "attendance_corrections": select(
            func.count(AttendanceCorrection.id)
        ),
        "attendance_month_locks": select(
            func.count(AttendanceMonthLock.id)
        ),
        "work_schedules": select(func.count(WorkSchedule.id)),
        "attendance_calculations": select(
            func.count(AttendanceCalculation.id)
        ),
        "holidays": select(func.count(Holiday.id)),
        "leave_records": select(func.count(LeaveRecord.id)),
        "monthly_dtr": select(func.count(MonthlyDTR.id)),
        "dtr_daily_lines": select(func.count(DTRDailyLine.id)),
        "daily_tasks": select(func.count(DailyTask.id)),
        "task_month_reviews": select(func.count(TaskMonthReview.id)),
        "overtime_claims": select(func.count(OvertimeClaim.id)),
        "comp_leave_transactions": select(func.count(CompLeaveTransaction.id)),
        "leave_requests": select(func.count(LeaveRequest.id)),
        "hr_policies": select(func.count(HRPolicy.id)),
        "dtr_task_lines": select(func.count(DTRTaskLine.id)),
        "dtr_comp_lines": select(func.count(DTRCompLine.id)),
        "dtr_leave_lines": select(func.count(DTRLeaveLine.id)),
        "portal_projects": select(func.count(PortalProject.id)),
        "portal_project_members": select(func.count(PortalProjectMember.id)),
        "portal_tasks": select(func.count(PortalTask.id)),
        "portal_task_assignments": select(func.count(PortalTaskAssignment.id)),
        "project_member_directory": select(func.count(ProjectMember.id)),
        "mapped_project_members": select(func.count(ProjectMember.id)).where(ProjectMember.freelancer_id.is_not(None)),
        "unmapped_project_members": select(func.count(ProjectMember.id)).where(ProjectMember.freelancer_id.is_(None)),
        "legacy_project_source_members": select(func.count(ProjectSourceMember.id)),
        "legacy_synced_project_tasks": select(func.count(SyncedProjectTask.id)),
        "legacy_project_sync_runs": select(func.count(ProjectSyncRun.id)),
        "audit_log": select(func.count(AuditLog.id)),
        }

        for table_name, query in queries.items():
            table_counts[table_name] = int(
                database.scalar(query) or 0
            )

    journal_mode = None
    foreign_keys_enabled = None
    if DATABASE_DIALECT == "sqlite":
        with closing(sqlite3.connect(DATABASE_PATH)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
            foreign_keys_enabled = bool(
                connection.execute("PRAGMA foreign_keys").fetchone()[0]
            )

    return {
        "database_ready": database_is_available(),
        "database_dialect": DATABASE_DIALECT,
        "project_mode": "postgresql_native_member_mapping",
        "synchronization_required": False,
        "journal_mode": journal_mode,
        "foreign_keys_enabled": foreign_keys_enabled,
        "table_counts": table_counts,
    }


@router.post("/language")
def set_language(request: Request, locale: str = Form(...), csrf: str = Form(...), next_url: str = Form("/")):
    if not validate_csrf(request, csrf):
        return RedirectResponse("/", status_code=303)
    if locale in SUPPORTED_LOCALES:
        request.session["locale"] = locale
    safe_next = next_url if next_url.startswith("/") and not next_url.startswith("//") else "/"
    return RedirectResponse(safe_next, status_code=303)
