# Database Safety — Release 21.19

Release 21.19 is a reporting-interface correction.

## No schema migration

The Alembic head remains:

```text
20260804_0015
```

The release adds no tables, columns, indexes, constraints, or data backfills.

## No record changes

Deployment does not modify:

- Projects or tasks
- Work Orders or Daily Task entries
- Task Start Dates or Deadlines
- Attendance or DTR records
- Leave or overtime records
- Finance calculations or salaries
- Quality Scores
- Accounts or passwords

The update only changes which metric is presented graphically on the Task Time Utilization page. Existing utilization calculations remain report-time calculations and are not stored as new database values.
