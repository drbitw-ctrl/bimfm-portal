# Render Deployment — Release 21.24.1

## Important
This release has NO database schema or data changes.
Do not copy `data/`, `.env`, `alembic/`, or `app/models/` from the release package into the Git repository.

## Paths used in VS Code PowerShell

```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
$Release = "C:\Users\Don\Documents\PROGRAMMING\BIM_PORTAL_RELEASE_21_24_1_RENDER"

$Repo = (Resolve-Path $Repo).Path
$Release = (Resolve-Path $Release).Path
$env:GIT_PAGER = "cat"
Set-Location $Repo
```

## 1. Confirm current repository

```powershell
git status
git log -1 --oneline
```

## 2. Create rollback tag

```powershell
$Tag = git tag --list "production-before-21.24.1"
if ([string]::IsNullOrWhiteSpace($Tag)) {
    git tag -a production-before-21.24.1 -m "Production before Release 21.24.1"
    git push origin production-before-21.24.1
}
```

## 3. Copy only approved files

```powershell
$ReleaseFiles = @(
    "app\config.py",
    "app\excel_exports.py",
    "app\locales\en.json",
    "app\locales\zh_TW.json",
    "app\performance_reporting.py",
    "app\routers\portal.py",
    "templates\project_reports.html",
    "tests\test_release_21_23_1_1_screen_share_usability_hotfix.py",
    "tests\test_release_21_23_1_2_ratings_utilization_hotfix.py",
    "tests\test_release_21_23_1_render_live_work_screen_sharing.py",
    "tests\test_release_21_24_0_1_dtr_overtime_render_hotfix.py",
    "tests\test_release_21_24_0_2_finance_ui_leave_approval_hotfix.py",
    "tests\test_release_21_24_0_finance_reporting_bank_details.py",
    "tests\test_release_21_24_1_project_reporting_localized_excel.py",
    "README_RELEASE_21_24_1_PROJECT_REPORT_PERIOD_LOCALIZED_EXCEL.md",
    "DATABASE_SAFETY_RELEASE_21_24_1.md",
    "DEPLOYMENT_RELEASE_21_24_1_RENDER.md",
    "TEST_REPORT_RELEASE_21_24_1_RENDER.txt"
)

foreach ($File in $ReleaseFiles) {
    $Source = Join-Path $Release $File
    $Target = Join-Path $Repo $File
    New-Item -ItemType Directory -Force -Path (Split-Path $Target) | Out-Null
    Copy-Item $Source $Target -Force
}
```

## 4. Database safety check

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

## 5. Review and stage

```powershell
git diff --stat
git diff --name-only
git add -- $ReleaseFiles
git diff --cached --name-only
```

## 6. Commit and push

```powershell
git commit -m "Release 21.24.1 project reports and localized Excel"
git push origin main
```

Ensure the push shows a new commit range and does not say `Everything up-to-date`.

## Render settings
Keep the existing production settings unchanged.

Build:
`pip install -r requirements.txt && alembic upgrade head`

Start:
`uvicorn app.main:app --host 0.0.0.0 --port $PORT`

Health:
`/health/ready`

There is no new Alembic revision in 21.24.1; `alembic upgrade head` should leave the existing 0018 schema unchanged.

## Post-deploy verification
1. Hard refresh with Ctrl+Shift+R.
2. Confirm version: `v3.0.24.1-release21.24.1-project-report-period-localized-excel`.
3. Project Reports -> Monthly: verify selected-month project/member totals.
4. Switch to 12 Months: verify totals expand to the rolling 12-month period.
5. Switch to All Time: verify complete historical totals.
6. Export Project Work Time from each period and confirm workbook totals match the page.
7. Switch portal to Traditional Chinese and export again; workbook sheet names, titles and headers should be Traditional Chinese.
