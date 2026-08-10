# Release 21.22.6 Render Deployment

Production can remain on 21.22.4 until you are ready. This ZIP is cumulative; you do not need to deploy 21.22.5 first.

1. Extract `BIM_PORTAL_RELEASE_21_22_6_RENDER.zip`.
2. In PowerShell inside the extracted folder:

```powershell
$Repo = "C:\Users\Don\Documents\PROGRAMMING\BIMFM_PORTAL_RELEASE_20_6_RENDER"
$Release = (Get-Location).Path
$Repo = (Resolve-Path $Repo).Path
$Release = (Resolve-Path $Release).Path
robocopy $Release $Repo /E /XD .git .venv venv __pycache__ data backups logs uploads /XF .env *.db *.sqlite *.sqlite3 *.pyc /R:2 /W:1
Set-Location $Repo
$env:GIT_PAGER = "cat"
git status
git diff --stat
git add .
git status
git diff --cached --stat
git commit -m "Release 21.22.6 review queue production hotfix"
git push origin main
git log -1 --oneline
```

3. Keep Render commands unchanged:

Build: `pip install -r requirements.txt && alembic upgrade head`

Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

Health: `/health/ready`

4. After Render is Live, hard refresh (`Ctrl+Shift+R`) and verify version:
`v3.0.22.6-release21.22.6-review-work-queue-hotfix`

5. Smoke test in this order: `/admin` -> Review Queue -> assign reviewer -> Start Review -> Stop Review. Confirm the freelancer's task assignment/status remains unchanged.

Database safety: no new Alembic migration, table, column, schema alteration, or backfill is included in this hotfix.
