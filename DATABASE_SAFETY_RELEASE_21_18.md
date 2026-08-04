# Database Safety — Release 21.18

Release 21.18 is a reporting and presentation update.

## No schema migration

The Alembic head remains:

```text
20260804_0015
```

The release adds no tables, columns, indexes, constraints, or backfill operations.

## No historical record rewrite

Deployment does not modify or generate:

- Work Orders
- Daily Task entries
- Task Start Dates or Deadlines
- Task assignments
- Project records
- Attendance or DTR records
- Leave or overtime records
- Quality Scores
- Accounts or passwords

## Planned-time fallback

When a scheduled task has no recorded time, the report uses its planned time as the effective utilization time. This value exists only in the generated report and Excel export. It is not saved to PostgreSQL or SQLite.

A fallback task is clearly labelled so management can distinguish it from genuine Work Order or Daily Task time.
