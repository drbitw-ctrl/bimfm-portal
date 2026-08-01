"""BIMFM Portal v2 administration routes.

Extracted from the verified legacy application without changing route behavior.
Dependencies are injected during application startup as a compatibility bridge.
"""
from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.auth.permissions import Permission, has_permission, normalize_role
from app.models import (
    AttendanceCalculation,
    AttendanceCorrection,
    AttendanceEvent,
    CompLeaveTransaction,
    DailyAttendance,
    DailyTask,
    DTRDailyLine,
    Freelancer,
    FreelancerAccount,
    HRAdminAccount,
    LeaveRecord,
    LeaveRequest,
    MonthlyCompLeaveBalance,
    MonthlyDTR,
    OvertimeClaim,
    PayrollMonthSummary,
    PortalProjectMember,
    PortalTaskAssignment,
    PortalTaskUpdate,
    ProjectMember,
    TaskMonthReview,
)


def _staff_can_manage(account) -> bool:
    return bool(
        account
        and has_permission(
            normalize_role(getattr(account, "role", "")),
            Permission.STAFF_MANAGE,
        )
    )


def _freelancer_delete_summary(database, freelancer_id: int) -> dict[str, object]:
    """Return protected dependency counts for safe test-account deletion.

    A real member with operational history must be disabled instead of erased.
    Only empty/testing profiles can be permanently removed.
    """
    direct_models = (
        ("Attendance events", AttendanceEvent),
        ("Daily attendance", DailyAttendance),
        ("Attendance corrections", AttendanceCorrection),
        ("Attendance calculations", AttendanceCalculation),
        ("Leave records", LeaveRecord),
        ("Leave requests", LeaveRequest),
        ("Compensatory leave ledger", CompLeaveTransaction),
        ("Monthly comp balances", MonthlyCompLeaveBalance),
        ("Monthly DTR records", MonthlyDTR),
        ("DTR daily lines", DTRDailyLine),
        ("Daily task reports", DailyTask),
        ("Task month reviews", TaskMonthReview),
        ("Overtime claims", OvertimeClaim),
        ("Payroll summaries", PayrollMonthSummary),
        ("Project memberships", PortalProjectMember),
        ("Task assignments", PortalTaskAssignment),
        ("Task updates", PortalTaskUpdate),
    )
    counts: list[dict[str, object]] = []
    total = 0
    for label, model in direct_models:
        count = int(
            database.scalar(
                select(func.count(model.id)).where(
                    model.freelancer_id == freelancer_id
                )
            )
            or 0
        )
        if count:
            counts.append({"label": label, "count": count})
            total += count

    directory_count = int(
        database.scalar(
            select(func.count(ProjectMember.id)).where(
                ProjectMember.source_freelancer_id.is_not(None),
                (ProjectMember.freelancer_id == freelancer_id)
                | (ProjectMember.source_freelancer_id == freelancer_id),
            )
        )
        or 0
    )
    if directory_count:
        counts.append({"label": "Project-member directory links", "count": directory_count})
        total += directory_count

    return {
        "blocked": total > 0,
        "total": total,
        "items": counts,
    }


