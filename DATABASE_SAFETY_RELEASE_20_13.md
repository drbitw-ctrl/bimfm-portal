# Database Safety — Release 20.13

Release 20.13 does not connect to or directly modify the user's live Render
PostgreSQL database while the package is being prepared.

During deployment, the existing Render build command runs:

```text
alembic upgrade head
```

The new revision `20260801_0006` performs a narrow historical Quality Score
backfill.

## It may update

Only:

```text
portal_tasks.quality_score
```

and only when all of these are true:

1. The current value is null.
2. The same task description contains `Legacy quality score:`.
3. The preserved value is a whole number from 1 to 100.

## It does not modify

- Existing non-null Quality Scores
- Project names or project engineers
- Project members or HR mappings
- Task assignments
- Attendance or DTR records
- Leave or overtime records
- Compensatory-credit records
- Finance data
- Staff or freelancer accounts

No table or column is added, removed, renamed, or dropped.

Create or confirm a current PostgreSQL backup before deployment because the
portal contains business-critical HR and task data.
