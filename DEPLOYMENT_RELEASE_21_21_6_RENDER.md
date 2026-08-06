# BIM Portal Release 21.21.6 — Render Deployment

## 1. Extract and open PowerShell

Extract `BIMFM_PORTAL_RELEASE_21_21_6_RENDER.zip` and open PowerShell inside the extracted inner folder.

## 2. Set folders

```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
$Release = (Get-Location).Path

$Repo = (Resolve-Path $Repo).Path
$Release = (Resolve-Path $Release).Path

Write-Host "Repository: $Repo"
Write-Host "Release: $Release"
```

The paths must be different.

## 3. Copy Release 21.21.6

```powershell
robocopy $Release $Repo /E /XD .git .venv venv __pycache__ data backups logs uploads /XF .env *.db *.sqlite *.sqlite3 *.pyc /R:2 /W:1
```

Robocopy exit codes 0 through 7 indicate success.

## 4. Enter and review the repository

```powershell
Set-Location $Repo
$env:GIT_PAGER = "cat"

git status
git diff --stat
```

## 5. Stage this stabilization release

Copy this command as one line:

```powershell
git add app/config.py app/routers/administration.py app/routers/portal.py tests/test_release_21_21_6_task_assignment_deadline_fix.py README_RELEASE_21_21_6_TASK_ASSIGNMENT_DEADLINE_FIX.md DEPLOYMENT_RELEASE_21_21_6_RENDER.md DATABASE_SAFETY_RELEASE_21_21_6.md TEST_REPORT_RELEASE_21_21_6.txt
```

Review:

```powershell
git status
git diff --cached --stat
```

## 6. Commit and push

```powershell
git commit -m "Release 21.21.6 task assignment and deadline edit fixes"
git push origin main
git log -1 --oneline
```

## 7. Render configuration

Keep the Build Command:

```text
pip install -r requirements.txt && alembic upgrade head
```

Keep the Start Command:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Keep the Health Check Path:

```text
/health/ready
```

There is no new migration in this release. Render should confirm the existing database is already at Alembic head.

If automatic deployment does not begin:

`Render Dashboard → Manual Deploy → Deploy latest commit`

## 8. Verify after Live

Press `Ctrl + Shift + R` and confirm the version shows:

```text
v3.0.21.6
```

Then test:

1. Administration → Staff Access.
2. Select Enable Task Assignment for Me.
3. Confirm the page redirects back with a success message.
4. Confirm the Administrator appears in New Task and Edit Task member lists.
5. Edit an existing task and change only its deadline.
6. Save and confirm there is no Internal Server Error.
7. Confirm the task retains its assignments and other values.
