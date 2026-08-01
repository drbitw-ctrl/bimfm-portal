# BIMFM Portal Release 20.16 — Selective Task Quick Edit

**Application version:** `2.3.11-release20.16-selective-task-quick-edit`  
**Release date:** 2026-08-01  
**Source base:** Release 20.14 stable Render deployment

## Purpose

Release 20.16 replaces the rolled-back broad inline-edit implementation with a limited quick-edit workflow on the **Tasks** sidebar page only.

## Editable columns

Authorized project editors can update only:

- **Status** — dropdown
- **Progress** — dropdown with the percentage label and progress bar retained
- **Quality** — dropdown with the percentage label and quality bar retained
- **Completed** — date picker, enabled when Status is `COMPLETED`

All other task columns remain display-only in the task register:

- Project
- Task name
- Assigned Member
- Priority
- Discipline
- Start
- Deadline

The existing **Edit** action remains available for complete task editing.

## Scope protection

Quick editing is rendered only when:

- The current sidebar module is `Tasks` (`/portal/tasks`)
- The signed-in account has the existing `PROJECT_EDIT` permission

The quick-edit endpoint accepts only these server-side fields:

```text
status
progress
quality_score
completion_date
```

Requests for Project, Task name, Assigned Member, Priority, Discipline, Start, Deadline, or any unknown field are rejected.

## Status behavior

- `Completed` and `Completed — For Review` set Progress to `100%`.
- `Completed` automatically records today's completion date when no date exists.
- Moving away from `Completed` clears the completion date.
- `Unassigned` sets Progress to `0%` and removes task assignments, matching the existing task-edit rules.

## Visual behavior

Progress and Quality remain visually readable as percentage bars. Changing a dropdown updates the number and bar immediately after the database save succeeds.

Each row shows a small `Saving…`, `Saved`, or error message below the Status dropdown.

## Database impact

- No new table
- No new column
- No new Alembic migration
- No changes to projects, attendance, DTR, leave, overtime, payroll, or Finance calculations
- Existing task edit and delete routes remain available

## Rollback

Redeploy the previous known-good Git commit. A database restore is not required because Release 20.16 does not change the schema.
