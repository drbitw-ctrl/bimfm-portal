# Database Safety — Release 20.22

## Schema impact

```text
New tables: None
New columns: None
New indexes: None
New Alembic migration: None
```

## Read operations

The new page reads:

- `portal_projects`
- `portal_tasks`
- `portal_task_assignments`
- `project_members`
- `freelancers`
- `daily_tasks`
- `work_schedules`
- `holidays`

## Write operations

The Task Time Utilization page performs no business-data writes.

Tasks-page row highlighting is presentation-only. Existing inline task editing
continues to use the established quick-edit endpoint and audit logging.

## Preserved data

Release 20.22 does not rewrite or backfill:

- Projects
- Tasks
- Assignments
- Daily Task reports
- Attendance or DTR
- Leave or overtime
- Finance records
- Quality Scores
- HR policies

## Reporting limitation

Task-level actual time requires a Daily Task record linked through
`portal_task_id`. Unlinked entries are displayed at project level when their
project code or name can be matched. Unmatched entries remain explicitly
reported instead of being guessed or silently allocated.
