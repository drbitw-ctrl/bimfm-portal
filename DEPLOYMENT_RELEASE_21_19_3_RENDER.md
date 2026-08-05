# BIMFM Portal Release 21.19.3 — Render Deployment

## 1. Extract the release

Extract the ZIP and open PowerShell inside the inner folder:

`BIMFM_PORTAL_RELEASE_21_19_3_RENDER`

## 2. Set the release and repository folders

```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
$Release = (Get-Location).Path

$Repo = (Resolve-Path $Repo).Path
$Release = (Resolve-Path $Release).Path

Write-Host "Repository: $Repo"
Write-Host "Release: $Release"
```

The paths must be different.

## 3. Copy Release 21.19.3

```powershell
robocopy $Release $Repo /E /XD .git .venv venv __pycache__ data backups logs uploads /XF .env *.db *.sqlite *.sqlite3 *.pyc /R:2 /W:1
```

Robocopy exit codes 0 through 7 mean success.

## 4. Review the repository

```powershell
Set-Location $Repo
$env:GIT_PAGER = "cat"
git status
git diff --stat
```

## 5. Stage only Release 21.19.3

```powershell
git add app/config.py app/member_directory.py app/routers/overtime.py app/locales/en.json app/locales/zh_TW.json tests/test_release_21_19_3_active_member_selectors.py README_RELEASE_21_19_3_ACTIVE_MEMBER_SELECTORS.md DEPLOYMENT_RELEASE_21_19_3_RENDER.md DATABASE_SAFETY_RELEASE_21_19_3.md TEST_REPORT_RELEASE_21_19_3.txt
```

Review:

```powershell
git status
git diff --cached --stat
```

## 6. Commit and push

```powershell
git commit -m "Release 21.19.3 active portal member selectors"
git push origin main
git log -1 --oneline
```

## 7. Render settings

No database migration is required. Keep the existing commands unchanged.

Build Command:

```text
pip install -r requirements.txt && alembic upgrade head
```

Start Command:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

If automatic deployment does not start:

`Render Dashboard → Manual Deploy → Deploy latest commit`

## 8. Verify after deployment

After Render reports **Live**, press `Ctrl + Shift + R`.

Confirm the lower-left version is:

`v3.0.19.3-release21.19.3-active-member-selectors`

Then open:

`Overtime Claims → Add Previous Overtime`

Verify:

- Each active portal freelancer appears once.
- Legacy-only or unmapped duplicate names are absent.
- Inactive members and disabled accounts are absent.
- Historical OT can still be created for a valid active member.
- Existing projects, tasks, attendance, leave, DTR, Finance, and OT records remain unchanged.
