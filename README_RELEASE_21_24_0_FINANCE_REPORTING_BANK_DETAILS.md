# BIM Portal Release 21.24.0 — Finance Reporting & Bank Details

## Release scope

Release 21.24.0 is based on Release 21.23.1.2 and adds five requested finance/reporting improvements.

### 1. Monthly Project Work Time report

Project Reports now includes a **Monthly Project Work Time** table.

The hierarchy is:

- Month
  - Project — total logged production time
    - Member — time logged by that member for the project

The report uses the portal's existing `DailyTask.minutes_spent` records, including stopped Work Orders already mirrored into Daily Task records. It does not invent or estimate time. The monthly Project Reports Excel package now also includes a **Monthly Project Time** worksheet with one row per project/member contribution.

### 2. Leave approval reason is optional

The decision reason is optional when an authorized reviewer **approves** a leave request.

- Approval: reason optional
- Rejection: reason remains required (minimum 5 characters)
- The freelancer's original leave-request reason remains unchanged and required.

### 3. Freelancer bank details

Freelancer Accounts now includes a Bank Details column and an Edit Bank Details page with:

- Account Name
- Account Number
- Bank Name
- SWIFT Code
- Bank Branch Address

Sensitive bank values are not written into the audit log. The audit log only records that the bank profile was updated.

### 4. Bank details in DTR and Finance

Bank details are shown to authorized **Administrator and Finance Head** users in:

- each freelancer's Monthly DTR Summary
- Finance Center monthly table

Supervisor read-only views do not display bank information.

### 5. Actual leave and overtime history in DTR Summary

Administrator and Finance Head users can see two new finance tables directly on each Monthly DTR Summary:

- Actual Leave History — approved leave date, type, duration, OT credit used, payroll treatment
- Actual Overtime History — date, work description, actual end time, approved OT, final status

## Database change

This release contains one intentionally small, additive migration:

`20260819_0018_freelancer_bank_details.py`

It adds five **nullable** columns to the existing `freelancers` table. It does not modify existing freelancer values, attendance, DTR, leave, overtime, project, payroll, or Work Order records.

See `DATABASE_SAFETY_RELEASE_21_24_0.md` before deployment.

## Validation

- Python compile: PASS
- JavaScript syntax check: PASS
- Locale JSON validation: PASS
- Test suite: 115 passed, 0 failed
- Fresh database migration through 0018: PASS
- Existing-schema 0017 → 0018 migration with an existing freelancer record: PASS; original record retained unchanged and new fields were NULL
- `/health/ready` on migrated temporary database: HTTP 200
