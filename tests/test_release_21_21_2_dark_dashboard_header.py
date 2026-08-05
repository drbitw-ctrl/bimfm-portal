from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class DarkDashboardHeaderTests(unittest.TestCase):
    def test_visible_logout_is_rightmost_header_action(self):
        text = (ROOT / 'templates' / 'base.html').read_text(encoding='utf-8')
        self.assertIn('class="topbar-logout-form"', text)
        self.assertIn('class="topbar-logout-button"', text)
        self.assertLess(text.index('premium-user-menu'), text.index('topbar-logout-form'))

    def test_dark_dashboard_overrides_exist(self):
        css = (ROOT / 'static' / 'css' / 'ui-refresh.css').read_text(encoding='utf-8')
        self.assertIn('balanced dark dashboard and action-first header', css)
        self.assertIn('html[data-theme="dark"] .availability-board-three .available-group', css)
        self.assertIn('html[data-theme="dark"] .member-availability-card.state-assigned', css)

    def test_language_switch_remains_segmented(self):
        text = (ROOT / 'templates' / 'base.html').read_text(encoding='utf-8')
        self.assertIn('premium-language-switch', text)
        self.assertIn('value="en"', text)
        self.assertIn('value="zh_TW"', text)

if __name__ == '__main__':
    unittest.main()
