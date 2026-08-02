# BIMFM Portal Release 21.05 — Render Deployment

## Important

Deploy this package into the existing Git repository and existing Render service.
Do not create a new database or replace production environment variables.

## Copy into the repository

Open PowerShell inside the extracted `BIMFM_PORTAL_RELEASE_21_05_RENDER` folder.
Run commands one line at a time.

```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
$Release = (Get-Location).Path
$Repo = (Resolve-Path $Repo).Path
$Release = (Resolve-Path $Release).Path
Write-Host "Repository: $Repo"
Write-Host "Release: $Release"
robocopy $Release $Repo /E /XD .git .venv venv __pycache__ data backups logs uploads /XF .env *.db *.sqlite *.sqlite3 *.pyc /R:2 /W:1
```

Robocopy exit codes 0 through 7 indicate success.

## Stage and push

```powershell
Set-Location $Repo
$env:GIT_PAGER = "cat"
git status
git diff --stat
git add app/config.py app/calendar_board.py app/task_time_reporting.py app/routers/administration.py app/routers/portal.py app/locales/en.json app/locales/zh_TW.json static/css/ui-refresh.css templates/base.html templates/admin_dashboard.html templates/admin_hr_calendar.html templates/_reminder_calendar_board.html templates/reminder_calendar.html templates/task_time_utilization.html templates/performance_leaderboards.html templates/project_reports.html README_RELEASE_21_05_CALENDAR_UTILIZATION_DASHBOARD.md DEPLOYMENT_RELEASE_21_05_RENDER.md DATABASE_SAFETY_RELEASE_21_05.md TEST_REPORT_RELEASE_21_05.txt
git status
git diff --cached --stat
git commit -m "Release 21.05 calendar utilization and dashboard presentation"
git push origin main
```

Stage only the listed files. Do not add unrelated old or accidental files.

## Render commands

Keep the existing commands unchanged.

```text
Build: pip install -r requirements.txt && alembic upgrade head
Start: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

No new migration line is expected for Release 21.05.

If Auto-Deploy is disabled, use:

```text
Manual Deploy → Deploy latest commit
```

After Render reports Live, press `Ctrl + Shift + R`.

## Acceptance checks

1. Confirm Team Availability appears before Live Work Orders on Dashboard.
2. Open Performance and confirm the quality area says Quality Score as calculated.
3. Open Project Reports and confirm the old Quality Score explanation is absent.
4. Open Task Time Utilization and verify project time cards show total actual time.
5. Open Reminder Calendar and test previous month, next month, and Today.
6. Confirm task deadlines and HR holidays appear on the correct dates.
7. Open HR Calendar and confirm the same board appears above the management forms.
8. Confirm the sidebar version is `v3.0.5-release21.05-calendar-utilization-dashboard`.
