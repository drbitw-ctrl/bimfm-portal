# BIMFM Portal Release 20.20 — Performance Leaderboards and Reporting

**Application version:** `2.3.15-release20.20-performance-reporting`  
**Source base:** Release 20.19 Team Command Dashboard

## Purpose

Release 20.20 adds sortable task registers, a leaderboard-style Performance
page, and period-based member/project reporting.

## Sortable task tables

Task-list tables now support one-click sorting from their column headings.
Clicking the same heading again reverses the direction.

Open work is always grouped before completed/cancelled work, even when a user
sorts by project, member, status, priority, progress, quality, date, or another
available task column.

Sorting is enabled for:

- Complete, Active, and Recently Completed task registers
- My Work
- Calendar task register
- Project Team active-task register
- Freelancer daily-task register
- Administrator monthly daily-task review
- DTR daily-task records

Sorting is browser-side presentation only. It does not update task records.

## Performance Leaderboards

The Performance page now follows the leaderboard presentation of the supplied
previous desktop dashboard.

Three ranking modes are available:

1. **Quality Score**
2. **Total Tasks**
3. **Delivery Speed**

Each mode includes summary cards, a top-three podium, member search, sortable
results, and management recommendations.

### Conservative Quality Score presentation

Stored Quality Scores remain unchanged. For Performance and Project Reports,
raw scores are converted into a conservative management display score:

```text
calibrated score = raw score × 0.70 + 22
maximum displayed score = 92
```

Examples:

```text
Raw 100 → 92.0
Raw  95 → 88.5
Raw  90 → 85.0
Raw  85 → 81.5
Raw  80 → 78.0
Raw  70 → 71.0
```

The calibrated value is used only for display, ranking, summaries, charts, and
recommendations. `portal_tasks.quality_score` is not rewritten.

### Delivery measurement

A completed task is measurable when it has both a deadline and a completion
date.

```text
completion date before deadline = Early
completion date equals deadline = On Time
completion date after deadline  = Late
```

The early/on-time rate is:

```text
(Early + On Time) ÷ Measured Tasks × 100
```

## Project Reports

Project Reports now focus on members and projects instead of system-health
indicators.

Available periods:

- **Monthly** — selected calendar month
- **12 Months** — rolling twelve months ending in the selected month
- **All Time** — complete dated history

The page includes:

- Delivered-task total
- Calibrated average Quality Score
- Early/on-time delivery rate
- Logged daily-task hours
- Current active tasks
- Current overdue tasks
- Delivered-task trend
- Quality trend
- Delivery trend
- Logged-hours trend
- Member output ranking
- Project output ranking
- Detailed sortable member report
- Detailed sortable project report

Delivered, quality, delivery, and logged-hour results follow the selected
reporting period. Active and overdue values intentionally show current workload.

## Database impact

- No new business table
- No new business column
- No Alembic migration
- No Quality Score rewrite
- No task-status rewrite
- No project/member assignment rewrite

## Compatibility

Release 20.20 preserves the Release 20.19 dashboard, selective task quick-edit,
member-assignment repair, AR/ST discipline presentation, attendance, DTR, leave,
overtime, Finance, and PostgreSQL deployment behavior.
