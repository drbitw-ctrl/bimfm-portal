# BIM Portal Release 21.22 — Render Deployment

Release 21.22 contains **no database migration**. The Render database schema is not changed by this release.

## 1. Extract the release

Extract the ZIP and open PowerShell inside the inner release folder.

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

## 3. Copy Release 21.22

```powershell
robocopy $Release $Repo /E /XD .git .venv venv __pycache__ data backups logs uploads /XF .env *.db *.sqlite *.sqlite3 *.pyc /R:2 /W:1
```

Robocopy exit codes `0` through `7` mean success.

## 4. Enter the Git repository and review

```powershell
Set-Location $Repo
$env:GIT_PAGER = "cat"

git status
git diff --stat
```

## 5. Stage Release 21.22

```powershell
git add app/config.py app/dtr_service.py app/task_hourly_mode.py app/routers/attendance.py app/locales/en.json app/locales/zh_TW.json static/css/ui-refresh.css templates/attendance.html templates/admin_dtr_task_hourly.html tests/test_release_21_21_6_task_assignment_deadline_fix.py tests/test_release_21_22_task_hourly_member.py README_RELEASE_21_22_TASK_HOURLY_MEMBER.md DEPLOYMENT_RELEASE_21_22_RENDER.md DATABASE_SAFETY_RELEASE_21_22.md TEST_REPORT_RELEASE_21_22.txt
```

Review before committing:

```powershell
git status
git diff --cached --stat
```

## 6. Commit and push

```powershell
git commit -m "Release 21.22 task-hourly member mode"
git push origin main
git log -1 --oneline
```

## 7. Render settings

Keep the existing Build Command:

```text
pip install -r requirements.txt && alembic upgrade head
```

There is no new Alembic revision in this release, so `alembic upgrade head` should report the existing database is already at head.

Keep the Start Command:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Keep the Health Check Path:

```text
/health/ready
```

If auto-deploy does not start:

`Render Dashboard → Manual Deploy → Deploy latest commit`

## 8. Verify after Render reports Live

Press:

```text
Ctrl + Shift + R
```

Confirm the lower-left version shows:

```text
v3.0.22-release21.22-task-hourly-member
```

Then verify:

1. Log in as a normal freelancer: Time In is green and Time Out is red.
2. Log in as Belinda (`LEGACY-00008`): Time In / Time Out controls are replaced by Task-Hourly Work Mode.
3. Start and stop one assigned Work Order for Belinda.
4. Confirm the stopped Work Order appears in her monthly task-hour register with project, task, description, start/stop times, and hours/minutes/seconds.
5. Administrator → Monthly DTR → generate Belinda's DTR.
6. Open Belinda's DTR and confirm the task-hour tabulation is shown instead of attendance punches.
7. Confirm `/health/ready` remains healthy.

## Rollback

Because Release 21.22 has no schema migration, if you do not like the result you can use Render's application rollback to the previous successful deployment. No Alembic downgrade is required for this release.
