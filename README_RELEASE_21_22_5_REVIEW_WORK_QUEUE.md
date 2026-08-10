# Release 21.22.5 — Review Work Queue

Adds a separate Administrator/Supervisor review workflow for tasks in IN_PROGRESS or FOR_REVIEW.

- Freelancer task assignment, status, progress, and production Work Orders are not changed by review assignment.
- Administrators can assign review work to active Administrator or Supervisor accounts.
- Assigned reviewers can start/stop a Review Work Order against the same task.
- Review time is stored separately from freelancer Daily Task/DTR production time.
- Dashboard gains a compact Review Queue card and active review indicator.
- Review sessions are excluded from the freelancer Live Work Orders board.
- No new database migration, table, or column.

Implementation note: this release intentionally reuses existing PortalTaskUpdate and TaskWorkSession records, marked with review-only prefixes, because production currently has no verified database backup.
