# BIMFM Portal Release 20.20 — Render Deployment Guide

## Before deployment

1. Confirm a current production PostgreSQL backup.
2. Keep the existing Render PostgreSQL database.
3. Preserve all production environment variables and secrets.
4. Do not upload `.env`, SQLite databases, backups, logs, or local uploads.

Release 20.20 has no new database migration.

## Safer copy method

Extract the Release 20.20 ZIP into a folder separate from the existing Git
repository. Open PowerShell inside the extracted inner folder and set:

```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
$Release = (Get-Location).Path
$Repo = (Resolve-Path $Repo).Path
$Release = (Resolve-Path $Release).Path
```

Copy the release:

```powershell
robocopy $Release $Repo /E /XD .git .venv venv __pycache__ data backups logs uploads /XF .env *.db *.sqlite *.sqlite3 *.pyc /R:2 /W:1
```

Robocopy exit codes 0–7 are successful.

## Review, commit, and push

```powershell
Set-Location $Repo
$env:GIT_PAGER = "cat"
git status
git diff --stat
```

Stage Release 20.20 files:

```powershell
git add app/config.py app/performance_reporting.py app/routers/portal.py static/css/ui-refresh.css static/js/ui.js static/js/reporting.js templates/portal_module.html templates/performance_leaderboards.html templates/project_reports.html templates/admin_project_team.html templates/freelancer_tasks.html templates/admin_tasks_monthly.html templates/admin_dtr_details.html README_RELEASE_20_20_PERFORMANCE_REPORTING.md DEPLOYMENT_RELEASE_20_20_RENDER.md DATABASE_SAFETY_RELEASE_20_20.md TEST_REPORT_RELEASE_20_20.txt
```

Commit and push:

```powershell
git commit -m "Release 20.20 performance leaderboards and reporting"
git push origin main
```

## Render commands

Keep the existing commands unchanged.

```text
Build:
pip install -r requirements.txt && alembic upgrade head

Start:
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

If Auto-Deploy is disabled, use:

```text
Manual Deploy → Deploy latest commit
```

## Acceptance checks

After Render reports **Live**:

1. Hard-refresh with `Ctrl + Shift + R`.
2. Open Tasks and click multiple column headings.
3. Confirm open work remains before completed work.
4. Check Active Tasks, Recently Completed, My Work, Calendar, and task-review tables.
5. Open Performance and switch among Quality, Total Tasks, and Delivery Speed.
6. Confirm raw task Quality Scores are unchanged on the Tasks page.
7. Open Project Reports and test Monthly, 12 Months, and All Time.
8. Confirm charts and member/project tables update for the selected period.
9. Confirm Supervisor accounts remain read-only.
