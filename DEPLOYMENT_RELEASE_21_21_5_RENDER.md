# BIM Portal Release 21.21.5 — Render Deployment

## Before deployment

This release has no Alembic migration. It changes utilization presentation, administrator task-member activation visibility, and task-completion notifications. Existing data is not backfilled.

## Deployment commands

Extract the release ZIP and open PowerShell inside the extracted `BIMFM_PORTAL_RELEASE_21_21_5_RENDER` folder.

```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
$Release = (Get-Location).Path

$Repo = (Resolve-Path $Repo).Path
$Release = (Resolve-Path $Release).Path

Write-Host "Repository: $Repo"
Write-Host "Release: $Release"
```

The two paths must be different.

Copy the release:

```powershell
robocopy $Release $Repo /E /XD .git .venv venv __pycache__ data backups logs uploads /XF .env *.db *.sqlite *.sqlite3 *.pyc /R:2 /W:1
```

Robocopy exit codes 0 through 7 indicate success.

Enter the repository and review:

```powershell
Set-Location $Repo
$env:GIT_PAGER = "cat"

git status
git diff --stat
```

Stage Release 21.21.5:

```powershell
git add app/config.py app/routers/portal.py app/locales/en.json app/locales/zh_TW.json static/css/ui-refresh.css templates/admin_staff_accounts.html templates/task_time_utilization.html tests/test_release_21_21_5_utilization_notifications_staff_mapping.py README_RELEASE_21_21_5_UTILIZATION_OVERRUN_TASK_NOTIFICATIONS.md DEPLOYMENT_RELEASE_21_21_5_RENDER.md DATABASE_SAFETY_RELEASE_21_21_5.md TEST_REPORT_RELEASE_21_21_5.txt
```

Review staged files:

```powershell
git status
git diff --cached --stat
```

Commit and push:

```powershell
git commit -m "Release 21.21.5 utilization overruns and completion notifications"
git push origin main
git log -1 --oneline
```

Keep Render settings unchanged.

Build Command:

```text
pip install -r requirements.txt && alembic upgrade head
```

Start Command:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Health Check Path:

```text
/health/ready
```

After Render reports Live, press `Ctrl + Shift + R` and confirm the version is `v3.0.21.5`.

## Post-deployment checks

1. Open Project Utilization and verify projects can display values above 100%.
2. Confirm the utilization bar marks the 100% plan point and shows over-plan duration.
3. Open Staff Access and use **Enable Task Assignment for Me** for your Administrator account.
4. Confirm your name appears in New Task and Edit Task assignment lists.
5. Assign a test task to a freelancer, then change it to Completed as Administrator.
6. Sign in as that freelancer and confirm a new unread reminder appears.
