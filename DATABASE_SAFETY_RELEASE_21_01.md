# Database Safety — Release 21.01

Release 21.01 is an application hotfix for the Version 21.00 Work Order page.

## Schema impact

```text
New tables: None
New columns: None
New indexes: None
New Alembic revision: None
Data backfill: None
```

The existing Version 21.00 revision `20260802_0008` remains the latest schema
revision and continues to provide `task_work_sessions` and `task_reminders`.

## Data writes

Opening Work Orders performs read-only queries. Starting and stopping work use
the existing Version 21.00 transaction logic.

Stopping a valid timer creates or updates only:

- One `task_work_sessions` record
- One linked `daily_tasks` record
- The related audit record
- Existing DTR/task-review invalidation state for the affected month

If the save fails, Release 21.01 rolls the transaction back before showing the
freelancer an error message.

## Preserved records

Release deployment does not rewrite or delete:

- Projects and portal tasks
- Task assignments
- Existing work sessions
- Existing Daily Task records
- Attendance, DTR, leave, overtime, and payroll records
- Freelancer or staff accounts
- Reminders or HR policy data
