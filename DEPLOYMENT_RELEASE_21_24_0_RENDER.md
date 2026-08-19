# Render Deployment — BIM Portal Release 21.24.0

This release is based on 21.23.1.2. It includes one additive Alembic migration for the five optional bank-detail fields. No existing production records are rewritten.

## 1. Extract the release

Expected folder:

`C:\Users\Don\Documents\PROGRAMMING\BIM_PORTAL_RELEASE_21_24_0_RENDER`

Your Render-connected Git repository:

`C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER`

Open the repository in Visual Studio Code and use a PowerShell terminal.

## 2. Set paths

```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
$Release = "C:\Users\Don\Documents\PROGRAMMING\BIM_PORTAL_RELEASE_21_24_0_RENDER"

$Repo = (Resolve-Path $Repo).Path
$Release = (Resolve-Path $Release).Path
$env:GIT_PAGER = "cat"
Set-Location $Repo

git status
git log -1 --oneline
```

If there are unrelated uncommitted changes, stop and review them before continuing.

## 3. Create a rollback tag BEFORE copying the release

```powershell
$RollbackTag = git tag --list "production-before-21.24.0"
if ([string]::IsNullOrWhiteSpace($RollbackTag)) {
    git tag -a production-before-21.24.0 -m "Production before Release 21.24.0"
    git push origin production-before-21.24.0
} else {
    Write-Host "Rollback tag already exists: $RollbackTag" -ForegroundColor Green
}
```

## 4. Copy only approved release files

```powershell
$ReleaseFiles = @(
    "app\config.py",
    "app\excel_exports.py",
    "app\finance_service.py",
    "app\hr_workflow.py",
    "app\locales\en.json",
    "app\locales\zh_TW.json",
    "app\models\identity.py",
    "app\performance_reporting.py",
    "app\routers\administration.py",
    "app\routers\attendance.py",
    "app\routers\leave.py",
    "alembic\versions\20260819_0018_freelancer_bank_details.py",
    "static\css\ui-refresh.css",
    "templates\_dtr_actual_leave_overtime_history.html",
    "templates\_freelancer_bank_summary.html",
    "templates\admin_dtr_detail.html",
    "templates\admin_dtr_task_hourly.html",
    "templates\admin_finance_center.html",
    "templates\admin_freelancer_bank_details.html",
    "templates\admin_freelancers.html",
    "templates\admin_leave_requests.html",
    "templates\project_reports.html",
    "tests\test_release_21_23_1_render_live_work_screen_sharing.py",
    "tests\test_release_21_23_1_1_screen_share_usability_hotfix.py",
    "tests\test_release_21_23_1_2_ratings_utilization_hotfix.py",
    "tests\test_release_21_24_0_finance_reporting_bank_details.py",
    "README_RELEASE_21_24_0_FINANCE_REPORTING_BANK_DETAILS.md",
    "DATABASE_SAFETY_RELEASE_21_24_0.md",
    "DEPLOYMENT_RELEASE_21_24_0_RENDER.md",
    "TEST_REPORT_RELEASE_21_24_0_RENDER.txt"
)

foreach ($File in $ReleaseFiles) {
    $Source = Join-Path $Release $File
    $Target = Join-Path $Repo $File
    New-Item -ItemType Directory -Force -Path (Split-Path $Target) | Out-Null
    Copy-Item $Source $Target -Force
}
```

This intentionally does NOT copy `data/`, `.env`, backups, uploads, or any database file.

## 5. Safety check the database-related changes

The only allowed database/schema files in this release are:

- `app/models/identity.py`
- `alembic/versions/20260819_0018_freelancer_bank_details.py`

Run:

```powershell
Set-Location $Repo

$Changed = git status --porcelain | ForEach-Object { $_.Substring(3).Replace('\\','/') }
$UnexpectedDb = $Changed | Where-Object {
    ($_ -match '^data/' -or $_ -eq '.env' -or $_ -match '^app/models/' -or $_ -match '^alembic/versions/') -and
    $_ -ne 'app/models/identity.py' -and
    $_ -ne 'alembic/versions/20260819_0018_freelancer_bank_details.py'
}

if ($UnexpectedDb) {
    Write-Host "STOP - unexpected database/model files changed" -ForegroundColor Red
    $UnexpectedDb
} else {
    Write-Host "PASS - only the approved additive bank-detail schema change is present" -ForegroundColor Green
}
```

Do not continue if the check reports STOP.

Review:

```powershell
git status
git diff --stat
git diff --name-only
```

## 6. Optional local validation

If you have pytest installed:

```powershell
python -m pip install -r requirements.txt
python -m pip install pytest
python -m pytest -q
```

Expected release suite: `115 passed`.

Do NOT point local testing at your Render `DATABASE_URL`.

## 7. Stage only the approved files

```powershell
git add -- $ReleaseFiles

git diff --cached --stat
git diff --cached --name-only
```

Confirm no `data/` or `.env` file is staged and no other model/migration file is staged.

## 8. Commit and push

```powershell
git commit -m "Release 21.24.0 finance reporting and bank details"
git log -1 --oneline
git push origin main
```

The push must show a new commit range. If it says `Everything up-to-date`, the new release was not committed.

## 9. Render settings

Keep the existing environment variables, especially the production PostgreSQL `DATABASE_URL`.

Build command:

`pip install -r requirements.txt && alembic upgrade head`

Start command:

`uvicorn app.main:app --host 0.0.0.0 --port $PORT`

Health check:

`/health/ready`

Release 21.24.0 requires the existing build command because Alembic must apply revision `20260819_0018` before the new application starts.

## 10. Post-deployment checks

Hard-refresh the browser with `Ctrl + Shift + R`.

Expected version:

`v3.0.24.0-release21.24.0-finance-reporting-bank-details`

Verify:

1. Project Reports -> Monthly Project Work Time shows Project Total and member breakdown.
2. Approve a test leave request without entering an approval reason; approval should succeed. Rejection without a reason should still fail.
3. Freelancer Accounts -> Bank Details column -> Edit Bank Details saves the five fields.
4. Finance Center shows bank details for Admin/Finance users.
5. Monthly DTR Summary shows bank details plus Actual Leave History and Actual Overtime History for Admin/Finance users.

## Rollback

Preferred rollback: Render Dashboard -> service -> previous successful deployment -> Rollback.

Do NOT downgrade the database just to roll back the application. The five extra nullable columns are harmless to the previous application version.

Important: if you later perform a Git-based rollback and redeploy old application code, keep `alembic/versions/20260819_0018_freelancer_bank_details.py` in the repository so Alembic recognizes the database revision.

A full `alembic downgrade 20260806_0017` would drop the bank-detail columns and delete any bank values entered after deployment. Only do that if a deliberate schema rollback is required and bank data has been backed up.
