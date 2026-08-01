# BIMFM Portal Release 20.18 — Render Deployment

## Package

Use `BIMFM_PORTAL_RELEASE_20_18_RENDER.zip` with the existing GitHub repository
and existing Render Web Service.

## Before copying

1. Confirm the production PostgreSQL backup is current.
2. Keep the existing Render environment variables unchanged.
3. Do not create or replace the production database.
4. Extract the ZIP into a folder separate from the Git repository.

## Copy into the repository

Open PowerShell inside the extracted inner folder and run one line at a time:

```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
$Release = (Get-Location).Path
$Repo = (Resolve-Path $Repo).Path
$Release = (Resolve-Path $Release).Path
```

Confirm the paths are different, then copy:

```powershell
robocopy $Release $Repo /E /XD .git .venv venv __pycache__ data backups logs uploads /XF .env *.db *.sqlite *.sqlite3 *.pyc /R:2 /W:1
```

Robocopy exit codes 0 through 7 are successful.

## Commit and push

```powershell
Set-Location $Repo
$env:GIT_PAGER = "cat"
git status
git add app/config.py app/web_helpers.py app/locales/en.json app/locales/zh_TW.json static/css/ui-refresh.css templates/portal_module.html templates/freelancer_projects.html templates/freelancer_tasks.html templates/freelancer_task_edit.html templates/admin_tasks_monthly.html README_RELEASE_20_18_DISCIPLINE_LABEL_QUALITY_CLEANUP.md DEPLOYMENT_RELEASE_20_18_RENDER.md DATABASE_SAFETY_RELEASE_20_18.md TEST_REPORT_RELEASE_20_18.txt
git status
git commit -m "Release 20.18 discipline labels and quality cleanup"
git push origin main
```

## Render commands

Keep the current commands unchanged.

Build:

```text
pip install -r requirements.txt && alembic upgrade head
```

Start:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Post-deployment verification

1. Wait for Render to report **Live**.
2. Open `/portal/tasks` and press `Ctrl + Shift + R`.
3. Confirm Progress still displays its percentage bar.
4. Confirm Quality has no bar but retains its inline dropdown and percentage.
5. Change a Quality value and refresh to confirm persistence.
6. Confirm Architecture displays as AR and Structure displays as ST.
7. Open New Task and Edit Task and confirm the selector labels are AR and ST.
8. Confirm newly created freelancer accounts remain assignable.
