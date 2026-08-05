from contextlib import asynccontextmanager
from datetime import date, datetime, time as clock_time, timedelta, timezone
import re
import secrets
import sqlite3
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.exception_handlers import http_exception_handler as default_http_exception_handler, request_validation_exception_handler as default_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.config import (
    ACCOUNT_LOCK_MINUTES,
    APP_NAME,
    APP_VERSION,
    BASE_DIR,
    COOKIE_HTTPS_ONLY,
    DATABASE_PATH,
    DEFAULT_TIMEZONE,
    MAX_FAILED_LOGIN_ATTEMPTS,
    SESSION_SECRET,
    BOOTSTRAP_ADMIN_USERNAME,
    BOOTSTRAP_ADMIN_DISPLAY_NAME,
    BOOTSTRAP_ADMIN_PASSWORD,
    DATABASE_URL, IS_PRODUCTION, LOG_LEVEL, API_RATE_LIMIT_PER_MINUTE,
    LOGIN_RATE_LIMIT_PER_MINUTE, ENVIRONMENT,
)
from app.production import (
    configure_structured_logging, validate_environment, SecurityHeadersMiddleware,
    RequestLoggingMiddleware, RateLimitMiddleware,
)
from app.database import (
    SessionLocal,
    database_is_available,
    dispose_database,
    initialize_database,
)
from app.models import (
    AttendanceCalculation,
    AttendanceCorrection,
    AttendanceCorrectionRequest,
    AttendanceEvent,
    AttendanceMonthLock,
    AuditLog,
    DTRCompLine,
    DTRDailyLine,
    DTRLeaveLine,
    DTRTaskLine,
    DailyAttendance,
    DailyTask,
    Freelancer,
    FreelancerAccount,
    Holiday,
    HRAdminAccount,
    HRPolicy,
    LeaveRecord,
    LeaveRequest,
    MonthlyDTR,
    MonthlyCompLeaveBalance,
    PayrollMonthSummary,
    OvertimeClaim,
    CompLeaveTransaction,
    TaskMonthReview,
    WorkSchedule, PortalProject, PortalProjectMember, PortalTask, PortalTaskAssignment,
    ProjectMember, TaskWorkSession, TaskReminder,
)
from app.security import (
    hash_password,
    password_needs_rehash,
    verify_password,
)
from app.web_helpers import (
    utc_now, request_ip, is_local_request, csrf_token, validate_csrf,
    set_flash, pop_flash, template_context, write_audit, admin_count,
    get_current_admin, get_current_freelancer_account, account_is_locked,
    record_failed_login, clear_failed_login,
)
from app.attendance_calculations import (
    calculate_attendance_record,
    ensure_default_schedule,
    get_active_schedule,
    get_calculation,
    initialize_missing_calculations,
    minutes_label,
    parse_hhmm,
    recalculate_month,
)
from app.dtr_exporter import build_dtr_workbook
from app.finance_service import finance_rows, sync_finance_summary
from app.payroll_engine import calculate_payroll_multiplier
from app.dtr_service import (
    dtr_can_be_reviewed,
    generate_monthly_dtr,
    get_monthly_dtr,
)
from app.hr_workflow import (
    approve_leave_request,
    approve_overtime_claim,
    adjust_approved_overtime_claim,
    comp_balance,
    whole_comp_days,
    comp_remainder_minutes,
    COMP_LEAVE_DAY_MINUTES,
    ensure_default_policy,
    get_policy,
    get_task_review,
    invalidate_dtr,
    invalidate_task_review,
    reject_leave_request,
    reject_overtime_claim,
    task_minutes_for_date,
)

from app.work_order_service import (
    active_work_session,
    start_work_session,
    stop_work_session,
    auto_stop_active_work_session,
    repair_flagged_work_session,
    freelancer_work_order_view,
    live_work_rows,
    unread_reminder_count,
    reminder_rows,
    mark_reminder_read,
    create_task_reminder,
)
from app.portal_project_service import (
    active_task_counts_by_freelancer,
    active_task_details_by_freelancer,
    active_task_overview_rows,
    current_freelancer_portal_projects,
    current_freelancer_portal_tasks,
    sort_assigned_portal_projects,
    completed_freelancer_portal_tasks,
    portal_task_for_freelancer,
    project_data_health,
    project_overview_rows,
    team_assignment_rows,
    project_member_rows,
    hr_freelancer_choices,
    map_project_member,
    ensure_hr_project_members,
)


