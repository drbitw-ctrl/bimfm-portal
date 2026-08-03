# Database Safety — Release 21.10

## Migration

`20260803_0013_july_standard_attendance.py`

## Approved write scope

The migration may create or complete July 2026 weekday attendance records for six active freelancers using the supervisor-approved 09:00–18:00 schedule and 60-minute break.

## Safeguards

- Existing actual Time In or Time Out values are preserved.
- Weekends are skipped.
- Active HR Calendar holidays are skipped.
- Approved leave dates are skipped.
- Gabrielle Gameng's July 1–3 and July 6 leave records are preserved.
- Carlo Ninoy Nilo's incorrect July 27 leave is removed when present.
- Raymond Navarro is excluded because the profile/account is inactive.
- Finalized DTRs are not deleted or changed.
- Only non-finalized July DTR snapshots are invalidated for regeneration.
- A system audit entry records the import totals.

## Schema impact

- New tables: None
- New columns: None
- New indexes: None
- Alembic head after deployment: `20260803_0013`

A current PostgreSQL backup remains recommended before every deployment that includes historical data backfill.
