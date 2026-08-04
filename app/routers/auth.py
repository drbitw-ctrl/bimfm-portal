import re

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app.database import SessionLocal
from app.models import FreelancerAccount, HRAdminAccount
from app.security import hash_password, password_needs_rehash, verify_password
from app.work_order_service import unread_reminder_count
from app.web_helpers import (
    account_is_locked,
    admin_count,
    clear_failed_login,
    csrf_token,
    get_current_admin,
    get_current_freelancer_account,
    is_local_request,
    record_failed_login,
    set_flash,
    template_context,
    validate_csrf,
    write_audit,
)

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]{3,80}$")


def create_auth_router(templates: Jinja2Templates) -> APIRouter:
    router = APIRouter(tags=["authentication"])

    @router.get("/setup", response_class=HTMLResponse)
    def setup_page(request: Request):
        with SessionLocal() as database:
            if admin_count(database) > 0:
                return RedirectResponse(
                    "/admin/login",
                    status_code=303,
                )

        return templates.TemplateResponse(
            request=request,
            name="setup.html",
            context=template_context(
                request,
                local_only=not is_local_request(request),
            ),
        )


    @router.post("/setup")
    def create_initial_admin(
        request: Request,
        csrf: str = Form(...),
        username: str = Form(...),
        display_name: str = Form(...),
        password: str = Form(...),
        confirm_password: str = Form(...),
    ):
        if not validate_csrf(request, csrf):
            set_flash(request, "Invalid form token.", "error")
            return RedirectResponse("/setup", status_code=303)

        if not is_local_request(request):
            set_flash(
                request,
                "Initial setup is allowed only from the server computer.",
                "error",
            )
            return RedirectResponse("/setup", status_code=303)

        username = username.strip().lower()
        display_name = display_name.strip()

        with SessionLocal() as database:
            if admin_count(database) > 0:
                return RedirectResponse(
                    "/admin/login",
                    status_code=303,
                )

            if not USERNAME_PATTERN.fullmatch(username):
                set_flash(
                    request,
                    "Username must be 3-80 characters and use only "
                    "letters, numbers, period, underscore, or hyphen.",
                    "error",
                )
                return RedirectResponse("/setup", status_code=303)

            if not display_name:
                set_flash(
                    request,
                    "Display name is required.",
                    "error",
                )
                return RedirectResponse("/setup", status_code=303)

            if len(password) < 8:
                set_flash(
                    request,
                    "Password must contain at least 8 characters.",
                    "error",
                )
                return RedirectResponse("/setup", status_code=303)

            if password != confirm_password:
                set_flash(
                    request,
                    "Password confirmation does not match.",
                    "error",
                )
                return RedirectResponse("/setup", status_code=303)

            admin = HRAdminAccount(
                username=username,
                display_name=display_name,
                password_hash=hash_password(password),
                must_change_password=False,
                is_active=True,
            )

            database.add(admin)
            database.flush()

            write_audit(
                database,
                actor_type="SYSTEM_SETUP",
                actor_id=None,
                action="CREATE_INITIAL_HR_ADMIN",
                request=request,
                target_type="HR_ADMIN",
                target_id=admin.id,
                details=f"Initial HR administrator created: {username}",
            )

            try:
                database.commit()
            except IntegrityError:
                database.rollback()
                set_flash(
                    request,
                    "The username already exists.",
                    "error",
                )
                return RedirectResponse("/setup", status_code=303)

        set_flash(
            request,
            "Initial HR Administrator created successfully.",
            "success",
        )
        return RedirectResponse(
            "/admin/login",
            status_code=303,
        )


    @router.get("/admin/login", response_class=HTMLResponse)
    def admin_login_page(request: Request):
        with SessionLocal() as database:
            if admin_count(database) == 0:
                return RedirectResponse(
                    "/setup",
                    status_code=303,
                )

            current_admin = get_current_admin(request, database)
            if current_admin:
                return RedirectResponse(
                    "/admin/change-password"
                    if current_admin.must_change_password
                    else "/admin",
                    status_code=303,
                )

        return templates.TemplateResponse(
            request=request,
            name="admin_login.html",
            context=template_context(request),
        )


    @router.post("/admin/login")
    def admin_login(
        request: Request,
        csrf: str = Form(...),
        username: str = Form(...),
        password: str = Form(...),
    ):
        if not validate_csrf(request, csrf):
            set_flash(request, "Invalid form token.", "error")
            return RedirectResponse(
                "/admin/login",
                status_code=303,
            )

        username = username.strip().lower()

        with SessionLocal() as database:
            admin = database.scalar(
                select(HRAdminAccount).where(
                    func.lower(HRAdminAccount.username) == username
                )
            )

            if admin is None or not admin.is_active:
                set_flash(
                    request,
                    "Invalid username or password.",
                    "error",
                )
                return RedirectResponse(
                    "/admin/login",
                    status_code=303,
                )

            if account_is_locked(admin.locked_until):
                set_flash(
                    request,
                    "Account is temporarily locked. Try again later.",
                    "error",
                )
                return RedirectResponse(
                    "/admin/login",
                    status_code=303,
                )

            if not verify_password(admin.password_hash, password):
                record_failed_login(admin)
                write_audit(
                    database,
                    actor_type="HR_ADMIN",
                    actor_id=admin.id,
                    action="FAILED_LOGIN",
                    request=request,
                )
                database.commit()

                set_flash(
                    request,
                    "Invalid username or password.",
                    "error",
                )
                return RedirectResponse(
                    "/admin/login",
                    status_code=303,
                )

            clear_failed_login(admin)

            if password_needs_rehash(admin.password_hash):
                admin.password_hash = hash_password(password)

            write_audit(
                database,
                actor_type="HR_ADMIN",
                actor_id=admin.id,
                action="LOGIN",
                request=request,
            )
            database.commit()

            request.session.clear()
            request.session["admin_id"] = admin.id
            csrf_token(request)

        return RedirectResponse(
            "/admin/change-password" if admin.must_change_password else "/admin",
            status_code=303,
        )


    @router.get("/admin/change-password", response_class=HTMLResponse)
    def admin_change_password_page(request: Request):
        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", status_code=303)
            return templates.TemplateResponse(
                request=request,
                name="change_password.html",
                context=template_context(
                    request,
                    account=admin,
                    password_action="/admin/change-password",
                    account_name=admin.display_name,
                    forced=bool(admin.must_change_password),
                    staff_password_change=True,
                ),
            )


    @router.post("/admin/change-password")
    def admin_change_password(
        request: Request,
        csrf: str = Form(...),
        current_password: str = Form(...),
        new_password: str = Form(...),
        confirm_password: str = Form(...),
    ):
        if not validate_csrf(request, csrf):
            set_flash(request, "Invalid form token.", "error")
            return RedirectResponse("/admin/change-password", status_code=303)

        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", status_code=303)
            if not verify_password(admin.password_hash, current_password):
                set_flash(request, "Current password is incorrect.", "error")
                return RedirectResponse("/admin/change-password", status_code=303)
            if len(new_password) < 10:
                set_flash(request, "New password must contain at least 10 characters.", "error")
                return RedirectResponse("/admin/change-password", status_code=303)
            if new_password != confirm_password:
                set_flash(request, "New password confirmation does not match.", "error")
                return RedirectResponse("/admin/change-password", status_code=303)
            if verify_password(admin.password_hash, new_password):
                set_flash(request, "The new password must be different.", "error")
                return RedirectResponse("/admin/change-password", status_code=303)

            admin.password_hash = hash_password(new_password)
            admin.must_change_password = False
            clear_failed_login(admin)
            write_audit(
                database,
                actor_type="HR_ADMIN",
                actor_id=admin.id,
                action="CHANGE_OWN_PASSWORD",
                request=request,
                target_type="HR_ADMIN",
                target_id=admin.id,
            )
            database.commit()

        set_flash(request, "Password changed successfully.", "success")
        return RedirectResponse("/admin", status_code=303)


    @router.post("/admin/logout")
    def admin_logout(
        request: Request,
        csrf: str = Form(...),
    ):
        if not validate_csrf(request, csrf):
            return RedirectResponse(
                "/admin",
                status_code=303,
            )

        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin:
                write_audit(
                    database,
                    actor_type="HR_ADMIN",
                    actor_id=admin.id,
                    action="LOGOUT",
                    request=request,
                )
                database.commit()

        request.session.clear()
        return RedirectResponse(
            "/admin/login",
            status_code=303,
        )


    @router.get("/login", response_class=HTMLResponse)
    def freelancer_login_page(request: Request):
        with SessionLocal() as database:
            account = get_current_freelancer_account(
                request,
                database,
            )
            if account:
                if account.must_change_password:
                    return RedirectResponse(
                        "/change-password",
                        status_code=303,
                    )
                return RedirectResponse(
                    "/attendance",
                    status_code=303,
                )

        return templates.TemplateResponse(
            request=request,
            name="freelancer_login.html",
            context=template_context(request),
        )


    @router.post("/login")
    def freelancer_login(
        request: Request,
        csrf: str = Form(...),
        username: str = Form(...),
        password: str = Form(...),
    ):
        if not validate_csrf(request, csrf):
            set_flash(request, "Invalid form token.", "error")
            return RedirectResponse(
                "/login",
                status_code=303,
            )

        username = username.strip().lower()

        with SessionLocal() as database:
            account = database.scalar(
                select(FreelancerAccount)
                .options(joinedload(FreelancerAccount.freelancer))
                .where(
                    func.lower(FreelancerAccount.username) == username
                )
            )

            if (
                account is None
                or not account.is_active
                or not account.freelancer.is_active
            ):
                set_flash(
                    request,
                    "Invalid username or password.",
                    "error",
                )
                return RedirectResponse(
                    "/login",
                    status_code=303,
                )

            if account_is_locked(account.locked_until):
                set_flash(
                    request,
                    "Account is temporarily locked. Try again later.",
                    "error",
                )
                return RedirectResponse(
                    "/login",
                    status_code=303,
                )

            if not verify_password(account.password_hash, password):
                record_failed_login(account)
                write_audit(
                    database,
                    actor_type="FREELANCER",
                    actor_id=account.freelancer_id,
                    action="FAILED_LOGIN",
                    request=request,
                )
                database.commit()

                set_flash(
                    request,
                    "Invalid username or password.",
                    "error",
                )
                return RedirectResponse(
                    "/login",
                    status_code=303,
                )

            clear_failed_login(account)

            if password_needs_rehash(account.password_hash):
                account.password_hash = hash_password(password)

            write_audit(
                database,
                actor_type="FREELANCER",
                actor_id=account.freelancer_id,
                action="LOGIN",
                request=request,
            )
            database.commit()

            request.session.clear()
            request.session["freelancer_account_id"] = account.id
            csrf_token(request)

            if account.must_change_password:
                return RedirectResponse(
                    "/change-password",
                    status_code=303,
                )

            has_unread_reminders = unread_reminder_count(
                database,
                account.freelancer_id,
            ) > 0

        return RedirectResponse(
            "/reminders?login=1" if has_unread_reminders else "/attendance",
            status_code=303,
        )


    @router.get("/change-password", response_class=HTMLResponse)
    def change_password_page(request: Request):
        with SessionLocal() as database:
            account = get_current_freelancer_account(
                request,
                database,
            )
            if account is None:
                return RedirectResponse(
                    "/login",
                    status_code=303,
                )

            return templates.TemplateResponse(
                request=request,
                name="change_password.html",
                context=template_context(
                    request,
                    account=account,
                    password_action="/change-password",
                    account_name=account.freelancer.full_name,
                    forced=bool(account.must_change_password),
                    staff_password_change=False,
                ),
            )


    @router.post("/change-password")
    def change_password(
        request: Request,
        csrf: str = Form(...),
        current_password: str = Form(...),
        new_password: str = Form(...),
        confirm_password: str = Form(...),
    ):
        if not validate_csrf(request, csrf):
            set_flash(request, "Invalid form token.", "error")
            return RedirectResponse(
                "/change-password",
                status_code=303,
            )

        with SessionLocal() as database:
            account = get_current_freelancer_account(
                request,
                database,
            )
            if account is None:
                return RedirectResponse(
                    "/login",
                    status_code=303,
                )

            if not verify_password(
                account.password_hash,
                current_password,
            ):
                set_flash(
                    request,
                    "Current password is incorrect.",
                    "error",
                )
                return RedirectResponse(
                    "/change-password",
                    status_code=303,
                )

            if len(new_password) < 8:
                set_flash(
                    request,
                    "New password must contain at least 8 characters.",
                    "error",
                )
                return RedirectResponse(
                    "/change-password",
                    status_code=303,
                )

            if new_password != confirm_password:
                set_flash(
                    request,
                    "New password confirmation does not match.",
                    "error",
                )
                return RedirectResponse(
                    "/change-password",
                    status_code=303,
                )

            if verify_password(
                account.password_hash,
                new_password,
            ):
                set_flash(
                    request,
                    "The new password must be different.",
                    "error",
                )
                return RedirectResponse(
                    "/change-password",
                    status_code=303,
                )

            account.password_hash = hash_password(new_password)
            account.must_change_password = False

            write_audit(
                database,
                actor_type="FREELANCER",
                actor_id=account.freelancer_id,
                action="CHANGE_PASSWORD",
                request=request,
            )
            database.commit()
            has_unread_reminders = unread_reminder_count(
                database,
                account.freelancer_id,
            ) > 0

        set_flash(
            request,
            "Password changed successfully.",
            "success",
        )
        return RedirectResponse(
            "/reminders?login=1" if has_unread_reminders else "/attendance",
            status_code=303,
        )


    @router.post("/logout")
    def freelancer_logout(
        request: Request,
        csrf: str = Form(...),
    ):
        if not validate_csrf(request, csrf):
            return RedirectResponse(
                "/attendance",
                status_code=303,
            )

        with SessionLocal() as database:
            account = get_current_freelancer_account(
                request,
                database,
            )
            if account:
                write_audit(
                    database,
                    actor_type="FREELANCER",
                    actor_id=account.freelancer_id,
                    action="LOGOUT",
                    request=request,
                )
                database.commit()

        request.session.clear()
        return RedirectResponse(
            "/login",
            status_code=303,
        )

    return router
