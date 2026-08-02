# BIMFM Portal Release 21.04 Revision 2 — Render Deployment

## Included fixes

This package is cumulative. It includes:

1. The Release 21.04 Finance attendance-population correction.
2. Stable Tasks-table Progress and Quality columns.
3. Cleaner management Quality Score wording with a transparent reporting-scale note.

## Files changed from Release 21.03

- `app/config.py`
- `app/my_work_service.py`
- `app/performance_reporting.py`
- `app/locales/en.json`
- `app/locales/zh_TW.json`
- `static/css/ui-refresh.css`
- `templates/portal_module.html`
- `templates/performance_leaderboards.html`
- `templates/project_reports.html`
- Release 21.04 Revision 2 documentation

## Database

There is no Alembic migration. Keep the existing PostgreSQL database and Render
environment variables.

## Render commands

Build:

```text
pip install -r requirements.txt && alembic upgrade head
```

Start:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Post-deployment checks

1. Sign in as Finance Head and confirm the attendance population is correct.
2. Open Tasks as Administrator and confirm Progress and Quality do not overlap.
3. Open Active Tasks as a read-only role and confirm the static progress bar remains inside its column.
4. Open Performance and Project Reports and confirm headings display `Quality Score`.
5. Confirm the reporting-scale note remains visible.
