# Database Safety — Release 20.16

Release 20.16 introduces no schema revision and no automatic data backfill.

## Fields that quick editing may update

Only the selected `portal_tasks` record may have these existing fields changed:

- `status`
- `progress`
- `quality_score`
- `completed_at`

When Status is changed to `UNASSIGNED`, existing rows in `portal_task_assignments` for that task are removed to preserve the established assignment rule.

## Fields not changed by quick editing

The quick-edit endpoint does not accept changes to:

- Project identity or name
- Task title or description
- Priority
- Discipline
- Start date
- Deadline
- Project membership
- Attendance, DTR, leave, overtime, payroll, or Finance data

## Deployment safety

Keep the existing PostgreSQL database and Render environment variables. Create or confirm a current PostgreSQL backup before deployment as normal operational practice.
