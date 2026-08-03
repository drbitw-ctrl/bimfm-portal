# Database Safety — Release 21.07

## Migration

Release 21.07 adds Alembic revision `20260803_0010`.

Schema change:

- Adds nullable column `freelancers.join_date`.

Data backfill:

- Sets the confirmed Join Date for seven named freelancer profiles when their existing Join Date is blank.
- Sets Raymond Navarro's freelancer profile and freelancer login account to inactive.

## Records not rewritten

The migration does not rewrite:

- Projects
- Tasks or assignments
- Progress or Quality Scores
- Attendance events or daily attendance
- Work Order sessions or Daily Tasks
- DTR details
- Leave or overtime records
- Payroll or Finance summaries
- Password hashes
- Other account roles or active states

## Export behavior

Excel generation is read-only. It queries portal data and creates a temporary in-memory workbook for download. Export actions are written to the audit log.

No exported workbook is stored in PostgreSQL by the application.

## Recommended deployment procedure

1. Confirm the latest PostgreSQL backup or Render recovery point.
2. Deploy through the normal Render build command.
3. Verify migration `20260803_0010` completes.
4. Confirm the seven Join Dates under Freelancer Accounts.
5. Confirm Raymond Navarro is inactive.
6. Test one small Excel export before downloading the complete package.

## Rollback note

Application rollback is possible through Render. A database downgrade removes the Join Date column but does not automatically reactivate Raymond because automatically reactivating an account could be unsafe. An Administrator can reactivate the profile manually when authorized.
