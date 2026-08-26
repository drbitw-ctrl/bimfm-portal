from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def test_release_version():
    config = (ROOT / "app" / "config.py").read_text(encoding="utf-8")
    assert 'APP_VERSION = "v3.0.24.3.1-release21.24.3.1-dashboard-leave-availability-hotfix"' in config


def test_leave_approval_form_reason_is_optional_at_fastapi_boundary():
    source = (ROOT / "app" / "routers" / "leave.py").read_text(encoding="utf-8")
    block = source[source.index('@router.post("/admin/leave-requests/{request_id}/review")'):]
    block = block[:block.index("return router")]
    assert 'reason: str = Form("")' in block
    assert 'reason: str = Form(...)' not in block


def test_rejection_reason_remains_required_by_workflow():
    source = (ROOT / "app" / "hr_workflow.py").read_text(encoding="utf-8")
    block = source[source.index("def reject_leave_request"):]
    assert 'if len(reason) < 5:' in block
    assert 'A rejection reason of at least 5 characters is required.' in block


def test_finance_light_mode_contrast_overrides_legacy_white_text():
    css = (ROOT / "static" / "css" / "ui-refresh.css").read_text(encoding="utf-8")
    assert 'Release 21.24.0.2 — finance light-mode contrast' in css
    assert 'html:not([data-theme="dark"]) .payroll-formula-banner h2' in css
    assert 'color: var(--ui-text-strong);' in css
    assert 'html:not([data-theme="dark"]) .payroll-formula-banner p' in css
    assert 'color: #4f6579;' in css


def test_payroll_explanation_is_plain_three_step_formula_and_bilingual():
    template = (ROOT / "templates" / "admin_finance_center.html").read_text(encoding="utf-8")
    assert "How monthly salary coverage is calculated" in template
    assert "Approved leave hours − OT credit used" in template
    assert "Unpaid leave hours + uncovered absence hours" in template
    assert "Monthly salary basis hours − total deduction hours" in template
    assert template.count('<div class="payroll-rule-step">') == 2
    assert template.count('<div class="payroll-rule-step result">') == 1

    en = json.loads((ROOT / "app" / "locales" / "en.json").read_text(encoding="utf-8"))
    zh = json.loads((ROOT / "app" / "locales" / "zh_TW.json").read_text(encoding="utf-8"))
    key = "How monthly salary coverage is calculated"
    assert en[key] == "How Monthly Salary Coverage Is Calculated"
    assert zh[key] == "每月薪資涵蓋時數如何計算"
    assert "薪資扣除" in zh["The system first uses approved overtime credit to cover approved leave. Any leave hours still uncovered, plus any uncovered absence hours, become salary deduction hours."]
