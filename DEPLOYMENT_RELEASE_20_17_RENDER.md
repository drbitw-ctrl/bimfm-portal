# BIMFM Portal Release 20.17 — Render Deployment

## Package

Use `BIMFM_PORTAL_RELEASE_20_17_RENDER.zip` with the existing GitHub repository
and existing Render Web Service.

## Before copying

1. Confirm the production PostgreSQL backup is current.
2. Keep the existing Render environment variables unchanged.
3. Do not create or replace the production database.
4. Extract the ZIP into a folder separate from the Git repository.

## Copy into the repository

Open PowerShell inside the extracted inner folder and set:

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
git add app/config.py app/main.py app/portal_project_service.py app/routers/administration.py static/css/ui-refresh.css templates/portal_module.html README_RELEASE_20_17_TASK_TABLE_MEMBER_ASSIGNMENT.md DEPLOYMENT_RELEASE_20_17_RENDER.md DATABASE_SAFETY_RELEASE_20_17.md TEST_REPORT_RELEASE_20_17.txt
git status
git commit -m "Release 20.17 task table and member assignment fixes"
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
2. Open `/portal/tasks` and hard-refresh the page.
3. Verify the Project column remains visible while scrolling horizontally.
4. Verify the rightmost Action or Completed column is accessible.
5. Confirm Progress and Quality percentage bars are still shown.
6. Create a freelancer test account.
7. Open New Task and confirm that account appears in Assigned Member.
8. Assign a task and confirm the assignment saves.
9. Verify the four Release 20.16 quick-edit fields still save.
