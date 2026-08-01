"""PostgreSQL-native project and assignment queries.

Release 20.7 makes the portal tables created by the one-time SQLite migration
(`portal_projects`, `portal_tasks`, `portal_project_members`, and
`portal_task_assignments`) the only live source for project presentation.
Legacy synchronization tables remain readable for historical compatibility but
are not used by these functions.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.models import (
    Freelancer,
    PortalProject,
    PortalProjectMember,
    PortalTask,
    PortalTaskAssignment,
)

CLOSED_TASK_STATUSES = ("COMPLETED", "CANCELLED")
CLOSED_PROJECT_STATUSES = ("COMPLETED", "CANCELLED", "CLOSED")


@dataclass(frozen=True)
class AssignedPortalTask:
    id: int
    project_code: str
    project_name: str
    deadline: Optional[date]
    project_status: str
    priority: str
    discipline: Optional[str]
    progress: int
    task_description: str


@dataclass(frozen=True)
class ProjectDataHealth:
    active_freelancers: int
    project_count: int
    active_task_count: int
    assigned_member_count: int
    unassigned_member_count: int
    projects_without_members: int
    active_tasks_without_assignees: int


def current_freelancer_portal_tasks(
    database: Session,
    *,
    freelancer_id: int,
    limit: int = 100,
) -> list[AssignedPortalTask]:
    """Return active PostgreSQL-native tasks assigned to one freelancer."""
    statement = (
        select(PortalTask, PortalProject)
        .join(
            PortalTaskAssignment,
            PortalTaskAssignment.task_id == PortalTask.id,
        )
        .join(PortalProject, PortalProject.id == PortalTask.project_id)
        .where(
            PortalTaskAssignment.freelancer_id == freelancer_id,
            PortalTask.status.notin_(CLOSED_TASK_STATUSES),
        )
        .order_by(
            PortalTask.due_date.is_(None),
            PortalTask.due_date,
            PortalTask.priority,
            PortalProject.project_code,
            PortalTask.id,
        )
        .limit(max(1, min(int(limit), 500)))
    )
    return [
        AssignedPortalTask(
            id=task.id,
            project_code=project.project_code,
            project_name=project.name,
            deadline=task.due_date,
            project_status=task.status,
            priority=task.priority,
            discipline=task.discipline or project.discipline,
            progress=max(0, min(100, int(task.progress or 0))),
            task_description=task.description or task.title,
        )
        for task, project in database.execute(statement).all()
    ]


def portal_task_for_freelancer(
    database: Session,
    *,
    task_id: int,
    freelancer_id: int,
) -> Optional[AssignedPortalTask]:
    """Return a task only when it is currently assigned to the freelancer."""
    statement = (
        select(PortalTask, PortalProject)
        .join(
            PortalTaskAssignment,
            PortalTaskAssignment.task_id == PortalTask.id,
        )
        .join(PortalProject, PortalProject.id == PortalTask.project_id)
        .where(
            PortalTask.id == task_id,
            PortalTaskAssignment.freelancer_id == freelancer_id,
            PortalTask.status.notin_(CLOSED_TASK_STATUSES),
        )
        .limit(1)
    )
    row = database.execute(statement).first()
    if row is None:
        return None
    task, project = row
    return AssignedPortalTask(
        id=task.id,
        project_code=project.project_code,
        project_name=project.name,
        deadline=task.due_date,
        project_status=task.status,
        priority=task.priority,
        discipline=task.discipline or project.discipline,
        progress=max(0, min(100, int(task.progress or 0))),
        task_description=task.description or task.title,
    )


def active_task_counts_by_freelancer(database: Session) -> dict[int, int]:
    rows = database.execute(
        select(
            PortalTaskAssignment.freelancer_id,
            func.count(distinct(PortalTask.id)),
        )
        .join(PortalTask, PortalTask.id == PortalTaskAssignment.task_id)
        .where(PortalTask.status.notin_(CLOSED_TASK_STATUSES))
        .group_by(PortalTaskAssignment.freelancer_id)
    ).all()
    return {int(freelancer_id): int(count) for freelancer_id, count in rows}


def team_assignment_rows(database: Session) -> list[dict[str, object]]:
    """Return every active freelancer, including members with zero assignments."""
    freelancers = list(
        database.scalars(
            select(Freelancer)
            .where(Freelancer.is_active.is_(True))
            .order_by(Freelancer.full_name)
        ).all()
    )

    project_counts = {
        int(freelancer_id): int(count)
        for freelancer_id, count in database.execute(
            select(
                PortalProjectMember.freelancer_id,
                func.count(distinct(PortalProjectMember.project_id)),
            )
            .where(PortalProjectMember.is_active.is_(True))
            .group_by(PortalProjectMember.freelancer_id)
        ).all()
    }
    active_task_counts = active_task_counts_by_freelancer(database)
    completed_task_counts = {
        int(freelancer_id): int(count)
        for freelancer_id, count in database.execute(
            select(
                PortalTaskAssignment.freelancer_id,
                func.count(distinct(PortalTask.id)),
            )
            .join(PortalTask, PortalTask.id == PortalTaskAssignment.task_id)
            .where(PortalTask.status == "COMPLETED")
            .group_by(PortalTaskAssignment.freelancer_id)
        ).all()
    }
    today = date.today()
    overdue_counts = {
        int(freelancer_id): int(count)
        for freelancer_id, count in database.execute(
            select(
                PortalTaskAssignment.freelancer_id,
                func.count(distinct(PortalTask.id)),
            )
            .join(PortalTask, PortalTask.id == PortalTaskAssignment.task_id)
            .where(
                PortalTask.status.notin_(CLOSED_TASK_STATUSES),
                PortalTask.due_date.is_not(None),
                PortalTask.due_date < today,
            )
            .group_by(PortalTaskAssignment.freelancer_id)
        ).all()
    }

    rows: list[dict[str, object]] = []
    for freelancer in freelancers:
        projects = project_counts.get(freelancer.id, 0)
        active_tasks = active_task_counts.get(freelancer.id, 0)
        if active_tasks:
            assignment_status = "Assigned"
        elif projects:
            assignment_status = "Project member · no active task"
        else:
            assignment_status = "No project assignment"
        rows.append(
            {
                "freelancer_id": freelancer.id,
                "code": freelancer.freelancer_code,
                "name": freelancer.full_name,
                "project_count": projects,
                "active_task_count": active_tasks,
                "completed_task_count": completed_task_counts.get(
                    freelancer.id, 0
                ),
                "overdue_task_count": overdue_counts.get(freelancer.id, 0),
                "assignment_status": assignment_status,
            }
        )
    return rows


def project_data_health(database: Session) -> ProjectDataHealth:
    active_freelancers = int(
        database.scalar(
            select(func.count(Freelancer.id)).where(
                Freelancer.is_active.is_(True)
            )
        )
        or 0
    )
    project_count = int(database.scalar(select(func.count(PortalProject.id))) or 0)
    active_task_count = int(
        database.scalar(
            select(func.count(PortalTask.id)).where(
                PortalTask.status.notin_(CLOSED_TASK_STATUSES)
            )
        )
        or 0
    )
    # A member is considered assigned when they have either an active project
    # membership or at least one portal task assignment. The one-time SQLite
    # migration can contain legitimate task assignments even when an older
    # project-membership row is absent, so use the union rather than reporting
    # those members as unassigned.
    membership_ids = select(PortalProjectMember.freelancer_id).where(
        PortalProjectMember.is_active.is_(True)
    )
    task_assignment_ids = select(PortalTaskAssignment.freelancer_id)
    assigned_ids = membership_ids.union(task_assignment_ids).subquery()
    assigned_member_count = int(
        database.scalar(
            select(func.count(distinct(assigned_ids.c.freelancer_id)))
            .join(
                Freelancer,
                Freelancer.id == assigned_ids.c.freelancer_id,
            )
            .where(Freelancer.is_active.is_(True))
        )
        or 0
    )
    unassigned_member_count = max(0, active_freelancers - assigned_member_count)

    projects_without_members = int(
        database.scalar(
            select(func.count(PortalProject.id)).where(
                ~select(PortalProjectMember.id)
                .where(
                    PortalProjectMember.project_id == PortalProject.id,
                    PortalProjectMember.is_active.is_(True),
                )
                .exists()
            )
        )
        or 0
    )
    active_tasks_without_assignees = int(
        database.scalar(
            select(func.count(PortalTask.id)).where(
                PortalTask.status.notin_(CLOSED_TASK_STATUSES),
                ~select(PortalTaskAssignment.id)
                .where(PortalTaskAssignment.task_id == PortalTask.id)
                .exists(),
            )
        )
        or 0
    )
    return ProjectDataHealth(
        active_freelancers=active_freelancers,
        project_count=project_count,
        active_task_count=active_task_count,
        assigned_member_count=assigned_member_count,
        unassigned_member_count=unassigned_member_count,
        projects_without_members=projects_without_members,
        active_tasks_without_assignees=active_tasks_without_assignees,
    )


def project_overview_rows(database: Session, *, limit: int = 100) -> list[dict[str, object]]:
    projects = list(
        database.scalars(
            select(PortalProject)
            .order_by(
                PortalProject.status,
                PortalProject.deadline.is_(None),
                PortalProject.deadline,
                PortalProject.project_code,
            )
            .limit(max(1, min(int(limit), 500)))
        ).all()
    )
    member_counts = {
        int(project_id): int(count)
        for project_id, count in database.execute(
            select(
                PortalProjectMember.project_id,
                func.count(distinct(PortalProjectMember.freelancer_id)),
            )
            .where(PortalProjectMember.is_active.is_(True))
            .group_by(PortalProjectMember.project_id)
        ).all()
    }
    active_counts = {
        int(project_id): int(count)
        for project_id, count in database.execute(
            select(PortalTask.project_id, func.count(PortalTask.id))
            .where(PortalTask.status.notin_(CLOSED_TASK_STATUSES))
            .group_by(PortalTask.project_id)
        ).all()
    }
    return [
        {
            "id": project.id,
            "code": project.project_code,
            "name": project.name,
            "status": project.status,
            "priority": project.priority,
            "progress": int(project.progress or 0),
            "deadline": project.deadline.isoformat() if project.deadline else "—",
            "member_count": member_counts.get(project.id, 0),
            "active_task_count": active_counts.get(project.id, 0),
        }
        for project in projects
    ]


def active_task_overview_rows(database: Session, *, limit: int = 200) -> list[dict[str, object]]:
    task_rows = database.execute(
        select(PortalTask, PortalProject)
        .join(PortalProject, PortalProject.id == PortalTask.project_id)
        .where(PortalTask.status.notin_(CLOSED_TASK_STATUSES))
        .order_by(
            PortalTask.due_date.is_(None),
            PortalTask.due_date,
            PortalProject.project_code,
            PortalTask.id,
        )
        .limit(max(1, min(int(limit), 500)))
    ).all()
    task_ids = [task.id for task, _ in task_rows]
    assignee_names: dict[int, list[str]] = {task_id: [] for task_id in task_ids}
    if task_ids:
        for task_id, full_name in database.execute(
            select(PortalTaskAssignment.task_id, Freelancer.full_name)
            .join(Freelancer, Freelancer.id == PortalTaskAssignment.freelancer_id)
            .where(PortalTaskAssignment.task_id.in_(task_ids))
            .order_by(Freelancer.full_name)
        ).all():
            assignee_names.setdefault(int(task_id), []).append(str(full_name))

    return [
        {
            "id": task.id,
            "project_code": project.project_code,
            "project_name": project.name,
            "title": task.title,
            "status": task.status,
            "priority": task.priority,
            "discipline": task.discipline or project.discipline or "—",
            "progress": int(task.progress or 0),
            "due_date": task.due_date.isoformat() if task.due_date else "—",
            "assignees": ", ".join(assignee_names.get(task.id, [])) or "Unassigned",
        }
        for task, project in task_rows
    ]
