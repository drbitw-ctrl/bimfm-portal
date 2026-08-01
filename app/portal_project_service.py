"""PostgreSQL-native project, member-directory, and assignment queries.

Release 20.8 keeps the original project-member identity separate from the HR
freelancer profile. Both datasets live in PostgreSQL; no projects.db runtime
synchronization is required.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.models import (
    Freelancer,
    ProjectMember,
    PortalProject,
    PortalProjectMember,
    PortalTask,
    PortalTaskAssignment,
)
from app.models.common import utc_now

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
    project_member_count: int = 0
    mapped_project_member_count: int = 0
    unmapped_project_member_count: int = 0


def _project_member_records(database: Session) -> list[ProjectMember]:
    return list(
        database.scalars(
            select(ProjectMember).order_by(
                ProjectMember.is_active.desc(),
                ProjectMember.member_name,
                ProjectMember.id,
            )
        ).all()
    )


def _member_resolution(database: Session) -> tuple[
    dict[int, ProjectMember],
    dict[int, int],
    set[int],
]:
    """Return source member rows, source→HR mapping, and placeholder IDs."""
    by_source: dict[int, ProjectMember] = {}
    source_to_hr: dict[int, int] = {}
    placeholder_ids: set[int] = set()
    for member in _project_member_records(database):
        if member.source_freelancer_id is None:
            continue
        source_id = int(member.source_freelancer_id)
        by_source[source_id] = member
        placeholder_ids.add(source_id)
        if member.freelancer_id is not None:
            source_to_hr[source_id] = int(member.freelancer_id)
    return by_source, source_to_hr, placeholder_ids


def _effective_owner(
    freelancer_id: int,
    *,
    source_to_hr: dict[int, int],
    placeholder_ids: set[int],
) -> int | None:
    source_id = int(freelancer_id)
    if source_id in source_to_hr:
        return source_to_hr[source_id]
    if source_id in placeholder_ids:
        return None
    return source_id


def resolved_assignment_ids(
    database: Session,
    *,
    freelancer_id: int,
) -> set[int]:
    """IDs whose assignments should be visible to one HR freelancer."""
    ids = {int(freelancer_id)}
    for source_id, target_id in database.execute(
        select(ProjectMember.source_freelancer_id, ProjectMember.freelancer_id)
        .where(
            ProjectMember.source_freelancer_id.is_not(None),
            ProjectMember.freelancer_id == freelancer_id,
            ProjectMember.is_active.is_(True),
        )
    ).all():
        if source_id is not None and target_id is not None:
            ids.add(int(source_id))
    return ids


def current_freelancer_portal_tasks(
    database: Session,
    *,
    freelancer_id: int,
    limit: int = 100,
) -> list[AssignedPortalTask]:
    """Return active tasks assigned directly or through a mapped project member."""
    assignment_ids = resolved_assignment_ids(
        database,
        freelancer_id=freelancer_id,
    )
    statement = (
        select(PortalTask, PortalProject)
        .join(
            PortalTaskAssignment,
            PortalTaskAssignment.task_id == PortalTask.id,
        )
        .join(PortalProject, PortalProject.id == PortalTask.project_id)
        .where(
            PortalTaskAssignment.freelancer_id.in_(assignment_ids),
            PortalTask.status.notin_(CLOSED_TASK_STATUSES),
        )
        .distinct()
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
    """Return a task when directly assigned or assigned through member mapping."""
    assignment_ids = resolved_assignment_ids(
        database,
        freelancer_id=freelancer_id,
    )
    statement = (
        select(PortalTask, PortalProject)
        .join(
            PortalTaskAssignment,
            PortalTaskAssignment.task_id == PortalTask.id,
        )
        .join(PortalProject, PortalProject.id == PortalTask.project_id)
        .where(
            PortalTask.id == task_id,
            PortalTaskAssignment.freelancer_id.in_(assignment_ids),
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


def _task_sets_by_owner(
    database: Session,
    *,
    status_mode: str,
) -> dict[int, set[int]]:
    by_source, source_to_hr, placeholder_ids = _member_resolution(database)
    del by_source
    statement = select(
        PortalTaskAssignment.freelancer_id,
        PortalTask.id,
        PortalTask.status,
        PortalTask.due_date,
    ).join(PortalTask, PortalTask.id == PortalTaskAssignment.task_id)
    today = date.today()
    result: dict[int, set[int]] = {}
    for assignment_id, task_id, status, due_date in database.execute(statement).all():
        include = False
        if status_mode == "active":
            include = status not in CLOSED_TASK_STATUSES
        elif status_mode == "completed":
            include = status == "COMPLETED"
        elif status_mode == "overdue":
            include = (
                status not in CLOSED_TASK_STATUSES
                and due_date is not None
                and due_date < today
            )
        else:
            raise ValueError(f"Unknown task status mode: {status_mode}")
        if not include:
            continue
        owner_id = _effective_owner(
            int(assignment_id),
            source_to_hr=source_to_hr,
            placeholder_ids=placeholder_ids,
        )
        if owner_id is None:
            continue
        result.setdefault(owner_id, set()).add(int(task_id))
    return result


def _project_sets_by_owner(database: Session) -> dict[int, set[int]]:
    _, source_to_hr, placeholder_ids = _member_resolution(database)
    result: dict[int, set[int]] = {}
    statement = select(
        PortalProjectMember.freelancer_id,
        PortalProjectMember.project_id,
    ).where(PortalProjectMember.is_active.is_(True))
    for assignment_id, project_id in database.execute(statement).all():
        owner_id = _effective_owner(
            int(assignment_id),
            source_to_hr=source_to_hr,
            placeholder_ids=placeholder_ids,
        )
        if owner_id is None:
            continue
        result.setdefault(owner_id, set()).add(int(project_id))
    return result


def active_task_counts_by_freelancer(database: Session) -> dict[int, int]:
    return {
        owner_id: len(task_ids)
        for owner_id, task_ids in _task_sets_by_owner(
            database,
            status_mode="active",
        ).items()
    }


def hr_freelancer_choices(database: Session) -> list[Freelancer]:
    """Return HR profiles, excluding imported LEGACY project placeholders."""
    placeholder_ids = {
        int(value)
        for value in database.scalars(
            select(ProjectMember.source_freelancer_id).where(
                ProjectMember.source_freelancer_id.is_not(None)
            )
        ).all()
        if value is not None
    }
    statement = select(Freelancer).order_by(
        Freelancer.is_active.desc(),
        Freelancer.full_name,
        Freelancer.id,
    )
    if placeholder_ids:
        statement = statement.where(Freelancer.id.notin_(placeholder_ids))
    return list(database.scalars(statement).all())


def project_member_rows(database: Session) -> list[dict[str, object]]:
    """Return the PostgreSQL project-member directory and mapping state."""
    members = _project_member_records(database)
    source_ids = {
        int(member.source_freelancer_id)
        for member in members
        if member.source_freelancer_id is not None
    }

    project_sets: dict[int, set[int]] = {source_id: set() for source_id in source_ids}
    task_sets: dict[int, set[int]] = {source_id: set() for source_id in source_ids}
    completed_sets: dict[int, set[int]] = {source_id: set() for source_id in source_ids}
    overdue_sets: dict[int, set[int]] = {source_id: set() for source_id in source_ids}

    if source_ids:
        for source_id, project_id in database.execute(
            select(
                PortalProjectMember.freelancer_id,
                PortalProjectMember.project_id,
            ).where(
                PortalProjectMember.freelancer_id.in_(source_ids),
                PortalProjectMember.is_active.is_(True),
            )
        ).all():
            project_sets.setdefault(int(source_id), set()).add(int(project_id))

        today = date.today()
        for source_id, task_id, status, due_date in database.execute(
            select(
                PortalTaskAssignment.freelancer_id,
                PortalTask.id,
                PortalTask.status,
                PortalTask.due_date,
            )
            .join(PortalTask, PortalTask.id == PortalTaskAssignment.task_id)
            .where(PortalTaskAssignment.freelancer_id.in_(source_ids))
        ).all():
            source = int(source_id)
            if status == "COMPLETED":
                completed_sets.setdefault(source, set()).add(int(task_id))
            elif status not in CLOSED_TASK_STATUSES:
                task_sets.setdefault(source, set()).add(int(task_id))
                if due_date is not None and due_date < today:
                    overdue_sets.setdefault(source, set()).add(int(task_id))

    freelancer_ids = {
        int(member.freelancer_id)
        for member in members
        if member.freelancer_id is not None
    }
    mapped_profiles = {
        freelancer.id: freelancer
        for freelancer in database.scalars(
            select(Freelancer).where(Freelancer.id.in_(freelancer_ids))
        ).all()
    } if freelancer_ids else {}

    rows: list[dict[str, object]] = []
    for member in members:
        source_id = int(member.source_freelancer_id) if member.source_freelancer_id else None
        mapped = mapped_profiles.get(member.freelancer_id) if member.freelancer_id else None
        active_tasks = len(task_sets.get(source_id, set())) if source_id else 0
        project_count = len(project_sets.get(source_id, set())) if source_id else 0
        if mapped is not None:
            mapping_status = "Mapped"
        elif active_tasks or project_count:
            mapping_status = "Unmapped · assignments preserved"
        else:
            mapping_status = "Unmapped"
        rows.append(
            {
                "id": member.id,
                "member_code": member.member_code or "—",
                "member_name": member.member_name,
                "email": member.email or "—",
                "is_active": bool(member.is_active),
                "source_freelancer_id": source_id,
                "freelancer_id": member.freelancer_id,
                "mapped_name": mapped.full_name if mapped else None,
                "mapped_code": mapped.freelancer_code if mapped else None,
                "mapped_active": bool(mapped.is_active) if mapped else None,
                "project_count": project_count,
                "active_task_count": active_tasks,
                "completed_task_count": len(completed_sets.get(source_id, set())) if source_id else 0,
                "overdue_task_count": len(overdue_sets.get(source_id, set())) if source_id else 0,
                "mapping_status": mapping_status,
                "source_key": member.source_key,
            }
        )
    return rows


def map_project_member(
    database: Session,
    *,
    project_member_id: int,
    freelancer_id: int | None,
    admin_id: int,
) -> ProjectMember:
    member = database.get(ProjectMember, project_member_id)
    if member is None:
        raise ValueError("Project member was not found.")

    if freelancer_id in (None, 0):
        member.freelancer_id = None
        member.mapped_by_admin_id = int(admin_id)
        member.mapped_at = None
        member.updated_at = utc_now()
        return member

    placeholder_ids = {
        int(value)
        for value in database.scalars(
            select(ProjectMember.source_freelancer_id).where(
                ProjectMember.source_freelancer_id.is_not(None)
            )
        ).all()
        if value is not None
    }
    if int(freelancer_id) in placeholder_ids:
        raise ValueError(
            "Select an HR freelancer account, not an imported project-member placeholder."
        )

    freelancer = database.get(Freelancer, int(freelancer_id))
    if freelancer is None:
        raise ValueError("The selected HR freelancer was not found.")
    if not freelancer.is_active:
        raise ValueError("The selected HR freelancer is inactive.")

    member.freelancer_id = freelancer.id
    member.mapped_by_admin_id = int(admin_id)
    member.mapped_at = utc_now()
    member.updated_at = utc_now()
    return member


def team_assignment_rows(database: Session) -> list[dict[str, object]]:
    """Return HR team workload after resolving project-member mappings."""
    freelancers = [
        freelancer
        for freelancer in hr_freelancer_choices(database)
        if freelancer.is_active
    ]
    project_sets = _project_sets_by_owner(database)
    active_sets = _task_sets_by_owner(database, status_mode="active")
    completed_sets = _task_sets_by_owner(database, status_mode="completed")
    overdue_sets = _task_sets_by_owner(database, status_mode="overdue")

    rows: list[dict[str, object]] = []
    for freelancer in freelancers:
        projects = len(project_sets.get(freelancer.id, set()))
        active_tasks = len(active_sets.get(freelancer.id, set()))
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
                "completed_task_count": len(
                    completed_sets.get(freelancer.id, set())
                ),
                "overdue_task_count": len(
                    overdue_sets.get(freelancer.id, set())
                ),
                "assignment_status": assignment_status,
            }
        )
    return rows


def project_data_health(database: Session) -> ProjectDataHealth:
    project_members = _project_member_records(database)
    active_project_members = [member for member in project_members if member.is_active]
    mapped_project_members = [
        member for member in active_project_members if member.freelancer_id is not None
    ]
    unmapped_project_members = [
        member for member in active_project_members if member.freelancer_id is None
    ]

    active_freelancers = len(
        [freelancer for freelancer in hr_freelancer_choices(database) if freelancer.is_active]
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

    project_sets = _project_sets_by_owner(database)
    task_sets = _task_sets_by_owner(database, status_mode="active")
    assigned_hr_ids = set(project_sets) | set(task_sets)
    assigned_member_count = len(assigned_hr_ids)
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
        project_member_count=len(active_project_members),
        mapped_project_member_count=len(mapped_project_members),
        unmapped_project_member_count=len(unmapped_project_members),
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

    by_source, source_to_hr, placeholder_ids = _member_resolution(database)
    del by_source
    member_tokens: dict[int, set[str]] = {}
    for project_id, assignment_id in database.execute(
        select(
            PortalProjectMember.project_id,
            PortalProjectMember.freelancer_id,
        ).where(PortalProjectMember.is_active.is_(True))
    ).all():
        assignment_id = int(assignment_id)
        owner_id = _effective_owner(
            assignment_id,
            source_to_hr=source_to_hr,
            placeholder_ids=placeholder_ids,
        )
        token = (
            f"hr:{owner_id}"
            if owner_id is not None
            else f"project-member:{assignment_id}"
        )
        member_tokens.setdefault(int(project_id), set()).add(token)

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
            "member_count": len(member_tokens.get(project.id, set())),
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
        by_source, _, _ = _member_resolution(database)
        freelancer_ids = {
            int(fid)
            for fid in database.scalars(
                select(PortalTaskAssignment.freelancer_id).where(
                    PortalTaskAssignment.task_id.in_(task_ids)
                )
            ).all()
        }
        profiles = {
            freelancer.id: freelancer
            for freelancer in database.scalars(
                select(Freelancer).where(Freelancer.id.in_(freelancer_ids))
            ).all()
        } if freelancer_ids else {}
        mapped_ids = {
            int(member.freelancer_id)
            for member in by_source.values()
            if member.freelancer_id is not None
        }
        mapped_profiles = {
            freelancer.id: freelancer
            for freelancer in database.scalars(
                select(Freelancer).where(Freelancer.id.in_(mapped_ids))
            ).all()
        } if mapped_ids else {}

        for task_id, assignment_id in database.execute(
            select(
                PortalTaskAssignment.task_id,
                PortalTaskAssignment.freelancer_id,
            )
            .where(PortalTaskAssignment.task_id.in_(task_ids))
            .order_by(PortalTaskAssignment.task_id, PortalTaskAssignment.id)
        ).all():
            assignment_id = int(assignment_id)
            member = by_source.get(assignment_id)
            if member is not None:
                if member.freelancer_id is not None:
                    mapped = mapped_profiles.get(int(member.freelancer_id))
                    label = (
                        f"{member.member_name} → {mapped.full_name}"
                        if mapped
                        else f"{member.member_name} → unavailable HR profile"
                    )
                else:
                    label = f"{member.member_name} (Unmapped)"
            else:
                profile = profiles.get(assignment_id)
                label = profile.full_name if profile else f"Freelancer #{assignment_id}"
            assignee_names.setdefault(int(task_id), []).append(label)

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
