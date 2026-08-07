# BIM Portal Release 21.22 — Task-Hourly Member Mode

## Scope

Release 21.22 adds a code-only Task-Hourly work mode for Belinda (`LEGACY-00008`, legacy identity `IDN-001`) and recolors the existing freelancer attendance actions.

### Belinda task-hourly mode

- Attendance Time In / Time Out is not required.
- The attendance landing page explains that Work Orders are the official time source.
- Direct Time In / Time Out POST requests are rejected safely for the task-hourly member.
- Previous attendance correction requests are not offered for the task-hourly member.
- Only verified, stopped Work Orders count in the monthly task-hour register.
- Active or missed-stop flagged sessions do not count until resolved.
- Cross-midnight sessions are split across calendar days in the member timezone.
- Exact elapsed time is shown as hours, minutes, and seconds.
- Project, task, discipline, activity/description, start time, stop time, and exact elapsed time are shown.
- The monthly DTR for Belinda renders as a task-hour tabulation instead of an attendance-punch DTR.
- No hourly rate or pay amount is displayed or calculated by this feature.

### Standard freelancer attendance colors

The existing layout is retained:

- Time In = green
- Time Out = red
- Disabled controls remain visually muted.

## Database impact

None.

- No Alembic migration
- No new table
- No new column
- No backfill
- No deletion or rewrite of historical records

The special member mode is identified in application code by the stable freelancer code `LEGACY-00008` with a name fallback for Belinda. This is intentional while the production database has no verified restorable backup.
