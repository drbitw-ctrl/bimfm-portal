# Database Safety — Release 21.08

## Migration

- Revision: `20260803_0011`
- Previous revision: `20260803_0010`
- Schema changes: none
- Data changes: targeted leave and task-date corrections only

## Targeted changes

1. Remove any Carlo Ninoy Nilo leave request and approved leave record dated 2026-07-27.
2. Insert missing approved whole-day leave records for Gabrielle Gameng on 2026-07-01, 2026-07-02, 2026-07-03, and 2026-07-06.
3. Delete only non-finalized July 2026 DTR snapshots for Carlo and Gabrielle so corrected DTRs can be regenerated.
4. Set Start Dates for task IDs 233–237 only when the current Start Date is NULL.

## Preserved data

The migration does not change:

- actual attendance punches;
- finalized DTR snapshots;
- other leave dates;
- overtime, payroll, or compensatory-leave transactions;
- task deadlines, completion dates, progress, or Quality Scores;
- project names or internal project identifiers;
- assignments, Work Orders, accounts, or passwords.

## Operational warning

The supplied July attendance workbook contains no Time In/Time Out values. Full July attendance cannot be safely imported from it. Do not invent historical punch times. Complete the workbook with the actual records before a full attendance import.

Confirm that a current managed-database backup exists before deployment.
