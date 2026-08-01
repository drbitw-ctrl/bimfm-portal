# BIMFM Portal Release 20.19 — Render Deployment

## Package

Use `BIMFM_PORTAL_RELEASE_20_19_RENDER.zip` with the existing GitHub repository
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
git add app/config.py app/main.py app/portal_project_service.py app/routers/administration.py static/css/ui-refresh.css templates/admin_dashboard.html templates/portal_module.html README_RELEASE_20_19_TEAM_COMMAND_DASHBOARD.md DEPLOYMENT_RELEASE_20_19_RENDER.md DATABASE_SAFETY_RELEASE_20_19.md TEST_REPORT_RELEASE_20_19.txt
git status
git commit -m "Release 20.19 team command dashboard"
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
3. Confirm the Progress bar is compact and does not overlap Quality.
4. Confirm the Progress and Quality dropdowns do not have duplicate bold
   percentage text.
5. Change Progress and Quality values and refresh to confirm persistence.
6. Open `/admin`.
7. Confirm the Dashboard opens as **Team Command Center**.
8. Confirm available members and busy members are separated.
9. Confirm current task titles, projects, progress, and due dates appear for busy
   members.
10. Confirm overdue tasks are highlighted.
11. Confirm attendance, approvals, activity, and quick-launch tools remain below
    the workload view.
