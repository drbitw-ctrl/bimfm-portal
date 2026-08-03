# Deploy Release 21.08 to Render

Extract the release ZIP and open PowerShell inside `BIMFM_PORTAL_RELEASE_21_08_RENDER`.

Run commands one line at a time.

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
robocopy $Release $Repo /E /XD .git .venv venv __pycache__ data backups logs uploads /XF .env *.db *.sqlite *.sqlite3 *.pyc /R:2 /W:1
```

Robocopy exit codes 0 through 7 mean success.

```powershell
Set-Location $Repo
```

```powershell
$env:GIT_PAGER = "cat"
```

```powershell
git status
```

Stage only Release 21.08 files:

```powershell
git add app/config.py app/locales/en.json app/locales/zh_TW.json alembic/versions/20260803_0011_july_leave_task_start_dates.py static/css/ui-refresh.css templates/admin_project_team.html templates/attendance.html README_RELEASE_21_08_JULY_DATA_PROJECT_LABELS_PROFILE_CARD.md DEPLOYMENT_RELEASE_21_08_RENDER.md DATABASE_SAFETY_RELEASE_21_08.md TEST_REPORT_RELEASE_21_08.txt
```

```powershell
git diff --cached --stat
```

```powershell
git commit -m "Release 21.08 July data and project label cleanup"
```

```powershell
git push origin main
```

Render Build Command:

```text
pip install -r requirements.txt && alembic upgrade head
```

Render Start Command:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Expected migration log:

```text
Running upgrade 20260803_0010 -> 20260803_0011, Correct July leave records and backfill task start dates.
```

After Render reports Live, press `Ctrl + Shift + R` and confirm:

```text
v3.0.8-release21.08-july-data-project-labels-profile-card
```
