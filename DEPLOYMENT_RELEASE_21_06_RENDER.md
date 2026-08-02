# Release 21.06 Render Deployment

## Release folder

Open PowerShell inside the extracted folder:

```text
BIMFM_PORTAL_RELEASE_21_06_RENDER
```

Run every command separately.

## 1. Set paths

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
Write-Host "Repository: $Repo"
```

```powershell
Write-Host "Release: $Release"
```

The paths must be different.

## 2. Copy the release

```powershell
robocopy $Release $Repo /E /XD .git .venv venv __pycache__ data backups logs uploads /XF .env *.db *.sqlite *.sqlite3 *.pyc /R:2 /W:1
```

Robocopy exit codes 0 through 7 indicate success.

## 3. Enter the repository

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

## 4. Stage Release 21.06 only

```powershell
git add .env.example app/config.py app/main.py app/auth/middleware.py app/work_order_service.py app/routers/attendance.py app/routers/administration.py app/locales/en.json app/locales/zh_TW.json templates/admin_login.html templates/freelancer_login.html templates/change_password.html README_RELEASE_21_06_PASSWORD_WORK_ORDER_SAFEGUARD.md DEPLOYMENT_RELEASE_21_06_RENDER.md DATABASE_SAFETY_RELEASE_21_06.md TEST_REPORT_RELEASE_21_06.txt
```

Do not use `git add .`.

## 5. Review staged changes

```powershell
git status
```

```powershell
git diff --cached --stat
```

## 6. Commit

```powershell
git commit -m "Release 21.06 password and work order safeguard"
```

## 7. Push

```powershell
git push origin main
```

## Render settings

Keep the existing commands unchanged.

Build Command:

```text
pip install -r requirements.txt && alembic upgrade head
```

Start Command:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

No new Alembic migration message is expected.

If automatic deployment is disabled:

```text
Manual Deploy → Deploy latest commit
```

After the service is Live, use `Ctrl + Shift + R`.

Expected displayed version:

```text
v3.0.6-release21.06-password-work-order-safeguard
```
