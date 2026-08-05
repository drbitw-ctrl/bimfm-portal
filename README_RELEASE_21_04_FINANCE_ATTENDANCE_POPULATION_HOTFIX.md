# BIMFM Portal Release 21.04

**Application version:** `3.0.4-release21.04-finance-attendance-population-hotfix`  
**Release type:** Finance My Work attendance-population hotfix

## Purpose

Release 21.04 corrects the Finance Head My Work attendance population. The
Release 21.03 implementation selected every active row from the `freelancers`
table. That table also contains active legacy project-import placeholders kept
for historical foreign-key compatibility, so those non-login identities could
inflate the displayed member count.

## Corrected population rule

Finance attendance and DTR summaries now include only freelancer profiles that:

- are active;
- have a freelancer login account; and
- have an active login account.

Legacy project-import placeholders do not have login accounts and are excluded.
Disabled former or test accounts are also excluded.

The corrected eligible population is used consistently for:

- Attendance Recorded Today;
- the Daily Attendance Overview table;
- Attendance Issues;
- monthly attendance record totals;
- monthly DTR generated counts; and
- DTR Not Generated counts.

## Important account behavior

An active test account with an active login is still a valid attendance member.
Disable or purge a test account when it should no longer appear in Finance
attendance reporting.

## Database compatibility

- No new tables
- No new columns
- No Alembic migration
- No data backfill
- No attendance or DTR rewrite

## Validation

The hotfix was tested with six enabled real freelancer accounts, seven active
legacy placeholders, and one disabled account. Attendance and DTR records were
created for both real accounts and placeholders. The Finance overview correctly
reported only the six enabled real accounts and excluded all placeholder and
disabled identities.
