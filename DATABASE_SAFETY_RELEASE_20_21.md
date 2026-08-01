# Database Safety — Release 20.21

## Migration

Release 20.21 adds one nullable-safe, server-defaulted Boolean column:

```text
hr_policies.show_project_engineer_to_freelancers
```

The default is `false`, so Project Engineer names remain hidden from
freelancers immediately after deployment.

Expected Alembic transition:

```text
20260801_0006 -> 20260802_0007
```

## Data preserved

The migration does not delete, rewrite, or backfill:

- Projects
- Project Engineer names
- Tasks
- Task assignments
- Project-member mappings
- Freelancer accounts
- Attendance
- Daily tasks
- DTR records
- Leave
- Overtime
- Compensatory-credit ledgers
- Finance records
- Quality Scores

## Deployment safety

Before deployment:

1. Confirm a current PostgreSQL backup exists.
2. Preserve all existing Render environment variables.
3. Continue using the existing PostgreSQL database.
4. Do not upload `.env` or local database files.

The build command should continue running:

```text
pip install -r requirements.txt && alembic upgrade head
```

## Rollback

Application rollback is safe, but the new Boolean column may remain in the
database. Older application releases ignore the extra column.

Do not delete or replace the production PostgreSQL database during rollback.
