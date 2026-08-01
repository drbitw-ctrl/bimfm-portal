"""PostgreSQL-native BIMFM Portal project modules."""
from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Freelancer, PortalProject, PortalTask
from app.portal_project_service import (
    active_task_overview_rows,
    project_data_health,
    project_overview_rows,
    team_assignment_rows,
)

AdminResolver = Callable[[Request, Session], Any]
TemplateContextBuilder = Callable[..., dict[str, Any]]


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

        rows: list[list[Any]] = []
        headings: list[str] = []
        section_title = "PostgreSQL-native records"
        section_note = (
            "This module reads the migrated project tables directly. "
            "No projects.db sync or name mapping is required."
        )

        if module_name == "projects":
            headings = [
                "Code",
                "Project",
                "Status",
                "Progress",
                "Members",
                "Active Tasks",
                "Deadline",
            ]
            rows = [
                [
                    row["code"],
                    row["name"],
                    row["status"],
                    f"{row['progress']}%",
                    row["member_count"],
                    row["active_task_count"],
                    row["deadline"],
                ]
                for row in project_overview_rows(database, limit=100)
            ]
        elif module_name in {"tasks", "my-work"}:
            headings = [
                "Project",
                "Task",
                "Assignees",
                "Status",
                "Priority",
                "Progress",
                "Due",
            ]
            task_rows = active_task_overview_rows(database, limit=200)
            if view == "completed":
                completed = database.execute(
                    select(PortalTask, PortalProject)
                    .join(PortalProject, PortalProject.id == PortalTask.project_id)
                    .where(PortalTask.status == "COMPLETED")
                    .order_by(PortalTask.updated_at.desc())
                    .limit(200)
                ).all()
                rows = [
                    [
                        project.project_code,
                        task.title,
                        "See project team",
                        task.status,
                        task.priority,
                        f"{task.progress}%",
                        task.due_date or "—",
                    ]
                    for task, project in completed
                ]
            else:
                rows = [
                    [
                        row["project_code"],
                        row["title"],
                        row["assignees"],
                        row["status"],
                        row["priority"],
                        f"{row['progress']}%",
                        row["due_date"],
                    ]
                    for row in task_rows
                ]
        elif module_name == "team-workload":
            headings = [
                "Member",
                "Code",
                "Projects",
                "Active Tasks",
                "Completed",
                "Overdue",
                "Status",
            ]
            rows = [
                [
                    row["name"],
                    row["code"],
                    row["project_count"],
                    row["active_task_count"],
                    row["completed_task_count"],
                    row["overdue_task_count"],
                    row["assignment_status"],
                ]
                for row in team_assignment_rows(database)
            ]
        elif module_name in {"performance", "reports"}:
            headings = ["Indicator", "Result", "Meaning"]
            rows = [
                ["Active projects", health.project_count, "Projects available in PostgreSQL"],
                ["Open tasks", health.active_task_count, "Not completed or cancelled"],
                ["Overdue tasks", overdue_task_count, "Open tasks past due date"],
                ["Members with projects", health.assigned_member_count, "Active project membership"],
                ["Members without projects", health.unassigned_member_count, "Needs assignment review"],
                ["Open tasks without assignees", health.active_tasks_without_assignees, "Needs task assignment"],
            ]
        elif module_name == "calendar":
            headings = ["Due Date", "Project", "Task", "Status", "Progress"]
            rows = [
                [
                    row["due_date"],
                    row["project_code"],
                    row["title"],
                    row["status"],
                    f"{row['progress']}%",
                ]
                for row in active_task_overview_rows(database, limit=200)
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
                headings=headings,
                rows=rows,
                section_title=section_title,
                section_note=section_note,
                account=account,
            ),
        )

    return router
