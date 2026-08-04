# BIM Portal Release 21.16 — Render Deployment

Deploy Release 21.16 from the extracted release folder into the existing local Git repository.

## 1. Open PowerShell in the extracted release folder

Expected folder name:

```text
BIMFM_PORTAL_RELEASE_21_16_RENDER
```

Run every command separately.

## 2. Set the release and repository paths

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
Write-Host "Release: $Release"
```

```powershell
Write-Host "Repository: $Repo"
```

The two paths must be different.

## 3. Copy Release 21.16 into the repository

```powershell
robocopy $Release $Repo /E /XD .git .venv venv __pycache__ data backups logs uploads /XF .env *.db *.sqlite *.sqlite3 *.pyc /R:2 /W:1
```

Robocopy exit codes **0 through 7 indicate success**.

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

## 5. Stage only Release 21.16 files

Copy this as one line:

```powershell
git add app/config.py app/database.py app/models/portal.py app/payroll_engine.py app/finance_service.py app/hr_workflow.py app/services/leave_service.py app/dtr_service.py app/dtr_exporter.py app/performance_reporting.py app/portal_project_service.py app/excel_exports.py app/main.py app/routers/finance.py app/routers/leave.py app/routers/overtime.py app/routers/portal.py app/locales/en.json app/locales/zh_TW.json alembic/versions/20260804_0015_hourly_finance_project_categories.py static/css/ui-refresh.css templates/admin_dashboard.html templates/attendance.html templates/admin_finance_center.html templates/admin_dtr_detail.html templates/admin_hr_policy.html templates/admin_leave_requests.html templates/freelancer_leave.html templates/freelancer_overtime.html templates/admin_new_portal_task.html templates/admin_edit_portal_task.html templates/performance_leaderboards.html templates/admin_project_team.html README_RELEASE_21_16_HOURLY_FINANCE_SPECIALTY_SUGGESTIONS.md DEPLOYMENT_RELEASE_21_16_RENDER.md DATABASE_SAFETY_RELEASE_21_16.md TEST_REPORT_RELEASE_21_16.txt
```

Do not use `git add .`.

## 6. Review staged changes

```powershell
git status
```

```powershell
git diff --cached --stat
```

Confirm that no unrelated local file or environment file is staged.

## 7. Commit Release 21.16

```powershell
git commit -m "Release 21.16 hourly finance and specialty suggestions"
```

## 8. Push to GitHub

```powershell
git push origin main
```

Confirm the latest commit:

```powershell
git log -1 --oneline
```

## 9. Render deployment

Keep the current Render commands unchanged.

**Build Command**

```text
pip install -r requirements.txt && alembic upgrade head
```

**Start Command**

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Expected migration message:

```text
Running upgrade 20260804_0014 -> 20260804_0015, Add project categories and align Gab's July 2026 hourly comp-credit data.
```

When automatic deployment does not start:

```text
Render Dashboard → Manual Deploy → Deploy latest commit
```

After Render reports **Live**, press:

```text
Ctrl + Shift + R
```

Confirm that the sidebar displays:

```text
v3.0.16-release21.16-hourly-finance-specialty-suggestions
```

## 10. Post-deployment verification

1. Open Finance Center for July 2026.
2. Regenerate Gab's July DTR when it is not finalized.
3. Confirm 32 leave hours, 15 credit hours applied, and 17 unpaid leave hours.
4. Open Performance and review specialty recommendations.
5. Open New Task and change Discipline and Project Category.
6. Confirm suggested members refresh and show availability, active tasks, overdue tasks, and current Work Order information.
7. Confirm Project Category appears in Projects, Project Team, and Excel exports.
