"""Portal-native project-member directory and mapping routes.

Project members and HR freelancer accounts are managed inside the portal.
Mapping links those identities without exposing storage implementation details.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter


def configure_integration_routes(legacy_namespace: dict[str, object]) -> APIRouter:
    globals().update(legacy_namespace)
    router = APIRouter(tags=["Project Members"])
    globals()["router"] = router

    @router.post("/api/integration/project-tasks/sync")
    def retired_project_task_sync_api(request: Request):
        del request
        raise HTTPException(
            status_code=410,
            detail=(
                "Legacy project synchronization is retired. Project members, "
                "projects, tasks, assignments, and account mappings are managed "
                "directly in the portal."
            ),
        )

    @router.get("/api/integration/project-tasks/status")
    def project_data_status_api(request: Request):
        del request
        with SessionLocal() as database:
            health = project_data_health(database)
            return {
                "mode": "portal_native",
                "synchronization_required": False,
                "project_members": health.project_member_count,
                "mapped_project_members": health.mapped_project_member_count,
                "unmapped_project_members": health.unmapped_project_member_count,
                "message": (
                    "Project-member identities and their HR mappings are "
                    "stored directly in the portal database."
                ),
            }

    @router.get("/admin/integration/projects", include_in_schema=False)
    def legacy_project_integration_redirect(request: Request):
        with SessionLocal() as database:
            if get_current_admin(request, database) is None:
                return RedirectResponse("/admin/login", status_code=303)
        return RedirectResponse("/admin/project-team", status_code=303)

    @router.get("/admin/project-team", response_class=HTMLResponse)
    def admin_project_team(request: Request):
        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", status_code=303)

            health = project_data_health(database)
            task_rows = active_task_overview_rows(database, limit=200)
            for row in task_rows:
                status = str(row.get("status") or "").upper()
                due_text = str(row.get("due_date") or "")
                delayed = False
                if due_text and due_text != "—":
                    try:
                        delayed = date.fromisoformat(due_text) < date.today()
                    except ValueError:
                        delayed = False
                row["row_highlight"] = (
                    "task-row-delayed" if delayed
                    else "task-row-attention" if status in {"IN_PROGRESS", "FOR_REVIEW"}
                    else ""
                )
            return templates.TemplateResponse(
                request=request,
                name="admin_project_team.html",
                context=template_context(
                    request,
                    admin=admin,
                    health=health,
                    project_member_rows=project_member_rows(database),
                    freelancer_choices=hr_freelancer_choices(database),
                    member_rows=team_assignment_rows(database),
                    project_rows=project_overview_rows(database, limit=100),
                    task_rows=task_rows,
                ),
            )

    def _map_member(
        *,
        project_member_id: int,
        request: Request,
        csrf: str,
        freelancer_id: int,
    ):
        redirect_path = "/admin/project-team"
        if not validate_csrf(request, csrf):
            set_flash(request, "Invalid form token.", "error")
            return RedirectResponse(redirect_path, status_code=303)

        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", status_code=303)
            if str(getattr(admin, "role", "ADMIN")).upper() != "ADMIN":
                set_flash(
                    request,
                    "Only an Administrator can change project-member mappings.",
                    "error",
                )
                return RedirectResponse(redirect_path, status_code=303)
            try:
                member = map_project_member(
                    database,
                    project_member_id=project_member_id,
                    freelancer_id=freelancer_id or None,
                    admin_id=admin.id,
                )
            except ValueError as exc:
                set_flash(request, str(exc), "error")
                return RedirectResponse(redirect_path, status_code=303)

            action = "UNMAP_PROJECT_MEMBER" if not freelancer_id else "MAP_PROJECT_MEMBER"
            details = (
                f"project_member={member.member_name}; "
                f"freelancer_id={member.freelancer_id or 'none'}"
            )
            write_audit(
                database,
                actor_type="HR_ADMIN",
                actor_id=admin.id,
                action=action,
                request=request,
                target_type="PROJECT_MEMBER",
                target_id=member.id,
                details=details,
            )
            database.commit()

        if freelancer_id:
            set_flash(
                request,
                "Project member mapped to the selected HR freelancer.",
                "success",
            )
        else:
            set_flash(request, "Project member mapping removed.", "success")
        return RedirectResponse(redirect_path, status_code=303)

    @router.post("/admin/project-members/{project_member_id}/map")
    def map_project_member_submit(
        project_member_id: int,
        request: Request,
        csrf: str = Form(...),
        freelancer_id: int = Form(0),
    ):
        return _map_member(
            project_member_id=project_member_id,
            request=request,
            csrf=csrf,
            freelancer_id=freelancer_id,
        )

    # Compatibility with the mapping form used by older releases.
    @router.post(
        "/admin/integration/projects/source-members/{source_member_id}/map",
        include_in_schema=False,
    )
    def legacy_member_mapping_submit(
        source_member_id: int,
        request: Request,
        csrf: str = Form(...),
        freelancer_id: int = Form(0),
    ):
        return _map_member(
            project_member_id=source_member_id,
            request=request,
            csrf=csrf,
            freelancer_id=freelancer_id,
        )

    return router
