# BIM Portal Release 21.21.2 — Render Deployment

## Scope

Presentation-only update for the dark dashboard and application header. There is no Alembic migration and no database change. Render application rollback is sufficient if you prefer the previous design.

## 1. Extract the release

Extract `BIMFM_PORTAL_RELEASE_21_21_2_RENDER.zip` and open PowerShell inside the extracted inner folder.

## 2. Set the folders

```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
$Release = (Get-Location).Path

$Repo = (Resolve-Path $Repo).Path
$Release = (Resolve-Path $Release).Path

Write-Host "Repository: $Repo"
Write-Host "Release: $Release"
```

The paths must be different.

## 3. Copy the release

```powershell
robocopy $Release $Repo /E /XD .git .venv venv __pycache__ data backups logs uploads /XF .env *.db *.sqlite *.sqlite3 *.pyc /R:2 /W:1
```

Robocopy exit codes `0` through `7` indicate success.

## 4. Enter the repository and review

```powershell
Set-Location $Repo
$env:GIT_PAGER = "cat"

git status
git diff --stat
```

## 5. Stage Release 21.21.2

```powershell
git add app/config.py static/css/ui-refresh.css templates/base.html tests/test_release_21_21_2_dark_dashboard_header.py README_RELEASE_21_21_2_DARK_DASHBOARD_HEADER.md DEPLOYMENT_RELEASE_21_21_2_RENDER.md DATABASE_SAFETY_RELEASE_21_21_2.md TEST_REPORT_RELEASE_21_21_2.txt
```

Review:

```powershell
git status
git diff --cached --stat
```

## 6. Commit and push

```powershell
git commit -m "Release 21.21.2 dark dashboard and header refinement"
git push origin main
git log -1 --oneline
```

## 7. Render settings

Keep the existing Build Command:

```text
pip install -r requirements.txt && alembic upgrade head
```

Keep the existing Start Command:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Health Check Path:

```text
/health/ready
```

If auto-deploy does not begin, use **Manual Deploy → Deploy latest commit**.

## 8. Verify

After Render reports **Live**, press `Ctrl + Shift + R`.

Confirm:

- Version shows `v3.0.21.2`
- Dark dashboard cards are readable and no longer use bright pastel blocks
- Member names, project tasks, and status badges have clear contrast
- EN / 繁中 remains a segmented switch
- A visible `Log out` button appears at the far right of the header
- Profile menu still contains Change Password

## Rollback

Because this release has no database migration, use Render **Rollback** to the previous successful deployment if needed. No PostgreSQL rollback is required.
