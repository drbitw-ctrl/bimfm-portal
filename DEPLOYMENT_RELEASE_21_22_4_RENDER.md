# BIM Portal Release 21.22.4 — Render Deployment

## 1. Extract

Extract `BIM_PORTAL_RELEASE_21_22_4_RENDER.zip` and open PowerShell inside the extracted `BIM_PORTAL_RELEASE_21_22_4_RENDER` folder.

## 2. Set paths

```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
$Release = (Get-Location).Path

$Repo = (Resolve-Path $Repo).Path
$Release = (Resolve-Path $Release).Path

Write-Host "Repository: $Repo"
Write-Host "Release: $Release"
```

## 3. Copy release into Git repository

```powershell
robocopy $Release $Repo /E /XD .git .venv venv __pycache__ data backups logs uploads /XF .env *.db *.sqlite *.sqlite3 *.pyc /R:2 /W:1
```

Robocopy exit codes 0–7 indicate success.

## 4. Review

```powershell
Set-Location $Repo
$env:GIT_PAGER = "cat"

git status
git diff --stat
```

## 5. Stage this release

```powershell
git add app/config.py app/payroll_engine.py app/dtr_service.py app/finance_service.py app/dtr_exporter.py app/main.py app/routers/finance.py app/locales/en.json app/locales/zh_TW.json templates/admin_finance_center.html templates/admin_dtr_detail.html tests/test_release_21_22_3_absence_payroll_deduction.py tests/test_release_21_22_4_comp_credit_absence_coverage.py README_RELEASE_21_22_4_COMP_CREDIT_ABSENCE_COVERAGE.md DATABASE_SAFETY_RELEASE_21_22_4.md DEPLOYMENT_RELEASE_21_22_4_RENDER.md TEST_REPORT_RELEASE_21_22_4.txt
```

Review:

```powershell
git status
git diff --cached --stat
```

## 6. Commit and push

```powershell
git commit -m "Release 21.22.4 comp credit absence coverage"
git push origin main
git log -1 --oneline
```

## 7. Render configuration

Build Command remains:

```text
pip install -r requirements.txt && alembic upgrade head
```

Start Command remains:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Health Check Path:

```text
/health/ready
```

There is no new Alembic migration in this release.

## 8. Verify after deployment

After Render reports Live, press `Ctrl + Shift + R`.

Confirm version:

```text
v3.0.22.4-release21.22.4-comp-credit-absence-coverage
```

Then regenerate a non-finalized monthly DTR that contains an ABSENT day and approved available comp credit. Confirm:

- comp credit first covers approved leave;
- remaining comp credit covers ABSENT time;
- only uncovered absence reduces salary coverage;
- the comp-credit balance is reduced through an auditable `USED_ABSENCE` ledger entry;
- regenerating the DTR does not duplicate the credit usage.
