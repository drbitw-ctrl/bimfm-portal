# BIM Portal Release 21.24.2 — Finance History Quick View

## Verified baseline
This release was built directly from the uploaded `BIM_PORTAL_RELEASE_21_24_1.zip` package.
The baseline application version was verified as:

`v3.0.24.1-release21.24.1-project-report-period-localized-excel`

## New application version
`v3.0.24.2-release21.24.2-finance-history-quick-view`

## Changes

### 1. Freelancer DTR Summary — all-time Finance history
The selected DTR month still controls the monthly attendance/payroll calculation, but Finance/Admin history sections now show the freelancer's complete recorded history across all months.

- All-time approved leave history, newest first.
- All-time submitted/final overtime history, newest first.
- Current overtime-credit balance.
- Lifetime OT credit earned and used.
- Expandable full compensatory-credit ledger.

### 2. Finance quick-view shortcuts
The freelancer Summary page now provides direct anchors for:

- OT History
- OT Credit Balance
- Leave History

### 3. Finance Center table reorganization
The wide payroll table is reorganized into grouped columns:

- Freelancer
- Work
- Leave / Absence
- OT Credit
- Salary
- Bank Details
- Status
- Quick View

Quick View provides direct links to Summary, OT History, OT Credit, Leave History, and Monthly Details for Admin/Finance roles.

### 4. Bilingual UI
New Finance Center and history labels are available in English and Traditional Chinese through the existing portal locale system.

## Database safety
There are no database changes in Release 21.24.2.

- No Alembic revision added.
- `app/models/` unchanged.
- `app/database.py` unchanged.
- `requirements.txt` unchanged.
- Bundled `data/hr.db` restored byte-for-byte to the uploaded 21.24.1 baseline.

Existing PostgreSQL production data is not migrated, rewritten, backfilled, or deleted by this release.

## Validation
- Python compile: PASS
- Jinja template compilation: PASS (59 templates)
- Locale JSON validation: PASS
- Regression suite: 133 passed, 0 failed
