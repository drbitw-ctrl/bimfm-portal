from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _extract_function(source: str, name: str) -> str:
    marker = f"function {name}("
    start = source.index(marker)
    brace = source.index("{", start)
    depth = 0
    for idx in range(brace, len(source)):
        char = source[idx]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start : idx + 1]
    raise AssertionError(f"Could not extract {name}")


def test_release_21_23_1_1_version_and_cache_bust():
    config = (ROOT / "app" / "config.py").read_text(encoding="utf-8")
    assert 'APP_VERSION = "v3.0.24.3.1-release21.24.3.1-dashboard-leave-availability-hotfix"' in config
    assert 'APP_VERSION_NUMBER = "3.0.24.3.1"' in config
    for template in ["admin_dashboard.html", "freelancer_tasks.html", "screen_share_test.html"]:
        html = (ROOT / "templates" / template).read_text(encoding="utf-8")
        assert "screen-share.js?v=21.23.1.2" in html


def test_expanded_live_view_reuses_existing_thumbnail_connection():
    js = (ROOT / "static" / "js" / "screen-share.js").read_text(encoding="utf-8")
    expanded = _extract_function(js, "openExpandedViewer")
    assert "ensureViewerPeer" in expanded
    assert "entry.stream" in expanded
    assert "video.srcObject = entry.stream" in expanded
    assert "sameViewerAlreadyOpen" in expanded
    assert "disconnectViewerPeer(key)" not in expanded
    assert "connectPeer(" not in expanded
    assert "const viewerPeers = new Map();" in js


def test_repeated_view_live_click_is_idempotent():
    js = (ROOT / "static" / "js" / "screen-share.js").read_text(encoding="utf-8")
    expanded = _extract_function(js, "openExpandedViewer")
    assert "if (sameViewerAlreadyOpen)" in expanded
    assert "return;" in expanded


def test_freelancer_has_local_shared_screen_preview():
    html = (ROOT / "templates" / "freelancer_tasks.html").read_text(encoding="utf-8")
    js = (ROOT / "static" / "js" / "screen-share.js").read_text(encoding="utf-8")
    assert "YOUR SHARED VIEW" in html
    assert "data-share-preview" in html
    assert "data-share-preview-placeholder" in html
    assert "preview.srcObject = mediaStream || null" in js
    assert "setLocalPreview(stream)" in js
    assert "setLocalPreview(null)" in js


def test_freelancer_is_guided_to_share_revit_window_only():
    html = (ROOT / "templates" / "freelancer_tasks.html").read_text(encoding="utf-8")
    js = (ROOT / "static" / "js" / "screen-share.js").read_text(encoding="utf-8")
    assert "Recommended: share the Revit window only." in html
    assert "Autodesk Revit application window" in html
    assert "Select your Revit window" in js
    assert "displaySurface: 'window'" in js


def test_share_notifications_cover_start_live_stop_and_interruptions():
    html = (ROOT / "templates" / "freelancer_tasks.html").read_text(encoding="utf-8")
    js = (ROOT / "static" / "js" / "screen-share.js").read_text(encoding="utf-8")
    assert "data-share-notification" in html
    assert 'aria-live="polite"' in html
    assert "Select the Revit window to share" in js
    assert "Live screen sharing is active" in js
    assert "Live screen sharing stopped" in js
    assert "Live screen connection interrupted" in js


def test_start_stop_buttons_have_opposite_disabled_states():
    html = (ROOT / "templates" / "freelancer_tasks.html").read_text(encoding="utf-8")
    js = (ROOT / "static" / "js" / "screen-share.js").read_text(encoding="utf-8")
    css = (ROOT / "static" / "css" / "ui-refresh.css").read_text(encoding="utf-8")
    assert "data-share-start" in html
    assert "data-share-stop disabled" in html
    assert "stopButton.hidden" not in js
    assert "shareButton.disabled = isSharing || isTransitioning" in js
    assert "stopButton.disabled = !isSharing || isTransitioning" in js
    assert ".screen-share-prototype-actions .button:disabled" in css


def test_privacy_boundary_still_has_no_recording_or_database_media_pipeline():
    js = (ROOT / "static" / "js" / "screen-share.js").read_text(encoding="utf-8")
    html = (ROOT / "templates" / "freelancer_tasks.html").read_text(encoding="utf-8")
    assert "MediaRecorder" not in js
    assert "getUserMedia" not in js
    assert "audio: false" in js
    assert "this session is not being recorded" in html


def test_hotfix_adds_no_database_migration_or_seed():
    migrations = ROOT / "alembic" / "versions"
    names = {p.name for p in migrations.glob("*.py")} if migrations.exists() else set()
    assert not any("21_23_1_1" in name or "screen_share_usability" in name for name in names)
    assert not (ROOT / "tools" / "seed_local_test_accounts.py").exists()
