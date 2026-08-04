# Deploy BIMFM Portal Release 21.13 to Render

Extract `BIMFM_PORTAL_RELEASE_21_13_RENDER.zip` and open PowerShell inside the extracted folder.

Run every command separately.

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

Stage only Release 21.13 files:

```powershell
git add app/config.py app/routers/administration.py app/locales/en.json app/locales/zh_TW.json static/css/ui-refresh.css templates/admin_dashboard.html templates/attendance.html README_RELEASE_21_13_DASHBOARD_MEMBER_VISIBILITY_ATTENDANCE_CARD.md DEPLOYMENT_RELEASE_21_13_RENDER.md DATABASE_SAFETY_RELEASE_21_13.md TEST_REPORT_RELEASE_21_13.txt
```

```powershell
git diff --cached --stat
```

```powershell
git commit -m "Release 21.13 dashboard member visibility and attendance card"
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

No new migration message is expected.

After Render reports Live, press `Ctrl + Shift + R` and confirm:

```text
v3.0.13-release21.13-dashboard-member-visibility-attendance-card
```
