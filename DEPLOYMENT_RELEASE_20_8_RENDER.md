# BIMFM Portal Release 20.8 — Render Deployment

This guide updates the existing Release 20.7 GitHub repository and keeps the
same populated Render PostgreSQL database.

## 1. Back up PostgreSQL

Create or confirm a current backup of the populated Render database before
pushing the release.

Do not create a new database and do not rerun the SQLite migration.

## 2. Extract the deployment ZIP

Extract:

```text
BIMFM_PORTAL_RELEASE_20_8_RENDER_DEPLOY.zip
```

Example destination:

```text
C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_8_RENDER
```

## 3. Replace the application files while preserving `.git`

Your existing Git repository is probably:

```text
C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER
```

In PowerShell:

```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
$Release = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_8_RENDER"

Test-Path "$Repo\.git"
```

The result must be `True`.

Remove the old tracked application files but preserve `.git`:

```powershell
Get-ChildItem -LiteralPath $Repo -Force |
  Where-Object { $_.Name -ne ".git" } |
  Remove-Item -Recurse -Force
```

Copy Release 20.8:

```powershell
Get-ChildItem -LiteralPath $Release -Force |
  Copy-Item -Destination $Repo -Recurse -Force

Set-Location $Repo
```

## 4. Review and push

```powershell
git status
git diff --stat
git add -A
git commit -m "Release 20.8 restore PostgreSQL member mapping"
git push
```

## 5. Confirm Render commands

The Render fields must contain only these commands—do not include labels such as
`Build Command:` or `Start Command:`.

Build Command:

```text
pip install -r requirements.txt && alembic upgrade head
```

Start Command:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Health Check Path:

```text
/health/ready
```

## 6. Keep existing environment variables

Keep the current populated database connection and session secret:

```text
DATABASE_URL
BIMFM_SESSION_SECRET
BIMFM_ENV=production
BIMFM_LOG_LEVEL=INFO
BIMFM_COOKIE_HTTPS_ONLY=true
PYTHON_VERSION=3.12.8
```

`BIMFM_PROJECT_SYNC_TOKEN` is not required by Release 20.8.

## 7. Watch the deployment log

The build should show:

```text
Running upgrade 20260801_0002 -> 20260801_0003
```

The migration creates and backfills `project_member_directory`.

A successful start should show:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## 8. Verify health and migration

Open:

```text
https://YOUR-SERVICE.onrender.com/health
https://YOUR-SERVICE.onrender.com/health/ready
https://YOUR-SERVICE.onrender.com/setup-status
```

In `/setup-status`, verify:

```text
project_mode: postgresql_native_member_mapping

table_counts:
  project_member_directory: greater than 0 when legacy members exist
  mapped_project_members: expected preserved mappings, possibly 0
  unmapped_project_members: expected original members awaiting mapping
```

Also confirm that the existing counts for projects, tasks, attendance, DTR,
leave, overtime, and Finance records have not unexpectedly changed.

## 9. Map the members

Log in as an Administrator and open:

```text
/admin/project-team
```

The page should show the original member names under **Project Member
Directory**. For each member:

1. Select the correct HR freelancer.
2. Click **Save Mapping**.
3. Confirm the row changes to **Mapped**.
4. Check the active project and task totals.

Only Administrator accounts can change mappings. Finance accounts remain
read-only.

## 10. Verify a freelancer account

Log in as one mapped freelancer and open:

```text
/projects
```

The assignments previously attached to the original project-member identity
should now appear for that HR account.

## Troubleshooting

### Directory count is zero

Do not rerun the SQLite migration. Confirm the build log shows revision
`20260801_0003`, then check whether the populated database contains any of:

```text
members
LEGACY-* rows in freelancers
project_source_members
synced_project_tasks
```

### Members appear but project counts are zero

The directory was restored, but that member may not have a matching imported
`LEGACY-*` placeholder. Keep the member unmapped and record the exact member
name and `/setup-status` counts for diagnosis.

### Rollback

Redeploy the previous Git commit. The additive `project_member_directory` table
may remain; Release 20.7 ignores it. Do not downgrade or delete the table during
an emergency application rollback.
