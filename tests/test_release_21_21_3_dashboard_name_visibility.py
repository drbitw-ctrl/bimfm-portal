from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class DashboardNameVisibilityTests(unittest.TestCase):
    def test_dashboard_has_default_show_toggle(self):
        text = (ROOT / "templates" / "admin_dashboard.html").read_text(encoding="utf-8")
        self.assertIn("data-member-visibility-toggle", text)
        self.assertIn('aria-pressed="false"', text)
        self.assertIn("Hide member names", text)

    def test_names_are_marked_for_privacy_without_server_side_hiding(self):
        text = (ROOT / "templates" / "admin_dashboard.html").read_text(encoding="utf-8")
        self.assertIn("privacy-member-name", text)
        self.assertNotIn("sessionStorage", (ROOT / "static" / "js" / "ui.js").read_text(encoding="utf-8"))

    def test_fresh_page_load_forces_names_visible(self):
        text = (ROOT / "static" / "js" / "ui.js").read_text(encoding="utf-8")
        self.assertIn("update(false)", text)
        self.assertIn("member-names-hidden", text)

    def test_bilingual_labels_exist(self):
        import json
        en=json.loads((ROOT / "app" / "locales" / "en.json").read_text(encoding="utf-8"))
        zh=json.loads((ROOT / "app" / "locales" / "zh_TW.json").read_text(encoding="utf-8"))
        for key in ["Hide member names","Show member names","Member names are shown by default.","Hidden member"]:
            self.assertIn(key,en); self.assertIn(key,zh)

if __name__ == "__main__":
    unittest.main()
