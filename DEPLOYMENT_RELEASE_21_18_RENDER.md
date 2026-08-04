# Deploy BIM Portal Release 21.18 to Render

This is a cumulative release. It retains the Release 21.17 completed-task filters and all Release 21.16 functions.

## 1. Extract the package

Extract:

```text
BIMFM_PORTAL_RELEASE_21_18_RENDER.zip
```

Open PowerShell inside the extracted `BIMFM_PORTAL_RELEASE_21_18_RENDER` folder.

## 2. Set the folders

Run each command separately:

```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
```

```powershell
$Release = (Get-Location).Path
```

```powershell
$Repo = (Resolve-Path $Repo).Path
```

```powershell
$Release = (Resolve-Path $Release).Path
```

```powershell
Write-Host "Release: $Release"
```

```powershell
Write-Host "Repository: $Repo"
```

The Release and Repository paths must be different.

## 3. Copy the release

```powershell
robocopy $Release $Repo /E /XD .git .venv venv __pycache__ data backups logs uploads /XF .env *.db *.sqlite *.sqlite3 *.pyc /R:2 /W:1
```

Robocopy exit codes 0 through 7 indicate success.

## 4. Enter the repository

```powershell
Set-Location $Repo
```

```powershell
$env:GIT_PAGER = "cat"
```

```powershell
git status
```

```powershell
git diff --stat
```

## 5. Stage Release 21.18 only

Copy the following as one line:

```powershell
git add app/config.py app/task_time_reporting.py app/excel_exports.py app/locales/en.json app/locales/zh_TW.json templates/task_time_utilization.html README_RELEASE_21_18_ALL_TIME_UTILIZATION_FALLBACK.md DEPLOYMENT_RELEASE_21_18_RENDER.md DATABASE_SAFETY_RELEASE_21_18.md TEST_REPORT_RELEASE_21_18.txt
```

Do not use `git add .`.

## 6. Review the staged changes

```powershell
git diff --cached --stat
```

```powershell
git status
```

## 7. Commit and push

```powershell
git commit -m "Release 21.18 add all-time utilization fallback"
```

```powershell
git push origin main
```

```powershell
git log -1 --oneline
```

## 8. Render settings

Keep the existing Build Command:

```text
pip install -r requirements.txt && alembic upgrade head
```

Keep the existing Start Command:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

No new migration message is expected because the Alembic head remains `20260804_0015`.

When automatic deployment does not start:

```text
Render Dashboard → Manual Deploy → Deploy latest commit
```

After Render reports Live, hard-refresh the browser:

```text
Ctrl + Shift + R
```

Confirm the lower-left status displays:

```text
System online
v3.0.18
```

Then open:

```text
Performance → Task Time Utilization
```

Confirm that a scheduled historical task with no actual time displays:

```text
Recorded Time: 0h
Utilization Time: same as Planned Time
Time Source: Planned fallback
Time Budget Used: 100.0%
```
