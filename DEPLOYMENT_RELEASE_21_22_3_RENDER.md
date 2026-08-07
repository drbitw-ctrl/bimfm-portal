# BIM Portal Release 21.22.3 — Render Deployment

## 1. Extract the release

Extract `BIM_PORTAL_RELEASE_21_22_3_RENDER.zip` and open PowerShell inside the extracted `BIM_PORTAL_RELEASE_21_22_3_RENDER` folder.

## 2. Set paths

```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
$Release = (Get-Location).Path

$Repo = (Resolve-Path $Repo).Path
$Release = (Resolve-Path $Release).Path

Write-Host "Repository: $Repo"
Write-Host "Release: $Release"
```

The repository and release paths must be different.

## 3. Copy the release

```powershell
robocopy $Release $Repo /E /XD .git .venv venv __pycache__ data backups logs uploads /XF .env *.db *.sqlite *.sqlite3 *.pyc /R:2 /W:1
```

Robocopy exit codes 0 through 7 mean success.

## 4. Review changes

```powershell
Set-Location $Repo
$env:GIT_PAGER = "cat"

git status
git diff --stat
```

## 5. Stage Release 21.22.3

```powershell
git add app/config.py app/payroll_engine.py app/finance_service.py app/main.py app/dtr_exporter.py app/routers/finance.py app/locales/en.json app/locales/zh_TW.json templates/admin_finance_center.html templates/admin_dtr_detail.html tests/test_release_21_22_3_absence_payroll_deduction.py README_RELEASE_21_22_3_ABSENCE_PAYROLL_DEDUCTION.md DATABASE_SAFETY_RELEASE_21_22_3.md DEPLOYMENT_RELEASE_21_22_3_RENDER.md TEST_REPORT_RELEASE_21_22_3.txt
```

Review the staged changes:

```powershell
git status
git diff --cached --stat
```

## 6. Commit and push

```powershell
git commit -m "Release 21.22.3 absence payroll deduction"
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

Keep the Health Check Path:

```text
/health/ready
```

There is no new Alembic migration in Release 21.22.3.

## 8. Post-deployment verification

After Render reports Live, hard refresh with `Ctrl + Shift + R`.

Confirm the version footer shows:

```text
v3.0.22.3-release21.22.3-absence-payroll-deduction
```

Then verify:

1. Open Monthly DTR for a normal freelancer who has a day classified as `ABSENT`.
2. Confirm the Attendance Summary shows the absent day.
3. Confirm Payroll Treatment shows separate Unpaid Leave Hours and Absent Hours.
4. Confirm Total Deduction includes both categories.
5. Confirm Salary Coverage percentage is lower when an absence exists.
6. Confirm available OT/comp credit offsets approved leave only and does not remove the absence deduction.
7. Confirm a member with no absence and no uncovered leave still shows 100% salary coverage.
8. Confirm Belinda's task-hourly mode continues to operate separately and is not assigned normal attendance absences.
