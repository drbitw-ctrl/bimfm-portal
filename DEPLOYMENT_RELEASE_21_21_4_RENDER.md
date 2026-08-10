# BIM Portal Release 21.21.4 — Render Deployment

## 1. Confirm a PostgreSQL backup

Before deployment, confirm that Render PostgreSQL has a recent restorable backup or recovery point.

## 2. Extract the release

Extract `BIMFM_PORTAL_RELEASE_21_21_4_RENDER.zip` and open PowerShell inside the inner folder:

`BIMFM_PORTAL_RELEASE_21_21_4_RENDER`

## 3. Set the release and repository folders

```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
$Release = (Get-Location).Path

$Repo = (Resolve-Path $Repo).Path
$Release = (Resolve-Path $Release).Path

Write-Host "Repository: $Repo"
Write-Host "Release: $Release"
```

The paths must be different.

## 4. Copy the release

```powershell
robocopy $Release $Repo /E /XD .git .venv venv __pycache__ data backups logs uploads /XF .env *.db *.sqlite *.sqlite3 *.pyc /R:2 /W:1
```

Robocopy exit codes `0` through `7` mean success.

## 5. Review the changes

```powershell
Set-Location $Repo
$env:GIT_PAGER = "cat"

git status
git diff --stat
```

## 6. Stage Release 21.21.4

```powershell
git add app/config.py app/database.py app/task_time_reporting.py app/excel_exports.py app/models/identity.py app/routers/administration.py app/locales/en.json app/locales/zh_TW.json alembic/versions/20260806_0017_staff_task_member_mapping.py templates/admin_staff_accounts.html templates/task_time_utilization.html tests/test_release_21_21_4_utilization_task_supervisor.py README_RELEASE_21_21_4_UTILIZATION_TASK_SUPERVISOR.md DEPLOYMENT_RELEASE_21_21_4_RENDER.md DATABASE_SAFETY_RELEASE_21_21_4.md TEST_REPORT_RELEASE_21_21_4.txt
```

Review:

```powershell
git status
git diff --cached --stat
```

## 7. Commit and push

```powershell
git commit -m "Release 21.21.4 utilization and task supervisor mapping"
git push origin main
git log -1 --oneline
```

## 8. Render settings

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

If Auto-Deploy does not start:

`Render Dashboard → Manual Deploy → Deploy latest commit`

Expected migration log:

```text
Running upgrade 20260805_0016 -> 20260806_0017
```

## 9. Verify after deployment

After Render reports **Live**, press `Ctrl + Shift + R`.

Confirm the lower-left version:

```text
v3.0.21.4
```

Then verify:

1. Open **Task Time Utilization**.
2. Confirm a task completed early without recorded hours shows below 100%.
3. Confirm a task completed late without recorded hours can show above 100%.
4. Open **Administration → Staff Access**.
5. Find your Administrator account and select **Enable Task Assignment**.
6. Open **New Task** or **Edit Task** and confirm your name appears in the assigned-member list.
7. Confirm your Administrator login and permissions remain unchanged.
