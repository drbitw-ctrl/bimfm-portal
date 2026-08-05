# Release 21.21.1 — Render Deployment

Extract the ZIP and open PowerShell inside `BIMFM_PORTAL_RELEASE_21_21_1_RENDER`.

```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
$Release = (Get-Location).Path
$Repo = (Resolve-Path $Repo).Path
$Release = (Resolve-Path $Release).Path
Write-Host "Repository: $Repo"
Write-Host "Release: $Release"
```

The paths must be different.

```powershell
robocopy $Release $Repo /E /XD .git .venv venv __pycache__ data backups logs uploads /XF .env *.db *.sqlite *.sqlite3 *.pyc /R:2 /W:1
```

Robocopy exit codes 0–7 indicate success.

```powershell
Set-Location $Repo
$env:GIT_PAGER = "cat"
git status
git diff --stat
```

Stage only this patch:

```powershell
git add app/config.py static/css/ui-refresh.css static/js/ui.js templates/base.html README_RELEASE_21_21_1_PREMIUM_WORKSPACE_HEADER.md DEPLOYMENT_RELEASE_21_21_1_RENDER.md DATABASE_SAFETY_RELEASE_21_21_1.md TEST_REPORT_RELEASE_21_21_1.txt
```

```powershell
git status
git diff --cached --stat
git commit -m "Release 21.21.1 premium workspace header"
git push origin main
git log -1 --oneline
```

Keep Render settings unchanged.

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

After Render reports Live, press `Ctrl + Shift + R` and confirm version `v3.0.21.1`.

Because there is no migration, you may use Render Rollback to return to the prior deployment without restoring PostgreSQL.
