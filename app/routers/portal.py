"""PostgreSQL-native BIMFM Portal project modules and task creation."""
from __future__ import annotations

from collections.abc import Callable
import hashlib
from datetime import date, datetime, time as clock_time, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
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
    progress = max(0, min(100, progress))
    if status in {"FOR_REVIEW", "COMPLETED"}:
        return 100
    if status == "UNASSIGNED":
        return 0
    return progress


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
            "Active and completed operational tasks with direct PostgreSQL assignments.",
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

    def task_form_context(
        request: Request,
        database: Session,
        *,
        account: HRAdminAccount,
        values: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        projects = list(
            database.scalars(
                select(PortalProject).order_by(
                    PortalProject.status,
                    PortalProject.name,
                )
            ).all()
        )
        project_members = list(
            database.scalars(
                select(ProjectMember)
                .where(ProjectMember.is_active.is_(True))
                .order_by(ProjectMember.member_name, ProjectMember.id)
            ).all()
        )
        project_members = [
            member
            for member in project_members
            if _project_member_assignment_id(member) is not None
        ]
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
            "task_description": "",
        }
        if values:
            defaults.update(values)
        return template_context(
            request,
            account=account,
            projects=projects,
            project_members=project_members,
            task_statuses=TASK_STATUSES,
            task_priorities=TASK_PRIORITIES,
            task_disciplines=TASK_DISCIPLINES,
            form_values=defaults,
        )

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
            "task_description": task_description.strip(),
        }

        try:
            normalized_status = form_values["status"]
            valid_statuses = {value for value, _ in TASK_STATUSES}
            if normalized_status not in valid_statuses:
                raise ValueError("Select a valid task status.")

            normalized_priority = form_values["priority"]
            valid_priorities = {value for value, _ in TASK_PRIORITIES}
            if normalized_priority not in valid_priorities:
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
                raise ValueError("Completion date is required for a completed task.")
            if parsed_completion and parsed_start and parsed_completion < parsed_start:
                raise ValueError("Completion date cannot be earlier than the start date.")

            normalized_progress = _normalized_progress(
                form_values["progress"], status=normalized_status
            )

            project: Optional[PortalProject]
            engineer_name = " ".join(form_values["project_engineer"].split())[:200]
            if existing_project_id:
                project = database.get(PortalProject, existing_project_id)
                if project is None:
                    raise ValueError("The selected project was not found.")
                if engineer_name:
                    project.project_engineer = engineer_name
            else:
                name = " ".join(form_values["project_name"].split())
                if not name:
                    raise ValueError("Project name is required when creating a new project.")
                duplicate = database.scalar(
                    select(PortalProject).where(
                        func.lower(PortalProject.name) == name.casefold()
                    )
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
                    priority=normalized_priority,
                    discipline=normalized_discipline,
                    start_date=parsed_start,
                    deadline=parsed_deadline,
                    completion_date=(parsed_completion if normalized_status == "COMPLETED" else None),
                    progress=(normalized_progress if normalized_status == "COMPLETED" else 0),
                    supervisor_id=None,
                )
                database.add(project)
                database.flush()

            if not project.discipline:
                project.discipline = normalized_discipline
            if project.start_date is None:
                project.start_date = parsed_start
            if project.deadline is None:
                project.deadline = parsed_deadline

            completed_at = None
            if normalized_status == "COMPLETED" and parsed_completion:
                completed_at = datetime.combine(
                    parsed_completion,
                    clock_time(hour=12),
                    tzinfo=timezone.utc,
                )

            task = PortalTask(
                project_id=project.id,
                title=title,
                description=form_values["task_description"] or title,
                status=normalized_status,
                priority=normalized_priority,
                discipline=normalized_discipline,
                progress=normalized_progress,
                start_date=parsed_start,
                due_date=parsed_deadline,
                completed_at=completed_at,
                created_by_admin_id=account.id,
            )
            database.add(task)
            database.flush()

            assigned_member_name = "Unassigned"
            if project_member_id and normalized_status != "UNASSIGNED":
                member = database.get(ProjectMember, project_member_id)
                if member is None or not member.is_active:
                    raise ValueError("The selected project member is unavailable.")
                assignment_id = _project_member_assignment_id(member)
                if assignment_id is None:
                    raise ValueError(
                        "The selected project member has no PostgreSQL assignment identity."
                    )
                assigned_member_name = member.member_name

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

            write_audit(
                database,
                actor_type="HR_ADMIN",
                actor_id=account.id,
                action="CREATE_PORTAL_TASK",
                request=request,
                target_type="PORTAL_TASK",
                target_id=task.id,
                details=(
                    f"project={project.name}; title={task.title}; "
                    f"status={task.status}; progress={task.progress}; "
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
                select(func.count(PortalTask.id)).where(
                    PortalTask.status == "COMPLETED"
                )
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
            {
                "label": "Projects",
                "value": health.project_count,
                "note": "PostgreSQL project records",
            },
            {
                "label": "Active tasks",
                "value": health.active_task_count,
                "note": "Open operational work",
            },
            {
                "label": "Completed tasks",
                "value": completed_task_count,
                "note": "Portal task history",
            },
            {
                "label": "Members without projects",
                "value": health.unassigned_member_count,
                "note": "Visible in Team Workload",
            },
        ]

        columns: list[dict[str, str]] = []
        rows: list[dict[str, Any]] = []
        section_title = "PostgreSQL-native records"
        section_note = (
            "This module reads the migrated project tables directly. "
            "No projects.db synchronization is required."
        )

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
                for row in project_overview_rows(database, limit=200)
            ]
        elif module_name in {"tasks", "my-work"}:
            columns = [
                {"key": "project", "label": "Project", "type": "project"},
                {"key": "title", "label": "Task", "type": "text"},
                {"key": "assignees", "label": "Assignees", "type": "text"},
                {"key": "status", "label": "Status", "type": "status"},
                {"key": "priority", "label": "Priority", "type": "priority"},
                {"key": "progress", "label": "Progress", "type": "progress"},
                {"key": "due_date", "label": "Due", "type": "date"},
            ]
            if view == "completed":
                completed = database.execute(
                    select(PortalTask, PortalProject)
                    .join(PortalProject, PortalProject.id == PortalTask.project_id)
                    .where(PortalTask.status == "COMPLETED")
                    .order_by(PortalTask.updated_at.desc())
                    .limit(200)
                ).all()
                rows = [
                    {
                        "project": {
                            "primary": project.name,
                            "secondary": project.project_engineer or "",
                        },
                        "title": task.title,
                        "assignees": "See Project Team",
                        "status": task.status,
                        "priority": task.priority,
                        "progress": int(task.progress or 0),
                        "due_date": task.due_date or "—",
                    }
                    for task, project in completed
                ]
            else:
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
                can_create_task=has_permission(
                    normalize_role(account.role), Permission.PROJECT_EDIT
                ),
            ),
        )

    return router
