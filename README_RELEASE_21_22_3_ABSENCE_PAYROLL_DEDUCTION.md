# BIM Portal Release 21.22.3 — Absence Payroll Deduction

## Purpose

Release 21.22.3 keeps the existing monthly payroll calculation and adds one missing rule: a scheduled workday classified as `ABSENT` now reduces salary coverage in the same payroll percentage calculation as uncovered unpaid leave.

## Rule

- Approved leave continues to be reduced by available compensatory/OT credit minute-for-minute.
- Any uncovered approved leave remains an unpaid-leave deduction.
- An `ABSENT` day is converted to one configured standard workday of deduction time.
- Compensatory/OT credit does **not** cancel or offset an `ABSENT` day.
- Salary coverage is therefore:

  `monthly salary-basis minutes - uncovered unpaid-leave minutes - absence minutes`

The existing calendar-day monthly salary basis and standard-day duration are unchanged.

## User interface

Finance Center and Monthly DTR now show absence separately from uncovered unpaid leave, plus the combined total deduction and resulting salary-coverage percentage.

## Database safety

No schema migration, table creation, column creation, backfill, deletion, or historical record rewrite is included. Existing DTR `absent_days` values are read by the new calculation.