configure_structured_logging(LOG_LEVEL)

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]{3,80}$")





def bootstrap_cloud_admin(database: Session) -> None:
    """Create the first administrator from environment variables.

    This is intended for cloud deployments where /setup cannot be opened from
    the server's loopback address. It runs only when the administrator table is
    empty.
    """
    existing_count = int(
        database.scalar(select(func.count(HRAdminAccount.id))) or 0
    )
    if existing_count > 0:
        return

    if not (
        BOOTSTRAP_ADMIN_USERNAME
        and BOOTSTRAP_ADMIN_DISPLAY_NAME
        and BOOTSTRAP_ADMIN_PASSWORD
    ):
        return

    if not USERNAME_PATTERN.fullmatch(BOOTSTRAP_ADMIN_USERNAME):
        raise RuntimeError(
            "BIMFM_BOOTSTRAP_ADMIN_USERNAME must be 3-80 characters and use "
            "only letters, numbers, period, underscore, or hyphen."
        )
    if len(BOOTSTRAP_ADMIN_PASSWORD) < 12:
        raise RuntimeError(
            "BIMFM_BOOTSTRAP_ADMIN_PASSWORD must contain at least 12 characters."
        )

    database.add(
        HRAdminAccount(
            username=BOOTSTRAP_ADMIN_USERNAME,
            display_name=BOOTSTRAP_ADMIN_DISPLAY_NAME,
            role="ADMIN",
            password_hash=hash_password(BOOTSTRAP_ADMIN_PASSWORD),
            must_change_password=False,
            is_active=True,
        )
    )
    database.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_environment(
        production=IS_PRODUCTION,
        session_secret=SESSION_SECRET,
        sync_token="",
        cookie_https_only=COOKIE_HTTPS_ONLY,
        database_url=DATABASE_URL,
    )
    app.state.ready = False
    app.state.environment = ENVIRONMENT
    initialize_database()
    with SessionLocal() as database:
        bootstrap_cloud_admin(database)
        ensure_default_schedule(database)
        ensure_default_policy(database)
        initialize_missing_calculations(database)
        if ensure_hr_project_members(database):
            database.commit()
    app.state.ready = True
    try:
        yield
    finally:
        app.state.ready = False
        dispose_database()


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    lifespan=lifespan,
)


@app.middleware("http")
async def api_request_context(request: Request, call_next):
    request.state.request_id = request.headers.get("X-Request-ID", "").strip()[:128] or secrets.token_hex(16)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


def _api_error(request: Request, status_code: int, code: str, message: str, details=None):
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {"code": code, "message": message, "details": details},
            "meta": {"request_id": getattr(request.state, "request_id", "unknown"), "api_version": "v1"},
        },
    )


@app.exception_handler(HTTPException)
async def api_http_exception_handler(request: Request, exc: HTTPException):
    if not request.url.path.startswith("/api/"):
        return await default_http_exception_handler(request, exc)
    detail = exc.detail
    if isinstance(detail, dict):
        code = str(detail.get("code", "request_error"))
        details = {key: value for key, value in detail.items() if key != "code"} or None
    else:
        code = str(detail or "request_error")
        details = None
    messages = {
        "authentication_required": "Authentication is required.",
        "permission_required": "The authenticated account does not have the required permission.",
        "not_found": "The requested resource was not found.",
    }
    return _api_error(request, exc.status_code, code, messages.get(code, "The request could not be completed."), details)


@app.exception_handler(RequestValidationError)
async def api_validation_exception_handler(request: Request, exc: RequestValidationError):
    if not request.url.path.startswith("/api/"):
        return await default_validation_exception_handler(request, exc)
    return _api_error(
        request,
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "validation_error",
        "One or more request values are invalid.",
        exc.errors(),
    )

