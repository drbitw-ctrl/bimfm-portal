# BIMFM Portal Release 21.03 — Database Safety

## Schema impact

```text
New tables: None
New columns: None
New indexes: None
New Alembic migration: None
Current Alembic head: 20260802_0009
```

## Data impact

Deployment does not automatically modify or rewrite:

- Staff or freelancer accounts
- Password hashes or password-change flags
- Projects, tasks, assignments, or member mappings
- Quality Scores
- Work Order sessions or reminders
- Attendance events or Daily Attendance records
- Attendance corrections
- Leave or overtime requests
- Monthly DTRs and DTR details
- Payroll and Finance records
- HR policies

Release 21.03 reads existing records to build role-specific My Work summaries. The only write exposed on Finance My Work is the already-authorized DTR generation operation from Release 21.02, and it occurs only when the Finance user explicitly presses the button.

## Attendance issue presentation

The Administrator My Work page identifies unreviewed attendance records from the previous 31 days when time-in or time-out is missing. This is a read-only summary and does not create, correct, approve, or delete attendance records.

## Deployment behavior

The existing Render build command may continue to run:

```text
alembic upgrade head
```

Because the database is already at `20260802_0009`, Release 21.03 should not display a new migration upgrade line.

## Rollback

Application rollback can be performed by redeploying the previous known-good Git commit. No database downgrade is needed because Release 21.03 adds no schema revision.
