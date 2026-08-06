from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PORTAL = ROOT / "app" / "routers" / "portal.py"


class SaveTaskHotfixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = PORTAL.read_text(encoding="utf-8")

    def test_new_task_initializes_completion_notification_count(self):
        marker = 'assigned_member_name = replace_task_assignment('
        start = self.source.index(marker, self.source.index('def new_portal_task_submit'))
        audit = self.source.index('write_audit(', start)
        block = self.source[start:audit]
        self.assertIn('completion_notifications = 0', block)

    def test_new_task_does_not_reference_uninitialized_task_variables(self):
        start = self.source.index('def new_portal_task_submit')
        end = self.source.index('@router.get("/portal/tasks/{task_id}/edit", response_class=HTMLResponse)', start)
        block = self.source[start:end]
        task_creation = block.index('task = PortalTask(')
        before_creation = block[:task_creation]
        self.assertNotIn('task.status', before_creation)
        self.assertNotIn('completion_notifications=', before_creation)

    def test_audit_details_reference_defined_completion_notification_count(self):
        start = self.source.index('def new_portal_task_submit')
        end = self.source.index('@router.get("/portal/tasks/{task_id}/edit", response_class=HTMLResponse)', start)
        block = self.source[start:end]
        self.assertLess(
            block.index('completion_notifications = 0'),
            block.index('completion_notifications={completion_notifications}'),
        )


if __name__ == '__main__':
    unittest.main()
