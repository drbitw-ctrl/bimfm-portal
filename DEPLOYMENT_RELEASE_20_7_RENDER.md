# BIMFM Portal Release 20.7 — Existing Render Database Deployment

This guide updates the existing GitHub-connected Render Web Service while
continuing to use the populated PostgreSQL database.

## Critical rules

1. Keep the existing populated `DATABASE_URL`.
2. Do not create or attach a new empty database.
3. Do not rerun the SQLite-to-PostgreSQL import.
4. Back up the PostgreSQL database before deployment.
5. Preserve the current `BIMFM_SESSION_SECRET` when available. A new value is
   allowed, but it signs all users out.

## Package to use

Use:

```text
BIMFM_PORTAL_RELEASE_20_7_RENDER_DEPLOY.zip
```

The Render package intentionally excludes:

- SQLite databases
- PostgreSQL credentials
- `.env`
- Production secrets
- Project Sync Agent files
- Compiled Python files
- Test databases and logs

## Replace the local Git repository contents

The current local repository is expected to be similar to:

```text
C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER
```

Extract the Release 20.7 ZIP to a separate folder first.

In PowerShell, set the two paths to the actual folders on the computer:

```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
$Release = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_7_RENDER"
```

Confirm that the repository contains `.git`:

```powershell
Test-Path "$Repo\.git"
```

It must return `True`.

Remove the old tracked application files while preserving Git history:

```powershell
Get-ChildItem -LiteralPath $Repo -Force |
  Where-Object { $_.Name -ne ".git" } |
  Remove-Item -Recurse -Force
```

Copy all Release 20.7 files, including hidden files such as `.gitignore`:

```powershell
Get-ChildItem -LiteralPath $Release -Force |
  Copy-Item -Destination $Repo -Recurse -Force
```

Return to the repository:

```powershell
Set-Location $Repo
```

Review the update:

```powershell
git status
git diff --stat
```

The removed legacy template should appear as deleted when it existed in the old
repository:

```text
templates/admin_project_integration.html
```

Commit every addition, modification, and deletion:

```powershell
git add -A
git commit -m "Release 20.7 PostgreSQL-native projects"
git push
```

## Render configuration

The existing Web Service should continue using:

```text
Build Command:
pip install -r requirements.txt && alembic upgrade head

Start Command:
uvicorn app.main:app --host 0.0.0.0 --port $PORT

Health Check Path:
/health/ready
```

Keep these environment variables:

```text
DATABASE_URL=<the populated existing PostgreSQL database URL>
BIMFM_SESSION_SECRET=<the current secure session secret>
BIMFM_ENV=production
BIMFM_LOG_LEVEL=INFO
BIMFM_COOKIE_HTTPS_ONLY=true
PYTHON_VERSION=3.12.8
```

`BIMFM_PROJECT_SYNC_TOKEN` is no longer used. It may be removed after Release
20.7 is confirmed healthy.

Do not add bootstrap administrator variables when the existing database already
contains the administrator account.

## What the deployment changes in PostgreSQL

The build runs:

```text
alembic upgrade head
```

The Release 20.7 migration adds only:

```text
daily_tasks.portal_task_id
```

It is a nullable foreign key to `portal_tasks.id` with an index. The migration
does not delete, truncate, replace, or re-import any table.

## Post-deployment verification

After Render reports that the service is live, check:

```text
/health
/health/ready
/api/v1/health
/docs
```

Log in with the recovered administrator account and verify:

1. `/admin` loads and shows PostgreSQL project-data indicators.
2. `/admin/project-team` shows every active member.
3. Members with no current assignment are labeled `No project assignment`.
4. Migrated projects appear in the project register.
5. Migrated task assignments show their correct assignees.
6. `/portal/team-workload` includes assigned and unassigned active members.
7. A freelancer's `/projects` page shows PostgreSQL-native assignments.
8. Attendance, DTR, Finance, leave, overtime, and compensatory balances remain.
9. `/api/integration/project-tasks/status` reports:

```json
{
  "mode": "postgresql_native",
  "synchronization_required": false
}
```

## Stop conditions

Stop the rollout and do not enter new production records when:

- Existing freelancers disappear
- Existing attendance or DTR data is missing
- `/health/ready` reports a database error
- The service is connected to an empty database
- Alembic reports a migration failure

In those cases, redeploy the previous known-good Git commit and keep the existing
PostgreSQL database unchanged while reviewing the Render logs.

## Rollback

Release 20.7 uses an additive nullable field, so application rollback can usually
be performed by redeploying the previous Git commit without immediately
reversing the database migration.

Do not delete the populated PostgreSQL database during rollback.
