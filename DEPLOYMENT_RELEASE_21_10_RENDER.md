# Release 21.10 Render Deployment

Run every PowerShell command one line at a time.

## 1. Open the extracted Release 21.10 folder

Expected folder name:

`BIMFM_PORTAL_RELEASE_21_10_RENDER`

## 2. Set paths

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

## 5. Stage Release 21.10 only

```powershell
git add app/config.py app/routers/attendance.py alembic/versions/20260803_0013_july_standard_attendance.py README_RELEASE_21_10_JULY_ATTENDANCE_SEARCH_HOTFIX.md DEPLOYMENT_RELEASE_21_10_RENDER.md DATABASE_SAFETY_RELEASE_21_10.md TEST_REPORT_RELEASE_21_10.txt
```

Do not use `git add .`.

## 6. Review, commit, and push

```powershell
git diff --cached --stat
```

```powershell
git commit -m "Release 21.10 July attendance and monthly search hotfix"
```

```powershell
git push origin main
```

## 7. Render

Build command remains:

`pip install -r requirements.txt && alembic upgrade head`

Start command remains:

`uvicorn app.main:app --host 0.0.0.0 --port $PORT`

Expected migration:

`Running upgrade 20260803_0012 -> 20260803_0013, Backfill supervisor-approved July 2026 standard attendance.`

After Render reports Live, refresh with `Ctrl + Shift + R`.
