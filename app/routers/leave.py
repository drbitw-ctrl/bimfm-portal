"""Leave-management HTTP controllers.

Milestone 16 moves workflow rules into :mod:`app.services.leave_service`.
This module now handles only HTTP/session concerns and view rendering.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.services.leave_service import LeaveService, LeaveServiceDependencies


def create_leave_router(legacy_namespace: dict[str, object]) -> APIRouter:
    globals().update(legacy_namespace)
    leave_router = APIRouter(tags=["Leave Management"])
    globals()["router"] = leave_router
    return leave_router


def _service(namespace: dict[str, object]) -> LeaveService:
    return LeaveService(LeaveServiceDependencies(
        comp_balance=namespace["comp_balance"],
        whole_comp_days=namespace["whole_comp_days"],
        month_is_locked=namespace["month_is_locked"],
        invalidate_dtr=namespace["invalidate_dtr"],
        approve_leave_request=namespace["approve_leave_request"],
        reject_leave_request=namespace["reject_leave_request"],
        write_audit=namespace["write_audit"],
        comp_leave_day_minutes=namespace["COMP_LEAVE_DAY_MINUTES"],
    ))


def configure_leave_routes(legacy_namespace: dict[str, object]) -> APIRouter:
    router = create_leave_router(legacy_namespace)
    service = _service(legacy_namespace)

    @router.get("/leave", response_class=HTMLResponse)
    def freelancer_leave(request: Request, month: str = ""):
        selected_month = month if parse_month_key(month) else current_month_key()
        first, next_month = parse_month_key(selected_month)
        with SessionLocal() as database:
            account = get_current_freelancer_account(request, database)
            if account is None:
                return RedirectResponse("/login", 303)
            requests = list(database.scalars(select(LeaveRequest).where(
                LeaveRequest.freelancer_id == account.freelancer_id,
                LeaveRequest.leave_date >= first,
                LeaveRequest.leave_date < next_month,
            ).order_by(LeaveRequest.leave_date.desc())).all())
            balance = comp_balance(database, account.freelancer_id)
            return templates.TemplateResponse(request=request, name="freelancer_leave.html", context=template_context(
                request,
                account=account,
                requests=requests,
                selected_month=selected_month,
                balance=balance,
                comp_days=whole_comp_days(balance),
                comp_remainder=comp_remainder_minutes(balance),
                policy=get_policy(database),
                month_locked=month_is_locked(database, selected_month),
            ))

    @router.post("/leave/request")
    def submit_leave_request(
        request: Request,
        csrf: str = Form(...),
        leave_date: str = Form(...),
        leave_type: str = Form(...),
        reason: str = Form(...),
    ):
        fallback = f"/leave?month={leave_date[:7]}"
        if not validate_csrf(request, csrf):
            return RedirectResponse(fallback, 303)
        with SessionLocal() as database:
            account = get_current_freelancer_account(request, database)
            if account is None:
                return RedirectResponse("/login", 303)
            result = service.submit(
                database,
                freelancer_id=account.freelancer_id,
                leave_date=leave_date,
                leave_type=leave_type,
                reason=reason,
            )
        set_flash(request, result.message_key, "success" if result.ok else "error")
        month = result.redirect_month or leave_date[:7]
        return RedirectResponse(f"/leave?month={month}" if month else "/leave", 303)

    @router.post("/leave/{request_id}/cancel")
    def cancel_leave_request(request_id: int, request: Request, csrf: str = Form(...)):
        if not validate_csrf(request, csrf):
            return RedirectResponse("/leave", 303)
        with SessionLocal() as database:
            account = get_current_freelancer_account(request, database)
            if account is None:
                return RedirectResponse("/login", 303)
            result = service.cancel(
                database, request_id=request_id, freelancer_id=account.freelancer_id
            )
        set_flash(request, result.message_key, "success" if result.ok else "error")
        target = f"/leave?month={result.redirect_month}" if result.redirect_month else "/leave"
        return RedirectResponse(target, 303)

    @router.get("/admin/leave-requests", response_class=HTMLResponse)
    def admin_leave_requests(request: Request, month: str = "", status: str = "PENDING"):
        selected_month = month if parse_month_key(month) else current_month_key()
        first, next_month = parse_month_key(selected_month)
        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", 303)
            query = select(LeaveRequest).where(
                LeaveRequest.leave_date >= first, LeaveRequest.leave_date < next_month
            )
            if status and status != "ALL":
                query = query.where(LeaveRequest.status == status)
            rows = list(database.scalars(query.order_by(LeaveRequest.leave_date, LeaveRequest.id)).all())
            freelancers = {f.id: f for f in database.scalars(select(Freelancer)).all()}
            balances = {fid: comp_balance(database, fid) for fid in freelancers}
            return templates.TemplateResponse(request=request, name="admin_leave_requests.html", context=template_context(
                request,
                admin=admin,
                rows=rows,
                freelancers=freelancers,
                balances=balances,
                balance_days={fid: whole_comp_days(minutes) for fid, minutes in balances.items()},
                balance_remainders={fid: comp_remainder_minutes(minutes) for fid, minutes in balances.items()},
                selected_month=selected_month,
                selected_status=status,
                policy=get_policy(database),
            ))

    @router.post("/admin/leave-requests/{request_id}/review")
    def review_leave_request(
        request_id: int,
        request: Request,
        csrf: str = Form(...),
        decision: str = Form(...),
        reason: str = Form(...),
    ):
        if not validate_csrf(request, csrf):
            return RedirectResponse("/admin/leave-requests", 303)
        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", 303)
            result = service.review(
                database,
                request_id=request_id,
                admin_id=admin.id,
                decision=decision,
                reason=reason,
                audit_request=request,
            )
        set_flash(request, result.message_key, "success" if result.ok else "error")
        target = (
            f"/admin/leave-requests?month={result.redirect_month}"
            if result.redirect_month else "/admin/leave-requests"
        )
        return RedirectResponse(target, 303)

    return router
