# BIMFM Portal Release 21.19.4 — Render Deployment

## 1. Extract the release

Extract `BIMFM_PORTAL_RELEASE_21_19_4_RENDER.zip` and open PowerShell inside the extracted inner folder:

`BIMFM_PORTAL_RELEASE_21_19_4_RENDER`

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

## 3. Copy Release 21.19.4 into the Git repository

```powershell
robocopy $Release $Repo /E /XD .git .venv venv __pycache__ data backups logs uploads /XF .env *.db *.sqlite *.sqlite3 *.pyc /R:2 /W:1
```

Robocopy exit codes 0 through 7 indicate success.

## 4. Review the copied changes

```powershell
Set-Location $Repo
$env:GIT_PAGER = "cat"

git status
git diff --stat
```

## 5. Stage only Release 21.19.4

```powershell
git add app/config.py app/services/overtime_service.py tests/test_release_21_19_4_overnight_ot_approval.py README_RELEASE_21_19_4_OVERNIGHT_OT_APPROVAL.md DEPLOYMENT_RELEASE_21_19_4_RENDER.md DATABASE_SAFETY_RELEASE_21_19_4.md TEST_REPORT_RELEASE_21_19_4.txt
```

Review:

```powershell
git status
git diff --cached --stat
```

## 6. Commit and push

```powershell
git commit -m "Release 21.19.4 overnight OT approval fix"
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

No new Alembic migration is expected for this release.

If automatic deployment does not begin:

`Render Dashboard -> Manual Deploy -> Deploy latest commit`

## 8. Verify after deployment

After Render reports Live, press `Ctrl + Shift + R`.

Confirm the lower-left version is:

`v3.0.19.4-release21.19.4-overnight-ot-approval`

Test this case:

1. Open Overtime Claims.
2. Use an OT claim planned from 6:00 PM to 11:00 PM.
3. Enter the Supervisor-approved end time as 2:30 AM.
4. Approve final credit.
5. Confirm approval succeeds and the verified duration is 510 minutes.

Also confirm a same-day end time such as 11:00 PM still calculates as 300 minutes.
