# Release 20.14 Render Deployment

## Important

Deploy Release 20.14 to the existing GitHub repository and keep the current populated PostgreSQL `DATABASE_URL`.

Do not create a new database. Do not rerun the SQLite migration or Project Member repair utility.

## Render settings

Use these exact values in the Render Web Service:

```text
Build Command
pip install -r requirements.txt && alembic upgrade head
```

```text
Start Command
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

```text
Health Check Path
/health/ready
```

Release 20.14 does not add an Alembic revision. `alembic upgrade head` remains in the build command to verify that the existing database is current.

## Safer Windows update method

Extract the deployment ZIP into a separate folder. Open PowerShell inside the inner folder named:

```text
BIMFM_PORTAL_RELEASE_20_14_RENDER
```

Set the existing Git repository and extracted release paths:

```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
$Release = (Get-Location).Path
```

Validate both paths before copying:

```powershell
$Repo = (Resolve-Path $Repo).Path
$Release = (Resolve-Path $Release).Path

if ($Repo -eq $Release) {
    throw "Release and repository folders must be different."
}

if (-not (Test-Path "$Repo\.git")) {
    throw "The repository .git folder was not found."
}

if (-not (Test-Path "$Release\requirements.txt")) {
    throw "This is not the extracted Release 20.14 folder."
}
```

Mirror the release into the repository with Robocopy. This avoids copying the repository’s `.git` directory onto itself:

```powershell
robocopy $Release $Repo /MIR /XD .git __pycache__ /XF .env *.db *.pyc /R:2 /W:1

if ($LASTEXITCODE -ge 8) {
    throw "Robocopy failed with exit code $LASTEXITCODE."
}
```

Robocopy exit codes `0` through `7` are successful outcomes.

Review and push:

```powershell
Set-Location $Repo

git status
git add -A
git commit -m "Release 20.14 supervisor dashboard and member tools"
git push
```

Render should deploy the pushed commit automatically.

## Environment variables

Keep the current values for:

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

After Render reports **Live**, verify:

```text
/health
/health/ready
/api/v1/health
/admin
/admin/staff-accounts
/admin/freelancers
```

Then complete these acceptance checks:

1. Dashboard prominently shows Team Availability, Active Tasks, and Attendance Today.
2. Create a temporary Supervisor account from Staff Accounts.
3. Log in as that Supervisor and confirm operational pages can be viewed.
4. Confirm New Task and editing actions are unavailable.
5. Confirm a Supervisor POST/write attempt is denied.
6. Reset the password of a noncritical test member and verify forced password change.
7. Confirm a member with project or HR history shows **Protected record**.
8. Delete only an unused testing member after verifying it contains no required data.

## Rollback

Release 20.14 has no schema migration. A code rollback can be performed by redeploying the previous known-good Git commit.

Do not restore or replace PostgreSQL solely to roll back this visual and authorization release.
