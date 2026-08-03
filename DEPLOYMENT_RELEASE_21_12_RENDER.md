# Deploy Release 21.12 to Render

Extract `BIMFM_PORTAL_RELEASE_21_12_RENDER.zip` into a separate folder. Open PowerShell inside the extracted folder and run each command one line at a time.

## 1. Set paths

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

## 2. Copy release

```powershell
robocopy $Release $Repo /E /XD .git .venv venv __pycache__ data backups logs uploads /XF .env *.db *.sqlite *.sqlite3 *.pyc /R:2 /W:1
```

Robocopy exit codes 0 through 7 mean success.

## 3. Enter repository

```powershell
Set-Location $Repo
```

```powershell
$env:GIT_PAGER = "cat"
```

```powershell
git status
```

## 4. Stage Release 21.12

```powershell
git add app/config.py app/work_order_service.py app/routers/projects.py app/locales/en.json app/locales/zh_TW.json static/css/ui-refresh.css templates/freelancer_tasks.html README_RELEASE_21_12_REQUIRED_DAILY_TASK_REPORT.md DEPLOYMENT_RELEASE_21_12_RENDER.md DATABASE_SAFETY_RELEASE_21_12.md TEST_REPORT_RELEASE_21_12.txt
```

Do not use `git add .`.

## 5. Review and commit

```powershell
git diff --cached --stat
```

```powershell
git commit -m "Release 21.12 require Work Order daily task reports"
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

After Render reports **Live**, press `Ctrl + Shift + R` and confirm:

```text
v3.0.12-release21.12-required-daily-task-report
```
