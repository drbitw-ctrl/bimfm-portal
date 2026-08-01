"""Project-management foundation routes for BIMFM Portal v2.

This module is intentionally isolated from ``app.main``.  The router factory
accepts the existing authentication and template helpers so the legacy HR
routes can remain operational while the application is refactored in stages.
"""

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PortalProject, PortalTask, SyncedProjectTask


AdminResolver = Callable[[Request, Session], Any]
TemplateContextBuilder = Callable[..., dict[str, Any]]


def create_portal_router(
    *,
    templates: Jinja2Templates,
    get_current_admin: AdminResolver,
    template_context: TemplateContextBuilder,
) -> APIRouter:
    """Build the project-management router using existing app helpers."""

    router = APIRouter(tags=["BIMFM Portal"])

    definitions = {
        "my-work": (
            "My Work",
            "Your assigned work, approvals, attendance and upcoming deadlines.",
        ),
        "projects": (
            "Projects",
            "Unified project register migrated from Task Manager Pro.",
        ),
        "tasks": (
            "Tasks",
            "Search, assign and update operational tasks from one shared database.",
        ),
        "team-workload": (
            "Team Availability / Workload",
            "Live attendance, active assignments and capacity by member.",
        ),
        "performance": (
            "Performance",
            "Operational completion, timeliness and workload indicators.",
        ),
        "reports": (
            "Project Reports",
            "Project progress, overdue work and delivery reporting.",
        ),
        "calendar": (
            "Calendar",
            "Project deadlines, milestones, leave, overtime and holidays.",
        ),
    }

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

        project_count = int(
            database.scalar(select(func.count(PortalProject.id))) or 0
        )
        task_count = int(database.scalar(select(func.count(PortalTask.id))) or 0)
        active_count = int(
            database.scalar(
                select(func.count(PortalTask.id)).where(
                    PortalTask.status.notin_(["COMPLETED", "CANCELLED"])
                )
            )
            or 0
        )
        synced_count = int(
            database.scalar(
                select(func.count(SyncedProjectTask.id)).where(
                    SyncedProjectTask.is_active.is_(True)
                )
            )
            or 0
        )

        cards = [
            {
                "label": "Unified projects",
                "value": project_count,
                "note": "Shared database records",
            },
            {
                "label": "Unified tasks",
                "value": task_count,
                "note": "Portal-native records",
            },
            {
                "label": "Active tasks",
                "value": active_count,
                "note": "Open operational work",
            },
            {
                "label": "Legacy synced rows",
                "value": synced_count,
                "note": "Available for migration",
            },
        ]

        rows: list[list[Any]] = []
        headings: list[str] = []

        if module_name == "projects":
            headings = ["Code", "Project", "Status", "Progress", "Deadline"]
            projects = database.scalars(
                select(PortalProject)
                .order_by(PortalProject.updated_at.desc())
                .limit(50)
            ).all()
            rows = [
                [
                    project.project_code,
                    project.name,
                    project.status,
                    f"{project.progress}%",
                    project.deadline or "—",
                ]
                for project in projects
            ]
        elif module_name in {"tasks", "my-work"}:
            headings = ["Task", "Status", "Priority", "Progress", "Due"]
            query = select(PortalTask).order_by(PortalTask.updated_at.desc()).limit(50)
            if view == "active":
                query = query.where(
                    PortalTask.status.notin_(["COMPLETED", "CANCELLED"])
                )
            elif view == "completed":
                query = query.where(PortalTask.status == "COMPLETED")

            tasks = database.scalars(query).all()
            rows = [
                [
                    task.title,
                    task.status,
                    task.priority,
                    f"{task.progress}%",
                    task.due_date or "—",
                ]
                for task in tasks
            ]

        return templates.TemplateResponse(
            request=request,
            name="portal_module.html",
            context=template_context(
                request,
                page_title=page_title,
                page_description=description,
                cards=cards,
                headings=headings,
                rows=rows,
                account=account,
            ),
        )

    return router
