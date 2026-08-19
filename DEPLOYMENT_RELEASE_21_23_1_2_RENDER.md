# Release 21.23.1.2 — Render Deployment (VS Code / PowerShell)

This release is intended for the existing Render-connected Git repository:

`C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER`

The extracted release folder is expected to be:

`C:\Users\Don\Documents\PROGRAMMING\BIM_PORTAL_RELEASE_21_23_1_2_RENDER`

## 1. Open the existing Render Git repository in VS Code

Open a PowerShell terminal and run:

```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
$Release = "C:\Users\Don\Documents\PROGRAMMING\BIM_PORTAL_RELEASE_21_23_1_2_RENDER"
$Repo = (Resolve-Path $Repo).Path
$Release = (Resolve-Path $Release).Path
$env:GIT_PAGER = "cat"
Set-Location $Repo

git status
git log -1 --oneline
```

Do not continue if unrelated uncommitted production changes are present.

## 2. Create a rollback tag for the version currently online

```powershell
git tag -a production-before-21.23.1.2 -m "Production before Release 21.23.1.2"
git push origin production-before-21.23.1.2
```

If the tag already exists, do not recreate it. Check with:

```powershell
git tag --list "production-before-21.23.1.2"
```

The older `production-21.22.10-before-screen-sharing` tag should also remain untouched.

## 3. Copy only approved 21.23.1.2 application files

```powershell
$ReleaseFiles = @(
    "app\config.py",
    "app\performance_reporting.py",
    "app\task_time_reporting.py",
    "app\excel_exports.py",
    "app\locales\en.json",
    "app\locales\zh_TW.json",
    "templates\admin_dashboard.html",
    "templates\freelancer_tasks.html",
    "templates\screen_share_test.html",
    "templates\task_time_utilization.html",
    "tests\test_release_21_23_1_render_live_work_screen_sharing.py",
    "tests\test_release_21_23_1_1_screen_share_usability_hotfix.py",
    "tests\test_release_21_23_1_2_ratings_utilization_hotfix.py",
    "README_RELEASE_21_23_1_2_RATINGS_UTILIZATION_HOTFIX.md",
    "DATABASE_SAFETY_RELEASE_21_23_1_2.md",
    "DEPLOYMENT_RELEASE_21_23_1_2_RENDER.md",
    "TEST_REPORT_RELEASE_21_23_1_2_RENDER.txt"
)

foreach ($File in $ReleaseFiles) {
    $Source = Join-Path $Release $File
    $Target = Join-Path $Repo $File
    New-Item -ItemType Directory -Force -Path (Split-Path $Target) | Out-Null
    Copy-Item $Source $Target -Force
}
```

This intentionally does not copy `data/`, `alembic/`, `app/models/`, `.env`, or database files.

## 4. Mandatory database safety check

```powershell
Set-Location $Repo
$Unsafe = git status --porcelain | Select-String -Pattern '(^|\s)(alembic/|app/models/|data/|\.env)'

if ($Unsafe) {
    Write-Host "STOP - DATABASE/MODEL FILES CHANGED" -ForegroundColor Red
    $Unsafe
} else {
    Write-Host "PASS - NO DATABASE/MODEL FILES CHANGED" -ForegroundColor Green
}
```

Continue only if the result is:

`PASS - NO DATABASE/MODEL FILES CHANGED`

Review:

```powershell
git status
git diff --stat
git diff --name-only
```

## 5. Optional local regression test

If `pytest` is not installed locally:

```powershell
python -m pip install pytest
```

Then:

```powershell
python -m pip install -r requirements.txt
python -m pytest -q
```

The packaged release passed 109 tests.

## 6. Stage the approved files

```powershell
git add -- $ReleaseFiles
```

Verify the staged set:

```powershell
git diff --cached --name-only

$UnsafeStaged = git diff --cached --name-only | Select-String -Pattern '^(alembic/|app/models/|data/|\.env)'
if ($UnsafeStaged) {
    Write-Host "STOP - DATABASE/MODEL FILES STAGED" -ForegroundColor Red
    $UnsafeStaged
} else {
    Write-Host "PASS - NO DATABASE/MODEL FILES STAGED" -ForegroundColor Green
}
```

## 7. Commit and push

```powershell
git commit -m "Release 21.23.1.2 ratings and utilization hotfix"
git log -1 --oneline
git push origin main
```

A successful push should show a new commit range instead of `Everything up-to-date`.

## 8. Render settings

Keep the existing production settings unchanged.

Build command:

`pip install -r requirements.txt && alembic upgrade head`

Start command:

`uvicorn app.main:app --host 0.0.0.0 --port $PORT`

Health check:

`/health/ready`

Do not change the production `DATABASE_URL`.

Keep one Render application instance / one Uvicorn worker while screen-sharing signaling remains process-local.

There is no new Alembic migration in Release 21.23.1.2, so the existing build command does not apply a new schema revision.

## 9. Post-deployment checks

Hard refresh the browser (`Ctrl + Shift + R`) and verify the displayed version:

`v3.0.23.1.2-release21.23.1.2-ratings-utilization-hotfix`

Check:

1. Performance / Ratings — Administrator accounts no longer appear in member rankings.
2. Task Time Utilization — Review Time is shown separately.
3. A task with saved review time uses Production Time + Review Time for its utilization percentage.
4. Existing Live Work Room and screen-sharing functions still operate normally.

## Rollback

If you do not want this release, use the previous successful deployment in Render's deployment history, or restore from the Git tag created before deployment:

`production-before-21.23.1.2`

No Release 21.23.1.2 database downgrade is required because this release creates no database migration or schema change.
