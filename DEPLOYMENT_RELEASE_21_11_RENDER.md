# Deploy BIMFM Portal Release 21.11 to Render

This is a cumulative package based on Release 21.10.

## PowerShell deployment

Open PowerShell inside the extracted `BIMFM_PORTAL_RELEASE_21_11_RENDER` folder. Run every command separately.

```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
```

```powershell
$Release = (Get-Location).Path
```

```powershell
$Repo = (Resolve-Path $Repo).Path
```

```powershell
$Release = (Resolve-Path $Release).Path
```

```powershell
robocopy $Release $Repo /E /XD .git .venv venv __pycache__ data backups logs uploads /XF .env *.db *.sqlite *.sqlite3 *.pyc /R:2 /W:1
```

Robocopy exit codes 0 through 7 mean success.

```powershell
Set-Location $Repo
```

```powershell
$env:GIT_PAGER = "cat"
```

```powershell
git status
```

Stage only Release 21.11 files:

```powershell
git add app/config.py app/work_order_service.py app/routers/portal.py static/js/ui.js static/css/ui-refresh.css templates/admin_dashboard.html README_RELEASE_21_11_ALL_LIVE_WORK_ORDERS.md DEPLOYMENT_RELEASE_21_11_RENDER.md DATABASE_SAFETY_RELEASE_21_11.md TEST_REPORT_RELEASE_21_11.txt
```

```powershell
git diff --cached --stat
```

```powershell
git commit -m "Release 21.11 show all live work orders"
```

```powershell
git push origin main
```

## Render settings

Build command:

```text
pip install -r requirements.txt && alembic upgrade head
```

Start command:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

No new migration line is expected for Release 21.11.

After Render reports Live, use `Ctrl + Shift + R` and confirm the sidebar version:

```text
v3.0.11-release21.11-all-live-work-orders
```
