"""PostgreSQL-native project team routes.

The historical sync endpoints remain present only to give old agents an
explicit retirement response. Live project data is read from portal tables.
"""
from __future__ import annotations

from fastapi import APIRouter


def configure_integration_routes(legacy_namespace: dict[str, object]) -> APIRouter:
    globals().update(legacy_namespace)
    router = APIRouter(tags=["Project Team"])
    globals()["router"] = router

    @router.post("/api/integration/project-tasks/sync")
    def retired_project_task_sync_api(request: Request):
        del request
        raise HTTPException(
            status_code=410,
            detail=(
                "Project synchronization was retired in Release 20.7. "
                "The portal reads portal_projects, portal_tasks, "
                "portal_project_members, and portal_task_assignments directly."
            ),
        )

    @router.get("/api/integration/project-tasks/status")
    def project_data_status_api(request: Request):
        del request
        return {
            "mode": "postgresql_native",
            "synchronization_required": False,
            "message": (
                "Project synchronization was retired in Release 20.7. "
                "Authorized staff can review project data on /admin/project-team."
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
            return templates.TemplateResponse(
                request=request,
                name="admin_project_team.html",
                context=template_context(
                    request,
                    admin=admin,
                    health=health,
                    member_rows=team_assignment_rows(database),
                    project_rows=project_overview_rows(database, limit=100),
                    task_rows=active_task_overview_rows(database, limit=200),
                ),
            )

    @router.post(
        "/admin/integration/projects/source-members/{source_member_id}/map",
        include_in_schema=False,
    )
    def retired_member_mapping(
        source_member_id: int,
        request: Request,
        csrf: str = Form(...),
        freelancer_id: int = Form(0),
    ):
        del source_member_id, freelancer_id
        if not validate_csrf(request, csrf):
            set_flash(request, "Invalid form token.", "error")
            return RedirectResponse("/admin/project-team", status_code=303)
        set_flash(
            request,
            "Member-name mapping is retired. Project membership is stored directly in PostgreSQL.",
            "info",
        )
        return RedirectResponse("/admin/project-team", status_code=303)

    return router
