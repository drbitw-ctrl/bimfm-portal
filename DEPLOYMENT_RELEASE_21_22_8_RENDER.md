# Deploy BIM Portal Release 21.22.8 to Render

Release 21.22.8 is cumulative from the stable 21.22.6 baseline. You do not need to deploy 21.22.7 first.

## PowerShell

Open PowerShell inside the extracted `BIM_PORTAL_RELEASE_21_22_8_RENDER` folder.

```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
$Release = (Get-Location).Path

$Repo = (Resolve-Path $Repo).Path
$Release = (Resolve-Path $Release).Path

Write-Host "Repository: $Repo"
Write-Host "Release:    $Release"
```

Copy the release while preserving the repository's `.git`, environment files, databases, uploads, and runtime folders:

```powershell
robocopy $Release $Repo /E /XD .git .venv venv __pycache__ data backups logs uploads /XF .env *.db *.sqlite *.sqlite3 *.pyc /R:2 /W:1
```

Robocopy codes 0 through 7 are success codes.

```powershell
Set-Location $Repo
$env:GIT_PAGER = "cat"

git status
git diff --stat
```

Stage Release 21.22.8:

```powershell
git add app/config.py app/locales/en.json app/locales/zh_TW.json app/portal_project_service.py app/review_work_service.py app/routers/administration.py app/routers/attendance.py app/routers/portal.py static/css/ui-refresh.css templates/admin_dashboard.html templates/admin_dtr_dashboard.html templates/admin_review_queue.html templates/base.html templates/staff_my_work.html tests/test_release_21_22_8_review_dashboard_dtr.py README_RELEASE_21_22_8.md DATABASE_SAFETY_RELEASE_21_22_8.md DEPLOYMENT_RELEASE_21_22_8_RENDER.md TEST_REPORT_RELEASE_21_22_8.txt

git status
git diff --cached --stat
```

Commit and push:

```powershell
git commit -m "Release 21.22.8 review queue dashboard stabilization"
git push origin main
git log -1 --oneline
```

## Render configuration

Keep the existing settings:

Build Command:

```text
pip install -r requirements.txt && alembic upgrade head
```

Start Command:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Health Check Path:

```text
/health/ready
```

## Post-deploy verification

1. Wait until Render reports `Live`.
2. Hard refresh with `Ctrl + Shift + R`.
3. Confirm the lower-left version is `v3.0.22.8`.
4. Open `/admin` first and verify the dashboard loads.
5. Verify Availability lanes retain full member/task cards but scroll horizontally.
6. Open `/portal/my-work` and confirm My Review Work is shown for Admin/Supervisor.
7. Open `/admin/review-queue`.
8. Assign one review to your signed-in Admin account and verify the reviewer name appears once.
9. Start Review, then Stop Review with a review activity note.
10. Confirm the freelancer's original task assignee, status, progress, and production Work Orders are unchanged.
11. Open DTR and confirm TS-* Admin/Supervisor identities are not available for DTR generation.
12. Confirm sidebar labels clearly separate Daily Task Reports from Daily Time Record (DTR).
