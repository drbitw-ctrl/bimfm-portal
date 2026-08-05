import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = (ROOT / 'templates' / 'base.html').read_text(encoding='utf-8')
CSS = (ROOT / 'static' / 'css' / 'ui-refresh.css').read_text(encoding='utf-8')


class WorkspaceProfileRefreshTests(unittest.TestCase):
    def test_sidebar_uses_bim_portal_and_unified_workspace(self):
        self.assertIn("t('BIM Portal')", BASE)
        self.assertIn("t('Unified Workspace')", BASE)
        self.assertNotIn("<small>{{ t('Freelancers') }}</small>", BASE)

    def test_language_control_remains_switch_bar(self):
        self.assertIn('class="language-switcher"', BASE)
        self.assertIn('value="en"', BASE)
        self.assertIn('value="zh_TW"', BASE)
        self.assertNotIn('<select', BASE)

    def test_profile_panel_and_online_avatar_are_present(self):
        self.assertIn('user-profile-panel', BASE)
        self.assertIn('user-avatar-enhanced', BASE)
        self.assertIn('.user-avatar-enhanced i', CSS)
        self.assertIn('.user-profile-actions', CSS)


if __name__ == '__main__':
    unittest.main()
