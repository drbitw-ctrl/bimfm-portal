# BIMFM Portal Release 21.01 — Render Deployment

## Source base

Release 21.01 is based on Version 21.00 and should be deployed over the same
GitHub repository and Render Web Service.

## Copy into the repository

Open PowerShell inside the extracted `BIMFM_PORTAL_RELEASE_21_01_RENDER` folder.

```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
$Release = (Get-Location).Path
$Repo = (Resolve-Path $Repo).Path
$Release = (Resolve-Path $Release).Path
robocopy $Release $Repo /E /XD .git .venv venv __pycache__ data backups logs uploads /XF .env *.db *.sqlite *.sqlite3 *.pyc /R:2 /W:1
Set-Location $Repo
$env:GIT_PAGER = "cat"
git status
git diff --stat
```

## Stage the hotfix

```powershell
git add app/config.py app/work_order_service.py app/routers/projects.py app/locales/en.json app/locales/zh_TW.json static/css/ui-refresh.css templates/freelancer_projects.html templates/freelancer_tasks.html README_RELEASE_21_01_WORK_ORDER_HOTFIX.md DEPLOYMENT_RELEASE_21_01_RENDER.md DATABASE_SAFETY_RELEASE_21_01.md TEST_REPORT_RELEASE_21_01.txt
```

## Commit and push

```powershell
git status
git diff --cached --stat
git commit -m "Release 21.01 work order hotfix"
git push origin main
```

## Render commands

Keep the existing commands unchanged.

```text
Build: pip install -r requirements.txt && alembic upgrade head
Start: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

No new Alembic migration line is expected for Release 21.01. Render may report
that the database is already at revision `20260802_0008`.

## Acceptance check

1. Log in as a freelancer with an assigned active task.
2. Open Assigned Projects.
3. Select **Open Work Order**.
4. Confirm the Work Orders page loads and highlights the selected task.
5. Start the timer.
6. Refresh the page and confirm the timer remains active.
7. Stop the timer and record a note.
8. Confirm the session appears in today's recorded work.
9. Confirm Task Time Utilization includes the recorded minutes.
