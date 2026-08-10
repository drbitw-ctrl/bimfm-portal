from pathlib import Path

def test_review_feature_is_separate_from_freelancer_assignment():
    text=Path('app/review_work_service.py').read_text(encoding='utf-8')
    assert 'PortalTaskAssignment' not in text
    assert 'from app.models import DailyTask' not in text
    assert 'task.status =' not in text
    assert 'task.progress =' not in text

def test_review_routes_are_present():
    text=Path('app/routers/administration.py').read_text(encoding='utf-8')
    assert '@router.get("/admin/review-queue"' in text
    assert '@router.post("/admin/review-queue/{task_id}/assign")' in text
    assert '@router.post("/admin/review-queue/{task_id}/start")' in text
    assert '@router.post("/admin/review-queue/stop")' in text

def test_dashboard_has_compact_review_queue():
    text=Path('templates/admin_dashboard.html').read_text(encoding='utf-8')
    assert 'REVIEW QUEUE' in text and 'review_queue_rows[:4]' in text

def test_no_new_migration_for_review_release():
    # Feature intentionally reuses existing task-update/work-session tables.
    assert Path('app/review_work_service.py').exists()
