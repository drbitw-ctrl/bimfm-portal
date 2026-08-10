# BIM Portal Release 21.22.9

## Review Work + Staff Work Order Stabilization

Release 21.22.9 is a cumulative application release built from 21.22.8. It does not introduce an Alembic migration or database schema change.

### Dashboard availability layout

The Availability and Current Assignments board retains the existing card design, status colors, task details, progress, deadlines, attendance details, light theme, and dark theme. Member cards now wrap into a responsive grid instead of requiring horizontal scrolling.

- Wide displays: up to 4 cards per row.
- Medium displays: 3 cards per row.
- Narrow displays: 2 cards per row.
- Mobile: 1 card per row.

This naturally creates two or three rows when more members are present.

### Review Queue production repair

The Render traceback for 21.22.8 showed that the review timer was already active, then `/admin/review-queue` failed while rendering the active timer because `format_local_datetime` was not present in that template context. Release 21.22.9 removes that undefined template helper dependency.

The review lifecycle was regression-tested end to end:

1. Review Queue loads.
2. Administrator starts assigned review work.
3. Review Queue reloads successfully while the timer is active.
4. Review timer stops and review time is retained.
5. Freelancer task assignment, status, and progress remain independent.

### Administrator / Supervisor My Work

My Work now contains two distinct staff work areas:

#### My Assigned Tasks

Shows tasks assigned directly to the staff task profile (TS-*). Staff can start and stop a normal Work Order directly from My Work. Stopping requires a work-activity description and creates the same timed-work record used by normal project task time reporting.

#### My Review Work

Shows review assignments separately. Review work has its own Start Review / Stop Review controls directly on My Work. Review timers remain separate from normal task Work Orders and from freelancer production task assignment.

Only one timer can run for a staff member at a time. A normal staff Work Order blocks review timing, and a review timer blocks a normal staff Work Order.

### Preserved from 21.22.8

- Administrator task/review identities remain excluded from DTR generation.
- Sidebar clearly distinguishes Daily Task Reports (Work Activities) from Daily Time Record (DTR).
- Duplicate visible staff shadow identities remain deduplicated in user-facing staff/task selectors without deleting database records.
- No freelancer task is reassigned by review work.

## Database safety

No new table, column, migration, backfill, deletion, or schema mutation is included.
