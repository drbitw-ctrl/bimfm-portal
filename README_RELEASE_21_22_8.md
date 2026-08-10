# BIM Portal Release 21.22.8

## Review queue + dashboard stabilization

This release is based on the stable Release 21.22.6 baseline. Release 21.22.7 does not need to be deployed first.

### Review work
- Review assignments remain separate from freelancer task assignments.
- Review timers never change freelancer task status, progress, assignee, production Work Orders, or Daily Task Reports.
- Administrators and Supervisors can receive review work for tasks in `IN_PROGRESS` or `FOR_REVIEW`.
- Starting review work automatically creates/reuses the deterministic internal `TS-<staff id>` timer identity when needed. A separate "Enable Task Assignment" step is no longer required for review work.
- Review Queue now shows both Task Status and Review Status (`ASSIGNED`, `REVIEWING`, `REVIEWED`, `UNASSIGNED`).
- Review Queue, Start Review, Stop Review, and the dashboard are hardened so review-data problems do not take down the full Administration workspace.
- Duplicate visible Admin/Supervisor names in the reviewer picker are collapsed without deleting any account.

### My Work
- Administrator and Supervisor My Work includes My Review Work, assigned review tasks, review status, accumulated review time, and active review timer state.

### Dashboard layout
- Existing color palette, status colors, light/dark themes, card design, task information, progress, deadlines, attendance indicators, and Work Order states are retained.
- Available Now, Assigned Members, and Overdue Responsibility are arranged as horizontal lanes.
- Every member still uses the full detail card. Long categories scroll horizontally instead of making the dashboard excessively tall.

### DTR terminology and eligibility
- Sidebar now distinguishes:
  - `Daily Task Reports (Work Activities)`
  - `Daily Time Record (DTR)`
- Administrator/Supervisor internal `TS-*` task/review identities are excluded from Daily Time Record generation.
- Existing TS-* DTR rows are not deleted or rewritten; they are simply excluded from normal DTR generation/listing.

### Duplicate staff task identities
- UI-level duplicate historical `LEGACY-*`/`TS-*` shadows with the same staff name are collapsed in team/task assignment views.
- No database rows are deleted or merged.

## Database safety
There is no new Alembic migration, table, column, schema operation, or automatic data backfill in Release 21.22.8.
