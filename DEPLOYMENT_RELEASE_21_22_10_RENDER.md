# Deploy BIM Portal Release 21.22.10 to Render

Release 21.22.10 can be deployed directly over Release 21.22.9. It contains no database migration or schema change.

## 1. Extract the release

Extract `BIM_PORTAL_RELEASE_21_22_10_RENDER.zip` and open PowerShell inside the extracted `BIM_PORTAL_RELEASE_21_22_10_RENDER` folder.

## 2. Set paths

```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
$Release = (Get-Location).Path

$Repo = (Resolve-Path $Repo).Path
$Release = (Resolve-Path $Release).Path

Write-Host "Repository: $Repo"
Write-Host "Release:    $Release"
```

## 3. Copy the release without local databases or secrets

```powershell
robocopy $Release $Repo /E `
/XD .git .venv venv __pycache__ .pytest_cache data backups logs uploads `
/XF .env *.db *.sqlite *.sqlite3 *.pyc `
/R:2 /W:1
```

Robocopy exit codes `0` through `7` are successful.

## 4. Review changes

```powershell
Set-Location $Repo
$env:GIT_PAGER = "cat"

git status
git diff --stat
```

Expected application changes are limited to the personal attendance/DTR history feature plus release documentation/tests.

## 5. Stage Release 21.22.10

```powershell
git add app/config.py `
app/locales/en.json `
app/locales/zh_TW.json `
app/routers/attendance.py `
static/css/ui-refresh.css `
templates/attendance_history.html `
templates/base.html `
templates/freelancer_dtr_detail.html `
tests/test_release_21_22_10_personal_attendance_dtr_history.py `
README_RELEASE_21_22_10_PERSONAL_ATTENDANCE_DTR_HISTORY.md `
DATABASE_SAFETY_RELEASE_21_22_10.md `
DEPLOYMENT_RELEASE_21_22_10_RENDER.md `
TEST_REPORT_RELEASE_21_22_10.txt
```

Review the staged changes:

```powershell
git status
git diff --cached --stat
```

## 6. Commit and push

```powershell
git commit -m "Release 21.22.10 freelancer attendance and DTR history"
git push origin main
git log -1 --oneline
```

## 7. Render settings remain unchanged

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

## 8. Post-deployment checks

After Render reports **Live**, hard-refresh the browser with `Ctrl + Shift + R`.

Confirm version:

```text
v3.0.22.10-release21.22.10-attendance-dtr-history
```

Then log in as a normal freelancer and verify:

1. Sidebar shows **Attendance History & DTR**.
2. Recent 31 attendance records load.
3. **This Month**, **Last Month**, and a specific month load.
4. **All Time** loads the full retained attendance record history.
5. Monthly DTR cards appear for that freelancer only.
6. **View DTR** opens the selected personal DTR.
7. Manually entering another member's DTR ID does not expose that DTR.
8. The DTR page is read-only and clearly separates Daily Time Record from Daily Task Reports.
9. Normal Administration, Work Orders, OT, Finance, and DTR generation remain unchanged.
