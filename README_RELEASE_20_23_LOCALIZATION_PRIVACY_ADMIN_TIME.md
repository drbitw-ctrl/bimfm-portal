# BIMFM Portal Release 20.23

**Application version:** `2.3.18-release20.23-localization-privacy-admin-time-fallback`  
**Release type:** Interface, privacy, account cleanup, and reporting logic update

## Purpose

Release 20.23 improves Traditional Chinese coverage across portal tables, cards,
labels, dynamic status text, and management reports. It also removes Quality
Score from freelancer-facing task pages, adds safe permanent deletion for unused
staff/test administrator accounts, and adds an estimated actual-time fallback to
Task Time Utilization when no Daily Task time has been recorded.

## Traditional Chinese localization

The Traditional Chinese catalog and browser-side dynamic translation rules were
expanded for:

- Dashboard cards and workload text
- Performance Leaderboards
- Project Reports
- Attendance, DTR, leave, overtime, and Finance tables
- Staff and freelancer account-management pages
- Task Time Utilization labels and estimate indicators
- Dynamic durations, counts, rankings, statuses, and review labels

Member names, project names, task descriptions, company names, and technical
terms such as PostgreSQL, DTR, OT, AR, ST, MEP, GE, API, Excel, and projects.db
remain unchanged.

## Freelancer Quality Score privacy

Quality Score is no longer included in freelancer-facing completed-task data or
tables. Management and reporting pages continue to use Quality Score normally.

Affected freelancer views include:

- Assigned Projects
- Daily Tasks
- Recently Completed Tasks
- Daily Task edit pages

## Staff and test administrator deletion

Administrators can now open:

`Administration > Staff Access > Delete`

Permanent deletion is allowed only when all safeguards pass:

- The target is not the currently signed-in account.
- At least one active Administrator remains.
- The target account has no operational database references.
- The exact username is entered for confirmation.

Accounts referenced by attendance corrections, DTR generation, approvals,
policies, project records, or other operational history are protected and must
be disabled instead. The confirmation page displays the blocking references.

## Task Time Utilization fallback

Actual time still prioritizes linked freelancer Daily Task entries.

When a completed portal task has no linked Daily Task entry, Release 20.23 uses:

`Estimated actual time = scheduled workdays from Start Date through Completion Date × 8 hours`

The same active Work Schedule and company-holiday rules used for Target Time are
applied. Estimated values are clearly labelled and are counted separately in the
project and page summaries.

If even one linked Daily Task entry exists, the submitted Daily Task minutes are
used and the completion-date estimate is not applied.

## Database compatibility

- No new tables
- No new columns
- No Alembic migration
- No data backfill
- No Quality Score rewrite
- No task or Daily Task rewrite
- No automatic staff-account deletion

Release 20.23 is compatible with the Release 20.22 PostgreSQL schema.
