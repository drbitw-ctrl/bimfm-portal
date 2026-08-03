# BIMFM Portal Release 21.10
## July Attendance Backfill and Monthly Search Hotfix

Release 21.10 is a focused data and reliability update based on the supervisor-approved July 2026 attendance rule.

## Monthly Attendance Search

The Monthly Attendance filter no longer sends an empty freelancer value into an integer-only request field. This was the cause of the error when **All Freelancers** was selected.

The Search button now supports:

- All Freelancers
- A selected freelancer
- A valid month
- Safe redirection when an invalid freelancer value is received

## July 2026 Attendance

The migration creates missing weekday attendance records for the active approved roster using:

- Time In: 09:00
- Time Out: 18:00
- Break: 60 minutes
- Rendered time: 8 hours
- Late: 0 minutes
- Undertime: 0 minutes
- Potential overtime: 0 minutes

Included active members:

- Alexsandria Santos
- Carlo Ninoy Nilo
- Gabrielle Gameng
- Jonica Jomadiao
- Kaizer Macatiag
- Lander Samson

Raymond Navarro is excluded because the account is inactive.

## Gabrielle Gameng Leave

No attendance punch is created for Gabrielle Gameng on:

- July 1, 2026
- July 2, 2026
- July 3, 2026
- July 6, 2026

The approved leave records remain the source of truth for those dates.

Carlo Ninoy Nilo has no July leave. Any incorrect July 27 leave record is removed.

## Data Protection

The migration fills only missing attendance records or records where both Time In and Time Out are empty. Existing actual historical punches are not overwritten.

Active HR Calendar holidays and weekends are excluded. Non-finalized July DTR snapshots are invalidated so Finance can regenerate them from the corrected attendance and leave data. Finalized DTRs remain untouched.

## Database Revision

- Revision: `20260803_0013`
- Previous revision: `20260803_0012`
- New tables: None
- New columns: None
- New indexes: None
