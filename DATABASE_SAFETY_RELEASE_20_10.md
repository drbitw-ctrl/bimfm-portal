# Database Safety Statement — Release 20.10

Release 20.10 is an interface and application-workflow release.

## Schema changes

```text
New Alembic migration: No
New database table: No
New database column: No
Automatic backfill: No
SQLite migration rerun: No
Member repair rerun: No
```

The current Alembic head remains:

```text
20260801_0003_project_member_directory
```

Running the normal Render build command remains safe:

```text
pip install -r requirements.txt && alembic upgrade head
```

Alembic should confirm that the existing PostgreSQL database is already current.

## Preserved data

The release does not automatically modify or remove existing records in:

```text
project_member_directory
portal_projects
portal_project_members
portal_tasks
portal_task_assignments
freelancers
freelancer_accounts
attendance_events
daily_attendance
monthly_dtr
leave_requests
overtime_claims
comp_leave_transactions
hr_admin_accounts
audit_log
```

The previous local project-member repair must not be rerun solely for this release.

## New Task writes

The New Task form writes only after an authorized Administrator or Supervisor submits it. Depending on the form selection, it may create:

- One new `portal_projects` row
- One new `portal_tasks` row
- One `portal_project_members` relationship when needed
- One `portal_task_assignments` row when a member is assigned
- One audit-log entry

It does not rewrite a Project Member mapping. Assignments use the member’s preserved source assignment identity so mapped and unmapped member behavior remains compatible with Release 20.8.

## Recommended deployment protection

Before deployment, retain a current PostgreSQL backup. After deployment, verify:

1. Project Members and HR mappings
2. Existing projects and assignments
3. Freelancer account access
4. Attendance and DTR history
5. Leave, overtime, compensatory-credit, and Finance records
6. Creation of one noncritical test task
