from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Release21222Tests(unittest.TestCase):
    def test_freelancer_welcome_hides_internal_code(self):
        text = (ROOT / 'templates' / 'attendance.html').read_text(encoding='utf-8')
        self.assertNotIn('account.freelancer.freelancer_code', text)
        self.assertIn("t('Joined')", text)

    def test_completed_task_periods_are_available(self):
        text = (ROOT / 'app' / 'routers' / 'portal.py').read_text(encoding='utf-8')
        for value in ('7d', '14d', '21d', '30d', 'this_month', 'last_month', '3m', '6m', 'all'):
            self.assertIn(f'"{value}"', text)
        template = (ROOT / 'templates' / 'portal_module.html').read_text(encoding='utf-8')
        self.assertIn('completed-task-period-filter', template)
        self.assertIn('name="period"', template)
        self.assertIn('name="view" value="completed"', template)

    def test_release_has_no_new_migration(self):
        versions = list((ROOT / 'alembic' / 'versions').glob('*.py'))
        self.assertFalse(any('21_22_2' in p.name or '20260807' in p.name for p in versions))


if __name__ == '__main__':
    unittest.main()
