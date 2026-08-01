# BIMFM Portal Release 20.22 — Task Time Utilization

**Application version:** `2.3.17-release20.22-task-time-utilization`  
**Source base:** Release 20.21

## Purpose

Release 20.22 adds subtle operational highlighting to the staff Tasks register
and introduces a dedicated Task Time Utilization page for comparing planned
working time with freelancer-reported actual time.

## Tasks register row highlighting

The staff Tasks page now uses light row cues:

- **In Progress:** pale yellow
- **Completed — For Review:** pale yellow
- **Delayed open task:** pale red
- **Completed or Cancelled:** no row highlight

A delayed task is an open task whose deadline is earlier than the current date.
The delayed warning takes priority over the yellow in-progress or review cue.

When Status is changed through inline editing, the row highlight updates without
requiring a full page refresh.

## Task Time Utilization page

A new staff navigation item is available:

```text
Project Management → Task Time Utilization
```

Route:

```text
/portal/time-utilization
```

The page follows this reporting hierarchy:

```text
Project → Task → Target Time → Actual Time
```

It also shows assigned members, task status, start date, deadline, variance,
utilization percentage, Daily Task entry count, and actual time contribution by
freelancer.

## Target time calculation

Target time is calculated from scheduled workdays between the task Start date
and Deadline, including both dates:

```text
Target Time = Scheduled Workdays × 8 hours
```

- Each counted day contributes exactly 480 minutes.
- Scheduled weekdays/rest days follow the active Work Schedule.
- Active company holidays are excluded.
- Missing dates or a deadline earlier than the start date produce no target.
- Inclusive dates mean a valid same-day task receives an 8-hour target.

## Actual time calculation

Actual time comes from `daily_tasks.minutes_spent`.

- A Daily Task linked through `portal_task_id` is included in that task's actual
  time.
- Actual time is broken down by the freelancer who entered it.
- Daily work that identifies a portal project but is not linked to a task is
  retained under **Unlinked / General Project Work**.
- Daily work that cannot be matched to a portal task or project is shown in the
  unmatched-time summary and is not silently assigned.

## Project totals

Each project card shows:

- Target time for tasks with valid schedule dates
- Actual project time
- Over/under variance
- Utilization percentage
- Active task count
- Tasks missing complete schedule dates
- General or unlinked project work

The page can be filtered to one project. Task tables are sortable while keeping
ongoing tasks before closed records.

## Database compatibility

Release 20.22 introduces no new table, column, or Alembic migration.

It does not rewrite projects, tasks, assignments, Daily Task entries, attendance,
DTR, leave, overtime, Finance, Quality Scores, or HR policy data.
