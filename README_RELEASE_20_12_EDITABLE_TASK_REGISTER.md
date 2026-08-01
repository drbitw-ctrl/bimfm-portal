# BIMFM Portal Release 20.12 — Editable Task Register

**Application version:** `2.3.7-release20.12-task-register-editing`  
**Release date:** 2026-08-01  
**Source base:** Release 20.11 Project Presentation

## Purpose

Release 20.12 brings the web portal Task Register closer to the desktop Task
Manager Pro workflow while preserving the current portal visual system.

The release focuses on task presentation and task editing. It does not redesign
or replace the interface introduced in Releases 20.9–20.11.

## Complete Task Register

The default **Tasks** page now displays all PostgreSQL project tasks, including:

- Not Started
- In Progress
- Completed — For Review
- Completed
- On Hold
- Unassigned

The separate **Active Tasks** and **Recently Completed Tasks** sidebar entries
remain available as focused views.

## Task filters

The Task Register now provides client-side filters for:

- Search text
- Project
- Assigned member
- Status
- Priority
- Discipline

The filters can be combined and cleared without reloading the page.

## Full task editing

Authorized Administrators and Supervisors can select **Edit** from the Tasks
page and update:

- Project assignment
- Project Engineer
- Task title
- Start date
- Deadline
- Completion date
- Status
- Priority
- Discipline
- Assigned Project Member
- Progress
- Quality Score
- Task description

The editor follows the existing portal form presentation and the desktop task
rules:

- Completed and Completed — For Review force progress to 100%.
- Unassigned forces progress to 0% and clears the task assignment.
- A completed task receives a completion date.
- Completion dates cannot be earlier than start dates.
- Quality Score is optional and accepts a whole number from 1 to 100.
- Project-member selections display names only.
- Project codes remain hidden.

A protected Delete Task action is available from the edit page.

## Sidebar order

Project Management navigation now appears in this order:

1. New Task
2. Tasks
3. Team Availability / Workload
4. Active Tasks
5. Recently Completed Tasks
6. Performance
7. Projects
8. Project Reports
9. Project Team
10. Calendar

## Database change

Release 20.12 includes one additive Alembic migration:

```text
20260801_0004 -> 20260801_0005
```

It adds only the nullable column:

```text
portal_tasks.quality_score
```

No task, member, project, mapping, attendance, leave, DTR, overtime, Finance, or
account record is deleted or re-imported.

## Validation

The full automated suite passed:

```text
95 tests
0 failures
0 errors
```

The acceptance workflow verified:

- Default Tasks page includes both active and completed records
- Project codes and LEGACY placeholder branding remain hidden
- Member names display correctly
- Task filters are rendered
- Edit page opens through the Tasks register
- Full task details can be updated
- Completed status forces 100% progress
- Quality Score is saved
- Completion date is saved
- Project Engineer is updated
- Assignment rows remain valid

## Production acceptance

The release was validated against isolated test databases. After Render deploys
the release, verify one existing active task and one completed task before using
the editor for live production changes.
