# Deploy BIM Portal Release 21.17 to Render

Extract `BIMFM_PORTAL_RELEASE_21_17_RENDER.zip` and open PowerShell inside the extracted `BIMFM_PORTAL_RELEASE_21_17_RENDER` folder.

Run every command separately.

## 1. Set the release and repository folders

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

## 2. Copy the cumulative release

```powershell
robocopy $Release $Repo /E /XD .git .venv venv __pycache__ data backups logs uploads /XF .env *.db *.sqlite *.sqlite3 *.pyc /R:2 /W:1
```

Robocopy exit codes 0 through 7 mean success.

## 3. Enter the Git repository

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

## 4. Stage only Release 21.17 files

Copy the following as one line:

```powershell
git add app/config.py app/web_helpers.py app/task_time_reporting.py app/excel_exports.py app/portal_project_service.py app/routers/projects.py app/locales/en.json app/locales/zh_TW.json static/css/ui-refresh.css templates/base.html templates/task_time_utilization.html templates/freelancer_completed_tasks.html README_RELEASE_21_17_CLEAR_UTILIZATION_COMPLETED_FILTERS.md DEPLOYMENT_RELEASE_21_17_RENDER.md DATABASE_SAFETY_RELEASE_21_17.md TEST_REPORT_RELEASE_21_17.txt
```

Do not use `git add .`.

## 5. Review the staged change

```powershell
git diff --cached --stat
```

```powershell
git status
```

## 6. Commit

```powershell
git commit -m "Release 21.17 clarify utilization and completed task filters"
```

## 7. Push

```powershell
git push origin main
```

```powershell
git log -1 --oneline
```

## Render settings

Keep the current Build Command:

```text
pip install -r requirements.txt && alembic upgrade head
```

Keep the current Start Command:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

No new migration line is expected. The database should remain at:

```text
20260804_0015
```

When automatic deployment does not start:

```text
Render Dashboard → Manual Deploy → Deploy latest commit
```

After Render reports **Live**, perform a hard refresh:

```text
Ctrl + Shift + R
```

Confirm the lower-left status displays:

```text
System online
v3.0.17
```

Then verify:

1. Open **Task Time Utilization** and confirm the formula, Included Recorded Time, Excluded Time, and task-level calculations are visible.
2. Open a freelancer account → **Recently Completed Tasks** and test This week, Last 2 weeks, Last 3 weeks, This month, Last 3 months, Last 6 months, This year, and All time.
