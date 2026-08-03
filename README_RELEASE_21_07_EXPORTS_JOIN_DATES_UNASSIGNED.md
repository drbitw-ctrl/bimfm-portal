# BIMFM Portal Release 21.07

**Version:** `3.0.7-release21.07-exports-join-dates-unassigned`  
**Release type:** Cumulative operational update based on Release 21.06

## Release purpose

Release 21.07 adds professional Excel exports, permanent freelancer joining dates, clearer dashboard workload colors, unassigned-task controls, and a repair for the Work Status arrow links.

## Excel Export Center

The new **Excel Export Center** is available to Administrators, Supervisors, and Finance users. Every export is read-only and creates an audit-log entry.

Available downloads:

- **Complete Excel Package** — all available operational and monthly reports in one workbook.
- **All Tasks** — complete task register, including assignments, schedule, progress, and Quality Score.
- **Monthly Reports** — project register, Team Availability, performance, project reports, Task Time Utilization, leave requests, and overtime claims.
- **Monthly Attendance** — detailed attendance rows for the selected month.
- **DTR Register** — monthly DTR summary and daily supporting details.

The complete package contains 13 worksheets:

1. Export Summary
2. All Tasks
3. Projects
4. Team Availability
5. Performance
6. Project Reports
7. Project Time Utilization
8. Task Time Details
9. Leave Requests
10. Overtime Claims
11. Monthly Attendance
12. Monthly DTR Summary
13. DTR Daily Details

## Dashboard color logic

The Dashboard and role-based My Work pages now use the same workload assignment logic and display a visible legend.

| Color | Meaning |
|---|---|
| Red | Member has overdue active work. This takes priority over the other colors. |
| Blue | Member has an active Work Order timer. |
| Yellow | Member has active assigned tasks but no active timer. |
| Green | Member has no active assigned task and is available. |

The color groups, summary counts, cards, and Team Availability rows now use the same precedence.

## Unassigned Tasks

A new **Unassigned Tasks** metric and detail section appears on:

- Administrator Dashboard
- Administrator My Work
- Supervisor My Work

The detail table shows project, task, priority, status or discipline, progress, start date, and deadline. Administrators receive a direct **Assign Task** action. Supervisors retain read-only access.

The Tasks page also supports the dedicated view:

`/portal/tasks?view=unassigned`

## Freelancer joining dates

Release 21.07 adds a permanent `join_date` field to freelancer profiles. It appears in the freelancer account list, Team Availability, My Work, dashboard member cards, and Excel exports.

The migration backfills these confirmed dates:

| Member | Join date |
|---|---|
| Alexsandria Santos | 2026-06-08 |
| Carlo Ninoy Nilo | 2025-07-21 |
| Gabrielle Gameng | 2025-04-07 |
| Jonica Jomadiao | 2025-08-12 |
| Kaizer Macatiag | 2026-03-16 |
| Lander Samson | 2025-11-24 |
| Raymond Navarro | 2025-07-01 |

Raymond Navarro's freelancer profile and login account are set to inactive during the migration, as requested.

Administrators can update or clear Join Date from **Freelancer Accounts**.

## Work Status arrow repair

The arrow in the Dashboard's **Attendance Today → Work Status** table now opens the correct attendance correction/detail route:

`/admin/attendance/<freelancer_id>/<date>/correct`

## Database change

New Alembic revision:

`20260803_0010`

New column:

`freelancers.join_date DATE NULL`

The migration does not rewrite task, project, attendance, DTR, payroll, Quality Score, Work Order, leave, or overtime records.

## July 2026 attendance workbook

The separate July workbook was corrected with:

- Carlo Ninoy Nilo — leave on July 27, 2026
- Gabrielle Gameng — leave on July 1, 2, 3, and 6, 2026
- Confirmed joining dates
- Raymond Navarro marked inactive and excluded from July import rows

The workbook remains an editable preparation file. Deploying Release 21.07 does not automatically import the workbook into production.
