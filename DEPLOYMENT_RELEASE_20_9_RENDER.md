# BIMFM Portal Release 20.9 — Render Deployment

Release 20.9 is a presentation-only update based on the working Release 20.8
database architecture.

## Before deployment

1. Confirm the current portal is connected to the populated PostgreSQL database.
2. Confirm the repaired project members appear under `/admin/project-team`.
3. Keep the current Render environment variables.
4. Do not create a new database.
5. Do not rerun the SQLite migration or project-member repair utility.

## Update the existing Git repository

Assume:

```text
Repository folder:
C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER

Extracted Release 20.9 folder:
C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_9_RENDER
```

In PowerShell:

```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
$Release = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_9_RENDER"
```

Confirm the Git repository:

```powershell
Test-Path "$Repo\.git"
```

The result must be `True`.

Remove the old application files while preserving `.git`:

```powershell
Get-ChildItem -LiteralPath $Repo -Force |
  Where-Object { $_.Name -ne ".git" } |
  Remove-Item -Recurse -Force
```

Copy Release 20.9:

```powershell
Get-ChildItem -LiteralPath $Release -Force |
  Copy-Item -Destination $Repo -Recurse -Force
```

Return to the repository:

```powershell
Set-Location $Repo
```

Review and push:

```powershell
git status
git add -A
git commit -m "Release 20.9 visual refresh"
git push
```

## Render settings

The **Build Command** field must contain only:

```text
pip install -r requirements.txt && alembic upgrade head
```

The **Start Command** field must contain only:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Health Check Path:

```text
/health/ready
```

Keep these environment variables:

```text
DATABASE_URL
BIMFM_SESSION_SECRET
BIMFM_ENV=production
BIMFM_LOG_LEVEL=INFO
BIMFM_COOKIE_HTTPS_ONLY=true
PYTHON_VERSION=3.12.8
```

No new environment variable is required.

## Post-deployment checks

After Render reports **Live**, check:

```text
/health
/health/ready
/api/v1/health
/admin/login
/admin
/admin/project-team
/admin/finance
/admin/attendance/today
```

Confirm:

1. Existing project members are still visible.
2. Mapped and unmapped states are unchanged.
3. The project-member search works.
4. **Show unmapped only** works.
5. The light/dark theme toggle works.
6. Sidebar navigation works on desktop and mobile widths.
7. Existing attendance, leave, DTR, overtime, and Finance data remain present.

## Rollback

Release 20.9 has no database migration. To roll back, redeploy the previous
known-good Git commit. The PostgreSQL database does not need to be restored for
a visual-only rollback.
