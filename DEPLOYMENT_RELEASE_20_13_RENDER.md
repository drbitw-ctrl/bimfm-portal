# BIMFM Portal Release 20.13 — Render Deployment

## Important

Use the existing GitHub repository and the existing populated PostgreSQL
`DATABASE_URL`.

Do not create another database. Do not rerun the SQLite migration or the member
repair utility.

## Safer Windows update method

The previous `Remove-Item` and `Copy-Item` workflow could fail when the Release
folder and Git repository folder were accidentally the same. Release 20.13 uses
`robocopy` with explicit checks and excludes `.git`.

Extract the deployment ZIP into a separate folder. Open PowerShell inside the
inner folder:

```text
BIMFM_PORTAL_RELEASE_20_13_RENDER
```

Set the existing Git repository path:

```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
$Release = (Get-Location).Path
```

Validate the paths:

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
    throw "This is not the extracted Release 20.13 application folder."
}
```

Mirror the new release into the repository while preserving `.git`:

```powershell
robocopy $Release $Repo /MIR /XD .git __pycache__ /XF .env *.db *.pyc /R:2 /W:1

if ($LASTEXITCODE -ge 8) {
    throw "Robocopy failed with exit code $LASTEXITCODE."
}
```

Robocopy exit codes `0` through `7` are successful outcomes.

Commit and push:

```powershell
Set-Location $Repo
git status
git add -A
git commit -m "Release 20.13 historical quality score recovery"
git push
```

## Render configuration

Build Command — enter only the command:

```text
pip install -r requirements.txt && alembic upgrade head
```

Start Command — enter only the command:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Health Check Path:

```text
/health/ready
```

Keep the existing environment variables, especially:

```text
DATABASE_URL
BIMFM_SESSION_SECRET
BIMFM_ENV=production
BIMFM_COOKIE_HTTPS_ONLY=true
```

## Expected deployment log

Look for an Alembic line similar to:

```text
Running upgrade 20260801_0005 -> 20260801_0006
```

After Render reports `Live`, open the Task Register and confirm that historical
Quality Scores are visible.

## Verification

Open:

```text
/health/ready
/setup-status
/portal/tasks
```

Expected Alembic head:

```text
20260801_0006
```

Do not manually re-enter scores until the deployment has completed and the Task
Register has been refreshed.
