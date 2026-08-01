from datetime import datetime, timedelta, timezone
import secrets
from typing import Optional

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.config import (
    ACCOUNT_LOCK_MINUTES,
    APP_NAME,
    APP_VERSION,
    MAX_FAILED_LOGIN_ATTEMPTS,
)
from app.database import SessionLocal
from app.i18n import load_catalog, locale_for_request, translator
from app.auth.permissions import Permission, has_permission, normalize_role
from app.models import (
    AuditLog,
    Freelancer,
    FreelancerAccount,
    HRAdminAccount,
)

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

def request_ip(request: Request) -> Optional[str]:
    if request.client is None:
        return None
    return request.client.host

def is_local_request(request: Request) -> bool:
    return request_ip(request) in {"127.0.0.1", "::1", "localhost"}

def csrf_token(request: Request) -> str:
    token = request.session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        request.session["csrf_token"] = token
    return token

def validate_csrf(request: Request, submitted_token: str) -> bool:
    stored_token = request.session.get("csrf_token")
    return bool(
        stored_token
        and submitted_token
        and secrets.compare_digest(stored_token, submitted_token)
    )

def set_flash(
    request: Request,
    message: str,
    category: str = "info",
) -> None:
    request.session["flash"] = {
        "message": message,
        "category": category,
    }

def pop_flash(request: Request) -> Optional[dict[str, str]]:
    value = request.session.pop("flash", None)
    return value if isinstance(value, dict) else None

def duration_label(minutes: object) -> str:
    """Render minute values without decimal-hour ambiguity."""
    try:
        total = int(minutes or 0)
    except (TypeError, ValueError):
        total = 0
    sign = "-" if total < 0 else ""
    total = abs(total)
    hours, remainder = divmod(total, 60)
    return f"{sign}{hours}h {remainder:02d}m"


def decimal_hours_input(minutes: object) -> str:
    """Return a compact decimal value only for editable form inputs."""
    try:
        total = max(0, int(minutes or 0))
    except (TypeError, ValueError):
        total = 0
    value = total / 60
    return f"{value:.2f}".rstrip("0").rstrip(".")


def discipline_label(value: object) -> str:
    """Return the compact portal label without rewriting stored discipline data."""
    text = str(value or "").strip()
    normalized = text.casefold()
    if normalized in {"architecture", "architectural", "ar"}:
        return "AR"
    if normalized in {"structure", "structural", "st"}:
        return "ST"
    return text or "—"

def template_context(
    request: Request,
    **extra,
) -> dict:
    current_staff = None
    current_freelancer = None
    staff_id = request.session.get("admin_id")
    freelancer_account_id = request.session.get("freelancer_account_id")
    if staff_id or freelancer_account_id:
        with SessionLocal() as database:
            if staff_id:
                current_staff = database.get(HRAdminAccount, int(staff_id))
            if freelancer_account_id:
                account_row = database.get(FreelancerAccount, int(freelancer_account_id))
                if account_row and account_row.is_active:
                    member = database.get(Freelancer, account_row.freelancer_id)
                    if member:
                        current_freelancer = {
                            "account_id": account_row.id,
                            "member_id": member.id,
                            "name": member.full_name,
                            "code": member.freelancer_code,
                        }

    locale = locale_for_request(request)
    context = {
        "request": request,
        "locale": locale,
        "t": translator(locale),
        "client_catalog": load_catalog(locale),
        "app_name": APP_NAME,
        "app_version": APP_VERSION,
        "csrf_token": csrf_token(request),
        "flash": pop_flash(request),
        "duration_label": duration_label,
        "hours_input": decimal_hours_input,
        "discipline_label": discipline_label,
        "current_staff": current_staff,
        "current_staff_role": (str(getattr(current_staff, "role", "ADMIN") or "ADMIN").upper() if current_staff else None),
        "current_freelancer": current_freelancer,
        "Permission": Permission,
        "can": (
            (lambda permission: has_permission(normalize_role(current_staff.role), permission))
            if current_staff else
            (lambda permission: has_permission("EMPLOYEE", permission))
            if current_freelancer else
            (lambda permission: False)
        ),
    }
    context.update(extra)
    return context

def write_audit(
    database: Session,
    *,
    actor_type: str,
    actor_id: Optional[int],
    action: str,
    request: Request,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    details: Optional[str] = None,
) -> None:
    database.add(
        AuditLog(
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details,
            ip_address=request_ip(request),
        )
    )

def admin_count(database: Session) -> int:
    return int(
        database.scalar(
            select(func.count(HRAdminAccount.id))
        )
        or 0
    )

def get_current_admin(
    request: Request,
    database: Session,
) -> Optional[HRAdminAccount]:
    admin_id = request.session.get("admin_id")
    if not admin_id:
        return None

    admin = database.get(HRAdminAccount, int(admin_id))
    if admin is None or not admin.is_active:
        request.session.pop("admin_id", None)
        return None

    return admin

def get_current_freelancer_account(
    request: Request,
    database: Session,
) -> Optional[FreelancerAccount]:
    account_id = request.session.get("freelancer_account_id")
    if not account_id:
        return None

    account = database.scalar(
        select(FreelancerAccount)
        .options(joinedload(FreelancerAccount.freelancer))
        .where(FreelancerAccount.id == int(account_id))
    )

    if (
        account is None
        or not account.is_active
        or not account.freelancer.is_active
    ):
        request.session.pop("freelancer_account_id", None)
        return None

    return account

def account_is_locked(locked_until: Optional[datetime]) -> bool:
    if locked_until is None:
        return False

    if locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=timezone.utc)

    return locked_until > utc_now()

def record_failed_login(account) -> None:
    account.failed_login_count += 1

    if account.failed_login_count >= MAX_FAILED_LOGIN_ATTEMPTS:
        account.locked_until = utc_now() + timedelta(
            minutes=ACCOUNT_LOCK_MINUTES
        )
        account.failed_login_count = 0

def clear_failed_login(account) -> None:
    account.failed_login_count = 0
    account.locked_until = None
    account.last_login_at = utc_now()
