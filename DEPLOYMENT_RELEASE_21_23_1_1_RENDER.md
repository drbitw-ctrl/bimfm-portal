# Deploy BIM Portal Release 21.23.1.1 to Render from VS Code

This guide assumes the Render-connected Git repository is:

`C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER`

and the extracted new release is:

`C:\Users\Don\Documents\PROGRAMMING\BIM_PORTAL_RELEASE_21_23_1_1_RENDER`

Release 21.23.1.1 contains no database migration or schema change.

## 1. Set paths in the VS Code PowerShell terminal

```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
$Release = "C:\Users\Don\Documents\PROGRAMMING\BIM_PORTAL_RELEASE_21_23_1_1_RENDER"

$Repo = (Resolve-Path $Repo).Path
$Release = (Resolve-Path $Release).Path
$env:GIT_PAGER = "cat"

Set-Location $Repo
```

## 2. Preserve the Release 21.22.10 rollback point before committing

The working tree may already contain uncommitted Release 21.23.1 files. A Git tag still points to the current committed HEAD, so create/push the rollback tag before the new commit if it does not already exist.

```powershell
git status
git log -1 --oneline

$RollbackTag = git tag --list "production-21.22.10-before-screen-sharing"
if ([string]::IsNullOrWhiteSpace($RollbackTag)) {
    git tag -a production-21.22.10-before-screen-sharing -m "Production 21.22.10 before screen sharing"
    git push origin production-21.22.10-before-screen-sharing
} else {
    Write-Host "Rollback tag already exists: $RollbackTag" -ForegroundColor Green
}
```

## 3. Copy only approved application files

This intentionally does not copy database, model, migration, environment, or seed files.

```powershell
$ReleaseFiles = @(
    "app\config.py",
    "app\main.py",
    "app\screen_share.py",
    "app\live_work_overview.py",
    "templates\admin_dashboard.html",
    "templates\freelancer_tasks.html",
    "templates\staff_my_work.html",
    "templates\base.html",
    "templates\screen_share_test.html",
    "static\js\screen-share.js",
    "static\css\ui-refresh.css",
    "tests\test_release_21_23_1_render_live_work_screen_sharing.py",
    "tests\test_release_21_23_1_1_screen_share_usability_hotfix.py",
    "README_RELEASE_21_23_1_LIVE_WORK_SCREEN_SHARING.md",
    "README_RELEASE_21_23_1_1_SCREEN_SHARE_USABILITY_HOTFIX.md",
    "DATABASE_SAFETY_RELEASE_21_23_1.md",
    "DATABASE_SAFETY_RELEASE_21_23_1_1.md",
    "DEPLOYMENT_RELEASE_21_23_1_1_RENDER.md",
    "TEST_REPORT_RELEASE_21_23_1_1_RENDER.txt"
)

foreach ($File in $ReleaseFiles) {
    $Source = Join-Path $Release $File
    $Target = Join-Path $Repo $File
    New-Item -ItemType Directory -Force -Path (Split-Path $Target) | Out-Null
    Copy-Item $Source $Target -Force
}
```

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

Do not commit if the result is `STOP`.

Then review:

```powershell
git status
git diff --stat
git diff --name-only
```

## 5. Local validation before deployment

If the repository already has `.venv`:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q
```

If `.venv` does not exist:

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q
```

## 6. Stage only Release 21.23.1.1 files

```powershell
git add -- $ReleaseFiles

git diff --cached --stat
git diff --cached --name-only
```

Confirm the staged list contains no `alembic/`, `app/models/`, `data/`, or `.env` files.

## 7. Commit and push

```powershell
git commit -m "Release 21.23.1.1 screen sharing usability hotfix"
git push origin main
```

If Render Auto-Deploy is enabled for `main`, the push starts the deployment.

## 8. Render service settings

Keep the existing production PostgreSQL `DATABASE_URL` unchanged.

Build command:

```text
pip install -r requirements.txt && alembic upgrade head
```

Start command:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Health check path:

```text
/health/ready
```

For this release keep one Render service instance and one Uvicorn worker because the screen-share signaling registry is still process-local/in-memory.

## 9. Post-deployment test

Hard-refresh the freelancer and management browsers (`Ctrl+Shift+R`).

Freelancer:

1. Start a Work Order.
2. Confirm Stop Live Screen is initially disabled/greyed out.
3. Press Start Live Screen.
4. Select the Autodesk Revit window.
5. Confirm the local Live Preview displays Revit.
6. Confirm the on-page notification says live screen sharing is active.
7. Confirm Start is disabled and Stop is enabled.

Admin/Supervisor/Finance Head:

1. Open Dashboard.
2. Confirm the live thumbnail appears.
3. Note the viewer count.
4. Press View Live and confirm the expanded live video appears.
5. Press View Live again; the same expanded view should remain and the viewer count should not increase because of the repeated click.
6. Close Live View; the thumbnail should continue.

Freelancer stop test:

1. Press Stop Live Screen.
2. Confirm local preview clears.
3. Confirm the stopped notification appears.
4. Confirm Start is enabled and Stop is disabled.
5. Confirm the Work Order timer remains running.

## 10. Rollback

If you do not want to keep Release 21.23.1.1, use Render Dashboard -> service -> Deploys -> select the previous successful deploy -> Rollback -> Rollback to this deploy.

The permanent Git recovery point is:

`production-21.22.10-before-screen-sharing`

No database downgrade is required for this release because it adds no database migration or schema change.
