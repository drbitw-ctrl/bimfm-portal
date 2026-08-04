# BIM Portal Release 21.15

## Purpose

Release 21.15 corrects Gabrielle Gameng's July 2026 DTR and Finance calculation while preserving all Release 21.14 features.

Gab has four approved leave dates in July 2026:

- July 1
- July 2
- July 3
- July 6

Two supervisor-approved overtime outcomes provide two complete 8-hour compensatory credits. The corrected result is:

- Physical days worked: 19
- Approved leave taken: 4 days
- Compensatory leave applied: 2 days
- Effective deduction: 2 days
- Payable workday equivalents: 21 days
- Salary-covered calendar days: 29 of 31

## Data treatment

The migration uses existing compensatory-credit ledger entries from approved overtime first. It adds only the shortfall required to establish two whole-day credits when those credits are not yet represented in the ledger. This prevents duplicate credit when the two approved overtime outcomes already exist in production.

The leave classification becomes:

- July 1: Compensatory Leave
- July 2: Compensatory Leave
- July 3: Approved Leave
- July 6: Approved Leave

The July 1 and July 2 leave records each use 480 compensatory minutes. July 3 and July 6 remain deductible whole-day leave.

## DTR behavior

The migration invalidates only non-finalized July 2026 DTR snapshots for Gab. After deployment, generate or refresh Gab's July DTR so the corrected Finance calculation is rebuilt from the attendance, leave, overtime, and compensatory-credit ledgers.

Finalized DTRs are not automatically deleted or rewritten.

## Preserved Release 21.14 features

- Overall Performance shown first under Performance
- Overall Performance weighting: 40% Speed and 60% Quality
- Existing Quality Score calculation retained
- Larger unread freelancer reminders after login
- Text-only BIM Portal / Freelancers identity
- All active Live Work Orders displayed simultaneously
- Required Work Order Daily Task Reports
- Dashboard member visibility correction
- Rounded freelancer attendance cards

## Database revision

- Revision: `20260804_0014`
- Previous revision: `20260803_0013`
- New tables: none
- New columns: none
- New indexes: none

This is a controlled data-correction migration with an audit entry.
