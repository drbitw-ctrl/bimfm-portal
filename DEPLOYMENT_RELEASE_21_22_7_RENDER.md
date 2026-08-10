# Release 21.22.7 — Render Deployment

This is cumulative from 21.22.6. You may deploy it directly over the stable 21.22.4 production rollback; 21.22.5/21.22.6 do not need to be deployed first.

## Database safety
No Alembic migration, schema change, or backfill is included in this release.

## PowerShell
Extract the ZIP and open PowerShell inside `BIM_PORTAL_RELEASE_21_22_7_RENDER`, then run:

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
git add .
git status
git diff --cached --stat
git commit -m "Release 21.22.7 review work dashboard optimization"
git push origin main
git log -1 --oneline
```

## Render settings
Build: `pip install -r requirements.txt && alembic upgrade head`

Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

Health check: `/health/ready`

## Post-deploy checks
1. `/admin` loads without HTTP 500.
2. Dashboard availability lists are horizontal and compact.
3. Sidebar clearly separates Daily Task Reports from Daily Time Record (DTR).
4. `/portal/my-work` shows My Review Queue for Admin/Supervisor.
5. Assign a review to yourself; it appears in My Review Queue and `/admin/review-queue`.
6. Start/stop review timer; freelancer task assignee/status/progress is unchanged.
7. `/admin/dtr` does not list `TS-*` staff task profiles and Generate All does not create DTRs for them.
