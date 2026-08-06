# Database safety

Release 21.21.8 is code-only.

- No new migration
- No schema alteration
- No table or column deletion
- No bulk update or backfill
- Existing task, attendance, payroll, OT, DTR, project, and user records are untouched

The task-supervisor helper only finds or creates one deterministic `Freelancer` task identity when the administrator explicitly enables task assignment. The transaction rolls back on an exception.
