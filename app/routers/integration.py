"""BIMFM Portal v2 integration routes.

Extracted from the verified legacy application without changing route behavior.
Dependencies are injected during application startup as a compatibility bridge.
"""
from __future__ import annotations

from fastapi import APIRouter


def configure_integration_routes(legacy_namespace: dict[str, object]) -> APIRouter:
    globals().update(legacy_namespace)
    router = APIRouter(tags=["Integration"])
    globals()["router"] = router

    @router.post("/api/integration/project-tasks/sync")
    def project_task_sync_api(
        payload: ProjectTaskSyncPayload,
        request: Request,
    ):
        if not project_sync_token_valid(request):
            raise HTTPException(
                status_code=401,
                detail="Invalid project synchronization token.",
            )

        with SessionLocal() as database:
            return apply_project_task_snapshot(
                database,
                payload=payload,
                request_ip=request_ip(request),
            )

    @router.get("/api/integration/project-tasks/status")
    def project_task_sync_status_api(request: Request):
        if not project_sync_token_valid(request):
            raise HTTPException(
                status_code=401,
                detail="Invalid project synchronization token.",
            )

        with SessionLocal() as database:
            last_run = database.scalar(
                select(ProjectSyncRun)
                .where(
                    ProjectSyncRun.source_system
                    == PROJECT_SYNC_SOURCE_SYSTEM
                )
                .order_by(ProjectSyncRun.id.desc())
                .limit(1)
            )
            return {
                "source_system": PROJECT_SYNC_SOURCE_SYSTEM,
                "last_sync": (
                    {
                        "id": last_run.id,
                        "status": last_run.status,
                        "received_count": last_run.received_count,
                        "mapped_count": last_run.mapped_count,
                        "unmapped_count": last_run.unmapped_count,
                        "completed_at_utc": (
                            last_run.completed_at_utc.isoformat()
                            if last_run.completed_at_utc
                            else None
                        ),
                        "message": last_run.message,
                    }
                    if last_run
                    else None
                ),
                "active_tasks": int(
                    database.scalar(
                        select(func.count(SyncedProjectTask.id)).where(
                            SyncedProjectTask.source_system
                            == PROJECT_SYNC_SOURCE_SYSTEM,
                            SyncedProjectTask.is_active.is_(True),
                        )
                    )
                    or 0
                ),
                "unmapped_active_tasks": int(
                    database.scalar(
                        select(func.count(SyncedProjectTask.id)).where(
                            SyncedProjectTask.source_system
                            == PROJECT_SYNC_SOURCE_SYSTEM,
                            SyncedProjectTask.is_active.is_(True),
                            SyncedProjectTask.freelancer_id.is_(None),
                        )
                    )
                    or 0
                ),
            }

    @router.get(
        "/admin/integration/projects",
        response_class=HTMLResponse,
    )
    def admin_project_integration(request: Request):
        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse(
                    "/admin/login",
                    status_code=303,
                )

            freelancers = list(
                database.scalars(
                    select(Freelancer)
                    .where(Freelancer.is_active.is_(True))
                    .order_by(Freelancer.full_name)
                ).all()
            )
            freelancer_names = {
                freelancer.id: (
                    f"{freelancer.freelancer_code} — "
                    f"{freelancer.full_name}"
                )
                for freelancer in freelancers
            }

            source_members = list(
                database.scalars(
                    select(ProjectSourceMember)
                    .where(
                        ProjectSourceMember.source_system
                        == PROJECT_SYNC_SOURCE_SYSTEM
                    )
                    .order_by(ProjectSourceMember.source_member_name)
                ).all()
            )
            member_rows = [
                {
                    "id": row.id,
                    "source_member_name": row.source_member_name,
                    "freelancer_id": row.freelancer_id or 0,
                    "mapped_name": freelancer_names.get(
                        row.freelancer_id,
                        "Not mapped",
                    ),
                    "active_task_count": row.active_task_count,
                    "last_seen": format_sync_timestamp(row.last_seen_at),
                }
                for row in source_members
            ]

            synced_tasks = list(
                database.scalars(
                    select(SyncedProjectTask)
                    .where(
                        SyncedProjectTask.source_system
                        == PROJECT_SYNC_SOURCE_SYSTEM
                    )
                    .order_by(
                        SyncedProjectTask.is_active.desc(),
                        SyncedProjectTask.deadline.is_(None),
                        SyncedProjectTask.deadline,
                        SyncedProjectTask.project_code,
                    )
                    .limit(200)
                ).all()
            )
            task_rows = [
                {
                    "source_project_id": row.source_project_id,
                    "source_member_name": row.source_member_name,
                    "mapped_name": freelancer_names.get(
                        row.freelancer_id,
                        "Not mapped",
                    ),
                    "project_code": row.project_code,
                    "project_name": row.project_name or "",
                    "deadline": (
                        row.deadline.isoformat()
                        if row.deadline
                        else "—"
                    ),
                    "status": row.project_status or "—",
                    "discipline": row.discipline or "—",
                    "progress": row.progress,
                    "is_active": row.is_active,
                    "synced_at": format_sync_timestamp(row.synced_at),
                }
                for row in synced_tasks
            ]

            sync_runs = list(
                database.scalars(
                    select(ProjectSyncRun)
                    .where(
                        ProjectSyncRun.source_system
                        == PROJECT_SYNC_SOURCE_SYSTEM
                    )
                    .order_by(ProjectSyncRun.id.desc())
                    .limit(10)
                ).all()
            )
            sync_rows = [
                {
                    "id": row.id,
                    "status": row.status,
                    "received_count": row.received_count,
                    "mapped_count": row.mapped_count,
                    "unmapped_count": row.unmapped_count,
                    "active_count": row.active_count,
                    "completed_at": format_sync_timestamp(
                        row.completed_at_utc
                    ),
                    "message": row.message or "",
                }
                for row in sync_runs
            ]

            active_task_count = int(
                database.scalar(
                    select(func.count(SyncedProjectTask.id)).where(
                        SyncedProjectTask.source_system
                        == PROJECT_SYNC_SOURCE_SYSTEM,
                        SyncedProjectTask.is_active.is_(True),
                    )
                )
                or 0
            )
            mapped_task_count = int(
                database.scalar(
                    select(func.count(SyncedProjectTask.id)).where(
                        SyncedProjectTask.source_system
                        == PROJECT_SYNC_SOURCE_SYSTEM,
                        SyncedProjectTask.is_active.is_(True),
                        SyncedProjectTask.freelancer_id.is_not(None),
                    )
                )
                or 0
            )
            unmapped_task_count = int(
                database.scalar(
                    select(func.count(SyncedProjectTask.id)).where(
                        SyncedProjectTask.source_system
                        == PROJECT_SYNC_SOURCE_SYSTEM,
                        SyncedProjectTask.is_active.is_(True),
                        SyncedProjectTask.freelancer_id.is_(None),
                    )
                )
                or 0
            )
            last_run = sync_runs[0] if sync_runs else None

            return templates.TemplateResponse(
                request=request,
                name="admin_project_integration.html",
                context=template_context(
                    request,
                    admin=admin,
                    freelancers=freelancers,
                    member_rows=member_rows,
                    task_rows=task_rows,
                    sync_rows=sync_rows,
                    active_task_count=active_task_count,
                    mapped_task_count=mapped_task_count,
                    unmapped_task_count=unmapped_task_count,
                    last_sync=format_sync_timestamp(
                        last_run.completed_at_utc
                        if last_run
                        else None
                    ),
                    using_default_token=(
                        PROJECT_SYNC_USING_DEFAULT_TOKEN
                    ),
                ),
            )

    @router.post(
        "/admin/integration/projects/source-members/{source_member_id}/map"
    )
    def map_project_source_member(
        source_member_id: int,
        request: Request,
        csrf: str = Form(...),
        freelancer_id: int = Form(0),
    ):
        if not validate_csrf(request, csrf):
            set_flash(request, "Invalid form token.", "error")
            return RedirectResponse(
                "/admin/integration/projects",
                status_code=303,
            )

        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse(
                    "/admin/login",
                    status_code=303,
                )

            source_member = database.get(
                ProjectSourceMember,
                source_member_id,
            )
            if (
                source_member is None
                or source_member.source_system
                != PROJECT_SYNC_SOURCE_SYSTEM
            ):
                set_flash(
                    request,
                    "Project source member was not found.",
                    "error",
                )
                return RedirectResponse(
                    "/admin/integration/projects",
                    status_code=303,
                )

            mapped_freelancer_id: Optional[int] = None
            mapped_name = "Unmapped"
            if freelancer_id > 0:
                freelancer = database.get(Freelancer, freelancer_id)
                if freelancer is None or not freelancer.is_active:
                    set_flash(
                        request,
                        "Selected freelancer is unavailable.",
                        "error",
                    )
                    return RedirectResponse(
                        "/admin/integration/projects",
                        status_code=303,
                    )
                mapped_freelancer_id = freelancer.id
                mapped_name = (
                    f"{freelancer.freelancer_code} "
                    f"{freelancer.full_name}"
                )

            affected_tasks = map_source_member(
                database,
                source_member=source_member,
                freelancer_id=mapped_freelancer_id,
            )

            write_audit(
                database,
                actor_type="HR_ADMIN",
                actor_id=admin.id,
                action="MAP_PROJECT_SOURCE_MEMBER",
                request=request,
                target_type="PROJECT_SOURCE_MEMBER",
                target_id=source_member.id,
                details=(
                    f"Mapped '{source_member.source_member_name}' "
                    f"to {mapped_name}; updated "
                    f"{affected_tasks} synchronized task(s)."
                ),
            )
            database.commit()

        set_flash(
            request,
            "Project member mapping updated.",
            "success",
        )
        return RedirectResponse(
            "/admin/integration/projects",
            status_code=303,
        )

    return router