@app.middleware("http")
async def disable_stale_ui_cache(request: Request, call_next):
    response = await call_next(request)
    # The HR portal is an internal operational application. Prevent old HTML,
    # templates and CSS from surviving after a server update.
    if request.url.path.startswith(("/admin", "/attendance", "/tasks", "/projects", "/overtime", "/leave", "/static")):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    response.headers["X-BIMFM-HR-Build"] = APP_VERSION
    return response


from app.auth.middleware import AuthorizationMiddleware

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=API_RATE_LIMIT_PER_MINUTE,
    login_requests_per_minute=LOGIN_RATE_LIMIT_PER_MINUTE,
)
app.add_middleware(AuthorizationMiddleware)

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie="bimfm_hr_session",
    max_age=60 * 60 * 8,
    same_site="lax",
    https_only=COOKIE_HTTPS_ONLY,
)

app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static",
)

templates = Jinja2Templates(
    directory=BASE_DIR / "templates",
)


@app.get("/access-denied", response_class=HTMLResponse, include_in_schema=False)
def access_denied(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="access_denied.html",
        context=template_context(request),
        status_code=403,
    )









def normalized_utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def freelancer_zone(timezone_name: str):
    """Return the requested IANA timezone with a safe UTC+8 fallback.

    Windows usually requires the Python ``tzdata`` package for IANA timezone
    names such as Asia/Manila. The fixed-offset fallback prevents the portal
    from crashing during local development if that package is missing.
    """
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        try:
            return ZoneInfo(DEFAULT_TIMEZONE)
        except ZoneInfoNotFoundError:
            return timezone(timedelta(hours=8), name="UTC+08:00")


def current_attendance_date(
    timezone_name: str,
    now_utc: Optional[datetime] = None,
) -> date:
    official_utc = now_utc or utc_now()
    return official_utc.astimezone(
        freelancer_zone(timezone_name)
    ).date()


def format_local_datetime(
    value: Optional[datetime],
    timezone_name: str,
) -> str:
    utc_value = normalized_utc(value)
    if utc_value is None:
        return "Not recorded"

    local_value = utc_value.astimezone(
        freelancer_zone(timezone_name)
    )
    return local_value.strftime("%I:%M:%S %p").lstrip("0")


