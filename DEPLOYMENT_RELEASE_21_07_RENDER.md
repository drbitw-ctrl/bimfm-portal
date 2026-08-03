# Release 21.07 Render Deployment

Run every PowerShell command separately.

## 1. Open PowerShell inside the extracted release folder

The current folder should be:

`BIMFM_PORTAL_RELEASE_21_07_RENDER`

## 2. Set the repository and release paths

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
Write-Host "Repository: $Repo"
```

```powershell
Write-Host "Release: $Release"
```

The repository and release paths must be different.

## 3. Copy the release

```powershell
robocopy $Release $Repo /E /XD .git .venv venv __pycache__ data backups logs uploads /XF .env *.db *.sqlite *.sqlite3 *.pyc /R:2 /W:1
```

Robocopy exit codes 0 through 7 mean success.

## 4. Enter the Git repository

```powershell
Set-Location $Repo
```

```powershell
$env:GIT_PAGER = "cat"
```

```powershell
git status
```

```powershell
git diff --stat
```

## 5. Stage only Release 21.07 files

Copy this as one line:

```powershell
git add app/auth/permissions.py app/config.py app/excel_exports.py app/locales/en.json app/locales/zh_TW.json app/models/identity.py app/my_work_service.py app/portal_project_service.py app/routers/administration.py app/routers/portal.py alembic/versions/20260803_0010_freelancer_join_dates.py static/css/ui-refresh.css templates/admin_attendance_monthly.html templates/admin_dashboard.html templates/admin_dtr_dashboard.html templates/admin_freelancers.html templates/admin_new_freelancer.html templates/base.html templates/export_center.html templates/performance_leaderboards.html templates/portal_module.html templates/project_reports.html templates/staff_my_work.html templates/task_time_utilization.html README_RELEASE_21_07_EXPORTS_JOIN_DATES_UNASSIGNED.md DEPLOYMENT_RELEASE_21_07_RENDER.md DATABASE_SAFETY_RELEASE_21_07.md TEST_REPORT_RELEASE_21_07.txt
```

Do not use `git add .`.

## 6. Review the staged changes

```powershell
git status
```

```powershell
git diff --cached --stat
```

## 7. Commit

```powershell
git commit -m "Release 21.07 exports join dates and unassigned tasks"
```

## 8. Push

```powershell
git push origin main
```

## 9. Confirm the commit

```powershell
git log -1 --oneline
```

## Render settings

Keep the existing commands unchanged.

**Build Command**

`pip install -r requirements.txt && alembic upgrade head`

**Start Command**

`uvicorn app.main:app --host 0.0.0.0 --port $PORT`

Expected migration line:

`Running upgrade 20260802_0009 -> 20260803_0010, Add freelancer join dates and backfill the current team roster.`

When automatic deployment does not start:

`Manual Deploy → Deploy latest commit`

After Render reports **Live**, press `Ctrl + Shift + R`.

Confirm the sidebar version:

`v3.0.7-release21.07-exports-join-dates-unassigned`
