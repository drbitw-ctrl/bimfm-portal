# Deploying BIMFM Portal Release 20.11 to Render

## 1. Use the existing Git repository

Extract the Render deployment ZIP. Its inner folder is:

```text
BIMFM_PORTAL_RELEASE_20_11_RENDER
```

Preserve the `.git` folder in the repository already connected to Render.
Replace only the application files.

Example PowerShell variables:

```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
$Release = "C:\FULL\PATH\TO\BIMFM_PORTAL_RELEASE_20_11_RENDER"
```

Verify both paths:

```powershell
Test-Path "$Repo\.git"
Test-Path $Release
```

Both commands must return `True`.

## 2. Replace the application while preserving Git

```powershell
Get-ChildItem -LiteralPath $Repo -Force |
  Where-Object { $_.Name -ne ".git" } |
  Remove-Item -Recurse -Force

Get-ChildItem -LiteralPath $Release -Force |
  Copy-Item -Destination $Repo -Recurse -Force
```

## 3. Commit and push

```powershell
Set-Location $Repo

git status
git add -A
git commit -m "Release 20.11 project presentation and freelancer access"
git push
```

## 4. Keep the current Render environment

Retain the populated PostgreSQL connection and existing production settings:

```text
DATABASE_URL
BIMFM_SESSION_SECRET
BIMFM_ENV=production
BIMFM_LOG_LEVEL=INFO
BIMFM_COOKIE_HTTPS_ONLY=true
PYTHON_VERSION=3.12.8
```

No new environment variable is required.

## 5. Render commands

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

## 6. Deployment log

The first Release 20.11 deployment should include an Alembic line similar to:

```text
Running upgrade 20260801_0003 -> 20260801_0004
```

Then Render should start Uvicorn and mark the service `Live`.

## 7. Acceptance checks

After deployment, verify:

1. `/health/ready` reports PostgreSQL available.
2. New Task shows project names only.
3. No Project Code input is visible.
4. Project Engineer is a manual text field.
5. Existing-project options show names such as `220.桃園長庚醫院`.
6. Project Register and task views show project names only.
7. Project-facing member selectors show member names only.
8. `/attendance` opens for a freelancer account.
9. `/projects` opens for a freelancer account.
10. A mapped freelancer sees the repaired PostgreSQL assignments.
11. A project membership remains visible even with no active task.
12. Project Team mapping remains unchanged and functional.
13. Existing attendance, DTR, leave, Finance, and account data remain present.
