# BIMFM Portal Release 20.22 — Render Deployment Guide

## Before deployment

1. Confirm the production PostgreSQL backup is current.
2. Preserve all existing Render environment variables.
3. Continue using the existing Render Web Service and PostgreSQL database.
4. Do not upload `.env` or local database files.

## Safe copy into the existing Git repository

Extract the ZIP into a separate folder and open PowerShell inside the inner
`BIMFM_PORTAL_RELEASE_20_22_RENDER` folder.

```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
$Release = (Get-Location).Path
$Repo = (Resolve-Path $Repo).Path
$Release = (Resolve-Path $Release).Path
```

Confirm the two paths are different:

```powershell
Write-Host "Repository: $Repo"
Write-Host "Release: $Release"
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

Stage Release 20.22 files:

```powershell
git add app/config.py app/task_time_reporting.py app/routers/portal.py app/locales/en.json app/locales/zh_TW.json static/css/ui-refresh.css templates/base.html templates/portal_module.html templates/task_time_utilization.html README_RELEASE_20_22_TASK_TIME_UTILIZATION.md DEPLOYMENT_RELEASE_20_22_RENDER.md DATABASE_SAFETY_RELEASE_20_22.md TEST_REPORT_RELEASE_20_22.txt
```

Commit and push:

```powershell
git commit -m "Release 20.22 task time utilization"
git push origin main
```

## Render commands

Keep the existing commands unchanged.

Build:

```text
pip install -r requirements.txt && alembic upgrade head
```

Start:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Release 20.22 has no new migration. If Auto-Deploy is disabled, use:

```text
Manual Deploy → Deploy latest commit
```

## Acceptance checks

After Render reports **Live**:

1. Hard-refresh the portal with `Ctrl + Shift + R`.
2. Open Tasks.
3. Confirm In Progress and For Review rows are pale yellow.
4. Confirm overdue open rows are pale red.
5. Confirm completed rows have no highlight.
6. Change Status inline and confirm the highlight updates.
7. Open Task Time Utilization.
8. Confirm project and task target/actual values display.
9. Confirm a same-day scheduled task receives an 8-hour target.
10. Confirm linked Daily Task hours appear under the correct task.
11. Confirm unlinked project work appears separately.
12. Verify Traditional Chinese labels.
