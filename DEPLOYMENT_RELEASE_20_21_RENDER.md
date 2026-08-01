# BIMFM Portal Release 20.21 — Render Deployment

## Before deployment

1. Confirm a current PostgreSQL backup.
2. Keep the existing Render Web Service and PostgreSQL database.
3. Preserve production environment variables and secrets.
4. Extract the Release 20.21 ZIP into a separate folder.

## Copy into the existing Git repository

Open PowerShell inside the extracted folder:

```text
BIMFM_PORTAL_RELEASE_20_21_RENDER
```

Set the paths:

```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
$Release = (Get-Location).Path
$Repo = (Resolve-Path $Repo).Path
$Release = (Resolve-Path $Release).Path
```

Copy the release:

```powershell
robocopy $Release $Repo /E /XD .git .venv venv __pycache__ data backups logs uploads /XF .env *.db *.sqlite *.sqlite3 *.pyc /R:2 /W:1
```

Robocopy exit codes 0 through 7 are successful.

Enter the repository:

```powershell
Set-Location $Repo
$env:GIT_PAGER = "cat"
```

Review:

```powershell
git status
git diff --stat
```

Stage Release 20.21 files:

```powershell
git add app/config.py app/hr_workflow.py app/main.py app/web_helpers.py app/models/policy.py app/portal_project_service.py app/routers/administration.py app/routers/projects.py app/locales/en.json app/locales/zh_TW.json alembic/versions/20260802_0007_freelancer_project_engineer_visibility.py static/css/ui-refresh.css templates/base.html templates/admin_hr_policy.html templates/freelancer_projects.html templates/freelancer_completed_tasks.html README_RELEASE_20_21_LOCALIZATION_PROJECT_PRIVACY.md DEPLOYMENT_RELEASE_20_21_RENDER.md DATABASE_SAFETY_RELEASE_20_21.md TEST_REPORT_RELEASE_20_21.txt
```

Commit and push:

```powershell
git commit -m "Release 20.21 localization and freelancer project privacy"
git push origin main
```

## Render commands

Keep unchanged:

```text
Build: pip install -r requirements.txt && alembic upgrade head
Start: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

During deployment, expect:

```text
Running upgrade 20260801_0006 -> 20260802_0007
```

## Acceptance checks

After Render reports Live:

1. Switch the portal to Traditional Chinese and inspect staff and freelancer pages.
2. Confirm names, project names, and task descriptions remain unchanged.
3. Log in as a freelancer and open Assigned Projects.
4. Confirm projects with active tasks appear first.
5. Change the project sort and direction; active projects must remain first.
6. Confirm Project Engineer names are hidden.
7. Open Recently Completed Tasks and confirm only the signed-in member's tasks appear.
8. Log in as Administrator and open HR Policy.
9. Enable Project Engineer visibility, save, and verify the name appears to freelancers.
10. Disable the toggle again if the current policy is to keep names private.
