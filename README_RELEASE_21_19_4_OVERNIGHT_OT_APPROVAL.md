# BIMFM Portal Release 21.19.4

## Overnight overtime final approval fix

This hotfix corrects final OT approval when an evening OT period ends after midnight.

Example:

- Planned OT start: 6:00 PM on August 4
- Planned OT end: 11:00 PM on August 4
- Verified actual end: 2:30 AM on August 5

The time-only value `02:30` is now interpreted as the following calendar day when using the attendance date would place it before the planned OT start.

The verified duration in the example is 510 minutes (8 hours 30 minutes).

Same-day end times remain unchanged. For example, 6:00 PM to 11:00 PM remains 300 minutes on the same date.

## Scope

Changed application file:

- `app/services/overtime_service.py`

Added regression tests:

- `tests/test_release_21_19_4_overnight_ot_approval.py`

No database migration, schema change, or data backfill is included.
