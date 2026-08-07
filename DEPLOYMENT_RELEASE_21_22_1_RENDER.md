# BIM Portal Release 21.22.1 — Render Deployment

No database migration is included in this hotfix.

## PowerShell

```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
$Release = (Get-Location).Path
$Repo = (Resolve-Path $Repo).Path
$Release = (Resolve-Path $Release).Path
Write-Host "Repository: $Repo"
Write-Host "Release: $Release"
```

```powershell
robocopy $Release $Repo /E /XD .git .venv venv __pycache__ data backups logs uploads /XF .env *.db *.sqlite *.sqlite3 *.pyc /R:2 /W:1
```

```powershell
Set-Location $Repo
$env:GIT_PAGER = "cat"
git status
git diff --stat
```

```powershell
git add app/config.py app/routers/projects.py tests/test_release_21_22_1_work_order_method_repair.py README_RELEASE_21_22_1_WORK_ORDER_METHOD_REPAIR.md DEPLOYMENT_RELEASE_21_22_1_RENDER.md DATABASE_SAFETY_RELEASE_21_22_1.md TEST_REPORT_RELEASE_21_22_1.txt
```

```powershell
git status
git diff --cached --stat
git commit -m "Release 21.22.1 work order method repair"
git push origin main
git log -1 --oneline
```

Render Build Command remains:

```text
pip install -r requirements.txt && alembic upgrade head
```

Start Command remains:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

After Render reports Live, hard refresh with `Ctrl + Shift + R`, log in as Belinda, open Work Orders, start a task, and stop it with the required Daily Task Report text.
