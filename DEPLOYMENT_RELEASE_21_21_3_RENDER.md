# BIM Portal Release 21.21.3 — Render Deployment

## 1. Extract the release

Extract `BIMFM_PORTAL_RELEASE_21_21_3_RENDER.zip` and open PowerShell inside the extracted inner folder:

`BIMFM_PORTAL_RELEASE_21_21_3_RENDER`

## 2. Set the folders

```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
$Release = (Get-Location).Path

$Repo = (Resolve-Path $Repo).Path
$Release = (Resolve-Path $Release).Path

Write-Host "Repository: $Repo"
Write-Host "Release: $Release"
```

The two paths must be different.

## 3. Copy Release 21.21.3

```powershell
robocopy $Release $Repo /E /XD .git .venv venv __pycache__ data backups logs uploads /XF .env *.db *.sqlite *.sqlite3 *.pyc /R:2 /W:1
```

Robocopy exit codes `0` through `7` indicate success.

## 4. Enter the repository and review

```powershell
Set-Location $Repo
$env:GIT_PAGER = "cat"

git status
git diff --stat
```

## 5. Stage only Release 21.21.3

```powershell
git add app/config.py app/locales/en.json app/locales/zh_TW.json static/css/ui-refresh.css static/js/ui.js templates/admin_dashboard.html tests/test_release_21_21_3_dashboard_name_visibility.py README_RELEASE_21_21_3_DASHBOARD_NAME_VISIBILITY.md DEPLOYMENT_RELEASE_21_21_3_RENDER.md DATABASE_SAFETY_RELEASE_21_21_3.md TEST_REPORT_RELEASE_21_21_3.txt
```

Review the staged changes:

```powershell
git status
git diff --cached --stat
```

## 6. Commit and push

```powershell
git commit -m "Release 21.21.3 dashboard member name visibility"
git push origin main
git log -1 --oneline
```

## 7. Render configuration

Keep the existing Build Command:

```text
pip install -r requirements.txt && alembic upgrade head
```

Keep the existing Start Command:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Keep the Health Check Path:

```text
/health/ready
```

If automatic deployment does not start:

`Render Dashboard → Manual Deploy → Deploy latest commit`

## 8. Verify after deployment

After Render reports **Live**, press `Ctrl + Shift + R`.

Confirm the lower-left version is:

```text
v3.0.21.3
```

Then verify:

1. Open the Administration Dashboard.
2. Confirm all member names are visible by default.
3. Select `Hide member names` beside the availability legend.
4. Confirm names and avatar initials are hidden while assignments and workload remain readable.
5. Confirm the button changes to `Show member names`.
6. Refresh the page and confirm names are visible again.
7. Switch between `EN` and `繁中` and verify the control is translated.
8. Confirm Live Work Order refreshes remain hidden while the current page toggle is active.

## Rollback

This release has no database migration. If the result is not preferred, use Render's Web Service rollback to the previous successful deployment. No PostgreSQL rollback is needed.
