"""Overtime and compensatory-leave HTTP controllers.

Milestone 16 moves planned/actual overtime rules into OvertimeService.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.services.overtime_service import OvertimeService, OvertimeServiceDependencies


def create_overtime_router(legacy_namespace: dict[str, object]) -> APIRouter:
    globals().update(legacy_namespace)
    overtime_router = APIRouter(tags=["Overtime & Comp Leave"])
    globals()["router"] = overtime_router
    return overtime_router


def _service(namespace: dict[str, object]) -> OvertimeService:
    return OvertimeService(OvertimeServiceDependencies(
        month_is_locked=namespace["month_is_locked"],
        local_time_to_utc=namespace["local_time_to_utc"],
        get_policy=namespace["get_policy"],
        get_daily_attendance=namespace["get_daily_attendance"],
        invalidate_dtr=namespace["invalidate_dtr"],
        utc_now=namespace["utc_now"],
        approve_overtime_claim=namespace["approve_overtime_claim"],
        reject_overtime_claim=namespace["reject_overtime_claim"],
        write_audit=namespace["write_audit"],
    ))


def configure_overtime_routes(legacy_namespace: dict[str, object]) -> APIRouter:
    router = create_overtime_router(legacy_namespace)
    service = _service(legacy_namespace)

    @router.get("/overtime", response_class=HTMLResponse)
    def freelancer_overtime(request: Request, month: str = ""):
        selected_month = month if parse_month_key(month) else current_month_key()
        first, next_month = parse_month_key(selected_month)
        with SessionLocal() as database:
            account = get_current_freelancer_account(request, database)
            if account is None:
                return RedirectResponse("/login", 303)
            freelancer = database.get(Freelancer, account.freelancer_id)
            claims = list(database.scalars(select(OvertimeClaim).where(
                OvertimeClaim.freelancer_id == account.freelancer_id,
                OvertimeClaim.attendance_date >= first,
                OvertimeClaim.attendance_date < next_month,
            ).order_by(OvertimeClaim.attendance_date.desc())).all())
            attendance = {r.attendance_date: r for r in database.scalars(select(DailyAttendance).where(
                DailyAttendance.freelancer_id == account.freelancer_id,
                DailyAttendance.attendance_date >= first,
                DailyAttendance.attendance_date < next_month,
            )).all()}
            balance = comp_balance(database, account.freelancer_id)
            return templates.TemplateResponse(request=request, name="freelancer_overtime.html", context=template_context(
                request,
                account=account,
                freelancer=freelancer,
                claims=claims,
                attendance=attendance,
                selected_month=selected_month,
                balance=balance,
                comp_days=whole_comp_days(balance),
                comp_remainder=comp_remainder_minutes(balance),
                policy=get_policy(database),
                month_locked=month_is_locked(database, selected_month),
                utc_to_time_input=utc_to_time_input,
                format_local_datetime=format_local_datetime,
            ))

    @router.post("/overtime/submit")
    def submit_overtime_plan(
        request: Request,
        csrf: str = Form(...),
        attendance_date: str = Form(...),
        planned_start: str = Form(...),
        planned_end: str = Form(...),
        work_description: str = Form(...),
    ):
        fallback = f"/overtime?month={attendance_date[:7]}"
        if not validate_csrf(request, csrf):
            return RedirectResponse(fallback, 303)
        with SessionLocal() as database:
            account = get_current_freelancer_account(request, database)
            if account is None:
                return RedirectResponse("/login", 303)
            result = service.submit_plan(
                database,
                freelancer_id=account.freelancer_id,
                attendance_date=attendance_date,
                planned_start=planned_start,
                planned_end=planned_end,
                work_description=work_description,
            )
        set_flash(request, result.message_key, "success" if result.ok else "error")
        month = result.redirect_month or attendance_date[:7]
        return RedirectResponse(f"/overtime?month={month}" if month else "/overtime", 303)

    @router.post("/overtime/{claim_id}/finalize")
    def finalize_overtime_claim(
        claim_id: int,
        request: Request,
        csrf: str = Form(...),
        claimed_time_out: str = Form(""),
        missing_time_out_reason: str = Form(""),
    ):
        if not validate_csrf(request, csrf):
            return RedirectResponse("/overtime", 303)
        with SessionLocal() as database:
            account = get_current_freelancer_account(request, database)
            if account is None:
                return RedirectResponse("/login", 303)
            result = service.finalize(
                database,
                claim_id=claim_id,
                freelancer_id=account.freelancer_id,
                claimed_time_out=claimed_time_out,
                missing_time_out_reason=missing_time_out_reason,
            )
        set_flash(request, result.message_key, "success" if result.ok else "error")
        target = f"/overtime?month={result.redirect_month}" if result.redirect_month else "/overtime"
        return RedirectResponse(target, 303)

    @router.get("/admin/overtime", response_class=HTMLResponse)
    def admin_overtime(request: Request, month: str = "", status: str = "PENDING"):
        selected_month = month if parse_month_key(month) else current_month_key()
        first, next_month = parse_month_key(selected_month)
        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", 303)
            query = select(OvertimeClaim).where(
                OvertimeClaim.attendance_date >= first,
                OvertimeClaim.attendance_date < next_month,
            )
            pending_states = ["PENDING_PLAN", "PENDING_FINAL", "PENDING_FINAL_MISSING", "PENDING"]
            if status == "PENDING":
                query = query.where(OvertimeClaim.status.in_(pending_states))
            elif status and status != "ALL":
                query = query.where(OvertimeClaim.status == status)
            claims = list(database.scalars(query.order_by(OvertimeClaim.attendance_date, OvertimeClaim.id)).all())
            freelancers = {f.id: f for f in database.scalars(select(Freelancer)).all()}
            attendance = {(r.freelancer_id, r.attendance_date): r for r in database.scalars(select(DailyAttendance).where(
                DailyAttendance.attendance_date >= first,
                DailyAttendance.attendance_date < next_month,
            )).all()}
            return templates.TemplateResponse(request=request, name="admin_overtime.html", context=template_context(
                request,
                admin=admin,
                claims=claims,
                freelancers=freelancers,
                attendance=attendance,
                selected_month=selected_month,
                selected_status=status,
                policy=get_policy(database),
                utc_to_time_input=utc_to_time_input,
                format_local_datetime=format_local_datetime,
            ))

    @router.post("/admin/overtime/{claim_id}/review")
    def review_overtime_claim(
        claim_id: int,
        request: Request,
        csrf: str = Form(...),
        decision: str = Form(...),
        approved_minutes: str = Form("0"),
        approved_time_out: str = Form(""),
        reason: str = Form(...),
    ):
        if not validate_csrf(request, csrf):
            return RedirectResponse("/admin/overtime", 303)
        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", 303)
            result = service.review(
                database,
                claim_id=claim_id,
                admin_id=admin.id,
                decision=decision,
                approved_minutes=approved_minutes,
                approved_time_out=approved_time_out,
                reason=reason,
                audit_request=request,
            )
        set_flash(request, result.message_key, "success" if result.ok else "error")
        target = (
            f"/admin/overtime?month={result.redirect_month}"
            if result.redirect_month else "/admin/overtime"
        )
        return RedirectResponse(target, 303)

    return router
