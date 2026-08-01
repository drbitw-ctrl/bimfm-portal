# Database Safety — Release 20.11

Release 20.11 is designed for the existing populated Render PostgreSQL
database.

## Additive migration

The release runs:

```text
20260801_0003 -> 20260801_0004
```

It adds only:

```text
portal_projects.project_engineer VARCHAR(200) NULL
```

The field is nullable so existing project rows remain valid.

## Conservative backfill

For a project with no Project Engineer value, the migration may copy an
engineer name from an existing imported task-description line beginning with:

```text
Legacy engineer:
```

This backfill does not remove the original task row and does not alter project,
task, or member assignments.

## Data not modified or deleted

The migration does not delete, recreate, or re-import:

- PostgreSQL projects and tasks
- Project-member directory records
- Project memberships and task assignments
- Member mappings
- HR freelancer profiles and accounts
- Administrator accounts
- Attendance and correction records
- DTR records and daily tasks
- Leave requests and balances
- Overtime and compensatory-credit records
- Finance records
- Audit history

## Important deployment rule

Keep the existing populated `DATABASE_URL`. Do not select an empty PostgreSQL
database and do not rerun the original SQLite migration or the member repair
utility.

A PostgreSQL backup should still be confirmed before deployment because the
portal contains operational HR and Finance data.
