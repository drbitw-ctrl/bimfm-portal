# Release 20.7 Database Safety Statement

## Live environment access

No build, test, packaging, or inspection command used to create Release 20.7
connected to the user's live Render PostgreSQL database.

## Existing data

Release 20.7 does not intentionally delete, truncate, replace, or re-import:

- Administrator or freelancer accounts
- Members
- Projects
- Project memberships
- Tasks or task assignments
- Attendance events or daily attendance
- Daily task reports
- Monthly DTR records
- Leave records
- Overtime claims
- Compensatory-credit ledger entries
- Finance records

## Schema change

Alembic revision `20260801_0002` adds one nullable relationship:

```text
daily_tasks.portal_task_id → portal_tasks.id
```

The field is indexed and uses `ON DELETE SET NULL`.

The previous nullable `daily_tasks.synced_project_task_id` field remains for
historical compatibility.

## Legacy synchronization tables

The following tables are retained but are no longer the current project source:

```text
project_source_members
project_sync_runs
synced_project_tasks
```

Release 20.7 does not erase them. Primary project pages read the PostgreSQL-native
portal tables instead.

## Migration validation

The migration was tested against:

1. An existing Release 20.6 schema stamped at `20260731_0001`.
2. A completely fresh Release 20.7 schema.

Both completed at Alembic revision `20260801_0002` with the new column, foreign
key, and index present.
