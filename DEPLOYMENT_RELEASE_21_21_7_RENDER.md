# BIM Portal Release 21.21.7 — Render Deployment

## 1. Extract and open PowerShell inside

`BIMFM_PORTAL_RELEASE_21_21_7_RENDER`

## 2. Set folders

```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
$Release = (Get-Location).Path
$Repo = (Resolve-Path $Repo).Path
$Release = (Resolve-Path $Release).Path
Write-Host "Repository: $Repo"
Write-Host "Release: $Release"
```

## 3. Copy release

```powershell
robocopy $Release $Repo /E /XD .git .venv venv __pycache__ data backups logs uploads /XF .env *.db *.sqlite *.sqlite3 *.pyc /R:2 /W:1
```

Exit codes 0–7 mean success.

## 4. Review and stage

```powershell
Set-Location $Repo
$env:GIT_PAGER = "cat"
git status
git diff --stat

git add app/config.py app/routers/administration.py templates/admin_staff_accounts.html tests/test_release_21_21_7_admin_task_assignment.py README_RELEASE_21_21_7_ADMIN_TASK_ASSIGNMENT_ROUTE.md DEPLOYMENT_RELEASE_21_21_7_RENDER.md DATABASE_SAFETY_RELEASE_21_21_7.md TEST_REPORT_RELEASE_21_21_7.txt

git status
git diff --cached --stat
```

## 5. Commit and push

```powershell
git commit -m "Release 21.21.7 administrator task assignment route repair"
git push origin main
git log -1 --oneline
```

## 6. Render settings

Build Command:

```text
pip install -r requirements.txt && alembic upgrade head
```

Start Command:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Health Check:

```text
/health/ready
```

After Render reports Live, press `Ctrl + Shift + R`, confirm `v3.0.21.7`, then open **Administration → Staff Access** and select **Enable Task Assignment for Me**.
