# Render Deployment Guide — BIMFM Portal Release 20.10

## Deployment package

Use:

```text
BIMFM_PORTAL_RELEASE_20_10_RENDER_DEPLOY.zip
```

The package contains no PostgreSQL credentials, `.env` file, SQLite database, private Sync Agent configuration, or compiled Python cache.

## Existing Git repository

Extract the ZIP. The archive contains the folder:

```text
BIMFM_PORTAL_RELEASE_20_10_RENDER
```

Use your existing local Git repository so its `.git` history and GitHub connection are preserved.

Example PowerShell commands:

```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
$Release = "C:\FULL\PATH\TO\BIMFM_PORTAL_RELEASE_20_10_RENDER"

Test-Path "$Repo\.git"
Test-Path $Release
```

Both checks must return `True`.

Replace the application files while preserving `.git`:

```powershell
Get-ChildItem -LiteralPath $Repo -Force |
  Where-Object { $_.Name -ne ".git" } |
  Remove-Item -Recurse -Force

Get-ChildItem -LiteralPath $Release -Force |
  Copy-Item -Destination $Repo -Recurse -Force
```

Commit and push:

```powershell
Set-Location $Repo
git status
git add -A
git commit -m "Release 20.10 connected task workspace"
git push
```

## Render configuration

Keep the existing populated `DATABASE_URL` and current production environment variables.

The Build Command field must contain only:

```text
pip install -r requirements.txt && alembic upgrade head
```

The Start Command field must contain only:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Health Check Path:

```text
/health/ready
```

Do not include labels such as `Build Command:` or `Start Command:` inside the Render command fields.

## Post-deployment checks

After Render reports **Live**, verify:

```text
/health
/health/ready
/api/v1/health
/admin
/portal/tasks/new
/admin/project-team
```

Using an Administrator account:

1. Confirm **New Task** appears in the sidebar.
2. Open the form and create one test task.
3. Confirm the task appears under `/portal/tasks`.
4. Confirm the selected member and project relationship are correct.

Using a freelancer account, open every sidebar destination:

```text
/attendance
/attendance/history
/tasks
/projects
/overtime
/leave
/change-password
```

Confirm the complete sidebar remains visible and each page loads normally.

## Rollback

Release 20.10 has no schema migration. To roll back the application, redeploy the previous known-good Git commit. Do not delete or replace the PostgreSQL database.
