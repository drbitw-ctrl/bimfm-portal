# Release 21.05 Database Safety

Release 21.05 is an interface and reporting-presentation update.

## Schema impact

```text
New tables: None
New columns: None
New indexes: None
New Alembic migration: None
Current Alembic head: 20260802_0009
```

## Data impact

Deployment does not automatically rewrite:

- Projects or tasks
- Task deadlines or completion dates
- Quality Scores
- Work Order sessions
- Daily Task records
- Attendance
- Holidays or leave
- DTR records
- Finance and payroll records
- Accounts or passwords
- HR policies

The reminder calendar reads existing task deadlines and active HR holiday records.
Task Time Utilization continues to calculate summaries from existing task and
Daily Task data.

## Rollback

Because this release has no schema migration, application rollback can be done by
redeploying the previous known-good Git commit. Do not replace or delete the
production database during rollback.
