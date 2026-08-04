# BIM Portal Release 21.17

**Version:** `3.0.17-release21.17-clear-utilization-completed-filters`

Release 21.17 is cumulative and retains all Release 21.16 functionality. It clarifies the Task Time Utilization report, adds selectable time periods to Recently Completed Tasks, and shortens the visible build label to the version number only.

## 1. Clear Task Time Utilization

The report now uses the visible formula:

```text
Time Budget Used = Recorded time on scheduled tasks ÷ Planned time for those same tasks × 100
```

### Planned time

Planned time is calculated only when a task has both a valid **Start Date** and **Deadline**:

```text
Scheduled workdays × 8 hours
```

The active Work Schedule and active company holidays remain respected.

### Recorded time

Recorded time comes only from linked Work Order / Daily Task records. Release 21.17 no longer creates an “actual time” estimate from the completion date when no time was recorded.

### Percentage scope

The numerator and denominator now use the same task population:

- Tasks with complete Start and Deadline dates are included.
- Tasks without complete schedule dates remain visible but are excluded from the percentage.
- Unlinked general project work remains visible in Total Recorded Time but is excluded from the percentage.
- Daily Task records that do not match a tracked project remain under Unmatched Time.

This prevents unscheduled or unlinked hours from silently inflating utilization.

### Reading the result

- **Below 100%:** planned hours remain.
- **Exactly 100%:** all planned hours have been used.
- **Above 100%:** recorded hours exceed the plan.

Time Budget Used is not a Quality Score or Overall Performance score.

### New report details

The page and Excel export now separate:

- Total Recorded Time
- Planned Time
- Recorded Time Included in the calculation
- Excluded Recorded Time
- Remaining Planned Hours or Overrun
- Time Budget Used percentage
- The exact task-level calculation

## 2. Recently Completed Tasks filters

The freelancer Recently Completed Tasks page now supports:

- This week
- Last 2 weeks
- Last 3 weeks
- This month
- Last 3 months
- Last 6 months
- This year
- All time

The page defaults to **This week** and shows the selected date range and result count. All time can display completed tasks whose completion date is missing; date-based filters require a recorded completion date.

## 3. Short visible version label

The portal keeps the **System online** status. Visible version labels now show only:

```text
v3.0.17
```

The longer release description remains internal for static-file cache control and diagnostics but is no longer shown beside System online, in the public header, or in the footer.

## Database impact

- New migration: **None**
- New table: **None**
- New column: **None**
- Existing data rewritten: **No**
- Alembic head remains: `20260804_0015`

## Files changed in Release 21.17

```text
app/config.py
app/web_helpers.py
app/task_time_reporting.py
app/excel_exports.py
app/portal_project_service.py
app/routers/projects.py
app/locales/en.json
app/locales/zh_TW.json
static/css/ui-refresh.css
templates/base.html
templates/task_time_utilization.html
templates/freelancer_completed_tasks.html
```
