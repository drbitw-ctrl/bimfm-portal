# BIM Portal Release 21.21.9 — Render Deployment

## 1. Extract the release

Extract `BIMFM_PORTAL_RELEASE_21_21_9_RENDER.zip` and open PowerShell inside the extracted folder.

## 2. Set the folders

```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
$Release = (Get-Location).Path

$Repo = (Resolve-Path $Repo).Path
$Release = (Resolve-Path $Release).Path

Write-Host "Repository: $Repo"
Write-Host "Release: $Release"
```

The two paths must be different.

## 3. Copy the release

```powershell
robocopy $Release $Repo /E /XD .git .venv venv __pycache__ data backups logs uploads /XF .env *.db *.sqlite *.sqlite3 *.pyc /R:2 /W:1
```

Robocopy exit codes 0 through 7 mean success.

## 4. Review

```powershell
Set-Location $Repo
$env:GIT_PAGER = "cat"

git status
git diff --stat
```

## 5. Stage this hotfix

```powershell
git add app/config.py app/routers/portal.py tests/test_release_21_21_9_save_task_hotfix.py README_RELEASE_21_21_9_SAVE_TASK_HOTFIX.md DATABASE_SAFETY_RELEASE_21_21_9.md DEPLOYMENT_RELEASE_21_21_9_RENDER.md TEST_REPORT_RELEASE_21_21_9.txt
```

Review:

```powershell
git status
git diff --cached --stat
```

## 6. Commit and push

```powershell
git commit -m "Release 21.21.9 save task hotfix"
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

Health Check Path:

```text
/health/ready
```

## 8. Verify

After Render reports Live, press `Ctrl + Shift + R`.

Confirm version:

```text
v3.0.21.9-release21.21.9-save-task-hotfix
```

Then create and save a new task.
