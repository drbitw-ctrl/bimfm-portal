# Deploy BIM Portal Release 21.22.9 to Render

You can deploy Release 21.22.9 directly over your current 21.22.8/21.22.6 application repository. You do not need to deploy 21.22.7 first.

## 1. Extract the ZIP

Extract `BIM_PORTAL_RELEASE_21_22_9_RENDER.zip` and open PowerShell inside the inner `BIM_PORTAL_RELEASE_21_22_9_RENDER` folder.

## 2. Set paths

```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
$Release = (Get-Location).Path

$Repo = (Resolve-Path $Repo).Path
$Release = (Resolve-Path $Release).Path

Write-Host "Repository: $Repo"
Write-Host "Release:    $Release"
```

The repository and release paths must be different.

## 3. Copy the release

```powershell
robocopy $Release $Repo /E `
/XD .git .venv venv __pycache__ data backups logs uploads `
/XF .env *.db *.sqlite *.sqlite3 *.pyc `
/R:2 /W:1
```

Robocopy exit codes 0 through 7 are successful.

## 4. Review Git changes

```powershell
Set-Location $Repo
$env:GIT_PAGER = "cat"

git status
git diff --stat
```

## 5. Stage Release 21.22.9

```powershell
git add app/config.py `
app/locales/en.json `
app/locales/zh_TW.json `
app/routers/administration.py `
app/routers/portal.py `
static/css/ui-refresh.css `
templates/admin_review_queue.html `
templates/staff_my_work.html `
tests/test_release_21_22_8_review_dashboard_dtr.py `
tests/test_release_21_22_9_review_and_staff_work.py `
README_RELEASE_21_22_9.md `
DATABASE_SAFETY_RELEASE_21_22_9.md `
DEPLOYMENT_RELEASE_21_22_9_RENDER.md `
TEST_REPORT_RELEASE_21_22_9.txt
```

Review the staged changes:

```powershell
git status
git diff --cached --stat
```

## 6. Commit and push

```powershell
git commit -m "Release 21.22.9 review and staff work order stabilization"
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

Release 21.22.9 adds no migration, so `alembic upgrade head` has no new 21.22.9 schema operation to apply.

## 8. After Render becomes Live

Hard-refresh the browser:

```text
Ctrl + Shift + R
```

Confirm the footer/version shows `v3.0.22.9`.

## 9. Production smoke-test order

1. Open `/admin` and confirm the Availability board has no horizontal scrollbar.
2. Confirm assigned member cards wrap into multiple rows while retaining full task details.
3. Open `/admin/review-queue` and confirm HTTP 200.
4. Assign a review to yourself.
5. Start Review; confirm the queue reloads instead of returning HTTP 500.
6. Stop Review with a short review activity note.
7. Open `/portal/my-work`.
8. Confirm `My Assigned Tasks` contains tasks assigned directly to your administrator/supervisor task profile.
9. Start one normal assigned-task Work Order, then stop it with a work activity description.
10. Confirm `My Review Work` remains separate and its Start/Stop controls work.
11. Confirm the freelancer's original assignment/status/progress has not changed because of review timing.
12. Confirm Administrator TS-* identities are still absent from DTR generation.
