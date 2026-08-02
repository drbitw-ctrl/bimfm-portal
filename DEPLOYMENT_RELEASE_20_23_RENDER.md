# BIMFM Portal Release 20.23 — Render Deployment

## Before deployment

1. Confirm the current Render PostgreSQL backup is available.
2. Preserve all existing Render environment variables.
3. Do not create a new PostgreSQL database.
4. Extract the Release 20.23 ZIP into a folder separate from the Git repository.

## Copy into the existing repository

Example repository:

```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
$Release = (Get-Location).Path
$Repo = (Resolve-Path $Repo).Path
$Release = (Resolve-Path $Release).Path
```

Confirm the paths are different, then copy:

```powershell
robocopy $Release $Repo /E /XD .git .venv venv __pycache__ data backups logs uploads /XF .env *.db *.sqlite *.sqlite3 *.pyc /R:2 /W:1
```

Robocopy exit codes 0 through 7 are successful.

## Git commands

```powershell
Set-Location $Repo
$env:GIT_PAGER = "cat"
git status
git diff --stat
git add app/config.py app/locales/en.json app/locales/zh_TW.json app/portal_project_service.py app/routers/administration.py app/task_time_reporting.py static/js/i18n.js templates/admin_staff_accounts.html templates/admin_delete_staff_account.html templates/freelancer_completed_tasks.html templates/task_time_utilization.html README_RELEASE_20_23_LOCALIZATION_PRIVACY_ADMIN_TIME.md DEPLOYMENT_RELEASE_20_23_RENDER.md DATABASE_SAFETY_RELEASE_20_23.md TEST_REPORT_RELEASE_20_23.txt
git status
git diff --cached --stat
git commit -m "Release 20.23 localization privacy admin cleanup and time fallback"
git push origin main
```

## Render commands

Keep these unchanged:

```text
Build: pip install -r requirements.txt && alembic upgrade head
Start: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

No new Alembic upgrade line is expected for Release 20.23.

## Acceptance checks

1. Switch to Traditional Chinese and review Dashboard, Tasks, Performance,
   Project Reports, Attendance, DTR, and account pages.
2. Log in as a freelancer and confirm Quality Score is absent from all task views.
3. Create an unused test Administrator, then delete it from Staff Access.
4. Confirm self-deletion and deletion of a referenced account are blocked.
5. Open Task Time Utilization.
6. Confirm tasks with Daily Task entries use submitted minutes.
7. Confirm a completed task with no Daily Task entry shows a clearly labelled
   Start-to-Completion estimate.
