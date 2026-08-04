# BIM Portal Release 21.19

## Project utilization bars

Release 21.19 removes the relative project-hours graphic from the project summary cards on **Performance → Task Time Utilization**.

The removed graphic compared each project with the project that had the highest all-time hours. Because it looked like a utilization percentage, it could be misunderstood during reporting and presentations.

Each project card now shows a clearly labelled **Time budget used** bar based on:

```text
Utilization time ÷ Planned time × 100
```

The utilization-time rules from Release 21.18 remain unchanged:

- Recorded time is used when a task has actual Work Order or linked Daily Task time.
- Planned time is used as the reporting fallback when a scheduled task has no actual time.
- Tasks using the planned fallback show 100% utilization.
- Recorded time for work without a complete plan remains visible but is excluded from the percentage.

## Project-card display

Every project card continues to show:

- All-time hours
- Actually recorded hours
- Planned-time fallback hours
- Planned hours
- Utilization time
- Time budget used percentage

The utilization bar behaves as follows:

- At or below 100%: standard utilization bar
- Above 100%: warning bar, while the displayed value can exceed 100%
- No planned time: neutral empty bar with **No planned time**

The former **percentage of all project hours** and its relative-length bar are no longer calculated or displayed.

## Other retained functions

Release 21.19 retains all Release 21.18 functions, including:

- All-time hours for every project
- Planned-time fallback for historical tasks
- Recently Completed Tasks period filters
- Hourly HR Finance and overtime-credit treatment
- Project Categories and custom Disciplines
- Performance recommendations
- Suggested members and availability during task creation
- `System online` with the short version number only

## Database impact

No database migration is included. The Alembic head remains:

```text
20260804_0015
```

No existing records are created, deleted, or rewritten.
