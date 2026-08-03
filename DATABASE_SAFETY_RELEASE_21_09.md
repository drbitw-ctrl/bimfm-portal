# Database Safety — Release 21.09

## Migration

Revision: `20260803_0012`

Revises: `20260803_0011`

## Schema changes

None.

Release 21.09 creates no tables, columns, indexes, constraints, or relationships.

## Task Start Dates

The migration contains 225 valid Task ID and Start Date pairs from the supplied Excel workbook.

A task is updated only when:

- The Task ID exists in the portal; and
- The current task Start Date is NULL.

Existing task Start Dates are never overwritten.

## Project Start Dates

A project is updated only when its current Start Date is NULL.

The value is calculated from the earliest non-null Start Date among the project's tasks.

## July leave correction

The migration:

- Deletes Carlo Ninoy Nilo's July 27, 2026 leave record and request when present.
- Ensures Gabrielle Gameng has approved leave records on July 1, 2, 3, and 6, 2026.
- Invalidates only non-finalized July 2026 DTR snapshots for Carlo and Gab.

Finalized DTR records are not deleted.

## Attendance punches

The supplied attendance workbook contains no Time In or Time Out values.

The migration does not create attendance events or Daily Attendance punches and does not estimate historical working times.

## Rollback

The downgrade does not erase Start Dates or recreate the incorrect Carlo leave record. These are controlled business-data corrections and are intentionally preserved.

## Recommended protection

Confirm that a current PostgreSQL backup exists before deploying any data migration.
