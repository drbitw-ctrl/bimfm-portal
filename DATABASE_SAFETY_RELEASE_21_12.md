# Database Safety — Release 21.12

## Schema impact

Release 21.12 has no database schema migration.

- New tables: None
- New columns: None
- New indexes: None
- Data backfill: None
- Existing records rewritten: No

The current Alembic head remains `20260803_0013`.

## New record behavior

For a normal freelancer-initiated Work Order stop:

- A Daily Task Report is required.
- The activity report is stored in `daily_tasks.accomplishment`.
- The same report is retained in `task_work_sessions.notes`.
- The Daily Task date uses the freelancer-local date on which the Work Order started.
- Time spent continues to be calculated by the server and recorded in minutes.

Official project-task progress remains unchanged by the Work Order submission.

## Existing records

The deployment does not modify existing:

- Work Order sessions
- Daily Task records
- DTR records
- Attendance records
- Tasks or projects
- Progress or Quality Scores
- Accounts or passwords
- Leave or overtime records
- Payroll records

## Operational safeguard

Administrator-controlled timer safeguards continue to operate without requiring freelancer input. Their behavior is unchanged by this release.
