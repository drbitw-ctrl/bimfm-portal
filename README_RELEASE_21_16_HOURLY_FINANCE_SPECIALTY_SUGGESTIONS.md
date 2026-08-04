# BIM Portal Release 21.16

**Version:** `3.0.16-release21.16-hourly-finance-specialty-suggestions`  
**Release focus:** Hourly HR Finance, specialty recommendations, Project Categories, flexible Disciplines, and task-assignment suggestions

## Release summary

Release 21.16 updates HR Finance so approved overtime credit offsets approved leave **hour-for-hour**. Working-day counts remain visible in attendance and DTR reports, while payroll deductions are calculated from working hours. Partial overtime-credit balances can be used immediately and any unused balance carries forward.

The Performance page now provides management suggestions for the strongest members by selected Discipline and Project Category. The New Task form also recommends members using their specialty history and current Team Availability.

## 1. Hourly HR Finance and overtime-credit logic

The previous complete-day redemption restriction is removed.

- Approved leave remains recorded by workday for attendance and DTR purposes.
- Each leave day is converted using the configured standard workday minutes.
- Approved overtime credit offsets leave minute-for-minute.
- Partial balances can be applied immediately.
- Unused overtime credit remains in the member's ledger.
- Overtime credit cannot increase salary above the full monthly rate.
- Existing working-day totals remain available for operational reporting.

### Gab's July 2026 example

| Item | Result |
|---|---:|
| Monthly salary used for the example | ₱50,000.00 |
| Calendar days | 31 |
| Standard hours per workday | 8 |
| Approved leave | 4 days / 32 hours |
| Confirmed overtime credit | 15 hours |
| Leave not covered by credit | 17 hours |
| Salary deduction | ₱3,427.42 |
| Net salary before other deductions | ₱46,572.58 |

The migration aligns Gab's July credit ledger to the supervisor-confirmed 15-hour opening balance without duplicating genuine approved-overtime entries. It applies 15 hours to the four approved leave days and invalidates only non-finalized July DTR snapshots for regeneration.

## 2. Performance suggestions by specialty

A new **Recommended Members by Specialty** summary appears near the top of Performance.

The initial recommendations cover:

- MEP
- AR
- ST
- MRT
- 安居
- Bridge
- RFA

Recommendations use the same visible Overall Performance basis:

`Overall Performance = 40% Speed + 60% Quality`

The existing Quality Score calculation remains unchanged. No internal Quality transformation formula is shown in the portal.

Each specialty card shows:

- Recommended member
- Overall Performance
- Speed
- Quality
- Completed-task evidence
- Rated-task evidence
- Recommended or Limited Data status

A recommendation is considered reliable only when sufficient completed, rated, and schedule-measured tasks exist. Otherwise, the page clearly identifies the result as limited data.

## 3. Project Category

Projects now have an optional **Project Category** field.

Default choices include:

- 安居
- MRT
- Bridge
- Housing
- Commercial

Administrators may also type a new custom category. Future custom category names do not require another database migration.

The category is available in:

- New Task and New Project workflow
- Edit Task workflow
- Project Register
- Project Team table
- Performance specialty recommendations
- Suggested-member ranking
- Excel project exports

Existing projects with recognizable names are safely categorized only when the field is blank:

- Names containing `安居` → 安居
- Names containing `MRT` or `捷運` → MRT
- Names containing `Bridge` or `橋` → Bridge

Other projects remain uncategorized until management selects a category.

## 4. Flexible Discipline options

The New Task and Edit Task forms now provide these suggested Disciplines:

- AR
- ST
- AS (AR+ST)
- MEP
- E&M
- RFA
- CDR
- GE
- Civil Works

The field also accepts a new custom Discipline of up to 100 characters. Existing historical Discipline values remain valid.

For recommendation purposes, AS task history contributes to both AR and ST specialty analysis.

## 5. Suggested members when creating tasks

The New Task page now displays **Suggested Members and Availability**.

Each suggested-member card shows:

- Recommendation rank
- Member name and code
- Current availability state
- Active-task count
- Overdue-task count
- Specialty score when available
- Current project and task when a Work Order is running

The availability colors follow the established Team Availability logic:

- Green — Available
- Yellow — Assigned, no active timer
- Blue — Working Now
- Red — Overdue responsibility

Suggestions refresh automatically when the Administrator changes the Discipline, Project Category, or existing Project. Selecting a suggestion fills the Assigned Member field. The final assignment always remains an Administrator decision.

## 6. Data and schema impact

Release 21.16 adds Alembic revision:

`20260804_0015`

Schema change:

- Adds nullable text column `portal_projects.project_category`

Controlled data changes:

- Backfills only blank project categories when a project name clearly matches 安居, MRT, or Bridge.
- Aligns Gab's July 2026 overtime-credit application to the confirmed hourly calculation.
- Removes only non-finalized Gab July DTR snapshots so Finance can regenerate them.

The release does not rewrite unrelated:

- Task progress or Quality Scores
- Project names or internal project identifiers
- Task assignments
- Attendance punches
- Other members' leave or overtime records
- Finalized DTRs
- Work Orders
- Accounts, passwords, payroll amounts, or salary records

## 7. Post-deployment checks

After deployment:

1. Open **Finance Center** and confirm leave and overtime-credit values are displayed in hours.
2. Regenerate Gab's July 2026 DTR if it is not finalized.
3. Confirm Gab shows 32 approved leave hours, 15 overtime-credit hours applied, and 17 unpaid leave hours.
4. Open **Performance** and review Recommended Members by Specialty.
5. Create a test task and confirm Project Category, custom Discipline, and Suggested Members are available.
6. Confirm the Projects and Project Team tables display Project Category.

A finalized July DTR is intentionally preserved. It must be reopened through the normal controlled process before regeneration if management needs the corrected hourly calculation reflected in that finalized snapshot.
