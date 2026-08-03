# BIMFM Portal Release 21.09

## Purpose

Release 21.09 is a cumulative dashboard and data-backfill update based on Release 21.08.

It removes the empty Working Now group card from the upper Live Team Availability board, applies the supplied task Start Dates to tasks that are still missing them, derives missing project Start Dates, and confirms the corrected July 2026 leave records.

## Dashboard cleanup

The upper Live Team Availability board now contains only:

- Available now
- Assigned — no active timer
- Overdue responsibility

The empty Working Now card has been removed from this upper board.

The following live-work functions remain available:

- Working Now summary counter
- Live Team Availability legend
- Separate Live Work Orders panel
- Real-time timer monitoring

## Start Date backfill

The supplied All Tasks workbook contains 225 valid task Start Dates.

During deployment, Release 21.09:

1. Matches the workbook records by portal Task ID.
2. Fills a task Start Date only when that task currently has no Start Date.
3. Never overwrites an existing task Start Date.
4. Fills a project Start Date only when the project currently has no Start Date.
5. Derives the project Start Date from the earliest dated task belonging to that project.

## July 2026 attendance correction

Confirmed records:

- Carlo Ninoy Nilo: no July leave
- Gabrielle Gameng: approved leave on July 1, 2, 3, and 6, 2026

The migration removes Carlo's July 27 leave when present and ensures Gab's four approved leave records exist.

The supplied July attendance workbook contains no Time In or Time Out values. Release 21.09 therefore does not invent or insert attendance punches. Only the confirmed leave information is written to the portal. Non-finalized July DTR snapshots for Carlo and Gab are invalidated so they can be regenerated.

## Database impact

Release 21.09 adds Alembic revision:

`20260803_0012`

No new tables, columns, or indexes are created.

The migration performs controlled data updates only:

- Missing task Start Dates from the supplied workbook
- Missing project Start Dates derived from task data
- Gab's confirmed July leave
- Removal of Carlo's incorrect July 27 leave
- Audit-log entry

Existing Start Dates, finalized DTRs, attendance punches, task progress, Quality Scores, assignments, Work Orders, passwords, and payroll records are not overwritten.

## Version

`3.0.9-release21.09-dashboard-data-backfill`
