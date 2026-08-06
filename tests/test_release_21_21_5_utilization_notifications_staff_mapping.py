from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class Release21195Tests(unittest.TestCase):
    def test_utilization_page_displays_over_plan_scale(self):
        text=(ROOT/'templates/task_time_utilization.html').read_text(encoding='utf-8')
        self.assertIn("Utilization can exceed 100%", text)
        self.assertIn("project.overrun_minutes", text)
        self.assertIn("[project.utilization, 200]", text)

    def test_current_admin_has_prominent_task_assignment_action(self):
        text=(ROOT/'templates/admin_staff_accounts.html').read_text(encoding='utf-8')
        self.assertIn("Enable Task Assignment for Me", text)
        self.assertIn('/enable-task-member', text)

    def test_completion_notification_is_created_on_transition(self):
        text=(ROOT/'app/routers/portal.py').read_text(encoding='utf-8')
        self.assertIn('_notify_task_marked_finished', text)
        self.assertIn('previous_status != "COMPLETED"', text)
        self.assertIn('Task marked as finished', text)

if __name__ == '__main__':
    unittest.main()
