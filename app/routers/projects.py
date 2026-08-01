"""PostgreSQL-native project and daily-task routes."""
from __future__ import annotations

from fastapi import APIRouter


def configure_projects_routes(legacy_namespace: dict[str, object]) -> APIRouter:
    globals().update(legacy_namespace)
    router = APIRouter(tags=["Projects"])
    globals()["router"] = router

    @router.get("/projects", response_class=HTMLResponse)
    def freelancer_project_assignments(request: Request):
        with SessionLocal() as database:
            account = get_current_freelancer_account(request, database)
            if account is None:
                return RedirectResponse("/login", status_code=303)
            if account.must_change_password:
                return RedirectResponse("/change-password", status_code=303)

            tasks = current_freelancer_portal_tasks(
                database,
                freelancer_id=account.freelancer_id,
            )
            rows = [
                {
                    "id": row.id,
                    "project_code": row.project_code,
                    "project_name": row.project_name,
                    "deadline": row.deadline.isoformat() if row.deadline else "No deadline",
                    "status": row.project_status or "—",
                    "priority": row.priority or "—",
                    "discipline": row.discipline or "—",
                    "progress": row.progress,
                    "task_description": row.task_description or "No task description provided.",
                }
                for row in tasks
            ]
            return templates.TemplateResponse(
                request=request,
                name="freelancer_projects.html",
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
            total_minutes = sum(row.minutes_spent for row in rows)
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
                    total_minutes=total_minutes,
                    month_locked=month_is_locked(database, selected_month),
                    selected_project_task=selected_project_task,
                ),
            )

    @router.post("/tasks/new")
    def create_daily_task(
        request: Request,
        csrf: str = Form(...),
        task_date: str = Form(...),
        project_code: str = Form(...),
        project_name: str = Form(""),
        discipline: str = Form(""),
        task_description: str = Form(...),
        portal_task_id: int = Form(0),
        synced_project_task_id: int = Form(0),
        accomplishment: str = Form(""),
        task_status: str = Form("COMPLETED"),
        hours_spent: str = Form(...),
        completion_percentage: str = Form(...),
        notes: str = Form(""),
    ):
        del synced_project_task_id  # Retained only for old cached forms.
        redirect_path = f"/tasks?month={task_date[:7]}"
        if not validate_csrf(request, csrf):
            set_flash(request, "Invalid form token.", "error")
            return RedirectResponse(redirect_path, status_code=303)
        try:
            parsed_date = date.fromisoformat(task_date)
            minutes = _parse_hours_to_minutes(hours_spent)
            completion = _parse_completion_percentage(completion_percentage)
        except ValueError as exc:
            set_flash(request, str(exc), "error")
            return RedirectResponse(redirect_path, status_code=303)
        if not project_code.strip() or not task_description.strip():
            set_flash(request, "Project code and task description are required.", "error")
            return RedirectResponse(redirect_path, status_code=303)
        normalized_task_status = task_status.strip().upper()
        if normalized_task_status not in {"COMPLETED", "IN_PROGRESS", "ON_HOLD"}:
            set_flash(request, "Invalid task status.", "error")
            return RedirectResponse(redirect_path, status_code=303)

        with SessionLocal() as database:
            account = get_current_freelancer_account(request, database)
            if account is None:
                return RedirectResponse("/login", status_code=303)
            month_key = parsed_date.strftime("%Y-%m")
            if month_is_locked(database, month_key):
                set_flash(request, "This month is locked. Daily tasks cannot be changed.", "error")
                return RedirectResponse(redirect_path, status_code=303)

            linked_project_task = None
            if portal_task_id > 0:
                linked_project_task = portal_task_for_freelancer(
                    database,
                    task_id=portal_task_id,
                    freelancer_id=account.freelancer_id,
                )
                if linked_project_task is None:
                    set_flash(request, "The selected PostgreSQL project task is unavailable.", "error")
                    return RedirectResponse(redirect_path, status_code=303)

            local_today = current_attendance_date(account.freelancer.timezone_name)
            if parsed_date > local_today:
                set_flash(request, "Daily tasks cannot be submitted for a future date.", "error")
                return RedirectResponse(redirect_path, status_code=303)

            task = DailyTask(
                freelancer_id=account.freelancer_id,
                portal_task_id=linked_project_task.id if linked_project_task else None,
                synced_project_task_id=None,
                task_date=parsed_date,
                project_code=project_code.strip(),
                project_name=project_name.strip() or None,
                discipline=discipline.strip() or None,
                task_description=task_description.strip(),
                accomplishment=accomplishment.strip() or None,
                task_status=normalized_task_status,
                minutes_spent=minutes,
                completion_percentage=completion,
                notes=notes.strip() or None,
            )
            database.add(task)
            invalidate_task_review(database, account.freelancer_id, month_key)
            write_audit(
                database,
                actor_type="FREELANCER",
                actor_id=account.freelancer_id,
                action="CREATE_DAILY_TASK",
                request=request,
                target_type="DAILY_TASK",
                details=(
                    f"{parsed_date} {project_code.strip()} {minutes_label(minutes)}; "
                    f"{completion}% complete; portal_task_id={task.portal_task_id or 'manual'}"
                ),
            )
            database.commit()
        set_flash(request, "Daily task added.", "success")
        return RedirectResponse(redirect_path, status_code=303)

    @router.get("/tasks/{task_id}/edit", response_class=HTMLResponse)
    def edit_task_page(task_id: int, request: Request):
        with SessionLocal() as database:
            account = get_current_freelancer_account(request, database)
            if account is None: return RedirectResponse("/login",303)
            task = database.get(DailyTask, task_id)
            if task is None or task.freelancer_id != account.freelancer_id:
                set_flash(request, "Daily task not found.", "error"); return RedirectResponse("/tasks",303)
            return templates.TemplateResponse(request=request, name="freelancer_task_edit.html",
                context=template_context(request, account=account, task=task,
                                         month_locked=month_is_locked(database,task.task_date.strftime('%Y-%m'))))

    @router.post("/tasks/{task_id}/edit")
    def edit_task_submit(
        task_id: int, request: Request, csrf: str = Form(...),
        project_code: str = Form(...), project_name: str = Form(""), discipline: str = Form(""),
        task_description: str = Form(...), accomplishment: str = Form(""),
        task_status: str = Form("COMPLETED"), hours_spent: str = Form(...),
        completion_percentage: str = Form(...), notes: str = Form(""),
    ):
        if not validate_csrf(request, csrf): return RedirectResponse(f"/tasks/{task_id}/edit",303)
        try:
            minutes = _parse_hours_to_minutes(hours_spent)
            completion = _parse_completion_percentage(completion_percentage)
        except ValueError as exc:
            set_flash(request,str(exc),"error"); return RedirectResponse(f"/tasks/{task_id}/edit",303)
        if not project_code.strip() or not task_description.strip():
            set_flash(request, "Project code and task description are required.", "error")
            return RedirectResponse(f"/tasks/{task_id}/edit",303)
        normalized_task_status = task_status.strip().upper()
        if normalized_task_status not in {"COMPLETED", "IN_PROGRESS", "ON_HOLD"}:
            set_flash(request, "Invalid task status.", "error")
            return RedirectResponse(f"/tasks/{task_id}/edit",303)
        with SessionLocal() as database:
            account=get_current_freelancer_account(request,database)
            if account is None: return RedirectResponse('/login',303)
            task=database.get(DailyTask,task_id)
            if task is None or task.freelancer_id != account.freelancer_id:
                return RedirectResponse('/tasks',303)
            month_key=task.task_date.strftime('%Y-%m')
            if month_is_locked(database,month_key):
                set_flash(request,'This month is locked.', 'error'); return RedirectResponse(f'/tasks?month={month_key}',303)
            task.project_code=project_code.strip(); task.project_name=project_name.strip() or None
            task.discipline=discipline.strip() or None; task.task_description=task_description.strip()
            task.accomplishment=accomplishment.strip() or None; task.task_status=normalized_task_status
            task.minutes_spent=minutes; task.completion_percentage=completion; task.notes=notes.strip() or None
            invalidate_task_review(database,account.freelancer_id,month_key)
            write_audit(database,actor_type='FREELANCER',actor_id=account.freelancer_id,
                        action='UPDATE_DAILY_TASK',request=request,target_type='DAILY_TASK',target_id=task.id)
            database.commit()
        set_flash(request,'Daily task updated.','success'); return RedirectResponse(f'/tasks?month={month_key}',303)

    @router.post("/tasks/{task_id}/delete")
    def delete_daily_task(task_id:int,request:Request,csrf:str=Form(...)):
        if not validate_csrf(request,csrf): return RedirectResponse('/tasks',303)
        with SessionLocal() as database:
            account=get_current_freelancer_account(request,database)
            if account is None: return RedirectResponse('/login',303)
            task=database.get(DailyTask,task_id)
            if task is None or task.freelancer_id != account.freelancer_id: return RedirectResponse('/tasks',303)
            month_key=task.task_date.strftime('%Y-%m')
            if month_is_locked(database,month_key):
                set_flash(request,'This month is locked.','error'); return RedirectResponse(f'/tasks?month={month_key}',303)
            invalidate_task_review(database,account.freelancer_id,month_key)
            database.delete(task); database.commit()
        set_flash(request,'Daily task removed.','success'); return RedirectResponse(f'/tasks?month={month_key}',303)

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
