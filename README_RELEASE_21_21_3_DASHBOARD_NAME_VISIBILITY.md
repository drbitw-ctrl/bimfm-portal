# BIM Portal Release 21.21.3 — Dashboard Member Name Visibility

Release 21.21.3 adds a presentation-friendly member-name visibility control to the Administration Dashboard.

## Default behavior

Member names are shown whenever the Dashboard is freshly loaded. The control does not permanently save a hidden state and does not alter accounts, profiles, projects, tasks, attendance, reports, exports, or database values.

## Hide names

The new `Hide member names` control appears beside the Team Availability legend. When activated, visible names and avatar initials are replaced with a neutral `Member` label while workload, attendance state, project assignments, tasks, progress, deadlines, and operational status remain visible.

Selecting `Show member names` restores the names immediately. Refreshing or reopening the page also restores the default visible state.

## Scope

The control affects the Administration Dashboard member displays, including:

- Availability and current assignments
- Live Work Orders
- Today's workforce table

It does not change Excel exports, reports, APIs, database records, or other portal pages.

## Localization

The control and hidden label are available in English and Traditional Chinese.

## Database impact

- New tables: none
- New columns: none
- Alembic migration: none
- Data backfill: none
