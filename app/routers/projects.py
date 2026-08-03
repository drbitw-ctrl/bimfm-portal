"""Portal-native project and daily-task routes."""
from __future__ import annotations

import hashlib

from fastapi import APIRouter


def _internal_daily_project_code(project_name: str) -> str:
    normalized = " ".join(str(project_name or "").strip().split()).casefold()
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:16]
    return f"daily-{digest}"[:80]


def configure_projects_routes(legacy_namespace: dict[str, object]) -> APIRouter:
    globals().update(legacy_namespace)
    router = APIRouter(tags=["Projects"])
    globals()["router"] = router

    @router.get("/projects", response_class=HTMLResponse)
    def freelancer_project_assignments(
        request: Request,
        sort: str = "deadline",
        direction: str = "asc",
    ):
        with SessionLocal() as database:
            account = get_current_freelancer_account(request, database)
            if account is None:
                return RedirectResponse("/login", status_code=303)
            if account.must_change_password:
                return RedirectResponse("/change-password", status_code=303)

            projects = current_freelancer_portal_projects(
                database,
                freelancer_id=account.freelancer_id,
            )
            projects = sort_assigned_portal_projects(
                projects,
                sort_by=sort,
                direction=direction,
            )
            policy = get_policy(database)
            show_project_engineer = bool(
                policy.show_project_engineer_to_freelancers
            )
            rows = [
                {
                    "id": row.id,
                    "project_name": row.project_name,
                    "project_engineer": (
                        row.project_engineer or "Not specified"
                        if show_project_engineer
                        else ""
                    ),
                    "deadline": row.deadline.isoformat() if row.deadline else "No deadline",
                    "status": row.status or "—",
                    "priority": row.priority or "—",
                    "discipline": row.discipline or "—",
                    "progress": row.progress,
                    "active_task_count": row.active_task_count,
                    "next_task_id": row.next_task_id,
                    "task_description": row.next_task_description,
                }
                for row in projects
            ]
            return templates.TemplateResponse(
                request=request,
                name="freelancer_projects.html",
                context=template_context(
                    request,
                    account=account,
                    rows=rows,
                    selected_sort=sort,
                    selected_direction=direction,
                    show_project_engineer=show_project_engineer,
                ),
            )

    @router.get("/projects/completed", response_class=HTMLResponse)
    def freelancer_recently_completed_tasks(request: Request):
        with SessionLocal() as database:
            account = get_current_freelancer_account(request, database)
            if account is None:
                return RedirectResponse("/login", status_code=303)
            if account.must_change_password:
                return RedirectResponse("/change-password", status_code=303)
            rows = completed_freelancer_portal_tasks(
                database,
                freelancer_id=account.freelancer_id,
            )
            return templates.TemplateResponse(
                request=request,
                name="freelancer_completed_tasks.html",
                context=template_context(
                    request,
                    account=account,
                    rows=rows,
                ),
            )

    @router.get("/tasks", response_class=HTMLResponse)
    def freelancer_tasks(
        request: Request,
        month: str = "",
        project_task_id: int = 0,
    ):
        selected_month = month if parse_month_key(month) else current_month_key()
        bounds = parse_month_key(selected_month)
        assert bounds is not None
        first, next_month = bounds
        with SessionLocal() as database:
            account = get_current_freelancer_account(request, database)
            if account is None:
                return RedirectResponse("/login", status_code=303)
            if account.must_change_password:
                return RedirectResponse("/change-password", status_code=303)

            work_orders = freelancer_work_order_view(database, account.freelancer)
            rows = list(
                database.scalars(
                    select(DailyTask)
                    .where(
                        DailyTask.freelancer_id == account.freelancer_id,
                        DailyTask.task_date >= first,
                        DailyTask.task_date < next_month,
                    )
                    .order_by(DailyTask.task_date.desc(), DailyTask.id.desc())
                ).all()
            )
            selected_project_task = None
            if project_task_id > 0:
                selected_project_task = portal_task_for_freelancer(
                    database,
                    task_id=project_task_id,
                    freelancer_id=account.freelancer_id,
                )

            return templates.TemplateResponse(
                request=request,
                name="freelancer_tasks.html",
                context=template_context(
                    request,
                    account=account,
                    rows=rows,
                    selected_month=selected_month,
                    total_minutes=sum(row.minutes_spent for row in rows),
                    month_locked=month_is_locked(database, selected_month),
                    selected_project_task=selected_project_task,
                    work_orders=work_orders,
                ),
            )

    @router.post("/tasks/work-orders/{task_id}/start")
    def start_freelancer_work_order(
        task_id: int,
        request: Request,
        csrf: str = Form(...),
    ):
        if not validate_csrf(request, csrf):
            set_flash(request, "Invalid form token.", "error")
            return RedirectResponse("/tasks", status_code=303)
        with SessionLocal() as database:
            account = get_current_freelancer_account(request, database)
            if account is None:
                return RedirectResponse("/login", status_code=303)
            try:
                session = start_work_session(
                    database,
                    freelancer=account.freelancer,
                    task_id=task_id,
                )
            except ValueError as exc:
                database.rollback()
                set_flash(request, str(exc), "error")
                return RedirectResponse("/tasks", status_code=303)
            except IntegrityError:
                database.rollback()
                set_flash(
                    request,
                    "A work timer is already active. Refresh the page and stop it before starting another task.",
                    "error",
                )
                return RedirectResponse("/tasks", status_code=303)
            write_audit(
                database,
                actor_type="FREELANCER",
                actor_id=account.freelancer_id,
                action="START_TASK_WORK_ORDER",
                request=request,
                target_type="TASK_WORK_SESSION",
                target_id=session.id,
                details=f"Started {session.project_name} / {session.task_title}.",
            )
            database.commit()
        set_flash(request, "Work timer started.", "success")
        return RedirectResponse("/tasks", status_code=303)

    @router.post("/tasks/work-orders/stop")
    def stop_freelancer_work_order(
        request: Request,
        csrf: str = Form(...),
        notes: str = Form(""),
    ):
        if not validate_csrf(request, csrf):
            set_flash(request, "Invalid form token.", "error")
            return RedirectResponse("/tasks", status_code=303)
        with SessionLocal() as database:
            account = get_current_freelancer_account(request, database)
            if account is None:
                return RedirectResponse("/login", status_code=303)
            try:
                session, daily_task = stop_work_session(
                    database,
                    freelancer=account.freelancer,
                    notes=notes,
                )
            except ValueError as exc:
                database.rollback()
                set_flash(request, str(exc), "error")
                return RedirectResponse("/tasks", status_code=303)
            except IntegrityError:
                database.rollback()
                set_flash(
                    request,
                    "The recorded work session could not be saved. Refresh the page and try stopping the timer again.",
                    "error",
                )
                return RedirectResponse("/tasks", status_code=303)
            month_key = daily_task.task_date.strftime("%Y-%m")
            invalidate_task_review(database, account.freelancer_id, month_key)
            invalidate_dtr(database, account.freelancer_id, month_key)
            write_audit(
                database,
                actor_type="FREELANCER",
                actor_id=account.freelancer_id,
                action="STOP_TASK_WORK_ORDER",
                request=request,
                target_type="TASK_WORK_SESSION",
                target_id=session.id,
                details=(
                    f"Stopped {session.project_name} / {session.task_title}; "
                    f"recorded {session.duration_minutes} minutes and submitted the Daily Task Report."
                ),
            )
            database.commit()
        set_flash(request, "Work timer stopped. Time and Daily Task Report were recorded.", "success")
        return RedirectResponse("/tasks", status_code=303)

    @router.get("/reminders", response_class=HTMLResponse)
    def freelancer_reminders(request: Request):
        with SessionLocal() as database:
            account = get_current_freelancer_account(request, database)
            if account is None:
                return RedirectResponse("/login", status_code=303)
            rows = reminder_rows(database, account.freelancer_id)
            return templates.TemplateResponse(
                request=request,
                name="freelancer_reminders.html",
                context=template_context(request, account=account, rows=rows),
            )

    @router.post("/reminders/{reminder_id}/read")
    def read_freelancer_reminder(
        reminder_id: int,
        request: Request,
        csrf: str = Form(...),
    ):
        if not validate_csrf(request, csrf):
            return RedirectResponse("/reminders", status_code=303)
        with SessionLocal() as database:
            account = get_current_freelancer_account(request, database)
            if account is None:
                return RedirectResponse("/login", status_code=303)
            if mark_reminder_read(database, reminder_id, account.freelancer_id):
                database.commit()
        return RedirectResponse("/reminders", status_code=303)

    @router.post("/tasks/new")
    def reject_manual_daily_task_creation(
        request: Request,
        csrf: str = Form(...),
    ):
        """Version 21.00 records freelancer time only through Work Orders."""
        if not validate_csrf(request, csrf):
            set_flash(request, "Invalid form token.", "error")
            return RedirectResponse("/tasks", status_code=303)
        with SessionLocal() as database:
            account = get_current_freelancer_account(request, database)
            if account is None:
                return RedirectResponse("/login", status_code=303)
        set_flash(
            request,
            "Manual time entry is disabled. Start and stop an assigned Work Order instead.",
            "error",
        )
        return RedirectResponse("/tasks", status_code=303)

    @router.get("/tasks/{task_id}/edit", response_class=HTMLResponse)
    def reject_manual_daily_task_edit_page(task_id: int, request: Request):
        del task_id
        with SessionLocal() as database:
            account = get_current_freelancer_account(request, database)
            if account is None:
                return RedirectResponse("/login", status_code=303)
        set_flash(
            request,
            "Timed work records are system-generated and cannot be edited by freelancers.",
            "error",
        )
        return RedirectResponse("/tasks", status_code=303)

    @router.post("/tasks/{task_id}/edit")
    def reject_manual_daily_task_edit(
        task_id: int,
        request: Request,
        csrf: str = Form(...),
    ):
        del task_id
        if not validate_csrf(request, csrf):
            set_flash(request, "Invalid form token.", "error")
            return RedirectResponse("/tasks", status_code=303)
        with SessionLocal() as database:
            account = get_current_freelancer_account(request, database)
            if account is None:
                return RedirectResponse("/login", status_code=303)
        set_flash(
            request,
            "Timed work records are system-generated and cannot be edited by freelancers.",
            "error",
        )
        return RedirectResponse("/tasks", status_code=303)

    @router.post("/tasks/{task_id}/delete")
    def reject_manual_daily_task_delete(
        task_id: int,
        request: Request,
        csrf: str = Form(...),
    ):
        del task_id
        if not validate_csrf(request, csrf):
            set_flash(request, "Invalid form token.", "error")
            return RedirectResponse("/tasks", status_code=303)
        with SessionLocal() as database:
            account = get_current_freelancer_account(request, database)
            if account is None:
                return RedirectResponse("/login", status_code=303)
        set_flash(
            request,
            "Timed work records cannot be deleted by freelancers. Contact an Administrator for corrections.",
            "error",
        )
        return RedirectResponse("/tasks", status_code=303)

    @router.get("/admin/tasks/monthly", response_class=HTMLResponse)
    def admin_tasks_monthly(request:Request,month:str="",freelancer_id:int=0):
        selected_month=month if parse_month_key(month) else current_month_key(); first,next_month=parse_month_key(selected_month)
        with SessionLocal() as database:
            admin=get_current_admin(request,database)
            if admin is None:return RedirectResponse('/admin/login',303)
            freelancers=hr_freelancer_choices(database)
            query=select(DailyTask).where(DailyTask.task_date>=first,DailyTask.task_date<next_month)
            if freelancer_id: query=query.where(DailyTask.freelancer_id==freelancer_id)
            rows=list(database.scalars(query.order_by(DailyTask.task_date,DailyTask.freelancer_id,DailyTask.id)).all())
            names={f.id:f for f in freelancers}; grouped={}
            for row in rows: grouped.setdefault(row.freelancer_id,[]).append(row)
            report=[]
            for fid,items in grouped.items():
                f=names.get(fid)
                if f: report.append({'freelancer':f,'task_rows':items,'total_minutes':sum(i.minutes_spent for i in items),'review':get_task_review(database,fid,selected_month)})
            return templates.TemplateResponse(request=request,name='admin_tasks_monthly.html',context=template_context(
                request,admin=admin,freelancers=freelancers,selected_month=selected_month,
                selected_freelancer_id=freelancer_id,report=report,month_locked=month_is_locked(database,selected_month)))

    @router.post("/admin/tasks/{freelancer_id}/{month_key}/review")
    def review_task_month(freelancer_id:int,month_key:str,request:Request,csrf:str=Form(...),reason:str=Form(...)):
        redirect=f'/admin/tasks/monthly?month={month_key}&freelancer_id={freelancer_id}'
        if not validate_csrf(request,csrf):return RedirectResponse(redirect,303)
        if not parse_month_key(month_key) or len(reason.strip())<5:
            set_flash(request,'A valid month and review reason are required.','error');return RedirectResponse(redirect,303)
        with SessionLocal() as database:
            admin=get_current_admin(request,database)
            if admin is None:return RedirectResponse('/admin/login',303)
            review=get_task_review(database,freelancer_id,month_key)
            if review is None:
                review=TaskMonthReview(freelancer_id=freelancer_id,month_key=month_key,
                    reviewed_by_admin_id=admin.id,review_reason=reason.strip(),status='REVIEWED')
                database.add(review)
            else:
                review.status='REVIEWED';review.reviewed_by_admin_id=admin.id;review.review_reason=reason.strip();review.reviewed_at=utc_now()
            invalidate_dtr(database, freelancer_id, month_key)
            write_audit(database,actor_type='HR_ADMIN',actor_id=admin.id,action='REVIEW_TASK_MONTH',request=request,
                        target_type='TASK_MONTH_REVIEW',target_id=review.id,details=f'{month_key}; {reason.strip()}')
            database.commit()
        set_flash(request,'Monthly daily-task report marked reviewed.','success');return RedirectResponse(redirect,303)

    return router
