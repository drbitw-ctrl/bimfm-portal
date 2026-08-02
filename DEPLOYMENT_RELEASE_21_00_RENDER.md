# BIMFM Portal Version 21.00 — Render Deployment

## Before deployment

1. Confirm a current PostgreSQL backup.
2. Keep the existing Render Web Service and PostgreSQL database.
3. Preserve all current environment variables and secrets.
4. Extract the Version 21.00 ZIP into a separate folder.
5. Do not copy `.env`, SQLite files, backups, logs, or uploads into the Git repository.

## Copy into the current repository

Run one line at a time in PowerShell from the extracted `BIMFM_PORTAL_RELEASE_21_00_RENDER` folder:

```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
$Release = (Get-Location).Path
$Repo = (Resolve-Path $Repo).Path
$Release = (Resolve-Path $Release).Path
Write-Host "Repository: $Repo"
Write-Host "Release: $Release"
robocopy $Release $Repo /E /XD .git .venv venv __pycache__ data backups logs uploads /XF .env *.db *.sqlite *.sqlite3 *.pyc /R:2 /W:1
Set-Location $Repo
$env:GIT_PAGER = "cat"
git status
git diff --stat
```

Robocopy exit codes 0 through 7 mean success.

## Stage Version 21.00

```powershell
git add .env.example app/config.py app/main.py app/web_helpers.py app/work_order_service.py app/auth/permissions.py app/models/__init__.py app/models/work_order.py app/routers/administration.py app/routers/portal.py app/routers/projects.py app/locales/en.json app/locales/zh_TW.json alembic/versions/20260802_0008_work_orders_and_reminders.py static/css/ui-refresh.css static/js/i18n.js static/js/ui.js templates/base.html templates/admin_dashboard.html templates/admin_delete_freelancer.html templates/admin_freelancers.html templates/freelancer_tasks.html templates/freelancer_reminders.html templates/portal_module.html templates/task_reminder_compose.html README_RELEASE_21_00_WORK_ORDER_OPERATIONS.md DEPLOYMENT_RELEASE_21_00_RENDER.md DATABASE_SAFETY_RELEASE_21_00.md TEST_REPORT_RELEASE_21_00.txt
```

Review the staged files:

```powershell
git status
git diff --cached --stat
```

Commit and push:

```powershell
git commit -m "Version 21.00 work order operations"
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

Expected migration:

```text
Running upgrade 20260802_0007 -> 20260802_0008
```

When Auto-Deploy is disabled, use:

```text
Manual Deploy → Deploy latest commit
```

## Optional email delivery

In-app reminders work without configuration. To also send email copies, add these values under Render Environment:

```text
BIMFM_SMTP_HOST
BIMFM_SMTP_PORT
BIMFM_SMTP_USERNAME
BIMFM_SMTP_PASSWORD
BIMFM_SMTP_FROM_EMAIL
BIMFM_SMTP_USE_TLS
```

Do not place SMTP credentials in `.env.example`, source files, Git commits, or screenshots.

## Acceptance checks

After Render reports **Live**, press `Ctrl + Shift + R`, then verify:

1. Sidebar version is `3.0.0-release21.00-work-order-operations`.
2. Manual freelancer time entry is rejected and a freelancer can start one assigned task.
3. Starting another task while the first timer is active is rejected.
4. Stopping creates a recorded session in Work Orders.
5. The same minutes appear in Task Time Utilization.
6. Task status and progress remain unchanged until an Administrator edits them.
7. The Administrator Dashboard shows the live task and project.
8. A Supervisor can view live work and send a reminder.
9. The freelancer receives the reminder in the portal inbox.
10. Traditional Chinese tables show translated priorities and assignment states.
11. Tasks, Team Availability, Active Tasks, Recently Completed Tasks, and Projects use compact headers.
12. A protected testing account displays the two-step purge workflow.

Use the protected-account purge only after confirming the account is test data and a current database backup exists.
