# Release 20.8 Database Safety Statement

## Live database access

The live Render PostgreSQL database was not accessed while preparing Release
20.8.

## Alembic revision

Deployment runs:

```text
20260801_0002 → 20260801_0003
```

The migration creates one additive table:

```text
project_member_directory
```

It then copies member identity and mapping references from records already in
PostgreSQL. It does not remove the source records.

## Records not modified by the migration

The migration does not update or delete rows in:

```text
freelancers
freelancer_accounts
portal_projects
portal_project_members
portal_tasks
portal_task_assignments
attendance_events
daily_attendance
monthly_dtr
leave_requests
overtime_claims
comp_leave_transactions
payroll_month_summaries
```

## Mapping writes after deployment

Using **Save Mapping** updates only the selected row in
`project_member_directory` and adds an audit-log entry. Original project and task
assignment foreign keys are preserved.

## Required precaution

Create or confirm a current PostgreSQL backup before deploying. Do not rerun the
legacy SQLite migration.
