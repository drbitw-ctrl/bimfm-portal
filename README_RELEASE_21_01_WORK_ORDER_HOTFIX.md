# BIMFM Portal Release 21.01

**Application version:** `3.0.1-release21.01-work-order-hotfix`  
**Release type:** Production hotfix for Version 21.00 Work Orders

## Purpose

Release 21.01 fixes the Internal Server Error that could occur when a freelancer
opened Work Orders from Assigned Projects or loaded `/tasks` on PostgreSQL.

## Root cause

Version 21.00 filtered today's work sessions with a database expression that
compared a PostgreSQL `DATE` result to an ISO-formatted text value. SQLite
accepted that comparison during isolated testing, while PostgreSQL can reject it
because the operands have different database types.

Release 21.01 removes the database-specific date comparison. Recent work
sessions are loaded with a bounded query and filtered in Python using the
freelancer's configured timezone. This is both PostgreSQL-safe and more accurate
for sessions close to midnight.

## Work Order behavior restored

The validated workflow is:

1. Open Assigned Projects.
2. Select **Open Work Order**.
3. The selected task is highlighted on the Work Orders page.
4. Select **Start working**.
5. Select **Stop and record time**.
6. The stopped session creates the linked Daily Task time record.
7. The recorded minutes are available to DTR and Task Time Utilization.

## Additional safeguards

- Duplicate Start requests are redirected with a clear message instead of
  exposing a database error.
- Stop requests that cannot save the time record are rolled back and return a
  clear message.
- Invalid or stale timer actions remain redirects rather than HTTP 500 pages.
- The old **Add to Daily Task Report** project action is renamed **Open Work
  Order** to match Version 21.00 behavior.

## Database compatibility

- No new table
- No new column
- No new Alembic migration
- No data backfill
- Existing Version 21.00 work sessions and reminders are preserved
- Existing tasks, Daily Tasks, DTRs, projects, assignments, and accounts are
  unchanged during deployment
