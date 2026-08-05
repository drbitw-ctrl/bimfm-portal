# Deploy BIM Portal Release 21.19.1 to Render

Release 21.19.1 is a cumulative package based on Release 21.19. It contains no
database migration and changes only project/task API authorization plus version
metadata.

## 1. Do not deploy over uncommitted work

Open PowerShell in the existing Git repository and check:

```powershell
git status
```

The repository should be clean, or your current work should already be committed.
Do not continue when important uncommitted files are present.

Create a local safety branch before copying:

```powershell
git branch safety-before-release-21-19-1
```

## 2. Extract the package

Extract:

```text
BIMFM_PORTAL_RELEASE_21_19_1_RENDER.zip
```

Open PowerShell inside the extracted inner folder:

```text
BIMFM_PORTAL_RELEASE_21_19_1_RENDER
```

## 3. Set the folders

Run each command separately:

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
Write-Host "Release: $Release"
```

```powershell
Write-Host "Repository: $Repo"
```

The Release and Repository paths must be different.

## 4. Copy the cumulative package

```powershell
robocopy $Release $Repo /E /XD .git .venv venv __pycache__ data backups logs uploads /XF .env *.db *.sqlite *.sqlite3 *.pyc /R:2 /W:1
```

Robocopy exit codes 0 through 7 indicate success.

## 5. Review before staging

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
git diff -- app/api/v1/router.py app/config.py
```

The application-code diff should be limited to:

- Assignment filtering in `app/api/v1/router.py`
- Version update in `app/config.py`

## 6. Run the included regression tests

Use the repository's active Python environment:

```powershell
python -m unittest -v tests.test_api_v1_freelancer_scope
```

Expected result:

```text
Ran 9 tests
OK
```

## 7. Stage Release 21.19.1 only

Copy this command as one line:

```powershell
git add app/api/v1/router.py app/config.py tests/__init__.py tests/test_api_v1_freelancer_scope.py README_RELEASE_21_19_1_API_AUTHORIZATION_HOTFIX.md DEPLOYMENT_RELEASE_21_19_1_RENDER.md DATABASE_SAFETY_RELEASE_21_19_1.md TEST_REPORT_RELEASE_21_19_1.txt
```

Do not use `git add .`.

Review the staged patch:

```powershell
git diff --cached --stat
```

```powershell
git diff --cached -- app/api/v1/router.py app/config.py
```

## 8. Commit and push

```powershell
git commit -m "Release 21.19.1 restrict freelancer project task API access"
```

```powershell
git push origin main
```

```powershell
git log -1 --oneline
```

## 9. Render deployment

Keep the existing Build Command:

```text
pip install -r requirements.txt && alembic upgrade head
```

Keep the existing Start Command:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

No new migration line is expected. The database head remains:

```text
20260804_0015
```

When automatic deployment does not begin:

```text
Render Dashboard → Manual Deploy → Deploy latest commit
```

After Render reports **Live**, hard-refresh:

```text
Ctrl + Shift + R
```

Confirm the lower-left status displays:

```text
System online
v3.0.19.1
```

## 10. Production smoke test

Use one test freelancer account that has a known task:

1. Confirm the normal My Projects and My Tasks pages still show its assignment.
2. While logged in as that freelancer, open `/api/v1/projects` and confirm only
   assigned projects are returned.
3. Open `/api/v1/tasks` and confirm only assigned tasks are returned.
4. Sign in as an Administrator and confirm management pages still show all work.

Do not edit, delete, or reassign any production task during this smoke test.

## Rollback

This hotfix has no database migration. To roll back, revert the application
commit and deploy the revert:

```powershell
git revert HEAD
```

```powershell
git push origin main
```

No Alembic downgrade is required.
