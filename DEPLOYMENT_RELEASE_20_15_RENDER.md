# BIMFM Portal Release 20.15 — Render Deployment Guide

## Before deployment

1. Confirm that the current production PostgreSQL backup is available.
2. Keep all existing Render environment variables and secrets.
3. Keep the existing Render Web Service and PostgreSQL database.
4. Do not upload local `.env` or database files.

## Deploy through the existing GitHub repository

Extract this package into the local folder connected to the existing BIMFM Portal
repository, then review the changes:

```powershell
git status
git diff
```

Commit and push:

```powershell
git add .
git commit -m "Release 20.15 inline task editing"
git push
```

When Render Auto-Deploy is enabled, the existing service will deploy the commit.
The included build and start commands remain unchanged.

## Post-deployment acceptance check

1. Sign in with an Administrator account.
2. Open **Tasks**.
3. Confirm that each editable task row shows inline controls.
4. Change Status, Priority, Discipline, Progress, and Quality values.
5. Confirm that each row changes from **Saving…** to **Saved**.
6. Change a Start Date or Deadline and confirm it persists after refresh.
7. Change a task title, press Enter, and confirm it persists after refresh.
8. Open **Details** and confirm the same saved values appear in the full form.
9. Sign in with a Supervisor account and confirm that the task list remains
   read-only without inline controls.
10. Review the audit log for `INLINE_UPDATE_PORTAL_TASK` entries.

## Rollback

Redeploy the previous known-good Git commit. This release has no schema change,
so an application rollback does not require a database downgrade.
