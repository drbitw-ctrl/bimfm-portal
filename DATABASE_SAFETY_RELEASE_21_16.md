# Database Safety — Release 21.16

## Migration

- **Revision:** `20260804_0015`
- **Previous revision:** `20260804_0014`
- **Purpose:** Add Project Category and align Gab's July 2026 compensatory-credit data with hourly Finance calculations.

## Schema change

One nullable column is added:

```text
portal_projects.project_category VARCHAR(100) NULL
```

The column is optional. Existing project records remain valid when no category is assigned.

## Controlled data updates

The migration may perform these limited updates:

1. Fill a blank Project Category when the existing project name clearly identifies 安居, MRT/捷運, or Bridge/橋.
2. Align Gab's supervisor-confirmed July opening overtime credit to 15 hours without duplicating genuine positive approved-overtime transactions.
3. Apply up to 15 credit hours to Gab's July 1, 2, 3, and 6 approved leave records, minute-for-minute.
4. Delete Gab's non-finalized July DTR and dependent snapshot rows so the DTR can be regenerated correctly.
5. Add a system audit record describing the correction.

## Records not rewritten

The migration does not automatically modify unrelated:

- Attendance punches
- Task progress, status, completion, or Quality Scores
- Project names or internal project identifiers
- Task and project assignments
- Other freelancers' overtime-credit ledgers
- Other freelancers' leave records
- Finalized DTRs
- Work Order sessions or Daily Task Reports
- User accounts, passwords, or permissions
- Salary amounts or payroll payments

## Finalized DTR protection

A finalized July 2026 DTR is never deleted by the migration. If management needs to recalculate a finalized record, use the normal controlled reopening/unlocking procedure and regenerate it after deployment.

## Backup recommendation

Before deployment, confirm that the Render database has a current backup or recovery option. Do not create a new database or change `DATABASE_URL` for this release.

## Rollback note

Downgrading removes the `project_category` column. Data corrections to genuine HR records should not be reversed automatically. Restore a verified database backup when a complete production rollback is required.
