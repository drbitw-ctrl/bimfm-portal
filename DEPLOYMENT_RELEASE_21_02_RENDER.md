# BIMFM Portal Release 21.02 — Render Deployment

## Before deployment

1. Confirm a current PostgreSQL backup.
2. Keep the existing Render Web Service and PostgreSQL database.
3. Do not replace production environment variables or secrets.
4. Extract this release into a separate folder.

## Copy into the existing Git repository

Run each PowerShell command separately.

```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
$Release = (Get-Location).Path
$Repo = (Resolve-Path $Repo).Path
$Release = (Resolve-Path $Release).Path
Write-Host "Repository: $Repo"
Write-Host "Release: $Release"
robocopy $Release $Repo /E /XD .git .venv venv __pycache__ data backups logs uploads /XF .env *.db *.sqlite *.sqlite3 *.pyc /R:2 /W:1
Set-Location $Repo
$env:GIT_PAGER = "cat"
git status
git diff --stat
```

Robocopy exit codes 0 through 7 indicate success.

## Stage Release 21.02

```powershell
git add app/config.py app/database.py app/main.py app/models/identity.py app/auth/permissions.py app/auth/middleware.py app/routers/auth.py app/routers/administration.py app/routers/attendance.py app/locales/en.json app/locales/zh_TW.json alembic/versions/20260802_0009_staff_password_change.py static/css/ui-refresh.css static/images/bimfm-mark.png static/images/favicon.ico static/images/bimfm-company-logo.png static/images/bimfm-company-logo-web.png templates/base.html templates/admin_login.html templates/freelancer_login.html templates/setup.html templates/change_password.html templates/admin_staff_accounts.html templates/admin_reset_staff_password.html templates/admin_dtr_dashboard.html templates/admin_dtr_detail.html README_RELEASE_21_02_FINANCE_DTR_PASSWORD_BRANDING.md DEPLOYMENT_RELEASE_21_02_RENDER.md DATABASE_SAFETY_RELEASE_21_02.md TEST_REPORT_RELEASE_21_02.txt
```

Review staged files:

```powershell
git status
git diff --cached --stat
```

## Commit and push

```powershell
git commit -m "Release 21.02 finance DTR password security and branding"
git push origin main
```

## Render commands

Keep the existing commands unchanged.

Build:

```text
pip install -r requirements.txt && alembic upgrade head
```

Start:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Expected migration:

```text
Running upgrade 20260802_0008 -> 20260802_0009, Add forced password-change flag for staff accounts.
```

If Auto-Deploy is disabled, select:

```text
Manual Deploy → Deploy latest commit
```

## Post-deployment checks

1. Confirm the sidebar displays the official company mark.
2. Confirm the browser tab uses the official favicon.
3. Confirm staff and freelancer login pages show the full official logo.
4. Create a temporary staff account and confirm first login redirects to Change Password.
5. Confirm all roles can change only their own password.
6. Confirm only an Administrator sees password-reset controls for other accounts.
7. Sign in as Finance and generate a Monthly DTR.
8. Confirm Finance can export the DTR.
9. Confirm Finance cannot review or finalize the DTR.
10. Confirm Supervisor remains unable to generate DTR.
11. Press Ctrl + Shift + R after deployment to refresh cached branding and CSS.
