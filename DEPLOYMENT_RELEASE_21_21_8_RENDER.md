# BIM Portal Release 21.21.8 — Render Deployment

This is a code-only hotfix. It contains no Alembic migration or schema change.

## 1. Extract and open PowerShell in

`BIMFM_PORTAL_RELEASE_21_21_8_RENDER`

## 2. Set folders

```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
$Release = (Get-Location).Path
$Repo = (Resolve-Path $Repo).Path
$Release = (Resolve-Path $Release).Path
Write-Host "Repository: $Repo"
Write-Host "Release: $Release"
```

## 3. Copy release

```powershell
robocopy $Release $Repo /E /XD .git .venv venv __pycache__ data backups logs uploads /XF .env *.db *.sqlite *.sqlite3 *.pyc /R:2 /W:1
```

Robocopy exit codes 0–7 mean success.

## 4. Review

```powershell
Set-Location $Repo
$env:GIT_PAGER = "cat"
git status
git diff --stat
```

## 5. Stage only this hotfix

```powershell
git add app/config.py app/routers/portal.py app/routers/administration.py tests/test_release_21_21_6_task_assignment_deadline_fix.py tests/test_release_21_21_8_task_creation_and_admin_assignment.py README_RELEASE_21_21_8_TASK_CREATION_ADMIN_ASSIGNMENT_HOTFIX.md DATABASE_SAFETY_RELEASE_21_21_8.md DEPLOYMENT_RELEASE_21_21_8_RENDER.md TEST_REPORT_RELEASE_21_21_8.txt
```

## 6. Commit and push

```powershell
git status
git diff --cached --stat
git commit -m "Release 21.21.8 task creation and admin assignment hotfix"
git push origin main
git log -1 --oneline
```

## 7. Render settings

Build Command:

```text
pip install -r requirements.txt && alembic upgrade head
```

Start Command:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Health Check:

```text
/health/ready
```

After Render reports Live, press `Ctrl + Shift + R`.

Verify:

1. Create a new task.
2. Enable task assignment for the Administrator.
3. Confirm the Administrator appears in New Task and Edit Task assignment lists.
4. Confirm version `v3.0.21.8-release21.21.8-task-creation-admin-assignment-hotfix`.
