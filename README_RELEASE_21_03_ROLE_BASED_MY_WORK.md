# BIMFM Portal Release 21.03

**Application version:** `3.0.3-release21.03-role-based-my-work`  
**Release type:** Role-based workspace, interface terminology, and shared table-status presentation

## Purpose

Release 21.03 turns **My Work** into a role-specific operational workspace. Each staff role receives the information and shortcuts needed for its assigned responsibilities instead of sharing one generic page.

The release also removes database-engine terminology from visible portal text and standardizes task-table row colors and legends across management and task-history views.

## Administrator My Work

Administrators see:

- Active Tasks summary and sortable active-task table
- Team Availability summary and table
- Delayed, in-progress, and for-review task counts
- Available, actively working, assigned, and overdue member counts
- Pending leave-request count and recent requests
- Pending overtime-request count and recent requests
- Attendance correction needs detected from unreviewed records with missing time-in or time-out
- Direct shortcuts to the full Tasks, Team Availability, Leave, Overtime, and Attendance pages

Attendance exceptions are based on existing unreviewed attendance records from the most recent 31 days. Release 21.03 does not add a new attendance-request table or change attendance data.

## Supervisor My Work

Supervisors see a read-only operational view containing:

- Active Tasks summary and sortable active-task table
- Team Availability summary and table
- Current assignments, live Work Order activity, active-task counts, and overdue-task counts

Pending HR requests and Finance controls are not shown in the Supervisor My Work content.

## Finance Head My Work

Finance users see:

- Today's attendance coverage
- Members currently working
- Missing or invalid attendance records
- Current-month attendance totals and rendered, late, undertime, and overtime durations
- Current-month DTR generated, draft, reviewed, finalized, and not-generated counts
- Shortcuts to Today's Attendance, Monthly Attendance, Monthly DTR, and Finance Center
- Finance-authorized **Generate / Refresh All DTRs** action

Finance remains restricted to its existing permissions. This page does not grant attendance editing, DTR review/finalization, HR approval, task editing, or Administrator account-management access.

## Shared task-table color language

Task lists use one consistent row-color meaning:

- Pale yellow: In Progress or Completed — For Review
- Pale red: Past deadline and still open
- Pale green: Completed
- No row color: Not Started, On Hold, Unassigned, Cancelled, or another neutral state

Delayed status takes priority over the yellow active-state color. Every affected task list includes a visible legend.

The shared presentation is applied to:

- Tasks, Active Tasks, and Recently Completed Tasks
- Administrator and Supervisor My Work task tables
- Calendar task register
- Project Team active-task register
- Task Time Utilization
- Freelancer Recently Completed Tasks
- Freelancer monthly Work Order history
- Administrator monthly Daily Task review
- DTR Daily Task records

## Team Availability color language

Team Availability rows use:

- Green: Available
- Blue: Working Now
- Yellow: Assigned but no running Work Order timer
- Red: Has overdue work

A visible legend appears on Team Availability and role-specific My Work pages.

## Neutral portal terminology

Visible interface text no longer explains or names the underlying database engine or retired database file. Pages now use operational terms such as:

- Project records
- Task register
- Portal records
- Project Member Directory
- Current assignments

English and Traditional Chinese catalog values were cleaned so database-engine terminology is not rendered by server-side or browser-side translation.

## Database compatibility

Release 21.03 introduces:

- No new table
- No new column
- No Alembic revision
- No data backfill
- No task, attendance, DTR, leave, overtime, payroll, account, or Work Order rewrite

The Alembic head remains `20260802_0009` from Release 21.02.
