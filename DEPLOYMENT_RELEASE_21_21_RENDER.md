# BIM Portal Release 21.21 — Render Deployment

## 1. Extract the release

Extract `BIMFM_PORTAL_RELEASE_21_21_RENDER.zip` and open PowerShell inside the extracted inner folder.

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

## 3. Copy Release 21.21

```powershell
robocopy $Release $Repo /E /XD .git .venv venv __pycache__ data backups logs uploads /XF .env *.db *.sqlite *.sqlite3 *.pyc /R:2 /W:1
```

Robocopy exit codes `0` through `7` mean success.

## 4. Review

```powershell
Set-Location $Repo
$env:GIT_PAGER = "cat"

git status
git diff --stat
```

## 5. Stage only Release 21.21

```powershell
git add app/config.py app/locales/en.json app/locales/zh_TW.json static/css/ui-refresh.css templates/base.html tests/test_release_21_21_workspace_profile_refresh.py README_RELEASE_21_21_WORKSPACE_PROFILE_REFRESH.md DEPLOYMENT_RELEASE_21_21_RENDER.md DATABASE_SAFETY_RELEASE_21_21.md TEST_REPORT_RELEASE_21_21.txt
```

Review:

```powershell
git status
git diff --cached --stat
```

## 6. Commit and push

```powershell
git commit -m "Release 21.21 workspace and profile refresh"
git push origin main
git log -1 --oneline
```

## 7. Render configuration

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

No new migration is expected for this release.

## 8. Verify

After Render reports **Live**, press `Ctrl + Shift + R`.

Confirm the lower-left version:

```text
v3.0.21
```

Verify:

- Upper-left shows `BIM Portal` and `Unified Workspace`.
- No BIMFM company name or logo appears.
- The upper-right profile card shows the user's avatar, online status, name, and role.
- Password and logout controls work.
- The EN / 繁中 language control remains a switch bar.
- Header remains usable on a laptop and mobile-width browser.

## Rollback

Render Dashboard → Web Service → Deploys → select the previous successful deployment → **Rollback**.

Release 21.21 has no database migration, so rolling back the application is sufficient.
