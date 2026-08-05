from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class OvertimePageRepairTests(unittest.TestCase):
    def test_historical_form_posts_to_registered_route(self):
        template = (ROOT / "templates" / "admin_overtime.html").read_text(encoding="utf-8")
        router = (ROOT / "app" / "routers" / "overtime.py").read_text(encoding="utf-8")
        self.assertIn('action="/admin/overtime/historical"', template)
        self.assertIn('@router.post("/admin/overtime/historical")', router)

    def test_active_freelancers_are_passed_to_template(self):
        router = (ROOT / "app" / "routers" / "overtime.py").read_text(encoding="utf-8")
        self.assertIn('active_freelancers=active_freelancer_list', router)

    def test_overtime_register_defaults_to_all_current_month_records(self):
        router = (ROOT / "app" / "routers" / "overtime.py").read_text(encoding="utf-8")
        self.assertIn('status: str = "ALL"', router)

    def test_filter_controls_are_present(self):
        template = (ROOT / "templates" / "admin_overtime.html").read_text(encoding="utf-8")
        self.assertIn('class="ot-filter-bar"', template)
        self.assertIn('name="month"', template)
        self.assertIn('name="status"', template)

if __name__ == "__main__":
    unittest.main()
