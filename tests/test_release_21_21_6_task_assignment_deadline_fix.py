from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Release21216Tests(unittest.TestCase):
    def test_task_assignment_route_supports_post_and_safe_get_fallback(self):
        text = (ROOT / "app/routers/administration.py").read_text(encoding="utf-8")
        route = '/admin/staff-accounts/{account_id}/enable-task-member'
        self.assertIn(f'@router.get("{route}")', text)
        self.assertIn(f'@router.post("{route}")', text)
        self.assertIn("Enable Task Assignment button on Staff Access", text)

    def test_full_task_edit_captures_previous_status_before_mutation(self):
        text = (ROOT / "app/routers/portal.py").read_text(encoding="utf-8")
        anchor = 'def edit_portal_task_submit('
        block = text[text.index(anchor):text.index('@router.post("/portal/tasks/{task_id}/quick-edit"')]
        capture = 'previous_status = str(task.status or "").upper()'
        self.assertIn(capture, block)
        self.assertLess(block.index(capture), block.index('task.status = str(form_values["status"])'))
        self.assertIn('if previous_status != "COMPLETED"', block)

    def test_release_version(self):
        text = (ROOT / "app/config.py").read_text(encoding="utf-8")
        self.assertIn("v3.0.21.8-release21.21.8-task-creation-admin-assignment-hotfix", text)


if __name__ == "__main__":
    unittest.main()
