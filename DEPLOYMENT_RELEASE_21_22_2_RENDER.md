# BIM Portal Release 21.22.2 — Render Deployment

This release has no database migration or schema change.

## 1. Extract the package
Extract `BIM_PORTAL_RELEASE_21_22_2_RENDER.zip` and open PowerShell inside the inner `BIM_PORTAL_RELEASE_21_22_2_RENDER` folder.

## 2. Set paths
```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
$Release = (Get-Location).Path

$Repo = (Resolve-Path $Repo).Path
$Release = (Resolve-Path $Release).Path

Write-Host "Repository: $Repo"
Write-Host "Release: $Release"
```

## 3. Copy the release
```powershell
robocopy $Release $Repo /E /XD .git .venv venv __pycache__ data backups logs uploads /XF .env *.db *.sqlite *.sqlite3 *.pyc /R:2 /W:1
```
Robocopy exit codes 0 through 7 indicate success.

## 4. Review
```powershell
Set-Location $Repo
$env:GIT_PAGER = "cat"

git status
git diff --stat
```

## 5. Stage Release 21.22.2
```powershell
git add app/config.py app/routers/portal.py app/locales/en.json app/locales/zh_TW.json static/css/ui-refresh.css templates/attendance.html templates/portal_module.html tests/test_release_21_22_2_completed_period_privacy.py README_RELEASE_21_22_2_COMPLETED_TASK_PERIODS_PRIVACY.md DEPLOYMENT_RELEASE_21_22_2_RENDER.md DATABASE_SAFETY_RELEASE_21_22_2.md TEST_REPORT_RELEASE_21_22_2.txt
```

## 6. Review staged changes
```powershell
git status
git diff --cached --stat
```

## 7. Commit and push
```powershell
git commit -m "Release 21.22.2 completed task periods and freelancer privacy"
git push origin main
git log -1 --oneline
```

## 8. Render settings
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

## 9. Verify after Render is Live
Hard refresh with `Ctrl + Shift + R`.

Confirm version:
```text
v3.0.22.2-release21.22.2-completed-task-periods-privacy
```

Verify:
1. Freelancer Today's Attendance shows the member name and join date but no PH/LEGACY/internal member code.
2. Administrator Recently Completed Tasks offers Last 1 Week, Last 2 Weeks, Last 3 Weeks, Last 30 Days, This Month, Last Month, Last 3 Months, Last 6 Months, and All Completed Tasks.
3. Repeat the Recently Completed Tasks check using Supervisor and Finance accounts.
4. Existing tasks and completed-task records remain unchanged.
