# BIM Portal Release 21.18

Version: `v3.0.18`

Release 21.18 revises Task Time Utilization so older scheduled tasks can receive a utilization percentage even when no Work Order or Daily Task time was recorded.

## Utilization rule

For every task with valid planned time:

1. Use actual recorded time when Work Order or linked Daily Task time exists.
2. When actual recorded time is zero, use planned time as the task's utilization time.
3. Calculate utilization as:

```text
Utilization = Utilization Time ÷ Planned Time × 100
```

Therefore, a task with planned time but no actual record displays 100% utilization.

Example:

```text
Planned Time: 40 hours
Recorded Time: 0 hours
Utilization Time: 40 hours (planned fallback)
Utilization: 40 ÷ 40 × 100 = 100%
```

The fallback is a reporting calculation only. It does not create a Work Order, Daily Task entry, or database time record.

## All-time project hours

Every project is displayed in the project overview, including projects with no tasks or no recorded hours.

Each project now separates:

- All-time project hours
- Actually recorded hours
- Planned-time fallback hours
- Planned hours
- Utilization percentage

All-time project hours include:

```text
Actual recorded task time
+ planned-time fallback for scheduled tasks with no actual record
+ recorded unlinked/general project work
```

Projects are ranked using their complete all-time project hours.

## Task-level clarity

The task table now shows separate columns for:

- Planned Time
- Recorded Time
- Utilization Time
- Time Source
- Remaining / Overrun
- Time Budget Used
- Exact Calculation

The Time Source identifies whether the calculation uses:

- Actual recorded time
- Planned fallback
- Unlinked recorded time

Tasks without complete Start and Deadline dates still cannot receive a percentage because no planned denominator exists. Their actual recorded hours remain included in the project's all-time total.

## Excel export

The Project Time Utilization and Task Time Details worksheets now contain the same all-time totals, fallback amounts, time-source labels, and utilization calculations shown in the portal.

## Preserved Release 21.17 features

- Recently Completed Tasks period filters
- Clear task-time calculation presentation
- Text-only lower-left status:

```text
System online
v3.0.18
```

- Hourly HR Finance and overtime-credit logic
- Project Categories and flexible Disciplines
- Specialty performance recommendations
- Suggested members and live availability when creating tasks

## Database impact

No migration is introduced.

```text
Alembic head: 20260804_0015
New tables: None
New columns: None
Existing records rewritten: No
```
