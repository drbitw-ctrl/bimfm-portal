# Render Deployment — Release 21.24.2

## Important
This release has **NO database schema or data changes**.
Do not copy `data/`, `.env`, `alembic/`, or `app/models/` from the release package into the Git repository.

## Paths
```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
$Release = "C:\Users\Don\Documents\PROGRAMMING\BIM_PORTAL_RELEASE_21_24_2_RENDER"
$Repo = (Resolve-Path $Repo).Path
$Release = (Resolve-Path $Release).Path
$env:GIT_PAGER = "cat"
Set-Location $Repo
```

## Verify current production repository
```powershell
git status
git log -1 --oneline
```

## Optional rollback tag
```powershell
$Tag = git tag --list "production-before-21.24.2"
if ([string]::IsNullOrWhiteSpace($Tag)) {
    git tag -a production-before-21.24.2 -m "Production before Release 21.24.2"
    git push origin production-before-21.24.2
}
```

## Copy approved files only
```powershell
$ReleaseFiles = @(
    "app\config.py",
    "app\locales\en.json",
    "app\locales\zh_TW.json",
    "app\routers\attendance.py",
    "app\routers\finance.py",
    "static\css\ui-refresh.css",
    "templates\_dtr_actual_leave_overtime_history.html",
    "templates\_finance_history_quick_nav.html",
    "templates\admin_dtr_detail.html",
    "templates\admin_dtr_task_hourly.html",
    "templates\admin_finance_center.html",
    "tests\test_release_21_23_1_1_screen_share_usability_hotfix.py",
    "tests\test_release_21_23_1_2_ratings_utilization_hotfix.py",
    "tests\test_release_21_23_1_render_live_work_screen_sharing.py",
    "tests\test_release_21_24_0_1_dtr_overtime_render_hotfix.py",
    "tests\test_release_21_24_0_2_finance_ui_leave_approval_hotfix.py",
    "tests\test_release_21_24_0_finance_reporting_bank_details.py",
    "tests\test_release_21_24_1_project_reporting_localized_excel.py",
    "tests\test_release_21_24_2_finance_history_quick_view.py",
    "README_RELEASE_21_24_2_FINANCE_HISTORY_QUICK_VIEW.md",
    "DATABASE_SAFETY_RELEASE_21_24_2.md",
    "DEPLOYMENT_RELEASE_21_24_2_RENDER.md",
    "TEST_REPORT_RELEASE_21_24_2_RENDER.txt"
)

foreach ($File in $ReleaseFiles) {
    $Source = Join-Path $Release $File
    $Target = Join-Path $Repo $File
    New-Item -ItemType Directory -Force -Path (Split-Path $Target) | Out-Null
    Copy-Item $Source $Target -Force
}
```

## Database safety check
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

## Review, stage, commit, push
```powershell
git diff --stat
git diff --name-only

git add -- $ReleaseFiles
git diff --cached --name-only

git commit -m "Release 21.24.2 finance history quick view"
git push origin main
```

## Render settings
Keep existing production settings unchanged.

Build:
`pip install -r requirements.txt && alembic upgrade head`

Start:
`uvicorn app.main:app --host 0.0.0.0 --port $PORT`

Health:
`/health/ready`

No new Alembic revision exists in 21.24.2; the existing `0018` schema remains unchanged.

## Post-deploy verification
1. Hard refresh `Ctrl + Shift + R`.
2. Confirm version `v3.0.24.2-release21.24.2-finance-history-quick-view`.
3. Finance Center: confirm grouped columns are easier to scan.
4. Click Summary for a freelancer with records from multiple months.
5. Confirm Leave History contains approved records from earlier months, not only the selected DTR month.
6. Confirm OT History contains submitted/final records from earlier months.
7. Confirm OT Credit Balance shows current available credit plus all-time earned/used totals.
8. Test OT History / OT Credit / Leave History shortcut buttons.
9. Switch to Traditional Chinese and confirm new labels translate correctly.
