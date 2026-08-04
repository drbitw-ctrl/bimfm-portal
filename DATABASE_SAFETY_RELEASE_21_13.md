# Database Safety — Release 21.13

Release 21.13 is a presentation and dashboard-grouping hotfix.

## Schema impact

- No Alembic migration
- No new table
- No new column
- No new index
- No data backfill

## Data impact

Deployment does not modify:

- Freelancer profiles or accounts
- Project assignments
- Task statuses, progress, deadlines, or Quality Scores
- Work Order sessions or Daily Task reports
- Attendance records
- Leave or overtime records
- DTR, Finance, or payroll records
- Passwords or permissions

## Runtime behavior

The Dashboard reads the same current task and Work Order records. The update changes only how active members are grouped for display:

- Non-overdue members with a live Work Order remain visible in Assigned members with a blue Working Now card.
- Overdue members remain in the red Overdue responsibility section.

No production records are rewritten.
