# BIMFM Portal Release 21.05

**Application version:** `3.0.5-release21.05-calendar-utilization-dashboard`  
**Release type:** Dashboard, reporting presentation, and calendar interface update  
**Source base:** Release 21.04 Revision 2

## Purpose

Release 21.05 improves the operational information hierarchy and makes schedule
information easier to understand at a glance. It places Team Availability before
Live Work Orders on the Dashboard, simplifies Quality Score wording, adds a
project-level time-consumption overview, and replaces the former deadline table
with a modern reminder calendar containing task deadlines and company holidays.

## Dashboard order

The Dashboard now presents:

1. Live Team Availability
2. Live Work Orders
3. Attendance and secondary operational panels

No workload, availability, or Work Order logic was changed. Only the visual order
was updated.

## Quality Score presentation

Performance pages now use the simple wording **Quality Score as calculated**.
The visible explanation about a management reporting scale and preserved original
ratings has been removed from the Performance and Project Reports interfaces.

The existing reporting calculation remains unchanged, and no stored task rating
is rewritten by deployment.

## Task Time Utilization

The page now includes a **Total time used by project** overview before the detailed
task tables.

Each project card shows:

- Rank by actual time used
- Total actual project time
- Share of all recorded project time
- Relative visual time bar
- Target time
- Active-task count

The top summary also identifies the project with the most recorded time. Detailed
project and task calculations remain available below the quick overview.

## Reminder Calendar

The former Calendar task table is replaced by a Monday-first reminder board.

The calendar combines:

- Task deadlines
- Company holidays maintained in HR Calendar
- Overdue deadline warnings
- For-review deadlines
- Completed deadlines

Color meanings:

- Blue: task deadline
- Yellow: completed for review
- Red: overdue deadline
- Green: completed deadline
- Purple: company holiday
- Orange: urgent deadline

The board includes month navigation, a Today shortcut, monthly summary metrics,
date-level event indicators, and an upcoming reminder agenda.

## HR Calendar

The HR Calendar now displays the same reminder board above its holiday and leave
management tools. Holiday creation, leave creation, month locking, and existing
record tables remain available.

## Database compatibility

Release 21.05 introduces:

- No new table
- No new column
- No new index
- No Alembic migration
- No data backfill

The current Alembic head remains `20260802_0009`.

## Validation

Release 21.05 passed:

- Python source compilation
- Application import
- JavaScript syntax checks
- 48 Jinja template parses
- 1,812 English localization keys
- 1,812 Traditional Chinese localization keys
- Localization catalog parity
- 172 focused assertions covering calendar and time-utilization behavior
- Dashboard section-order verification
- Quality wording verification
- Reminder Calendar cancelled-task exclusion
- ZIP integrity verification

All data tests used an isolated in-memory database. Production data was not
modified.
