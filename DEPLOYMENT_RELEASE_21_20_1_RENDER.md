# BIMFM Portal Release 21.20.1 — Render Deployment

## 1. Extract the release

Open PowerShell inside `BIMFM_PORTAL_RELEASE_21_20_1_RENDER`.

## 2. Set folders

```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
$Release = (Get-Location).Path
$Repo = (Resolve-Path $Repo).Path
$Release = (Resolve-Path $Release).Path
Write-Host "Repository: $Repo"
Write-Host "Release: $Release"
```

The paths must be different.

## 3. Copy the release

```powershell
robocopy $Release $Repo /E /XD .git .venv venv __pycache__ data backups logs uploads /XF .env *.db *.sqlite *.sqlite3 *.pyc /R:2 /W:1
```

Robocopy exit codes 0 through 7 indicate success.

## 4. Review and stage

```powershell
Set-Location $Repo
$env:GIT_PAGER = "cat"
git status
git diff --stat
```

```powershell
git add app/config.py app/routers/overtime.py static/css/ui-refresh.css templates/admin_overtime.html tests/test_release_21_20_1_overtime_page_repair.py README_RELEASE_21_20_1_OVERTIME_PAGE_REPAIR.md DEPLOYMENT_RELEASE_21_20_1_RENDER.md TEST_REPORT_RELEASE_21_20_1.txt
```

```powershell
git diff --cached --stat
git status
```

## 5. Commit and push

```powershell
git commit -m "Release 21.20.1 overtime page repair"
git push origin main
```

## 6. Render

Keep the existing commands:

Build Command:

```text
pip install -r requirements.txt && alembic upgrade head
```

Start Command:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

No Alembic migration is included. If auto-deploy is disabled, use **Manual Deploy → Deploy latest commit**.

After Render reports Live, press `Ctrl + Shift + R`. Confirm the version is:

```text
v3.0.20.1-release21.20.1-overtime-page-repair
```

Verify:

1. Member dropdown contains active mapped freelancers.
2. Add Previous Overtime submits successfully.
3. Current-month overtime records appear by default, regardless of pending/approved status.
4. Month and status filters work.
5. Overnight actual end time such as 2:30 AM still defaults to 510 minutes for a 6:00 PM start.
