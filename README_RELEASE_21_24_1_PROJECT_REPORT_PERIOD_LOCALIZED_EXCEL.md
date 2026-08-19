# BIM Portal Release 21.24.1 — Project Reporting & Localized Excel

## Scope

This release improves Project Reports and Excel exports without changing the database schema or production data.

### Project Time by Member
- The Project Reports period selector now drives the Project Time by Member table.
- Monthly = selected calendar month.
- 12 Months = rolling twelve months ending in the selected month.
- All Time = complete logged Daily Task history.
- Each project is shown once for the selected period, with its total production time and a member-by-member breakdown.
- Member contribution percentage and each project's share of all logged project time are shown.

### Project Work Time Excel
A dedicated Project Work Time export now follows the selected Project Reports period and contains:
1. Project Work Time Health — all projects, total logged time, member coverage, top contributor, share of total project time, active logging months, last logged date, and whether time was logged.
2. Project Time by Member — selected-period project total with member contribution breakdown.
3. Monthly Breakdown — calendar-month detail inside the selected reporting period.

The "Work Time Health" field is descriptive only. It reports whether production time was logged; it does not score or grade productivity.

### English / Traditional Chinese Excel
Excel output now follows the active portal language:
- English portal -> English workbook labels, sheet names, titles, headers, and report descriptions.
- Traditional Chinese portal -> Traditional Chinese workbook labels, sheet names, titles, headers, and report descriptions.

This applies to the existing Excel Export Center workbooks as well as the new Project Work Time workbook. User-entered project/member text is not translated.

## Database
No database changes are included in this release.
- No Alembic revision added.
- `app/models/` unchanged.
- `app/database.py` unchanged.
- `requirements.txt` unchanged.
- Packaged `data/hr.db` unchanged from Release 21.24.0.2.
