# BIMFM Portal Release 20.12 — Render Deployment

## Important

Deploy this release to the existing GitHub repository and keep the current
populated Render PostgreSQL database.

Do not rerun:

- The original SQLite-to-PostgreSQL migration
- The Project Member repair utility
- Any project synchronization agent

## Render settings

Use these exact values.

### Build Command

```text
pip install -r requirements.txt && alembic upgrade head
```

### Start Command

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Health Check Path

```text
/health/ready
```

Do not include the labels `Build Command:` or `Start Command:` inside the
command fields.

## Existing environment variables

Keep the current values for:

```text
DATABASE_URL
BIMFM_SESSION_SECRET
BIMFM_ENV
BIMFM_LOG_LEVEL
BIMFM_COOKIE_HTTPS_ONLY
PYTHON_VERSION
```

No new environment variable is required.

## GitHub update

Extract the deployment ZIP and copy its contents into the existing local Git
repository while preserving the `.git` folder.

Example:

```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
$Release = "C:\FULL\PATH\TO\BIMFM_PORTAL_RELEASE_20_12_RENDER"

Get-ChildItem -LiteralPath $Repo -Force |
  Where-Object { $_.Name -ne ".git" } |
  Remove-Item -Recurse -Force

Get-ChildItem -LiteralPath $Release -Force |
  Copy-Item -Destination $Repo -Recurse -Force

Set-Location $Repo
git status
git add -A
git commit -m "Release 20.12 editable task register"
git push
```

## Expected migration

The build log should show an upgrade similar to:

```text
Running upgrade 20260801_0004 -> 20260801_0005
```

The migration adds the nullable `portal_tasks.quality_score` column only.

## Post-deployment checks

After Render reports **Live**:

1. Open `/health/ready` and confirm the database is available.
2. Log in as an Administrator.
3. Open `/portal/tasks`.
4. Confirm both active and completed tasks are visible.
5. Test Search and each dropdown filter.
6. Open one task with **Edit**.
7. Update a harmless field and save.
8. Confirm the Task Register reflects the change.
9. Confirm Active Tasks and Recently Completed Tasks still work.
10. Confirm Project Team remains unchanged.

## Rollback

Release 20.12 is compatible with the existing PostgreSQL project data. When an
application rollback is required, redeploy the previous Git commit. The added
nullable quality-score column may safely remain in PostgreSQL.
