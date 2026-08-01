"""PostgreSQL-native BIMFM Portal project and task-management routes."""
from __future__ import annotations

from collections.abc import Callable
import hashlib
from datetime import date, datetime, time as clock_time, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.permissions import Permission, has_permission, normalize_role
from app.database import get_db
from app.models import (
    HRAdminAccount,
    PortalProject,
    PortalProjectMember,
    PortalTask,
    PortalTaskAssignment,
    ProjectMember,
)
from app.portal_project_service import (
    active_task_overview_rows,
    project_data_health,
    project_overview_rows,
    task_overview_rows,
    team_assignment_rows,
)
from app.web_helpers import set_flash, validate_csrf, write_audit

AdminResolver = Callable[[Request, Session], Any]
TemplateContextBuilder = Callable[..., dict[str, Any]]

TASK_STATUSES = (
    ("NOT_STARTED", "Not Started"),
    ("IN_PROGRESS", "In Progress"),
    ("FOR_REVIEW", "Completed — For Review"),
    ("COMPLETED", "Completed"),
    ("ON_HOLD", "On Hold"),
    ("UNASSIGNED", "Unassigned"),
)
TASK_PRIORITIES = (
    ("LOW", "Low"),
    ("NORMAL", "Medium"),
    ("HIGH", "High"),
    ("URGENT", "Critical"),
)
TASK_DISCIPLINES = (
    "Architecture",
    "Structure",
    "MEP",
    "GE",
    "Civil Works",
)


def _parse_optional_date(value: str, *, label: str) -> Optional[date]:
    text = (value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{label} must use YYYY-MM-DD format.") from exc


def _normalized_progress(value: str, *, status: str) -> int:
    try:
        progress = int(str(value or "0").strip())
    except ValueError as exc:
        raise ValueError("Progress must be a whole number from 0 to 100.") from exc
    if not 0 <= progress <= 100:
        raise ValueError("Progress must be a whole number from 0 to 100.")
    if status in {"FOR_REVIEW", "COMPLETED"}:
        return 100
    if status == "UNASSIGNED":
        return 0
    return progress


def _parse_quality_score(value: str) -> Optional[int]:
    text = str(value or "").strip().replace("%", "")
    if not text:
        return None
    try:
        score = int(text)
    except ValueError as exc:
        raise ValueError("Quality Score must be a whole number from 1 to 100.") from exc
    if not 1 <= score <= 100:
        raise ValueError("Quality Score must be a whole number from 1 to 100.")
    return score


def _internal_project_code(name: str) -> str:
    """Create a stable internal identifier that is never shown in the UI."""
    normalized = " ".join(str(name or "").strip().split()).casefold()
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:16]
    return f"project-{digest}"[:120]


def _project_member_assignment_id(member: ProjectMember) -> Optional[int]:
    """Return the PostgreSQL identity used by project/task assignment tables."""
    if member.source_freelancer_id is not None:
        return int(member.source_freelancer_id)
    if member.freelancer_id is not None:
        return int(member.freelancer_id)
    return None


def _task_completion_date(task: PortalTask) -> str:
    if task.completed_at is None:
        return ""
    return task.completed_at.date().isoformat()


