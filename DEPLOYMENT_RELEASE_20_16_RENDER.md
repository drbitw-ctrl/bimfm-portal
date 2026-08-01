# BIMFM Portal Release 20.16 — Render Deployment

## Package

Use `BIMFM_PORTAL_RELEASE_20_16_RENDER.zip`.

Release 20.16 is based on the stable Release 20.14 deployment and does not include the rolled-back broad Release 20.15 inline-edit implementation.

## Before deployment

1. Confirm the current production PostgreSQL backup.
2. Preserve the existing Render database and all environment variables.
3. Do not upload `.env` or local database files.
4. Confirm the Git repository is on the intended deployment branch, normally `main`.

## Copy into the existing repository

Extract this ZIP to a folder separate from the Git repository. Copy the release files into the repository while excluding `.git`, `.env`, database files, caches, and local runtime folders.

Recommended PowerShell copy command:

```powershell
robocopy $Release $Repo /E /XD .git .venv venv __pycache__ data backups logs uploads /XF .env *.db *.sqlite *.sqlite3 *.pyc /R:2 /W:1
```

Robocopy exit codes `0` through `7` indicate success.

## Review, commit, and push

```powershell
Set-Location $Repo
git status
git diff --stat
git add -A
git status
git commit -m "Release 20.16 selective task quick edit"
git push origin main
```

Confirm no `.env`, database, password, secret, or backup file is staged.

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

No new Release 20.16 Alembic upgrade line is expected.

## Acceptance checklist

After Render reports **Live**:

1. Sign in as an Administrator or authorized project editor.
2. Open the **Tasks** item in the sidebar.
3. Confirm only Status, Progress, Quality, and Completed are editable.
4. Confirm Project, Task, Member, Priority, Discipline, Start, and Deadline remain display-only.
5. Change Progress and confirm the percentage number and bar update.
6. Change Quality and confirm the percentage number and bar update.
7. Change Status to Completed and confirm Progress becomes 100% and Completed receives a date.
8. Edit the Completed date and refresh the page to confirm it persists.
9. Open Projects, My Work, Calendar, and other sidebar modules and confirm they have no task quick-edit controls.
10. Sign in as a Supervisor and confirm the Tasks table is read-only.
