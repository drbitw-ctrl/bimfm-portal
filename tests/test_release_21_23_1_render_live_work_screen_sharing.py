from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_release_version():
    config = (ROOT / "app" / "config.py").read_text(encoding="utf-8")
    assert 'APP_VERSION = "v3.0.24.1-release21.24.1-project-report-period-localized-excel"' in config
    assert 'APP_VERSION_NUMBER = "3.0.24.1"' in config


def test_dashboard_embeds_live_work_room_for_management_roles():
    html = (ROOT / "templates" / "admin_dashboard.html").read_text(encoding="utf-8")
    assert "current_staff_role in ['ADMIN', 'SUPERVISOR', 'FINANCE']" in html
    assert "data-screen-share-viewer-page" in html
    assert "LIVE WORK ROOM" in html
    assert "/portal/live-work/room" in html
    assert "data-live-share-list" in html
    assert "screen-share.js?v=21.23.1.2" in html


def test_management_authorization_is_server_side():
    source = (ROOT / "app" / "screen_share.py").read_text(encoding="utf-8")
    assert 'VIEWER_ROLES = {"ADMIN", "SUPERVISOR", "FINANCE"}' in source
    assert source.count('str(account.role or "").strip().upper() not in VIEWER_ROLES') >= 2
    assert '@router.websocket("/ws/screen-share/watch")' in source
    assert '@router.websocket("/ws/screen-share/view/{freelancer_id}")' in source


def test_screen_publishing_requires_active_work_order():
    source = (ROOT / "app" / "screen_share.py").read_text(encoding="utf-8")
    assert "from app.work_order_service import active_work_session" in source
    assert "if not _has_active_work_order(freelancer_id)" in source
    assert "code=4409" in source
    assert '"type": "work_order_ended"' in source


def test_freelancer_screen_share_is_work_order_linked_and_not_recorded():
    html = (ROOT / "templates" / "freelancer_tasks.html").read_text(encoding="utf-8")
    active = html.index("{% if work_orders.active_session %}")
    share = html.index("data-screen-share-publisher")
    otherwise = html.index("{% else %}", active)
    assert active < share < otherwise
    assert "Live viewing only — this session is not being recorded." in html
    assert "Stopping or losing the live screen does not stop your Work Order timer." in html
    assert "screen-share.js?v=21.23.1.2" in html


def test_control_room_has_live_thumbnails_and_no_recording_pipeline():
    js = (ROOT / "static" / "js" / "screen-share.js").read_text(encoding="utf-8")
    assert "ensureViewerPeer" in js
    assert 'class="live-work-thumb"' in js
    assert "MediaRecorder" not in js
    assert "getUserMedia" not in js
    assert "audio: false" in js
    assert "if (structure === lastRoomStructure)" in js
    assert "pc._pendingRemoteIce" in js
    assert "const pendingRemoteIce = []" in js


def test_no_local_seed_tool_is_packaged():
    assert not (ROOT / "tools" / "seed_local_test_accounts.py").exists()


def test_no_new_migration_file_for_release():
    migrations = ROOT / "alembic" / "versions"
    names = {p.name for p in migrations.glob("*.py")} if migrations.exists() else set()
    assert not any("21_23_1" in name or "screen" in name.lower() for name in names)