def configure_administration_routes(legacy_namespace: dict[str, object]) -> APIRouter:
    globals().update(legacy_namespace)
    router = APIRouter(tags=["Administration"])
    globals()["router"] = router

    @router.get("/admin", response_class=HTMLResponse)
    def admin_dashboard(request: Request, access: str = ""):
        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse(
                    "/admin/login",
                    status_code=303,
                )

            if access == "readonly" and str(getattr(admin, "role", "ADMIN")).upper() in {"FINANCE", "SUPERVISOR"}:
                role_label = (
                    "Supervisor"
                    if str(getattr(admin, "role", "ADMIN")).upper() == "SUPERVISOR"
                    else "Finance"
                )
                set_flash(
                    request,
                    f"{role_label} access is read-only. Operational changes require an Administrator account.",
                    "info",
                )

            hr_freelancers = hr_freelancer_choices(database)
            freelancer_count = len(hr_freelancers)
            active_freelancer_count = sum(
                1 for freelancer in hr_freelancers if freelancer.is_active
            )
            today_rows = []
            for freelancer in hr_freelancers:
                local_date = current_attendance_date(freelancer.timezone_name)
                record = get_daily_attendance(
                    database,
                    freelancer.id,
                    local_date,
                )
                today_rows.append(
                    build_admin_attendance_row(
                        freelancer,
                        record,
                        local_date,
                    )
                )

            today_complete = sum(
                row["status"] == "Complete" for row in today_rows
            )
            today_working = sum(
                row["status"] == "Currently Working" for row in today_rows
            )
            today_no_record = sum(
                row["status"] == "No Record" for row in today_rows
            )

            account_count = int(
                database.scalar(
                    select(func.count(FreelancerAccount.id))
                )
                or 0
            )

            pending_leave_count = int(
                database.scalar(
                    select(func.count(LeaveRequest.id)).where(
                        LeaveRequest.status == "PENDING"
                    )
                )
                or 0
            )
            pending_overtime_count = int(
                database.scalar(
                    select(func.count(OvertimeClaim.id)).where(
                        OvertimeClaim.status == "PENDING"
                    )
                )
                or 0
            )
            project_health = project_data_health(database)
            active_task_count = project_health.active_task_count
            today = date.today()
            overdue_task_count = int(
                database.scalar(
                    select(func.count(PortalTask.id)).where(
                        PortalTask.status.notin_(("COMPLETED", "CANCELLED")),
                        PortalTask.due_date.is_not(None),
                        PortalTask.due_date < today,
                    )
                )
                or 0
            )

            task_counts = active_task_counts_by_freelancer(database)
            workforce_rows = []
            for row in today_rows:
                freelancer_id = int(row["freelancer_id"])
                workforce_rows.append(
                    {
                        **row,
                        "active_tasks": task_counts.get(freelancer_id, 0),
                    }
                )
            workforce_rows.sort(
                key=lambda row: (
                    row["status"] == "No Record",
                    row["status"] == "Currently Working",
                    row["name"].lower(),
                ),
                reverse=True,
            )

            admin_names = admin_name_map(database)
            recent_activity = []
            for item in database.scalars(
                select(AuditLog).order_by(AuditLog.created_at.desc()).limit(8)
            ).all():
                actor_name = (
                    admin_names.get(int(item.actor_id), "HR Administrator")
                    if item.actor_type == "HR_ADMIN" and item.actor_id
                    else item.actor_type.replace("_", " ").title()
                )
                recent_activity.append(
                    {
                        "action": item.action.replace("_", " ").title(),
                        "details": item.details or "HR record updated.",
                        "actor": actor_name,
                        "time": format_local_datetime(item.created_at, DEFAULT_TIMEZONE),
                    }
                )

            project_team_rows = team_assignment_rows(database)
            unassigned_project_members = sum(
                row["assignment_status"] == "No project assignment"
                for row in project_team_rows
            )
            team_available_count = sum(
                int(row["active_task_count"]) == 0
                for row in project_team_rows
            )
            team_assigned_count = sum(
                int(row["active_task_count"]) > 0
                for row in project_team_rows
            )
            team_with_overdue_count = sum(
                int(row["overdue_task_count"]) > 0
                for row in project_team_rows
            )
            attendance_recorded_count = today_complete + today_working

            return templates.TemplateResponse(
                request=request,
                name="admin_dashboard.html",
                context=template_context(
                    request,
                    admin=admin,
                    freelancer_count=freelancer_count,
                    active_freelancer_count=active_freelancer_count,
                    account_count=account_count,
                    today_complete=today_complete,
                    today_working=today_working,
                    today_no_record=today_no_record,
                    pending_leave_count=pending_leave_count,
                    pending_overtime_count=pending_overtime_count,
                    pending_action_count=pending_leave_count + pending_overtime_count,
                    active_task_count=active_task_count,
                    overdue_task_count=overdue_task_count,
                    workforce_rows=workforce_rows[:8],
                    recent_activity=recent_activity,
                    schedule=get_active_schedule(database),
                    project_count=project_health.project_count,
                    assigned_project_members=project_health.assigned_member_count,
                    unassigned_project_members=unassigned_project_members,
                    projects_without_members=project_health.projects_without_members,
                    active_tasks_without_assignees=project_health.active_tasks_without_assignees,
                    team_available_count=team_available_count,
                    team_assigned_count=team_assigned_count,
                    team_with_overdue_count=team_with_overdue_count,
                    attendance_recorded_count=attendance_recorded_count,
                ),
            )

    @router.get("/admin/staff-accounts", response_class=HTMLResponse)
    def staff_accounts_page(request: Request):
        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", status_code=303)
            if str(getattr(admin, "role", "ADMIN")).upper() != "ADMIN":
                return RedirectResponse("/admin?access=readonly", status_code=303)
            accounts = list(database.scalars(select(HRAdminAccount).order_by(HRAdminAccount.display_name)).all())
            return templates.TemplateResponse(
                request=request, name="admin_staff_accounts.html",
                context=template_context(request, admin=admin, accounts=accounts),
            )

    @router.post("/admin/staff-accounts/new")
    def create_staff_account(
        request: Request, csrf: str = Form(...), username: str = Form(...),
        display_name: str = Form(...), role: str = Form(...), password: str = Form(...),
    ):
        if not validate_csrf(request, csrf):
            set_flash(request, "Invalid form token.", "error")
            return RedirectResponse("/admin/staff-accounts", status_code=303)
        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", status_code=303)
            if str(getattr(admin, "role", "ADMIN")).upper() != "ADMIN":
                return RedirectResponse("/admin?access=readonly", status_code=303)
            clean_username = username.strip().lower()
            clean_name = display_name.strip()
            clean_role = role.strip().upper()
            if clean_role not in {"ADMIN", "SUPERVISOR", "FINANCE"}:
                set_flash(
                    request,
                    "Choose Administrator, Read-only Supervisor, or Finance Head.",
                    "error",
                )
                return RedirectResponse("/admin/staff-accounts", status_code=303)
            if not USERNAME_PATTERN.fullmatch(clean_username) or not clean_name or len(password) < 10:
                set_flash(request, "Use a valid username, display name, and password of at least 10 characters.", "error")
                return RedirectResponse("/admin/staff-accounts", status_code=303)
            if database.scalar(select(HRAdminAccount).where(func.lower(HRAdminAccount.username) == clean_username)):
                set_flash(request, "That username already exists.", "error")
                return RedirectResponse("/admin/staff-accounts", status_code=303)
            account = HRAdminAccount(username=clean_username, display_name=clean_name, role=clean_role, password_hash=hash_password(password), is_active=True)
            database.add(account)
            database.flush()
            write_audit(database, actor_type="HR_ADMIN", actor_id=admin.id, action="CREATE_STAFF_ACCOUNT", request=request, target_type="HR_ADMIN", target_id=account.id, details=f"Created {clean_role} account: {clean_username}")
            database.commit()
        set_flash(request, "Staff account created successfully.", "success")
        return RedirectResponse("/admin/staff-accounts", status_code=303)

    @router.post("/admin/staff-accounts/{account_id}/toggle")
    def toggle_staff_account(request: Request, account_id: int, csrf: str = Form(...)):
        if not validate_csrf(request, csrf):
            return RedirectResponse("/admin/staff-accounts", status_code=303)
        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", status_code=303)
            if str(getattr(admin, "role", "ADMIN")).upper() != "ADMIN":
                return RedirectResponse("/admin?access=readonly", status_code=303)
            target = database.get(HRAdminAccount, account_id)
            if target is None:
                set_flash(request, "Account not found.", "error")
            elif target.id == admin.id:
                set_flash(request, "You cannot disable your own signed-in account.", "error")
            else:
                target.is_active = not target.is_active
                write_audit(database, actor_type="HR_ADMIN", actor_id=admin.id, action="TOGGLE_STAFF_ACCOUNT", request=request, target_type="HR_ADMIN", target_id=target.id, details=f"Active={target.is_active}")
                database.commit()
                set_flash(request, "Staff account status updated.", "success")
        return RedirectResponse("/admin/staff-accounts", status_code=303)

    @router.get("/admin/freelancers", response_class=HTMLResponse)
    def admin_freelancers(request: Request):
        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse(
                    "/admin/login",
                    status_code=303,
                )
            if not _staff_can_manage(admin):
                return RedirectResponse("/admin?access=readonly", status_code=303)

            hr_ids = [row.id for row in hr_freelancer_choices(database)]
            freelancers = list(
                database.scalars(
                    select(Freelancer)
                    .options(joinedload(Freelancer.account))
                    .where(Freelancer.id.in_(hr_ids))
                    .order_by(Freelancer.full_name)
                )
                .unique()
                .all()
            ) if hr_ids else []

            return templates.TemplateResponse(
                request=request,
                name="admin_freelancers.html",
                context=template_context(
                    request,
                    admin=admin,
                    freelancers=freelancers,
                    deletion_status={
                        freelancer.id: _freelancer_delete_summary(
                            database, freelancer.id
                        )
                        for freelancer in freelancers
                    },
                ),
            )

    @router.get(
        "/admin/freelancers/new",
        response_class=HTMLResponse,
    )
    def new_freelancer_page(request: Request):
        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", status_code=303)
            if not _staff_can_manage(admin):
                return RedirectResponse("/admin?access=readonly", status_code=303)
            return templates.TemplateResponse(
                request=request,
                name="admin_new_freelancer.html",
                context=template_context(
                    request,
                    admin=admin,
                    default_timezone=DEFAULT_TIMEZONE,
                ),
            )

    @router.post("/admin/freelancers/new")
    def create_freelancer(
        request: Request,
        csrf: str = Form(...),
        freelancer_code: str = Form(...),
        full_name: str = Form(...),
        email: str = Form(""),
        timezone_name: str = Form(DEFAULT_TIMEZONE),
        username: str = Form(...),
        temporary_password: str = Form(...),
        confirm_password: str = Form(...),
    ):
        form_redirect = "/admin/freelancers/new"

        if not validate_csrf(request, csrf):
            set_flash(request, "Invalid form token.", "error")
            return RedirectResponse(
                form_redirect,
                status_code=303,
            )

        freelancer_code = freelancer_code.strip().upper()
        full_name = full_name.strip()
        email = email.strip().lower() or None
        timezone_name = timezone_name.strip() or DEFAULT_TIMEZONE
        username = username.strip().lower()

        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse(
                    "/admin/login",
                    status_code=303,
                )
            if not _staff_can_manage(admin):
                return RedirectResponse("/admin?access=readonly", status_code=303)

            if not freelancer_code or len(freelancer_code) > 30:
                set_flash(
                    request,
                    "Freelancer code is required and must be 30 "
                    "characters or fewer.",
                    "error",
                )
                return RedirectResponse(
                    "/admin/freelancers/new",
                    status_code=303,
                )

            if not full_name:
                set_flash(
                    request,
                    "Full name is required.",
                    "error",
                )
                return RedirectResponse(
                    "/admin/freelancers/new",
                    status_code=303,
                )

            if not USERNAME_PATTERN.fullmatch(username):
                set_flash(
                    request,
                    "Username must be 3-80 characters and use only "
                    "letters, numbers, period, underscore, or hyphen.",
                    "error",
                )
                return RedirectResponse(
                    "/admin/freelancers/new",
                    status_code=303,
                )

            if len(temporary_password) < 8:
                set_flash(
                    request,
                    "Temporary password must contain at least 8 characters.",
                    "error",
                )
                return RedirectResponse(
                    "/admin/freelancers/new",
                    status_code=303,
                )

            if temporary_password != confirm_password:
                set_flash(
                    request,
                    "Password confirmation does not match.",
                    "error",
                )
                return RedirectResponse(
                    "/admin/freelancers/new",
                    status_code=303,
                )

            freelancer = Freelancer(
                freelancer_code=freelancer_code,
                full_name=full_name,
                email=email,
                timezone_name=timezone_name,
                is_active=True,
            )
            database.add(freelancer)
            database.flush()

            account = FreelancerAccount(
                freelancer_id=freelancer.id,
                username=username,
                password_hash=hash_password(temporary_password),
                must_change_password=True,
                is_active=True,
            )
            database.add(account)
            database.flush()

            ensure_hr_project_members(
                database,
                admin_id=admin.id,
                freelancer_ids={int(freelancer.id)},
            )

            write_audit(
                database,
                actor_type="HR_ADMIN",
                actor_id=admin.id,
                action="CREATE_FREELANCER_ACCOUNT",
                request=request,
                target_type="FREELANCER",
                target_id=freelancer.id,
                details=(
                    f"Created freelancer {freelancer_code} with username {username}."
                ),
            )

            try:
                database.commit()
            except IntegrityError:
                database.rollback()
                set_flash(
                    request,
                    "Freelancer code, email, or username already exists.",
                    "error",
                )
                return RedirectResponse(
                    "/admin/freelancers/new",
                    status_code=303,
                )

        set_flash(
            request,
            "Freelancer account created successfully.",
            "success",
        )
        return RedirectResponse(
            "/admin/freelancers",
            status_code=303,
        )

    @router.post("/admin/freelancers/{freelancer_id}/toggle")
    def toggle_freelancer(
        freelancer_id: int,
        request: Request,
        csrf: str = Form(...),
    ):
        if not validate_csrf(request, csrf):
            set_flash(request, "Invalid form token.", "error")
            return RedirectResponse(
                "/admin/freelancers",
                status_code=303,
            )

        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse(
                    "/admin/login",
                    status_code=303,
                )
            if not _staff_can_manage(admin):
                return RedirectResponse("/admin?access=readonly", status_code=303)

            freelancer = database.scalar(
                select(Freelancer)
                .options(joinedload(Freelancer.account))
                .where(Freelancer.id == freelancer_id)
            )

            if freelancer is None:
                set_flash(
                    request,
                    "Freelancer was not found.",
                    "error",
                )
                return RedirectResponse(
                    "/admin/freelancers",
                    status_code=303,
                )

            new_status = not freelancer.is_active
            freelancer.is_active = new_status

            if freelancer.account is not None:
                freelancer.account.is_active = new_status

            for member in database.scalars(
                select(ProjectMember).where(
                    ProjectMember.freelancer_id == freelancer.id,
                    ProjectMember.source_freelancer_id.is_(None),
                )
            ).all():
                member.is_active = new_status

            write_audit(
                database,
                actor_type="HR_ADMIN",
                actor_id=admin.id,
                action=(
                    "ENABLE_FREELANCER"
                    if new_status
                    else "DISABLE_FREELANCER"
                ),
                request=request,
                target_type="FREELANCER",
                target_id=freelancer.id,
            )
            database.commit()

        set_flash(
            request,
            "Freelancer account status updated.",
            "success",
        )
        return RedirectResponse(
            "/admin/freelancers",
            status_code=303,
        )

    @router.get(
        "/admin/freelancers/{freelancer_id}/reset-password",
        response_class=HTMLResponse,
    )
    def reset_freelancer_password_page(
        freelancer_id: int,
        request: Request,
    ):
        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", status_code=303)
            if not _staff_can_manage(admin):
                return RedirectResponse("/admin?access=readonly", status_code=303)

            freelancer = database.scalar(
                select(Freelancer)
                .options(joinedload(Freelancer.account))
                .where(Freelancer.id == freelancer_id)
            )
            if freelancer is None:
                set_flash(request, "Freelancer was not found.", "error")
                return RedirectResponse("/admin/freelancers", status_code=303)
            if freelancer.account is None:
                set_flash(
                    request,
                    "This freelancer does not have a login account to reset.",
                    "error",
                )
                return RedirectResponse("/admin/freelancers", status_code=303)

            return templates.TemplateResponse(
                request=request,
                name="admin_reset_freelancer_password.html",
                context=template_context(
                    request,
                    admin=admin,
                    freelancer=freelancer,
                ),
            )

    @router.post("/admin/freelancers/{freelancer_id}/reset-password")
    def reset_freelancer_password(
        freelancer_id: int,
        request: Request,
        csrf: str = Form(...),
        temporary_password: str = Form(...),
        confirm_password: str = Form(...),
    ):
        redirect_path = f"/admin/freelancers/{freelancer_id}/reset-password"
        if not validate_csrf(request, csrf):
            set_flash(request, "Invalid form token.", "error")
            return RedirectResponse(redirect_path, status_code=303)

        if len(temporary_password) < 10:
            set_flash(
                request,
                "Temporary password must contain at least 10 characters.",
                "error",
            )
            return RedirectResponse(redirect_path, status_code=303)
        if temporary_password != confirm_password:
            set_flash(request, "Password confirmation does not match.", "error")
            return RedirectResponse(redirect_path, status_code=303)

        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", status_code=303)
            if not _staff_can_manage(admin):
                return RedirectResponse("/admin?access=readonly", status_code=303)

            freelancer = database.scalar(
                select(Freelancer)
                .options(joinedload(Freelancer.account))
                .where(Freelancer.id == freelancer_id)
            )
            if freelancer is None or freelancer.account is None:
                set_flash(request, "Freelancer login account was not found.", "error")
                return RedirectResponse("/admin/freelancers", status_code=303)

            freelancer.account.password_hash = hash_password(temporary_password)
            freelancer.account.must_change_password = True
            freelancer.account.failed_login_count = 0
            freelancer.account.locked_until = None
            freelancer.account.updated_at = utc_now()
            write_audit(
                database,
                actor_type="HR_ADMIN",
                actor_id=admin.id,
                action="RESET_FREELANCER_PASSWORD",
                request=request,
                target_type="FREELANCER",
                target_id=freelancer.id,
                details=(
                    f"Reset password for {freelancer.full_name}; "
                    "forced password change on next login."
                ),
            )
            database.commit()

        set_flash(
            request,
            "Temporary password saved. The member must change it at the next login.",
            "success",
        )
        return RedirectResponse("/admin/freelancers", status_code=303)

    @router.get(
        "/admin/freelancers/{freelancer_id}/delete",
        response_class=HTMLResponse,
    )
    def delete_freelancer_page(
        freelancer_id: int,
        request: Request,
    ):
        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", status_code=303)
            if not _staff_can_manage(admin):
                return RedirectResponse("/admin?access=readonly", status_code=303)

            freelancer = database.scalar(
                select(Freelancer)
                .options(joinedload(Freelancer.account))
                .where(Freelancer.id == freelancer_id)
            )
            if freelancer is None:
                set_flash(request, "Freelancer was not found.", "error")
                return RedirectResponse("/admin/freelancers", status_code=303)

            return templates.TemplateResponse(
                request=request,
                name="admin_delete_freelancer.html",
                context=template_context(
                    request,
                    admin=admin,
                    freelancer=freelancer,
                    deletion=_freelancer_delete_summary(
                        database, freelancer.id
                    ),
                ),
            )

    @router.post("/admin/freelancers/{freelancer_id}/delete")
    def delete_freelancer(
        freelancer_id: int,
        request: Request,
        csrf: str = Form(...),
        confirm_name: str = Form(...),
    ):
        redirect_path = f"/admin/freelancers/{freelancer_id}/delete"
        if not validate_csrf(request, csrf):
            set_flash(request, "Invalid form token.", "error")
            return RedirectResponse(redirect_path, status_code=303)

        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", status_code=303)
            if not _staff_can_manage(admin):
                return RedirectResponse("/admin?access=readonly", status_code=303)

            freelancer = database.scalar(
                select(Freelancer)
                .options(joinedload(Freelancer.account))
                .where(Freelancer.id == freelancer_id)
            )
            if freelancer is None:
                set_flash(request, "Freelancer was not found.", "error")
                return RedirectResponse("/admin/freelancers", status_code=303)

            deletion = _freelancer_delete_summary(database, freelancer.id)
            if deletion["blocked"]:
                set_flash(
                    request,
                    "This member has operational history or project links and cannot be deleted. Disable the account instead.",
                    "error",
                )
                return RedirectResponse(redirect_path, status_code=303)

            if confirm_name.strip().casefold() != freelancer.full_name.strip().casefold():
                set_flash(
                    request,
                    "Type the member's complete name exactly to confirm deletion.",
                    "error",
                )
                return RedirectResponse(redirect_path, status_code=303)

            deleted_name = freelancer.full_name
            deleted_code = freelancer.freelancer_code
            target_id = freelancer.id
            write_audit(
                database,
                actor_type="HR_ADMIN",
                actor_id=admin.id,
                action="DELETE_UNUSED_TEST_MEMBER",
                request=request,
                target_type="FREELANCER",
                target_id=target_id,
                details=f"Deleted unused member {deleted_name} ({deleted_code}).",
            )
            # Remove the portal-native project-directory entry created for an
            # unused account. Imported source-member rows are protected above.
            for member in database.scalars(
                select(ProjectMember).where(
                    ProjectMember.freelancer_id == freelancer.id,
                    ProjectMember.source_freelancer_id.is_(None),
                )
            ).all():
                database.delete(member)

            # The Freelancer.account relationship is configured with
            # delete-orphan cascade, so deleting the member removes the login
            # account in the same transaction without issuing duplicate deletes.
            database.delete(freelancer)
            database.commit()

        set_flash(
            request,
            f"Unused member {deleted_name} was permanently deleted.",
            "success",
        )
        return RedirectResponse("/admin/freelancers", status_code=303)

    @router.get("/admin/settings/work-schedule", response_class=HTMLResponse)
    def work_schedule_page(request: Request):
        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", status_code=303)

            schedule = get_active_schedule(database)
            return templates.TemplateResponse(
                request=request,
                name="admin_work_schedule.html",
                context=template_context(
                    request,
                    admin=admin,
                    schedule=schedule,
                    workday_names=selected_workday_names(schedule),
                    current_month=current_month_key(DEFAULT_TIMEZONE),
                ),
            )

    @router.post("/admin/settings/work-schedule")
    def update_work_schedule(
        request: Request,
        csrf: str = Form(...),
        name: str = Form(...),
        start_time: str = Form(...),
        end_time: str = Form(...),
        grace_minutes: int = Form(...),
        break_minutes: int = Form(...),
        break_trigger_minutes: int = Form(...),
        monday: Optional[str] = Form(None),
        tuesday: Optional[str] = Form(None),
        wednesday: Optional[str] = Form(None),
        thursday: Optional[str] = Form(None),
        friday: Optional[str] = Form(None),
        saturday: Optional[str] = Form(None),
        sunday: Optional[str] = Form(None),
    ):
        redirect_path = "/admin/settings/work-schedule"
        if not validate_csrf(request, csrf):
            set_flash(request, "Invalid form token.", "error")
            return RedirectResponse(redirect_path, status_code=303)

        name = name.strip()
        try:
            parsed_start = parse_hhmm(start_time)
            parsed_end = parse_hhmm(end_time)
        except ValueError as exc:
            set_flash(request, str(exc), "error")
            return RedirectResponse(redirect_path, status_code=303)

        if not name:
            set_flash(request, "Schedule name is required.", "error")
            return RedirectResponse(redirect_path, status_code=303)
        if parsed_end <= parsed_start:
            set_flash(
                request,
                "End time must be later than start time. Overnight shifts are not supported yet.",
                "error",
            )
            return RedirectResponse(redirect_path, status_code=303)
        if not 0 <= grace_minutes <= 240:
            set_flash(request, "Grace period must be 0-240 minutes.", "error")
            return RedirectResponse(redirect_path, status_code=303)
        if not 0 <= break_minutes <= 240:
            set_flash(request, "Break duration must be 0-240 minutes.", "error")
            return RedirectResponse(redirect_path, status_code=303)
        if not 0 <= break_trigger_minutes <= 1440:
            set_flash(request, "Break trigger must be 0-1440 minutes.", "error")
            return RedirectResponse(redirect_path, status_code=303)

        workday_flags = {
            "monday": bool(monday),
            "tuesday": bool(tuesday),
            "wednesday": bool(wednesday),
            "thursday": bool(thursday),
            "friday": bool(friday),
            "saturday": bool(saturday),
            "sunday": bool(sunday),
        }
        if not any(workday_flags.values()):
            set_flash(request, "Select at least one scheduled workday.", "error")
            return RedirectResponse(redirect_path, status_code=303)

        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", status_code=303)

            schedule = get_active_schedule(database)
            schedule.name = name
            schedule.start_time_text = start_time
            schedule.end_time_text = end_time
            schedule.grace_minutes = grace_minutes
            schedule.break_minutes = break_minutes
            schedule.break_trigger_minutes = break_trigger_minutes
            schedule.updated_by_admin_id = admin.id
            for field_name, enabled in workday_flags.items():
                setattr(schedule, field_name, enabled)

            write_audit(
                database,
                actor_type="HR_ADMIN",
                actor_id=admin.id,
                action="UPDATE_WORK_SCHEDULE",
                request=request,
                target_type="WORK_SCHEDULE",
                target_id=schedule.id,
                details=(
                    f"{name}; {start_time}-{end_time}; grace {grace_minutes}; "
                    f"break {break_minutes} after {break_trigger_minutes} minutes"
                ),
            )
            database.commit()

        set_flash(
            request,
            "Work schedule saved. Use Recalculate Month to apply it to existing open records.",
            "success",
        )
        return RedirectResponse(redirect_path, status_code=303)

    @router.get("/admin/hr/calendar", response_class=HTMLResponse)
    def hr_calendar_page(
        request: Request,
        month: str = "",
        freelancer_id: int = 0,
    ):
        selected_month = month if parse_month_key(month) else current_month_key()
        month_start, next_month = parse_month_key(selected_month)  # type: ignore[misc]

        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", status_code=303)

            freelancers = hr_freelancer_choices(database)
            holidays = list(
                database.scalars(
                    select(Holiday)
                    .where(
                        Holiday.holiday_date >= month_start,
                        Holiday.holiday_date < next_month,
                        Holiday.is_active.is_(True),
                    )
                    .order_by(Holiday.holiday_date)
                ).all()
            )

            leave_query = select(LeaveRecord).where(
                LeaveRecord.leave_date >= month_start,
                LeaveRecord.leave_date < next_month,
            )
            if freelancer_id:
                leave_query = leave_query.where(
                    LeaveRecord.freelancer_id == freelancer_id
                )
            leave_records = list(
                database.scalars(
                    leave_query.order_by(LeaveRecord.leave_date)
                ).all()
            )
            freelancer_map = {row.id: row for row in freelancers}
            leave_rows = [
                {
                    "id": row.id,
                    "date": row.leave_date.strftime("%Y-%m-%d"),
                    "freelancer": freelancer_map.get(row.freelancer_id),
                    "leave_type": dtr_status_label(row.leave_type),
                    "paid": "Yes" if row.is_paid else "No",
                    "notes": row.notes or "",
                }
                for row in leave_records
            ]

            return templates.TemplateResponse(
                request=request,
                name="admin_hr_calendar.html",
                context=template_context(
                    request,
                    admin=admin,
                    selected_month=selected_month,
                    selected_freelancer_id=freelancer_id,
                    freelancers=freelancers,
                    holidays=holidays,
                    leave_rows=leave_rows,
                    month_locked=month_is_locked(database, selected_month),
                ),
            )

    @router.post("/admin/hr/holidays/new")
    def create_holiday(
        request: Request,
        csrf: str = Form(...),
        holiday_date: str = Form(...),
        name: str = Form(...),
        holiday_type: str = Form("COMPANY"),
        is_paid: Optional[str] = Form(None),
    ):
        redirect_path = f"/admin/hr/calendar?month={holiday_date[:7]}"
        if not validate_csrf(request, csrf):
            set_flash(request, "Invalid form token.", "error")
            return RedirectResponse(redirect_path, status_code=303)

        try:
            parsed_date = date.fromisoformat(holiday_date)
        except ValueError:
            set_flash(request, "Invalid holiday date.", "error")
            return RedirectResponse("/admin/hr/calendar", status_code=303)

        name = name.strip()
        holiday_type = holiday_type.strip().upper() or "COMPANY"
        if not name:
            set_flash(request, "Holiday name is required.", "error")
            return RedirectResponse(redirect_path, status_code=303)

        month_key = parsed_date.strftime("%Y-%m")
        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", status_code=303)
            if month_is_locked(database, month_key):
                set_flash(request, "Unlock the attendance month before changing holidays.", "error")
                return RedirectResponse(redirect_path, status_code=303)

            holiday = database.scalar(
                select(Holiday).where(Holiday.holiday_date == parsed_date)
            )
            if holiday is not None and holiday.is_active:
                set_flash(request, "A holiday already exists on that date.", "error")
                return RedirectResponse(redirect_path, status_code=303)
            if holiday is None:
                holiday = Holiday(
                    holiday_date=parsed_date,
                    name=name,
                    holiday_type=holiday_type,
                    is_paid=bool(is_paid),
                    is_active=True,
                    created_by_admin_id=admin.id,
                )
                database.add(holiday)
            else:
                holiday.name = name
                holiday.holiday_type = holiday_type
                holiday.is_paid = bool(is_paid)
                holiday.is_active = True
                holiday.created_by_admin_id = admin.id

            database.execute(
                delete(MonthlyDTR).where(
                    MonthlyDTR.month_key == month_key,
                    MonthlyDTR.status != "FINALIZED",
                )
            )

            write_audit(
                database,
                actor_type="HR_ADMIN",
                actor_id=admin.id,
                action="CREATE_HOLIDAY",
                request=request,
                target_type="HOLIDAY",
                details=f"{parsed_date.isoformat()} {name}",
            )
            database.commit()

        set_flash(request, "Holiday added. Regenerate affected DTRs.", "success")
        return RedirectResponse(redirect_path, status_code=303)

    @router.post("/admin/hr/holidays/{holiday_id}/delete")
    def delete_holiday(
        holiday_id: int,
        request: Request,
        csrf: str = Form(...),
    ):
        if not validate_csrf(request, csrf):
            set_flash(request, "Invalid form token.", "error")
            return RedirectResponse("/admin/hr/calendar", status_code=303)

        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", status_code=303)
            holiday = database.get(Holiday, holiday_id)
            if holiday is None:
                set_flash(request, "Holiday not found.", "error")
                return RedirectResponse("/admin/hr/calendar", status_code=303)
            month_key = holiday.holiday_date.strftime("%Y-%m")
            redirect_path = f"/admin/hr/calendar?month={month_key}"
            if month_is_locked(database, month_key):
                set_flash(request, "Unlock the attendance month before deleting holidays.", "error")
                return RedirectResponse(redirect_path, status_code=303)

            holiday.is_active = False
            database.execute(
                delete(MonthlyDTR).where(
                    MonthlyDTR.month_key == month_key,
                    MonthlyDTR.status != "FINALIZED",
                )
            )
            write_audit(
                database,
                actor_type="HR_ADMIN",
                actor_id=admin.id,
                action="DELETE_HOLIDAY",
                request=request,
                target_type="HOLIDAY",
                target_id=holiday.id,
                details=f"{holiday.holiday_date.isoformat()} {holiday.name}",
            )
            database.commit()

        set_flash(request, "Holiday removed. Regenerate affected DTRs.", "success")
        return RedirectResponse(redirect_path, status_code=303)

    @router.post("/admin/hr/leaves/new")
    def create_leave(
        request: Request,
        csrf: str = Form(...),
        freelancer_id: int = Form(...),
        leave_date: str = Form(...),
        leave_type: str = Form("APPROVED_LEAVE"),
        is_paid: Optional[str] = Form(None),
        notes: str = Form(""),
    ):
        redirect_path = f"/admin/hr/calendar?month={leave_date[:7]}&freelancer_id={freelancer_id}"
        if not validate_csrf(request, csrf):
            set_flash(request, "Invalid form token.", "error")
            return RedirectResponse(redirect_path, status_code=303)

        try:
            parsed_date = date.fromisoformat(leave_date)
        except ValueError:
            set_flash(request, "Invalid leave date.", "error")
            return RedirectResponse("/admin/hr/calendar", status_code=303)

        leave_type = leave_type.strip().upper() or "APPROVED_LEAVE"
        month_key = parsed_date.strftime("%Y-%m")
        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", status_code=303)
            freelancer = database.get(Freelancer, freelancer_id)
            if freelancer is None:
                set_flash(request, "Freelancer not found.", "error")
                return RedirectResponse(redirect_path, status_code=303)
            if month_is_locked(database, month_key):
                set_flash(request, "Unlock the attendance month before changing leave records.", "error")
                return RedirectResponse(redirect_path, status_code=303)

            if leave_type == "COMPENSATORY_LEAVE":
                set_flash(request, "Use Leave Requests for compensatory leave so the balance ledger remains auditable.", "error")
                return RedirectResponse(redirect_path, status_code=303)
            policy = get_policy(database)
            leave = LeaveRecord(
                freelancer_id=freelancer_id,
                leave_date=parsed_date,
                leave_type=leave_type,
                is_paid=bool(is_paid),
                status="APPROVED",
                duration_minutes=policy.standard_leave_day_minutes,
                comp_leave_minutes_used=0,
                notes=notes.strip() or None,
                approved_by_admin_id=admin.id,
            )
            database.add(leave)
            invalidate_dtr(database, freelancer_id, month_key)
            write_audit(
                database,
                actor_type="HR_ADMIN",
                actor_id=admin.id,
                action="CREATE_LEAVE_RECORD",
                request=request,
                target_type="LEAVE_RECORD",
                details=f"{freelancer.freelancer_code} {parsed_date.isoformat()} {leave_type}",
            )
            try:
                database.commit()
            except IntegrityError:
                database.rollback()
                set_flash(request, "A leave record already exists for this freelancer and date.", "error")
                return RedirectResponse(redirect_path, status_code=303)

        set_flash(request, "Leave record added. Regenerate the freelancer DTR.", "success")
        return RedirectResponse(redirect_path, status_code=303)

    @router.post("/admin/hr/leaves/{leave_id}/delete")
    def delete_leave(
        leave_id: int,
        request: Request,
        csrf: str = Form(...),
    ):
        if not validate_csrf(request, csrf):
            set_flash(request, "Invalid form token.", "error")
            return RedirectResponse("/admin/hr/calendar", status_code=303)

        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", status_code=303)
            leave = database.get(LeaveRecord, leave_id)
            if leave is None:
                set_flash(request, "Leave record not found.", "error")
                return RedirectResponse("/admin/hr/calendar", status_code=303)
            month_key = leave.leave_date.strftime("%Y-%m")
            redirect_path = f"/admin/hr/calendar?month={month_key}&freelancer_id={leave.freelancer_id}"
            if month_is_locked(database, month_key):
                set_flash(request, "Unlock the attendance month before deleting leave records.", "error")
                return RedirectResponse(redirect_path, status_code=303)

            if getattr(leave, "comp_leave_minutes_used", 0) > 0:
                set_flash(request, "Compensatory leave cannot be directly deleted because it has a ledger transaction. Use a controlled adjustment workflow.", "error")
                return RedirectResponse(redirect_path, status_code=303)

            invalidate_dtr(database, leave.freelancer_id, month_key)
            write_audit(
                database,
                actor_type="HR_ADMIN",
                actor_id=admin.id,
                action="DELETE_LEAVE_RECORD",
                request=request,
                target_type="LEAVE_RECORD",
                target_id=leave.id,
                details=f"{leave.leave_date.isoformat()} {leave.leave_type}",
            )
            database.delete(leave)
            database.commit()

        set_flash(request, "Leave record removed. Regenerate the freelancer DTR.", "success")
        return RedirectResponse(redirect_path, status_code=303)

    @router.get("/admin/settings/hr-policy", response_class=HTMLResponse)
    def admin_hr_policy(request: Request):
        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", status_code=303)
            policy = get_policy(database)
            return templates.TemplateResponse(
                request=request, name="admin_hr_policy.html",
                context=template_context(request, admin=admin, policy=policy),
            )

    @router.post("/admin/settings/hr-policy")
    def update_hr_policy(
        request: Request, csrf: str = Form(...),
        standard_leave_day_minutes: int = Form(...),
        overtime_minimum_minutes: int = Form(...),
        overtime_rounding_minutes: int = Form(...),
        overtime_to_comp_numerator: int = Form(...),
        overtime_to_comp_denominator: int = Form(...),
        max_approved_overtime_per_day: int = Form(...),
        task_variance_warning_minutes: int = Form(...),
        require_task_for_overtime: Optional[str] = Form(None),
        require_daily_task_for_dtr: Optional[str] = Form(None),
        allow_negative_comp_balance: Optional[str] = Form(None),
    ):
        if not validate_csrf(request, csrf):
            set_flash(request, "Invalid form token.", "error")
            return RedirectResponse("/admin/settings/hr-policy", status_code=303)
        values = [standard_leave_day_minutes, overtime_minimum_minutes,
                  overtime_rounding_minutes, overtime_to_comp_numerator,
                  overtime_to_comp_denominator, max_approved_overtime_per_day,
                  task_variance_warning_minutes]
        if any(v <= 0 for v in values):
            set_flash(request, "All policy numeric values must be positive.", "error")
            return RedirectResponse("/admin/settings/hr-policy", status_code=303)
        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None: return RedirectResponse("/admin/login", status_code=303)
            policy = get_policy(database)
            policy.standard_leave_day_minutes = min(1440, standard_leave_day_minutes)
            policy.overtime_minimum_minutes = min(1440, overtime_minimum_minutes)
            policy.overtime_rounding_minutes = min(1440, overtime_rounding_minutes)
            policy.overtime_to_comp_numerator = min(100, overtime_to_comp_numerator)
            policy.overtime_to_comp_denominator = min(100, overtime_to_comp_denominator)
            policy.max_approved_overtime_per_day = min(1440, max_approved_overtime_per_day)
            policy.task_variance_warning_minutes = min(1440, task_variance_warning_minutes)
            policy.require_task_for_overtime = bool(require_task_for_overtime)
            policy.require_daily_task_for_dtr = bool(require_daily_task_for_dtr)
            policy.allow_negative_comp_balance = bool(allow_negative_comp_balance)
            policy.updated_by_admin_id = admin.id
            database.execute(delete(MonthlyDTR).where(MonthlyDTR.status != "FINALIZED"))
            write_audit(database, actor_type="HR_ADMIN", actor_id=admin.id,
                        action="UPDATE_HR_POLICY", request=request,
                        target_type="HR_POLICY", target_id=policy.id,
                        details="Updated daily-task, overtime, and compensatory-leave rules.")
            database.commit()
        set_flash(request, "HR policy updated. Regenerate affected draft DTRs.", "success")
        return RedirectResponse("/admin/settings/hr-policy", status_code=303)

    return router
