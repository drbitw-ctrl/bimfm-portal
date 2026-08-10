# Deploy BIMFM Portal Release 21.20.2 to Render

## 1. Extract and open PowerShell

Extract the ZIP and open PowerShell inside:

`BIMFM_PORTAL_RELEASE_21_20_2_RENDER`

## 2. Set folders

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

Robocopy exit codes 0 through 7 mean success.

## 4. Review

```powershell
Set-Location $Repo
$env:GIT_PAGER = "cat"
git status
git diff --stat
```

## 5. Stage Release 21.20.2

```powershell
git add app/config.py app/main.py app/hr_workflow.py app/routers/overtime.py app/locales/en.json app/locales/zh_TW.json static/css/ui-refresh.css templates/admin_overtime.html templates/admin_overtime_credits.html tests/test_release_21_20_2_overtime_credit_adjustment.py README_RELEASE_21_20_2_OVERTIME_CREDIT_CORRECTION.md DEPLOYMENT_RELEASE_21_20_2_RENDER.md DATABASE_SAFETY_RELEASE_21_20_2.md TEST_REPORT_RELEASE_21_20_2.txt
```

Review:

```powershell
git status
git diff --cached --stat
```

## 6. Commit and push

```powershell
git commit -m "Release 21.20.2 overtime credit correction and balance page"
git push origin main
git log -1 --oneline
```

## 7. Render settings

Build Command:

```text
pip install -r requirements.txt && alembic upgrade head
```

Start Command:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

No new Alembic migration is expected.

## 8. Verify after Live

Press `Ctrl + Shift + R`.

Confirm version:

`v3.0.20.2-release21.20.2-overtime-credit-ledger`

Then:

1. Open **Overtime Claims**.
2. Set Status to **All statuses**.
3. Open Carlo's approved August 4 OT.
4. Expand **Adjust approved overtime**.
5. Keep verified end time at `02:30 AM`.
6. Enter an adjustment reason.
7. Select **Update Approved OT and Credit**.
8. Confirm Approved OT and Comp Credit both show `510 minutes`.
9. Open **Overtime Credit Balances** and confirm Carlo's available balance increased by 210 minutes compared with the old record.
