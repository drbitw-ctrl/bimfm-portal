# Release 21.14 — Render Deployment

Run every PowerShell command separately.

## 1. Open the extracted release folder

`BIMFM_PORTAL_RELEASE_21_14_RENDER`

## 2. Set the repository and release paths

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

## 3. Copy Release 21.14

```powershell
robocopy $Release $Repo /E /XD .git .venv venv __pycache__ data backups logs uploads /XF .env *.db *.sqlite *.sqlite3 *.pyc /R:2 /W:1
```

Robocopy exit codes 0 through 7 mean success.

## 4. Enter the Git repository

```powershell
Set-Location $Repo
```

```powershell
$env:GIT_PAGER = "cat"
```

Remove the retired image-brand assets:

```powershell
Remove-Item static\images\bimfm-company-logo.png,static\images\bimfm-company-logo-web.png,static\images\bimfm-mark.png,static\images\favicon.ico -Force -ErrorAction SilentlyContinue
```

Review the changes:

```powershell
git status
```

## 5. Stage only Release 21.14

```powershell
git add -u static/images
```

```powershell
git add app/config.py app/performance_reporting.py app/work_order_service.py app/excel_exports.py app/dtr_exporter.py app/routers/auth.py app/routers/projects.py app/routers/portal.py app/locales/en.json app/locales/zh_TW.json static/css/ui-refresh.css templates/base.html templates/admin_login.html templates/freelancer_login.html templates/setup.html templates/change_password.html templates/freelancer_reminders.html templates/performance_leaderboards.html README_RELEASE_21_14_OVERALL_PERFORMANCE_REMINDERS_BRAND_CLEANUP.md DEPLOYMENT_RELEASE_21_14_RENDER.md DATABASE_SAFETY_RELEASE_21_14.md TEST_REPORT_RELEASE_21_14.txt
```

Do not use `git add .`.

## 6. Review the staged files

```powershell
git diff --cached --stat
```

```powershell
git status
```

## 7. Commit and push

```powershell
git commit -m "Release 21.14 overall performance reminders and brand cleanup"
```

```powershell
git push origin main
```

## 8. Render settings

Build command:

`pip install -r requirements.txt && alembic upgrade head`

Start command:

`uvicorn app.main:app --host 0.0.0.0 --port $PORT`

No new Alembic migration line is expected.

If automatic deployment does not begin, use:

`Render Dashboard → Manual Deploy → Deploy latest commit`

After Render reports Live, press `Ctrl + Shift + R`.

Expected version:

`v3.0.14-release21.14-overall-performance-reminder-brand-cleanup`
