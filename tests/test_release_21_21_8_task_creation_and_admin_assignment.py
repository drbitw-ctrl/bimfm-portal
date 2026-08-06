from pathlib import Path
import ast
import unittest

ROOT = Path(__file__).resolve().parents[1]

class Release21218RegressionTests(unittest.TestCase):
    def test_new_task_submit_does_not_read_task_before_creation(self):
        source = (ROOT / 'app/routers/portal.py').read_text(encoding='utf-8')
        tree = ast.parse(source)
        fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'new_portal_task_submit')
        segment = ast.get_source_segment(source, fn) or ''
        before_constructor = segment.split('task = PortalTask(', 1)[0]
        self.assertNotIn('task.status', before_constructor)

    def test_admin_assignment_does_not_require_missing_model_attribute(self):
        source = (ROOT / 'app/routers/administration.py').read_text(encoding='utf-8')
        helper = source.split('def _enable_task_assignment_for_account', 1)[1].split('@router.get("/admin/task-assignment/enable")', 1)[0]
        self.assertNotIn('target.task_freelancer_id', helper)
        self.assertIn('TS-{int(target.id):03d}', helper)

if __name__ == '__main__':
    unittest.main()