def elapsed_text(
    time_in_utc: Optional[datetime],
    time_out_utc: Optional[datetime],
) -> str:
    start = normalized_utc(time_in_utc)
    end = normalized_utc(time_out_utc)

    if start is None or end is None or end <= start:
        return "—"

    minutes = int((end - start).total_seconds() // 60)
    hours, remaining_minutes = divmod(minutes, 60)
    return f"{hours}h {remaining_minutes:02d}m"


def get_daily_attendance(
    database: Session,
    freelancer_id: int,
    attendance_date: date,
) -> Optional[DailyAttendance]:
    return database.scalar(
        select(DailyAttendance).where(
            DailyAttendance.freelancer_id == freelancer_id,
            DailyAttendance.attendance_date == attendance_date,
        )
    )


def build_attendance_view(
    record: Optional[DailyAttendance],
    timezone_name: str,
) -> dict[str, object]:
    if record is None or record.time_in_utc is None:
        return {
            "state": "WAITING_FOR_TIME_IN",
            "status_label": "Waiting for Time In",
            "time_in": "Not recorded",
            "time_out": "Not recorded",
            "can_time_in": True,
            "can_time_out": False,
        }

    if record.time_out_utc is None:
        return {
            "state": "WORKING",
            "status_label": "Currently Working",
            "time_in": format_local_datetime(
                record.time_in_utc,
                timezone_name,
            ),
            "time_out": "Not recorded",
            "can_time_in": False,
            "can_time_out": True,
        }

    return {
        "state": "COMPLETE",
        "status_label": "Attendance Complete",
        "time_in": format_local_datetime(
            record.time_in_utc,
            timezone_name,
        ),
        "time_out": format_local_datetime(
            record.time_out_utc,
            timezone_name,
        ),
        "can_time_in": False,
        "can_time_out": False,
    }



def build_history_rows(
    records: list[DailyAttendance],
    timezone_name: str,
    calculations: Optional[dict[int, AttendanceCalculation]] = None,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    calculations = calculations or {}

    for record in records:
        if (
            record.time_in_utc is not None
            and record.time_out_utc is not None
        ):
            status = "Complete"
        elif record.time_in_utc is not None:
            status = "Missing Time Out"
        else:
            status = record.status.replace("_", " ").title()

        calculation = calculations.get(record.id)
        rows.append(
            {
                "date": record.attendance_date.strftime("%b %d, %Y"),
                "time_in": format_local_datetime(
                    record.time_in_utc,
                    timezone_name,
                ),
                "time_out": format_local_datetime(
                    record.time_out_utc,
                    timezone_name,
                ),
                "duration": elapsed_text(
                    record.time_in_utc,
                    record.time_out_utc,
                ),
                "status": status,
                "calculation": calculation_display(calculation),
            }
        )

    return rows

def calculation_display(
    calculation: Optional[AttendanceCalculation],
) -> dict[str, object]:
    if calculation is None:
        return {
            "status": "NOT_CALCULATED",
            "status_label": "Not calculated",
            "gross": "—",
            "break": "—",
            "rendered": "—",
            "late": "—",
            "undertime": "—",
            "overtime": "—",
            "gross_minutes": 0,
            "rendered_minutes": 0,
            "late_minutes": 0,
            "undertime_minutes": 0,
            "overtime_minutes": 0,
        }

    return {
        "status": calculation.calculation_status,
        "status_label": calculation.calculation_status.replace("_", " ").title(),
        "gross": minutes_label(calculation.gross_minutes),
        "break": minutes_label(calculation.applied_break_minutes),
        "rendered": minutes_label(calculation.rendered_minutes),
        "late": minutes_label(calculation.late_minutes),
        "undertime": minutes_label(calculation.undertime_minutes),
        "overtime": minutes_label(calculation.overtime_minutes),
        "gross_minutes": calculation.gross_minutes,
        "rendered_minutes": calculation.rendered_minutes,
        "late_minutes": calculation.late_minutes,
        "undertime_minutes": calculation.undertime_minutes,
        "overtime_minutes": calculation.overtime_minutes,
    }


def selected_workday_names(schedule: WorkSchedule) -> list[str]:
    mapping = (
        ("Monday", schedule.monday),
        ("Tuesday", schedule.tuesday),
        ("Wednesday", schedule.wednesday),
        ("Thursday", schedule.thursday),
        ("Friday", schedule.friday),
        ("Saturday", schedule.saturday),
        ("Sunday", schedule.sunday),
    )
    return [name for name, enabled in mapping if enabled]

MONTH_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def parse_month_key(month_key: str) -> Optional[tuple[date, date]]:
    if not MONTH_PATTERN.fullmatch(month_key):
        return None

    year, month = (int(part) for part in month_key.split("-"))
    first_day = date(year, month, 1)
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    return first_day, next_month


def current_month_key(timezone_name: str = DEFAULT_TIMEZONE) -> str:
    local_date = utc_now().astimezone(freelancer_zone(timezone_name)).date()
    return local_date.strftime("%Y-%m")


def get_month_lock(
    database: Session,
    month_key: str,
) -> Optional[AttendanceMonthLock]:
    return database.scalar(
        select(AttendanceMonthLock).where(
            AttendanceMonthLock.month_key == month_key
        )
    )


def month_is_locked(database: Session, month_key: str) -> bool:
    lock = get_month_lock(database, month_key)
    return bool(lock and lock.is_locked)


def local_time_to_utc(
    attendance_date: date,
    time_text: str,
    timezone_name: str,
) -> Optional[datetime]:
    value = time_text.strip()
    if not value:
        return None

    try:
        parsed_time = clock_time.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Time must use the HH:MM format.") from exc

    local_value = datetime.combine(
        attendance_date,
        parsed_time,
        tzinfo=freelancer_zone(timezone_name),
    )
    return local_value.astimezone(timezone.utc)


def utc_to_time_input(
    value: Optional[datetime],
    timezone_name: str,
) -> str:
    normalized = normalized_utc(value)
    if normalized is None:
        return ""
    return normalized.astimezone(
        freelancer_zone(timezone_name)
    ).strftime("%H:%M")


def attendance_status(record: Optional[DailyAttendance]) -> str:
    if record is None or (
        record.time_in_utc is None and record.time_out_utc is None
    ):
        return "No Record"
    if record.time_in_utc is not None and record.time_out_utc is None:
        return "Missing Time Out"
    if record.time_in_utc is None and record.time_out_utc is not None:
        return "Invalid Record"
    return "Complete"


def build_admin_attendance_row(
    freelancer: Freelancer,
    record: Optional[DailyAttendance],
    attendance_date: date,
    correction_count: int = 0,
    calculation: Optional[AttendanceCalculation] = None,
) -> dict[str, object]:
    timezone_name = freelancer.timezone_name
    status = attendance_status(record)

    if not freelancer.is_active:
        status = "Account Disabled"
    elif (
        record is not None
        and record.time_in_utc is not None
        and record.time_out_utc is None
        and attendance_date == current_attendance_date(timezone_name)
    ):
        status = "Currently Working"

    return {
        "freelancer_id": freelancer.id,
        "code": freelancer.freelancer_code,
        "name": freelancer.full_name,
        "timezone": timezone_name,
        "date": attendance_date.isoformat(),
        "date_display": attendance_date.strftime("%b %d, %Y"),
        "time_in": format_local_datetime(
            record.time_in_utc if record else None,
            timezone_name,
        ),
        "time_out": format_local_datetime(
            record.time_out_utc if record else None,
            timezone_name,
        ),
        "elapsed": elapsed_text(
            record.time_in_utc if record else None,
            record.time_out_utc if record else None,
        ),
        "status": status,
        "review_status": record.review_status if record else "UNREVIEWED",
        "correction_count": correction_count,
        "calculation": calculation_display(calculation),
    }


def correction_history_rows(
    corrections: list[AttendanceCorrection],
    timezone_name: str,
    admin_names: dict[int, str],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for correction in corrections:
        rows.append(
            {
                "created_at": format_local_datetime(
                    correction.created_at,
                    DEFAULT_TIMEZONE,
                ),
                "admin": admin_names.get(
                    correction.corrected_by_admin_id,
                    "HR Administrator",
                ),
                "original_time_in": format_local_datetime(
                    correction.original_time_in_utc,
                    timezone_name,
                ),
                "original_time_out": format_local_datetime(
                    correction.original_time_out_utc,
                    timezone_name,
                ),
                "corrected_time_in": format_local_datetime(
                    correction.corrected_time_in_utc,
                    timezone_name,
                ),
                "corrected_time_out": format_local_datetime(
                    correction.corrected_time_out_utc,
                    timezone_name,
                ),
                "reason": correction.reason,
            }
        )
    return rows

def admin_name_map(database: Session) -> dict[int, str]:
    return {
        row.id: row.display_name
        for row in database.scalars(
            select(HRAdminAccount).order_by(HRAdminAccount.id)
        ).all()
    }


def dtr_status_label(value: str) -> str:
    return value.replace("_", " ").title()


def dtr_summary_row(
    dtr: MonthlyDTR,
    freelancer: Freelancer,
) -> dict[str, object]:
    return {
        "id": dtr.id,
        "freelancer_code": freelancer.freelancer_code,
        "freelancer_name": freelancer.full_name,
        "month_key": dtr.month_key,
        "status": dtr.status,
        "status_label": dtr_status_label(dtr.status),
        "present_days": dtr.present_days,
        "late_days": dtr.late_days,
        "absent_days": dtr.absent_days,
        "leave_days": dtr.leave_days,
        "incomplete_days": dtr.incomplete_days,
        "rendered": minutes_label(dtr.rendered_minutes),
        "generated_at": format_local_datetime(dtr.generated_at, DEFAULT_TIMEZONE),
    }



def dtr_line_row(line: DTRDailyLine, timezone_name: str) -> dict[str, object]:
    return {
        "date": line.attendance_date.strftime("%Y-%m-%d"),
        "day": line.day_name,
        "day_type": dtr_status_label(line.day_type),
        "status": line.attendance_status,
        "status_label": dtr_status_label(line.attendance_status),
        "time_in": format_local_datetime(line.time_in_utc, timezone_name),
        "time_out": format_local_datetime(line.time_out_utc, timezone_name),
        "rendered": minutes_label(line.rendered_minutes),
        "late": minutes_label(line.late_minutes),
        "undertime": minutes_label(line.undertime_minutes),
        "overtime": minutes_label(line.potential_overtime_minutes),
        "approved_overtime": minutes_label(line.approved_overtime_minutes),
        "comp_earned": minutes_label(line.comp_leave_earned_minutes),
        "comp_used": minutes_label(line.comp_leave_used_minutes),
        "task_time": minutes_label(line.task_minutes),
        "task_summary": line.task_summary or "",
        "review": dtr_status_label(line.attendance_review_status),
        "notes": line.notes or "",
    }

def compact_dtr_metrics(database: Session, dtr: MonthlyDTR) -> dict[str, object]:
    policy = database.scalar(select(HRPolicy).order_by(HRPolicy.id))
    standard_day_minutes = max(
        1, int(policy.standard_leave_day_minutes if policy else COMP_LEAVE_DAY_MINUTES)
    )
    leave_lines = list(database.scalars(
        select(DTRLeaveLine).where(DTRLeaveLine.monthly_dtr_id == dtr.id)
    ).all())
    approved_leave_minutes = sum(
        max(0, int(line.duration_minutes or 0)) for line in leave_lines
    )
    comp_leave_minutes = sum(
        max(0, int(line.comp_leave_minutes_used or 0)) for line in leave_lines
    )

    # Working-day counts remain visible, but Finance deductions are based on
    # hours. Approved overtime credits offset approved leave minute-for-minute.
    worked_statuses = {
        "PRESENT", "LATE", "HOLIDAY_WORK", "REST_DAY_WORK",
        "WORKED_ON_LEAVE", "PARTIAL_LEAVE_WORK",
    }
    daily_lines = list(database.scalars(
        select(DTRDailyLine).where(DTRDailyLine.monthly_dtr_id == dtr.id)
    ).all())
    worked_days = len({
        line.attendance_date for line in daily_lines
        if line.attendance_status in worked_statuses
    })
    leave_days = len({line.leave_date for line in leave_lines})

    payroll = calculate_payroll_multiplier(
        calendar_days=int(dtr.calendar_days or 0),
        approved_leave_minutes=approved_leave_minutes,
        comp_credit_minutes_available=comp_leave_minutes,
        standard_day_minutes=standard_day_minutes,
    )
    payable_days = worked_days + payroll.comp_credit_days_applied
    non_payable_days = payroll.effective_unpaid_leave_days + int(dtr.absent_days or 0)

    return {
        "standard_day_hours": standard_day_minutes / 60,
        "standard_day_minutes": standard_day_minutes,
        "calendar_days": payroll.calendar_days,
        "worked_days": worked_days,
        "worked_hours": round(int(dtr.rendered_minutes or 0) / 60, 2),
        "regular_leave_taken_days": leave_days,
        "regular_leave_days": round(payroll.effective_unpaid_leave_days, 3),
        "comp_leave_days": round(payroll.comp_credit_days_applied, 3),
        "payable_days": round(payable_days, 3),
        "non_payable_days": round(non_payable_days, 3),
        "leave_days": leave_days,
        "approved_leave_minutes": payroll.approved_leave_minutes,
        "approved_leave_hours": round(payroll.approved_leave_hours, 2),
        "comp_credit_minutes_applied": payroll.comp_credit_minutes_applied,
        "comp_credit_hours_applied": round(payroll.comp_credit_hours_applied, 2),
        "effective_unpaid_leave_minutes": payroll.effective_unpaid_leave_minutes,
        "effective_unpaid_leave_hours": round(payroll.effective_unpaid_leave_hours, 2),
        "comp_credit_days_applied": round(payroll.comp_credit_days_applied, 3),
        "effective_unpaid_leave_days": round(payroll.effective_unpaid_leave_days, 3),
        "payroll_numerator_days": round(payroll.payroll_numerator_days, 3),
        "payroll_multiplier": payroll.payroll_multiplier,
        "payroll_multiplier_display": payroll.multiplier_display,
        "payroll_percentage_display": payroll.percentage_display,
        "payroll_formula_display": payroll.formula_display,
        "salary_covered_days": round(payroll.payroll_numerator_days, 3),
        "salary_covered_minutes": payroll.salary_covered_minutes,
        "salary_basis_minutes": payroll.salary_basis_minutes,
        "salary_coverage_display": payroll.salary_coverage_display,
        "payroll_treatment_display": payroll.payroll_treatment_display,
        "deduction_display": payroll.deduction_display,
        "payable_workday_equivalents": round(payable_days, 3),
        "rest_days": int(dtr.rest_days or 0),
        "holiday_days": int(dtr.holiday_days or 0),
        "absent_days": int(dtr.absent_days or 0),
        "approved_ot_label": minutes_label(int(dtr.approved_overtime_minutes or 0)),
        "opening_comp_label": minutes_label(int(dtr.comp_leave_opening_balance_minutes or 0)),
        "earned_comp_label": minutes_label(int(dtr.comp_leave_earned_minutes or 0)),
        "used_comp_label": minutes_label(int(dtr.comp_leave_used_minutes or 0)),
        "closing_comp_label": minutes_label(int(dtr.comp_leave_closing_balance_minutes or 0)),
    }











































# ---------------------------------------------------------------------------
# STEP 08: DAILY TASK, OVERTIME, COMPENSATORY LEAVE, AND LEAVE REQUESTS
# ---------------------------------------------------------------------------


def _parse_positive_minutes(value: str, *, maximum: int = 1440) -> int:
    try:
        minutes = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Minutes must be a whole number.") from exc
    if minutes <= 0 or minutes > maximum:
        raise ValueError(f"Minutes must be between 1 and {maximum}.")
    return minutes


def _parse_hours_to_minutes(value: str, *, maximum_hours: float = 24.0) -> int:
    try:
        hours_value = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Hours spent must be a number.") from exc
    if hours_value <= 0 or hours_value > maximum_hours:
        raise ValueError(f"Hours spent must be greater than 0 and not exceed {maximum_hours:g}.")
    minutes = int(round(hours_value * 60))
    if minutes <= 0:
        raise ValueError("Hours spent is too small.")
    return minutes


def _parse_completion_percentage(value: str) -> int:
    try:
        percentage = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Completion percentage must be a whole number.") from exc
    if percentage < 0 or percentage > 100:
        raise ValueError("Completion percentage must be between 0 and 100.")
    return percentage












































# BIMFM Portal v2 modular administration, integration, projects and finance routers
from app.routers.administration import configure_administration_routes
from app.routers.integration import configure_integration_routes
from app.routers.projects import configure_projects_routes
from app.routers.finance import configure_finance_routes

app.include_router(configure_administration_routes(globals()))
app.include_router(configure_integration_routes(globals()))
app.include_router(configure_projects_routes(globals()))
app.include_router(configure_finance_routes(globals()))

# BIMFM Portal v2 modular attendance and DTR router
from app.routers.attendance import configure_attendance_routes

app.include_router(configure_attendance_routes(globals()))
# BIMFM Portal v2 modular leave router
from app.routers.leave import configure_leave_routes

app.include_router(configure_leave_routes(globals()))
# BIMFM Portal v2 modular overtime and compensatory-leave router
from app.routers.overtime import configure_overtime_routes

app.include_router(configure_overtime_routes(globals()))

# Unified role-aware dashboard entry
from app.routers.dashboard import router as dashboard_router
app.include_router(dashboard_router)


# Versioned JSON API foundation
from app.api.v1 import router as api_v1_router
app.include_router(api_v1_router)
