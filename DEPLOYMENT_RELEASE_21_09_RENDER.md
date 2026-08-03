# BIMFM Portal Release 21.09 — Render Deployment

Release 21.09 can be deployed directly over the existing Git repository.

## Render settings

Build command:

`pip install -r requirements.txt && alembic upgrade head`

Start command:

`uvicorn app.main:app --host 0.0.0.0 --port $PORT`

## Expected migration

If Release 21.08 is already deployed:

`Running upgrade 20260803_0011 -> 20260803_0012`

If the live portal is still Release 21.07, Render should run:

`Running upgrade 20260803_0010 -> 20260803_0011`

then:

`Running upgrade 20260803_0011 -> 20260803_0012`

## PowerShell deployment

Run each command separately.

```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
```

```powershell
$Release = (Get-Location).Path
```

```powershell
$Repo = (Resolve-Path $Repo).Path
```

```powershell
$Release = (Resolve-Path $Release).Path
```

```powershell
robocopy $Release $Repo /E /XD .git .venv venv __pycache__ data backups logs uploads /XF .env *.db *.sqlite *.sqlite3 *.pyc /R:2 /W:1
```

```powershell
Set-Location $Repo
```

```powershell
$env:GIT_PAGER = "cat"
```

```powershell
git status
```

Stage the cumulative Release 21.08 and 21.09 files:

```powershell
git add app/auth/permissions.py app/config.py app/excel_exports.py app/locales/en.json app/locales/zh_TW.json app/models/identity.py app/my_work_service.py app/portal_project_service.py app/routers/administration.py app/routers/portal.py alembic/versions/20260803_0010_freelancer_join_dates.py alembic/versions/20260803_0011_july_leave_task_start_dates.py alembic/versions/20260803_0012_task_project_start_dates_july_leave.py static/css/ui-refresh.css templates/admin_attendance_monthly.html templates/admin_dashboard.html templates/admin_dtr_dashboard.html templates/admin_freelancers.html templates/admin_new_freelancer.html templates/admin_project_team.html templates/attendance.html templates/base.html templates/export_center.html templates/performance_leaderboards.html templates/portal_module.html templates/project_reports.html templates/staff_my_work.html templates/task_time_utilization.html README_RELEASE_21_07_EXPORTS_JOIN_DATES_UNASSIGNED.md DEPLOYMENT_RELEASE_21_07_RENDER.md DATABASE_SAFETY_RELEASE_21_07.md TEST_REPORT_RELEASE_21_07.txt README_RELEASE_21_08_JULY_DATA_PROJECT_LABELS_PROFILE_CARD.md DEPLOYMENT_RELEASE_21_08_RENDER.md DATABASE_SAFETY_RELEASE_21_08.md TEST_REPORT_RELEASE_21_08.txt README_RELEASE_21_09_DASHBOARD_DATA_BACKFILL.md DEPLOYMENT_RELEASE_21_09_RENDER.md DATABASE_SAFETY_RELEASE_21_09.md TEST_REPORT_RELEASE_21_09.txt
```

```powershell
git diff --cached --stat
```

```powershell
git commit -m "Release 21.09 dashboard cleanup and date backfill"
```

```powershell
git push origin main
```

After Render reports Live, hard refresh with `Ctrl + Shift + R`.

Expected sidebar version:

`v3.0.9-release21.09-dashboard-data-backfill`
