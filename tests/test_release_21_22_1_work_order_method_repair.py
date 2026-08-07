import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = (ROOT / "app" / "routers" / "projects.py").read_text(encoding="utf-8")
TASKS_TEMPLATE = (ROOT / "templates" / "freelancer_tasks.html").read_text(encoding="utf-8")


class WorkOrderMethodRepairTests(unittest.TestCase):
    def test_start_has_get_navigation_fallback_and_post_action(self):
        self.assertIn('@router.get("/tasks/work-orders/{task_id}/start", include_in_schema=False)', PROJECTS)
        self.assertIn('@router.post("/tasks/work-orders/{task_id}/start")', PROJECTS)

    def test_stop_has_get_navigation_fallback_and_post_action(self):
        self.assertIn('@router.get("/tasks/work-orders/stop", include_in_schema=False)', PROJECTS)
        self.assertIn('@router.post("/tasks/work-orders/stop")', PROJECTS)

    def test_state_changes_remain_post_forms(self):
        self.assertIn('method="post" action="/tasks/work-orders/stop"', TASKS_TEMPLATE)
        self.assertIn('method="post" action="/tasks/work-orders/{{ task.id }}/start"', TASKS_TEMPLATE)

    def test_no_schema_or_model_change_in_hotfix(self):
        self.assertNotIn('alembic', PROJECTS.lower())


if __name__ == "__main__":
    unittest.main()