def create_portal_router(
    *,
    templates: Jinja2Templates,
    get_current_admin: AdminResolver,
    template_context: TemplateContextBuilder,
) -> APIRouter:
    router = APIRouter(tags=["BIMFM Portal"])

    definitions = {
        "my-work": (
            "My Work",
            "Current operational tasks from the shared PostgreSQL project database.",
        ),
        "projects": (
            "Projects",
            "Unified project register migrated from Task Manager Pro.",
        ),
        "tasks": (
            "Tasks",
            "Complete task register with active, review, completed, unassigned, and on-hold records.",
        ),
        "team-workload": (
            "Team Availability / Workload",
            "All active members, including members with zero assignments.",
        ),
        "performance": (
            "Performance",
            "Project completion, open work, overdue tasks, and team coverage.",
        ),
        "reports": (
            "Project Reports",
            "Project progress and delivery status from portal-native records.",
        ),
        "calendar": (
            "Calendar",
            "Upcoming project and task deadlines.",
        ),
    }

    def require_project_editor(request: Request, database: Session):
        account = get_current_admin(request, database)
        if not account:
            return None
        if not has_permission(normalize_role(account.role), Permission.PROJECT_EDIT):
            return False
        return account

    def available_projects(database: Session) -> list[PortalProject]:
        return list(
            database.scalars(
                select(PortalProject).order_by(
                    PortalProject.status,
                    PortalProject.name,
                )
            ).all()
        )

    def available_project_members(database: Session) -> list[ProjectMember]:
        members = list(
            database.scalars(
                select(ProjectMember)
                .where(ProjectMember.is_active.is_(True))
                .order_by(ProjectMember.member_name, ProjectMember.id)
            ).all()
        )
        return [
            member for member in members
            if _project_member_assignment_id(member) is not None
        ]

    def selected_project_member_id(database: Session, task_id: int) -> int:
        assignment_ids = [
            int(value)
            for value in database.scalars(
                select(PortalTaskAssignment.freelancer_id)
                .where(PortalTaskAssignment.task_id == task_id)
                .order_by(PortalTaskAssignment.id)
            ).all()
        ]
        if not assignment_ids:
            return 0
        member = database.scalar(
            select(ProjectMember)
            .where(ProjectMember.source_freelancer_id.in_(assignment_ids))
            .order_by(ProjectMember.id)
            .limit(1)
        )
        if member is None:
            member = database.scalar(
                select(ProjectMember)
                .where(ProjectMember.freelancer_id.in_(assignment_ids))
                .order_by(ProjectMember.id)
                .limit(1)
            )
        return int(member.id) if member is not None else 0

    def task_form_context(
        request: Request,
        database: Session,
        *,
        account: HRAdminAccount,
        values: Optional[dict[str, Any]] = None,
        task: Optional[PortalTask] = None,
    ) -> dict[str, Any]:
        defaults = {
            "existing_project_id": 0,
            "project_name": "",
            "project_engineer": "",
            "task_title": "",
            "start_date": date.today().isoformat(),
            "deadline": "",
            "completion_date": "",
            "status": "NOT_STARTED",
            "priority": "NORMAL",
            "discipline": "Architecture",
            "project_member_id": 0,
            "progress": 0,
            "quality_score": "",
            "task_description": "",
        }
        if task is not None:
            project = database.get(PortalProject, task.project_id)
            defaults.update(
                {
                    "existing_project_id": task.project_id,
                    "project_name": project.name if project else "",
                    "project_engineer": project.project_engineer if project and project.project_engineer else "",
                    "task_title": task.title,
                    "start_date": task.start_date.isoformat() if task.start_date else "",
                    "deadline": task.due_date.isoformat() if task.due_date else "",
                    "completion_date": _task_completion_date(task),
                    "status": task.status,
                    "priority": task.priority,
                    "discipline": task.discipline or (project.discipline if project else None) or "Architecture",
                    "project_member_id": selected_project_member_id(database, task.id),
                    "progress": int(task.progress or 0),
                    "quality_score": task.quality_score or "",
                    "task_description": task.description or "",
                }
            )
        if values:
            defaults.update(values)
        return template_context(
            request,
            account=account,
            projects=available_projects(database),
            project_members=available_project_members(database),
            task_statuses=TASK_STATUSES,
            task_priorities=TASK_PRIORITIES,
            task_disciplines=TASK_DISCIPLINES,
            form_values=defaults,
            editing_task=task,
        )

    def validated_task_values(
        *,
        existing_project_id: int,
        project_name: str,
        project_engineer: str,
        task_title: str,
        start_date: str,
        deadline: str,
        completion_date: str,
        status: str,
        priority: str,
        discipline: str,
        project_member_id: int,
        progress: str,
        quality_score: str,
        task_description: str,
    ) -> tuple[dict[str, Any], Optional[date], Optional[date], Optional[date], int, Optional[int]]:
        form_values = {
            "existing_project_id": existing_project_id,
            "project_name": project_name.strip(),
            "project_engineer": project_engineer.strip(),
            "task_title": task_title.strip(),
            "start_date": start_date.strip(),
            "deadline": deadline.strip(),
            "completion_date": completion_date.strip(),
            "status": status.strip().upper(),
            "priority": priority.strip().upper(),
            "discipline": discipline.strip(),
            "project_member_id": project_member_id,
            "progress": progress,
            "quality_score": quality_score.strip(),
            "task_description": task_description.strip(),
        }
        normalized_status = form_values["status"]
        if normalized_status not in {value for value, _ in TASK_STATUSES}:
            raise ValueError("Select a valid task status.")
        normalized_priority = form_values["priority"]
        if normalized_priority not in {value for value, _ in TASK_PRIORITIES}:
            raise ValueError("Select a valid task priority.")
        normalized_discipline = form_values["discipline"]
        if normalized_discipline not in TASK_DISCIPLINES:
            raise ValueError("Select a valid discipline.")
        title = form_values["task_title"]
        if not title:
            raise ValueError("Task title is required.")
        if len(title) > 300:
            raise ValueError("Task title must contain 300 characters or fewer.")

        parsed_start = _parse_optional_date(form_values["start_date"], label="Start date")
        parsed_deadline = _parse_optional_date(form_values["deadline"], label="Deadline")
        parsed_completion = _parse_optional_date(
            form_values["completion_date"], label="Completion date"
        )
        if parsed_start and parsed_deadline and parsed_start > parsed_deadline:
            raise ValueError("Start date cannot be later than the deadline.")
        if normalized_status == "COMPLETED" and parsed_completion is None:
            parsed_completion = date.today()
            form_values["completion_date"] = parsed_completion.isoformat()
        if parsed_completion and parsed_start and parsed_completion < parsed_start:
            raise ValueError("Completion date cannot be earlier than the start date.")
        if normalized_status != "COMPLETED":
            parsed_completion = None
            form_values["completion_date"] = ""

        normalized_progress = _normalized_progress(
            form_values["progress"], status=normalized_status
        )
        parsed_quality_score = _parse_quality_score(form_values["quality_score"])
        return (
            form_values,
            parsed_start,
            parsed_deadline,
            parsed_completion,
            normalized_progress,
            parsed_quality_score,
        )

    def resolve_or_create_project(
        database: Session,
        *,
        existing_project_id: int,
        project_name: str,
        project_engineer: str,
        priority: str,
        discipline: str,
        start_date: Optional[date],
        deadline: Optional[date],
        completion_date: Optional[date],
        task_status: str,
        progress: int,
        allow_create: bool,
    ) -> PortalProject:
        engineer_name = " ".join(project_engineer.split())[:200]
        if existing_project_id:
            project = database.get(PortalProject, existing_project_id)
            if project is None:
                raise ValueError("The selected project was not found.")
            project.project_engineer = engineer_name or None
        else:
            if not allow_create:
                raise ValueError("Select an existing project for this task.")
            name = " ".join(project_name.split())
            if not name:
                raise ValueError("Project name is required when creating a new project.")
            duplicate = database.scalar(
                select(PortalProject).where(func.lower(PortalProject.name) == name.casefold())
            )
            if duplicate is not None:
                raise ValueError(
                    "That project name already exists. Select the existing project instead."
                )
            project = PortalProject(
                project_code=_internal_project_code(name),
                name=name[:300],
                project_engineer=engineer_name or None,
                description=None,
                status="ACTIVE",
                priority=priority,
                discipline=discipline,
                start_date=start_date,
                deadline=deadline,
                completion_date=(completion_date if task_status == "COMPLETED" else None),
                progress=(progress if task_status == "COMPLETED" else 0),
                supervisor_id=None,
            )
            database.add(project)
            database.flush()

        if not project.discipline:
            project.discipline = discipline
        if project.start_date is None:
            project.start_date = start_date
        if project.deadline is None:
            project.deadline = deadline
        return project

    def replace_task_assignment(
        database: Session,
        *,
        task: PortalTask,
        project: PortalProject,
        project_member_id: int,
        status: str,
    ) -> str:
        database.execute(
            delete(PortalTaskAssignment).where(PortalTaskAssignment.task_id == task.id)
        )
        if not project_member_id or status == "UNASSIGNED":
            return "Unassigned"

        member = database.get(ProjectMember, project_member_id)
        if member is None or not member.is_active:
            raise ValueError("The selected project member is unavailable.")
        assignment_id = _project_member_assignment_id(member)
        if assignment_id is None:
            raise ValueError(
                "The selected project member has no PostgreSQL assignment identity."
            )

        existing_membership = database.scalar(
            select(PortalProjectMember).where(
                PortalProjectMember.project_id == project.id,
                PortalProjectMember.freelancer_id == assignment_id,
            )
        )
        if existing_membership is None:
            database.add(
                PortalProjectMember(
                    project_id=project.id,
                    freelancer_id=assignment_id,
                    member_role="MEMBER",
                    is_active=True,
                )
            )
        elif not existing_membership.is_active:
            existing_membership.is_active = True

        database.add(
            PortalTaskAssignment(
                task_id=task.id,
                freelancer_id=assignment_id,
                assignment_role="ASSIGNEE",
            )
        )
        return member.member_name

    @router.get("/portal/tasks/new", response_class=HTMLResponse)
    def new_portal_task_page(
        request: Request,
        database: Session = Depends(get_db),
    ):
        account = require_project_editor(request, database)
        if account is None:
            return RedirectResponse("/admin/login", status_code=303)
        if account is False:
            set_flash(request, "You do not have permission to create project tasks.", "error")
            return RedirectResponse("/access-denied", status_code=303)
        return templates.TemplateResponse(
            request=request,
            name="admin_new_portal_task.html",
            context=task_form_context(request, database, account=account),
        )

    @router.post("/portal/tasks/new")
    def new_portal_task_submit(
        request: Request,
        csrf: str = Form(...),
        existing_project_id: int = Form(0),
        project_name: str = Form(""),
        project_engineer: str = Form(""),
        task_title: str = Form(...),
        start_date: str = Form(""),
        deadline: str = Form(""),
        completion_date: str = Form(""),
        status: str = Form("NOT_STARTED"),
        priority: str = Form("NORMAL"),
        discipline: str = Form("Architecture"),
        project_member_id: int = Form(0),
        progress: str = Form("0"),
        quality_score: str = Form(""),
        task_description: str = Form(""),
        database: Session = Depends(get_db),
    ):
        redirect_path = "/portal/tasks/new"
        if not validate_csrf(request, csrf):
            set_flash(request, "Invalid form token. Please submit the form again.", "error")
            return RedirectResponse(redirect_path, status_code=303)

        account = require_project_editor(request, database)
        if account is None:
            return RedirectResponse("/admin/login", status_code=303)
        if account is False:
            set_flash(request, "You do not have permission to create project tasks.", "error")
            return RedirectResponse("/access-denied", status_code=303)

        form_values: dict[str, Any] = {
            "existing_project_id": existing_project_id,
            "project_name": project_name,
            "project_engineer": project_engineer,
            "task_title": task_title,
            "start_date": start_date,
            "deadline": deadline,
            "completion_date": completion_date,
            "status": status,
            "priority": priority,
            "discipline": discipline,
            "project_member_id": project_member_id,
            "progress": progress,
            "quality_score": quality_score,
            "task_description": task_description,
        }
        try:
            (
                form_values,
                parsed_start,
                parsed_deadline,
                parsed_completion,
                normalized_progress,
                parsed_quality_score,
            ) = validated_task_values(**form_values)
            project = resolve_or_create_project(
                database,
                existing_project_id=int(form_values["existing_project_id"]),
                project_name=str(form_values["project_name"]),
                project_engineer=str(form_values["project_engineer"]),
                priority=str(form_values["priority"]),
                discipline=str(form_values["discipline"]),
                start_date=parsed_start,
                deadline=parsed_deadline,
                completion_date=parsed_completion,
                task_status=str(form_values["status"]),
                progress=normalized_progress,
                allow_create=True,
            )
            completed_at = (
                datetime.combine(parsed_completion, clock_time(hour=12), tzinfo=timezone.utc)
                if parsed_completion is not None
                else None
            )
            task = PortalTask(
                project_id=project.id,
                title=str(form_values["task_title"]),
                description=str(form_values["task_description"]) or str(form_values["task_title"]),
                status=str(form_values["status"]),
                priority=str(form_values["priority"]),
                discipline=str(form_values["discipline"]),
                progress=normalized_progress,
                quality_score=parsed_quality_score,
                start_date=parsed_start,
                due_date=parsed_deadline,
                completed_at=completed_at,
                created_by_admin_id=account.id,
            )
            database.add(task)
            database.flush()
            assigned_member_name = replace_task_assignment(
                database,
                task=task,
                project=project,
                project_member_id=int(form_values["project_member_id"]),
                status=str(form_values["status"]),
            )
            write_audit(
                database,
                actor_type="HR_ADMIN",
                actor_id=account.id,
                action="CREATE_PORTAL_TASK",
                request=request,
                target_type="PORTAL_TASK",
                target_id=task.id,
                details=(
                    f"project={project.name}; title={task.title}; status={task.status}; "
                    f"progress={task.progress}; quality={task.quality_score or 'not rated'}; "
                    f"assigned_member={assigned_member_name}"
                ),
            )
            database.commit()
        except ValueError as exc:
            database.rollback()
            set_flash(request, str(exc), "error")
            return templates.TemplateResponse(
                request=request,
                name="admin_new_portal_task.html",
                context=task_form_context(
                    request,
                    database,
                    account=account,
                    values=form_values,
                ),
                status_code=400,
            )
        except IntegrityError:
            database.rollback()
            set_flash(
                request,
                "The task could not be saved because one of its project or assignment values conflicts with an existing record.",
                "error",
            )
            return templates.TemplateResponse(
                request=request,
                name="admin_new_portal_task.html",
                context=task_form_context(
                    request,
                    database,
                    account=account,
                    values=form_values,
                ),
                status_code=409,
            )

        set_flash(request, f"Task “{task.title}” was created successfully.", "success")
        return RedirectResponse("/portal/tasks", status_code=303)

    @router.get("/portal/tasks/{task_id}/edit", response_class=HTMLResponse)
    def edit_portal_task_page(
        task_id: int,
        request: Request,
        database: Session = Depends(get_db),
    ):
        account = require_project_editor(request, database)
        if account is None:
            return RedirectResponse("/admin/login", status_code=303)
        if account is False:
            set_flash(request, "You do not have permission to edit project tasks.", "error")
            return RedirectResponse("/access-denied", status_code=303)
        task = database.get(PortalTask, task_id)
        if task is None:
            set_flash(request, "Task not found.", "error")
            return RedirectResponse("/portal/tasks", status_code=303)
        return templates.TemplateResponse(
            request=request,
            name="admin_edit_portal_task.html",
            context=task_form_context(
                request,
                database,
                account=account,
                task=task,
            ),
        )

    @router.post("/portal/tasks/{task_id}/edit")
    def edit_portal_task_submit(
        task_id: int,
        request: Request,
        csrf: str = Form(...),
        existing_project_id: int = Form(...),
        project_engineer: str = Form(""),
        task_title: str = Form(...),
        start_date: str = Form(""),
        deadline: str = Form(""),
        completion_date: str = Form(""),
        status: str = Form("NOT_STARTED"),
        priority: str = Form("NORMAL"),
        discipline: str = Form("Architecture"),
        project_member_id: int = Form(0),
        progress: str = Form("0"),
        quality_score: str = Form(""),
        task_description: str = Form(""),
        database: Session = Depends(get_db),
    ):
        redirect_path = f"/portal/tasks/{task_id}/edit"
        if not validate_csrf(request, csrf):
            set_flash(request, "Invalid form token. Please submit the form again.", "error")
            return RedirectResponse(redirect_path, status_code=303)
        account = require_project_editor(request, database)
        if account is None:
            return RedirectResponse("/admin/login", status_code=303)
        if account is False:
            set_flash(request, "You do not have permission to edit project tasks.", "error")
            return RedirectResponse("/access-denied", status_code=303)
        task = database.get(PortalTask, task_id)
        if task is None:
            set_flash(request, "Task not found.", "error")
            return RedirectResponse("/portal/tasks", status_code=303)

        form_values: dict[str, Any] = {
            "existing_project_id": existing_project_id,
            "project_name": "",
            "project_engineer": project_engineer,
            "task_title": task_title,
            "start_date": start_date,
            "deadline": deadline,
            "completion_date": completion_date,
            "status": status,
            "priority": priority,
            "discipline": discipline,
            "project_member_id": project_member_id,
            "progress": progress,
            "quality_score": quality_score,
            "task_description": task_description,
        }
        try:
            (
                form_values,
                parsed_start,
                parsed_deadline,
                parsed_completion,
                normalized_progress,
                parsed_quality_score,
            ) = validated_task_values(**form_values)
            project = resolve_or_create_project(
                database,
                existing_project_id=int(form_values["existing_project_id"]),
                project_name="",
                project_engineer=str(form_values["project_engineer"]),
                priority=str(form_values["priority"]),
                discipline=str(form_values["discipline"]),
                start_date=parsed_start,
                deadline=parsed_deadline,
                completion_date=parsed_completion,
                task_status=str(form_values["status"]),
                progress=normalized_progress,
                allow_create=False,
            )
            task.project_id = project.id
            task.title = str(form_values["task_title"])
            task.description = str(form_values["task_description"]) or task.title
            task.status = str(form_values["status"])
            task.priority = str(form_values["priority"])
            task.discipline = str(form_values["discipline"])
            task.progress = normalized_progress
            task.quality_score = parsed_quality_score
            task.start_date = parsed_start
            task.due_date = parsed_deadline
            task.completed_at = (
                datetime.combine(parsed_completion, clock_time(hour=12), tzinfo=timezone.utc)
                if parsed_completion is not None
                else None
            )
            assigned_member_name = replace_task_assignment(
                database,
                task=task,
                project=project,
                project_member_id=int(form_values["project_member_id"]),
                status=str(form_values["status"]),
            )
            write_audit(
                database,
                actor_type="HR_ADMIN",
                actor_id=account.id,
                action="UPDATE_PORTAL_TASK",
                request=request,
                target_type="PORTAL_TASK",
                target_id=task.id,
                details=(
                    f"project={project.name}; title={task.title}; status={task.status}; "
                    f"progress={task.progress}; quality={task.quality_score or 'not rated'}; "
                    f"assigned_member={assigned_member_name}"
                ),
            )
            database.commit()
        except ValueError as exc:
            database.rollback()
            set_flash(request, str(exc), "error")
            return templates.TemplateResponse(
                request=request,
                name="admin_edit_portal_task.html",
                context=task_form_context(
                    request,
                    database,
                    account=account,
                    values=form_values,
                    task=task,
                ),
                status_code=400,
            )
        except IntegrityError:
            database.rollback()
            set_flash(request, "The task could not be updated because an assignment value conflicts with an existing record.", "error")
            return templates.TemplateResponse(
                request=request,
                name="admin_edit_portal_task.html",
                context=task_form_context(
                    request,
                    database,
                    account=account,
                    values=form_values,
                    task=task,
                ),
                status_code=409,
            )

        set_flash(request, f"Task “{task.title}” was updated successfully.", "success")
        return RedirectResponse("/portal/tasks", status_code=303)

    @router.post("/portal/tasks/{task_id}/quick-edit", response_class=JSONResponse)
    def quick_edit_portal_task(
        task_id: int,
        request: Request,
        csrf: str = Form(...),
        field: str = Form(...),
        value: str = Form(""),
        database: Session = Depends(get_db),
    ):
        """Update one approved quick-edit field from the Tasks sidebar page."""
        if not validate_csrf(request, csrf):
            return JSONResponse(
                {"ok": False, "message": "Invalid form token. Refresh the page and try again."},
                status_code=400,
            )

        account = require_project_editor(request, database)
        if account is None:
            return JSONResponse(
                {"ok": False, "message": "Your session has expired. Please sign in again."},
                status_code=401,
            )
        if account is False:
            return JSONResponse(
                {"ok": False, "message": "You do not have permission to edit project tasks."},
                status_code=403,
            )

        task = database.get(PortalTask, task_id)
        if task is None:
            return JSONResponse(
                {"ok": False, "message": "Task not found."},
                status_code=404,
            )

        normalized_field = str(field or "").strip()
        editable_fields = {"status", "progress", "quality_score", "completion_date"}
        if normalized_field not in editable_fields:
            return JSONResponse(
                {"ok": False, "message": "That field is not available for quick editing."},
                status_code=400,
            )

        old_display = ""
        updates: dict[str, Any] = {}
        try:
            if normalized_field == "status":
                status = str(value or "").strip().upper()
                if status not in {item[0] for item in TASK_STATUSES}:
                    raise ValueError("Select a valid task status.")

                old_display = task.status
                task.status = status
                if status in {"FOR_REVIEW", "COMPLETED"}:
                    task.progress = 100
                elif status == "UNASSIGNED":
                    task.progress = 0
                    database.execute(
                        delete(PortalTaskAssignment).where(
                            PortalTaskAssignment.task_id == task.id
                        )
                    )
                    updates["assignee_name"] = "Unassigned"

                if status == "COMPLETED":
                    if task.completed_at is None:
                        task.completed_at = datetime.combine(
                            date.today(), clock_time(hour=12), tzinfo=timezone.utc
                        )
                else:
                    task.completed_at = None

                updates.update(
                    {
                        "status": status,
                        "filter_status": status,
                        "progress": int(task.progress or 0),
                        "completion_date": _task_completion_date(task),
                    }
                )

            elif normalized_field == "progress":
                old_display = str(int(task.progress or 0))
                task.progress = _normalized_progress(value, status=task.status)
                updates["progress"] = int(task.progress)

            elif normalized_field == "quality_score":
                old_display = str(task.quality_score or "")
                task.quality_score = _parse_quality_score(value)
                updates["quality_score"] = task.quality_score

            elif normalized_field == "completion_date":
                old_display = _task_completion_date(task)
                if task.status != "COMPLETED":
                    raise ValueError("Set the task status to Completed before entering a completion date.")
                parsed = _parse_optional_date(value, label="Completion date") or date.today()
                if task.start_date and parsed < task.start_date:
                    raise ValueError("Completion date cannot be earlier than the start date.")
                task.completed_at = datetime.combine(
                    parsed, clock_time(hour=12), tzinfo=timezone.utc
                )
                updates["completion_date"] = parsed.isoformat()

            new_display = str(updates.get(normalized_field, value or ""))
            write_audit(
                database,
                actor_type="HR_ADMIN",
                actor_id=account.id,
                action="QUICK_UPDATE_PORTAL_TASK",
                request=request,
                target_type="PORTAL_TASK",
                target_id=task.id,
                details=f"field={normalized_field}; from={old_display}; to={new_display}",
            )
            database.commit()
        except ValueError as exc:
            database.rollback()
            return JSONResponse(
                {"ok": False, "message": str(exc)},
                status_code=400,
            )

        return JSONResponse(
            {
                "ok": True,
                "message": "Saved",
                "task_id": task.id,
                "field": normalized_field,
                "updates": updates,
            }
        )

    @router.post("/portal/tasks/{task_id}/delete")
    def delete_portal_task(
        task_id: int,
        request: Request,
        csrf: str = Form(...),
        database: Session = Depends(get_db),
    ):
        if not validate_csrf(request, csrf):
            set_flash(request, "Invalid form token.", "error")
            return RedirectResponse(f"/portal/tasks/{task_id}/edit", status_code=303)
        account = require_project_editor(request, database)
        if account is None:
            return RedirectResponse("/admin/login", status_code=303)
        if account is False:
            set_flash(request, "You do not have permission to delete project tasks.", "error")
            return RedirectResponse("/access-denied", status_code=303)
        task = database.get(PortalTask, task_id)
        if task is None:
            set_flash(request, "Task not found.", "error")
            return RedirectResponse("/portal/tasks", status_code=303)
        task_title = task.title
        write_audit(
            database,
            actor_type="HR_ADMIN",
            actor_id=account.id,
            action="DELETE_PORTAL_TASK",
            request=request,
            target_type="PORTAL_TASK",
            target_id=task.id,
            details=f"Deleted task '{task.title}'.",
        )
        database.delete(task)
        database.commit()
        set_flash(request, f"Task “{task_title}” was deleted.", "success")
        return RedirectResponse("/portal/tasks", status_code=303)

    @router.get("/portal/{module_name}", response_class=HTMLResponse)
    def portal_module(
        request: Request,
        module_name: str,
        view: str = "",
        database: Session = Depends(get_db),
    ):
        account = get_current_admin(request, database)
        if not account:
            return RedirectResponse("/admin/login", status_code=303)

        page_title, description = definitions.get(
            module_name,
            ("BIMFM Portal", "Unified operations module."),
        )
        health = project_data_health(database)
        completed_task_count = int(
            database.scalar(
                select(func.count(PortalTask.id)).where(PortalTask.status == "COMPLETED")
            )
            or 0
        )
        overdue_task_count = int(
            database.scalar(
                select(func.count(PortalTask.id)).where(
                    PortalTask.status.notin_(("COMPLETED", "CANCELLED")),
                    PortalTask.due_date.is_not(None),
                    PortalTask.due_date < date.today(),
                )
            )
            or 0
        )

        cards = [
            {"label": "Projects", "value": health.project_count, "note": "PostgreSQL project records"},
            {"label": "Active tasks", "value": health.active_task_count, "note": "Open operational work"},
            {"label": "Completed tasks", "value": completed_task_count, "note": "Portal task history"},
            {"label": "Members without projects", "value": health.unassigned_member_count, "note": "Visible in Team Workload"},
        ]

        columns: list[dict[str, str]] = []
        rows: list[dict[str, Any]] = []
        section_title = "PostgreSQL-native records"
        section_note = "This module reads the migrated project tables directly. No projects.db synchronization is required."
        task_filters: dict[str, list[dict[str, str]]] | None = None
        can_edit_tasks = has_permission(normalize_role(account.role), Permission.PROJECT_EDIT)

        if module_name == "projects":
            columns = [
                {"key": "project", "label": "Project", "type": "project"},
                {"key": "project_engineer", "label": "Project Engineer", "type": "text"},
                {"key": "status", "label": "Status", "type": "status"},
                {"key": "progress", "label": "Progress", "type": "progress"},
                {"key": "member_count", "label": "Members", "type": "number"},
                {"key": "active_task_count", "label": "Active Tasks", "type": "number"},
                {"key": "deadline", "label": "Deadline", "type": "date"},
            ]
            rows = [
                {
                    "project": {"primary": row["name"], "secondary": ""},
                    "project_engineer": row["project_engineer"],
                    "status": row["status"],
                    "progress": int(row["progress"]),
                    "member_count": row["member_count"],
                    "active_task_count": row["active_task_count"],
                    "deadline": row["deadline"],
                }
                for row in project_overview_rows(database, limit=500)
            ]
        elif module_name == "tasks":
            normalized_view = view if view in {"active", "completed"} else "all"
            source_rows = task_overview_rows(database, status_mode=normalized_view, limit=1000)
            if normalized_view == "active":
                page_title = "Active Tasks"
                description = "Open project tasks that still require action."
                section_title = "Active Task Register"
            elif normalized_view == "completed":
                page_title = "Recently Completed Tasks"
                description = "Completed task history ordered by the latest update."
                section_title = "Completed Task Register"
            else:
                page_title = "Tasks"
                description = "All project tasks, including active, review, completed, on-hold, and unassigned records."
                section_title = "Complete Task Register"
            section_note = (
                "Search and filter the complete PostgreSQL task register. Status, Progress, Quality, and Completed can be updated directly; use Edit for all other fields."
                if can_edit_tasks
                else "Search and filter the complete PostgreSQL task register."
            )
            columns = [
                {"key": "project", "label": "Project", "type": "project"},
                {"key": "title", "label": "Task", "type": "text"},
                {"key": "assignees", "label": "Assigned Member", "type": "text"},
                {"key": "status", "label": "Status", "type": "quick_status" if can_edit_tasks else "status"},
                {"key": "priority", "label": "Priority", "type": "priority"},
                {"key": "discipline", "label": "Discipline", "type": "text"},
                {"key": "progress", "label": "Progress", "type": "quick_progress" if can_edit_tasks else "progress"},
                {"key": "quality", "label": "Quality", "type": "quick_quality" if can_edit_tasks else "quality"},
                {"key": "start_date", "label": "Start", "type": "date"},
                {"key": "due_date", "label": "Deadline", "type": "date"},
                {"key": "completion_date", "label": "Completed", "type": "quick_completed" if can_edit_tasks else "date"},
            ]
            if can_edit_tasks:
                columns.append({"key": "action", "label": "Action", "type": "action"})
            rows = []
            for row in source_rows:
                item: dict[str, Any] = {
                    "_task_id": int(row["id"]),
                    "_completion_date_value": "" if row["completion_date"] == "—" else str(row["completion_date"]),
                    "_filters": {
                        "project": str(row["project_id"]),
                        "member": "|" + "|".join(str(value).casefold() for value in str(row["assignees"]).split(", ")) + "|",
                        "status": str(row["status"]),
                        "priority": str(row["priority"]),
                        "discipline": str(row["discipline"]),
                    },
                    "project": {
                        "primary": row["project_name"],
                        "secondary": row["project_engineer"] if row["project_engineer"] != "—" else "",
                    },
                    "title": row["title"],
                    "assignees": row["assignees"],
                    "status": row["status"],
                    "priority": row["priority"],
                    "discipline": row["discipline"],
                    "progress": int(row["progress"]),
                    "quality": row["quality_score"],
                    "start_date": row["start_date"],
                    "due_date": row["due_date"],
                    "completion_date": row["completion_date"],
                }
                if can_edit_tasks:
                    item["action"] = {
                        "href": f"/portal/tasks/{row['id']}/edit",
                        "label": "Edit",
                    }
                rows.append(item)

            project_options = {
                str(row["project_id"]): str(row["project_name"])
                for row in source_rows
            }
            member_names = sorted(
                {
                    name.strip()
                    for row in source_rows
                    for name in str(row["assignees"]).split(",")
                    if name.strip() and name.strip() != "Unassigned"
                },
                key=str.casefold,
            )
            task_filters = {
                "projects": [
                    {"value": key, "label": value}
                    for key, value in sorted(project_options.items(), key=lambda item: item[1].casefold())
                ],
                "members": [{"value": name.casefold(), "label": name} for name in member_names],
                "statuses": [{"value": value, "label": label} for value, label in TASK_STATUSES],
                "priorities": [{"value": value, "label": label} for value, label in TASK_PRIORITIES],
                "disciplines": [
                    {"value": value, "label": value}
                    for value in sorted({str(row["discipline"]) for row in source_rows if row["discipline"] != "—"})
                ],
            }
        elif module_name == "my-work":
            columns = [
                {"key": "project", "label": "Project", "type": "project"},
                {"key": "title", "label": "Task", "type": "text"},
                {"key": "assignees", "label": "Assignees", "type": "text"},
                {"key": "status", "label": "Status", "type": "status"},
                {"key": "priority", "label": "Priority", "type": "priority"},
                {"key": "progress", "label": "Progress", "type": "progress"},
                {"key": "due_date", "label": "Due", "type": "date"},
            ]
            rows = [
                {
                    "project": {
                        "primary": row["project_name"],
                        "secondary": row.get("project_engineer", "") if row.get("project_engineer") != "—" else "",
                    },
                    "title": row["title"],
                    "assignees": row["assignees"],
                    "status": row["status"],
                    "priority": row["priority"],
                    "progress": int(row["progress"]),
                    "due_date": row["due_date"],
                }
                for row in active_task_overview_rows(database, limit=300)
            ]
        elif module_name == "team-workload":
            columns = [
                {"key": "member", "label": "Member", "type": "person"},
                {"key": "project_count", "label": "Projects", "type": "number"},
                {"key": "active_task_count", "label": "Active Tasks", "type": "number"},
                {"key": "completed_task_count", "label": "Completed", "type": "number"},
                {"key": "overdue_task_count", "label": "Overdue", "type": "warning_number"},
                {"key": "assignment_status", "label": "Status", "type": "status"},
            ]
            rows = [
                {
                    "member": {"primary": row["name"], "secondary": ""},
                    "project_count": row["project_count"],
                    "active_task_count": row["active_task_count"],
                    "completed_task_count": row["completed_task_count"],
                    "overdue_task_count": row["overdue_task_count"],
                    "assignment_status": row["assignment_status"],
                }
                for row in team_assignment_rows(database)
            ]
        elif module_name in {"performance", "reports"}:
            columns = [
                {"key": "indicator", "label": "Indicator", "type": "text"},
                {"key": "result", "label": "Result", "type": "number"},
                {"key": "meaning", "label": "Meaning", "type": "text"},
            ]
            rows = [
                {"indicator": "Active projects", "result": health.project_count, "meaning": "Projects available in PostgreSQL"},
                {"indicator": "Open tasks", "result": health.active_task_count, "meaning": "Not completed or cancelled"},
                {"indicator": "Overdue tasks", "result": overdue_task_count, "meaning": "Open tasks past due date"},
                {"indicator": "Members with projects", "result": health.assigned_member_count, "meaning": "Active project membership"},
                {"indicator": "Members without projects", "result": health.unassigned_member_count, "meaning": "Needs assignment review"},
                {"indicator": "Open tasks without assignees", "result": health.active_tasks_without_assignees, "meaning": "Needs task assignment"},
            ]
        elif module_name == "calendar":
            columns = [
                {"key": "due_date", "label": "Due Date", "type": "date"},
                {"key": "project", "label": "Project", "type": "project"},
                {"key": "title", "label": "Task", "type": "text"},
                {"key": "status", "label": "Status", "type": "status"},
                {"key": "progress", "label": "Progress", "type": "progress"},
            ]
            rows = [
                {
                    "due_date": row["due_date"],
                    "project": {
                        "primary": row["project_name"],
                        "secondary": row.get("project_engineer", "") if row.get("project_engineer") != "—" else "",
                    },
                    "title": row["title"],
                    "status": row["status"],
                    "progress": int(row["progress"]),
                }
                for row in active_task_overview_rows(database, limit=300)
                if row["due_date"] != "—"
            ]

        return templates.TemplateResponse(
            request=request,
            name="portal_module.html",
            context=template_context(
                request,
                page_title=page_title,
                page_description=description,
                cards=cards,
                columns=columns,
                rows=rows,
                section_title=section_title,
                section_note=section_note,
                account=account,
                module_name=module_name,
                task_view=view if view in {"active", "completed"} else "all",
                task_filters=task_filters,
                can_create_task=can_edit_tasks,
                can_edit_tasks=can_edit_tasks,
                task_quick_edit_options=(
                    {
                        "statuses": TASK_STATUSES,
                        "progress_values": tuple(range(0, 101, 5)),
                        "quality_values": tuple(range(1, 101)),
                    }
                    if module_name == "tasks" and can_edit_tasks
                    else None
                ),
            ),
        )

    return router
