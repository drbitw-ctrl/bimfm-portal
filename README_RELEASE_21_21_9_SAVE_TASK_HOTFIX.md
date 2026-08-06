# BIM Portal Release 21.21.9

## Save Task hotfix

This release fixes the Internal Server Error raised when saving a new task.

Root cause:

- The create-task route referenced `completion_notifications` in the audit details before the variable had been initialized.

Fix:

- Initialize `completion_notifications = 0` before audit logging.
- If a newly created task is already marked Completed, create completion notifications safely.
- Preserve the Release 21.21.8 task-creation and administrator-assignment fixes.

## Database safety

This is a code-only release.

- No Alembic migration
- No new tables
- No new columns
- No data rewrite
- No backfill
- No deletion

Existing production data is not modified by deployment.
