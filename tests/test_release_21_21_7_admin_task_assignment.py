from app.main import app


def test_static_admin_task_assignment_routes_are_registered():
    routes = {(route.path, frozenset(getattr(route, "methods", set()))) for route in app.routes}
    assert ("/admin/task-assignment/enable", frozenset({"GET"})) in routes
    assert ("/admin/task-assignment/enable", frozenset({"POST"})) in routes


def test_staff_access_uses_static_current_admin_endpoint():
    from pathlib import Path
    text = Path("templates/admin_staff_accounts.html").read_text(encoding="utf-8")
    assert 'action="/admin/task-assignment/enable"' in text
