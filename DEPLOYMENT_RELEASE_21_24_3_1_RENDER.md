# Render Deployment — Release 21.24.3.1

## Important
No database schema or data changes exist in this release.
Do not copy `data/`, `.env`, `alembic/`, or `app/models/`.

## VS Code PowerShell

```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
$Release = "C:\Users\Don\Documents\PROGRAMMING\BIM_PORTAL_RELEASE_21_24_3_1_RENDER"

$Repo = (Resolve-Path $Repo).Path
$Release = (Resolve-Path $Release).Path
$env:GIT_PAGER = "cat"
Set-Location $Repo

git status
git log -1 --oneline
```

### Create rollback tag

```powershell
$Tag = git tag --list "production-before-21.24.3.1"
if ([string]::IsNullOrWhiteSpace($Tag)) {
    git tag -a production-before-21.24.3.1 -m "Production before Release 21.24.3.1"
    git push origin production-before-21.24.3.1
}
```

### Copy approved release files

```powershell
$ReleaseFiles = @(
    "app\config.py",
    "app\locales\en.json",
    "app\locales\zh_TW.json",
    "app\routers\administration.py",
    "static\css\ui-refresh.css",
    "templates\admin_dashboard.html",
    "tests\test_release_21_23_1_render_live_work_screen_sharing.py",
    "tests\test_release_21_23_1_1_screen_share_usability_hotfix.py",
    "tests\test_release_21_23_1_2_ratings_utilization_hotfix.py",
    "tests\test_release_21_24_0_finance_reporting_bank_details.py",
    "tests\test_release_21_24_0_1_dtr_overtime_render_hotfix.py",
    "tests\test_release_21_24_0_2_finance_ui_leave_approval_hotfix.py",
    "tests\test_release_21_24_1_project_reporting_localized_excel.py",
    "tests\test_release_21_24_2_finance_history_quick_view.py",
    "tests\test_release_21_24_3_operations_overview_overtime_history.py",
    "tests\test_release_21_24_3_1_dashboard_leave_availability.py",
    "README_RELEASE_21_24_3_1_DASHBOARD_LEAVE_AVAILABILITY_HOTFIX.md",
    "DATABASE_SAFETY_RELEASE_21_24_3_1.md",
    "DEPLOYMENT_RELEASE_21_24_3_1_RENDER.md",
    "TEST_REPORT_RELEASE_21_24_3_1_RENDER.txt"
)

foreach ($File in $ReleaseFiles) {
    $Source = Join-Path $Release $File
    $Target = Join-Path $Repo $File
    New-Item -ItemType Directory -Force -Path (Split-Path $Target) | Out-Null
    Copy-Item $Source $Target -Force
}
```

### Database safety check

```powershell
$Unsafe = git status --porcelain | Select-String -Pattern '(^|\s)(alembic/|app/models/|data/|\.env)'
if ($Unsafe) {
    Write-Host "STOP - DATABASE/MODEL FILES CHANGED" -ForegroundColor Red
    $Unsafe
} else {
    Write-Host "PASS - NO DATABASE/MODEL FILES CHANGED" -ForegroundColor Green
}
```

Expected:
`PASS - NO DATABASE/MODEL FILES CHANGED`

### Review, commit, push

```powershell
git diff --stat
git diff --name-only

git add -- $ReleaseFiles
git diff --cached --name-only

git commit -m "Release 21.24.3.1 dashboard leave availability hotfix"
git log -1 --oneline
git push origin main
```

## Render settings
Keep unchanged.

Build:
`pip install -r requirements.txt && alembic upgrade head`

Start:
`uvicorn app.main:app --host 0.0.0.0 --port $PORT`

Health:
`/health/ready`

There is no new Alembic revision; the existing 0018 schema remains unchanged.

## Post-deploy verification
1. Hard refresh: `Ctrl + Shift + R`.
2. Confirm version: `v3.0.24.3.1-release21.24.3.1-dashboard-leave-availability-hotfix`.
3. Open Dashboard → Availability and current assignments.
4. A member with approved leave today must appear under **On Leave Today**, not **Available Now**.
5. Switch to Traditional Chinese and confirm **今日請假 / 請假中**.
