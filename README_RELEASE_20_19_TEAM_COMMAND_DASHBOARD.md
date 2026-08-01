# BIMFM Portal Release 20.19

**Application version:** `2.3.14-release20.19-team-command-dashboard`  
**Release date:** 2026-08-01  
**Source base:** Release 20.18 discipline-label and Quality presentation cleanup

## Purpose

Release 20.19 improves the Tasks register spacing and redesigns the management
Dashboard around two immediate operational questions:

1. Who is available and who is busy?
2. What current tasks are assigned to each active member?

The existing portal visual language, task quick-edit behavior, discipline labels,
and Release 20.17 freelancer-assignment repair are preserved.

## Tasks register refinement

On the Tasks sidebar page:

- Progress keeps its inline percentage dropdown.
- Progress keeps its visual loading-style bar.
- The Progress bar is narrower and centered within its own column.
- The separate bold Progress percentage text is removed because the dropdown
  already shows the percentage.
- Quality keeps its inline percentage dropdown.
- The separate bold Quality percentage text is removed.
- Quality continues to have no percentage bar.

Status, Progress, Quality, and Completed remain the only inline-editable task
columns.

## Dashboard redesign

The Dashboard is now a Team Command Center. Workload information is placed
before attendance, approvals, and administrative activity.

The top of the Dashboard shows:

- Available members
- Busy members
- Members with overdue work
- Total active tasks
- Tasks without assignees

### Available members

A member is classified as **Available** when the member has no active portal
task. Available cards show:

- Member name and code
- Ready-for-assignment status
- Project count
- Completed-task count
- Today’s attendance status

### Busy members

A member is classified as **Busy** when at least one active portal task is
assigned to the member. Busy cards show up to three current tasks directly on
the Dashboard:

- Task title
- Project name
- AR, ST, or the existing discipline label
- Progress percentage and a compact progress bar
- Due date
- Overdue warning

When a member has more than three active tasks, the card shows the number of
additional tasks and provides a link to the Active Tasks page.

Legacy imported member assignments and portal-native freelancer assignments are
resolved through the existing project-member mapping rules before the Dashboard
is built. Duplicate assignment rows are collapsed by task ID.

## Secondary information retained

The Dashboard still includes:

- Attendance today
- Pending leave and overtime requests
- Assignment-health warnings
- Recent HR activity
- Quick-launch links

These sections are placed after the team availability and current-task view.

## Preserved behavior

- Architecture and Structure continue to display as AR and ST.
- Newly created freelancer accounts remain assignable to tasks.
- The Tasks register retains its pinned Project and Action/Completed columns.
- Progress and Quality quick edits retain validation, CSRF protection, audit
  logging, and automatic saving.
- Supervisor access remains read-only.

## Database impact

- No new table
- No new column
- No Alembic schema revision
- No data backfill
- No task, project, assignment, member, attendance, DTR, leave, payroll, or
  Finance record is rewritten

## Deployment acceptance

After deployment:

1. Open `/portal/tasks` and hard-refresh.
2. Confirm the Progress bar is shorter and remains inside the Progress column.
3. Confirm no separate bold percentage appears beside Progress or Quality.
4. Confirm Progress and Quality inline editing still saves after refresh.
5. Open the Dashboard.
6. Confirm Available and Busy members are immediately separated.
7. Confirm busy-member cards show current task titles, projects, progress, and
   due dates.
8. Confirm overdue work is visibly marked.
9. Confirm attendance and approval tools remain available below the workload
   section.
