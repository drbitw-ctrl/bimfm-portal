# BIMFM Portal Release 20.6

**Application version:** `2.3.1-release20.6-finance-clarity`  
**Release date:** 2026-08-01  
**Source base:** Milestone 20.5 production-hardening release

## Purpose

Release 20.6 makes attendance, leave, compensatory leave, and payroll treatment
clearer for freelancers, management, and Finance.

The release removes confusing decimal-day and payroll-multiplier presentation
from the main interfaces while retaining precise internal calculations where
they are still required for validation and backward compatibility.

## Finance presentation

The Finance Center and DTR now distinguish:

- **Days Physically Worked**
- **Approved Leave Taken**
- **Compensatory Leave Applied**
- **Payable Workday Equivalents**
- **Salary-Covered Calendar Days**
- **Effective Payroll Deduction**
- **Payroll Treatment**

Example:

```text
Days Physically Worked:        22
Approved Leave Taken:           1 day
Compensatory Leave Applied:     1 day
Payable Workday Equivalents:   23
Salary-Covered Calendar Days:  31 of 31
Effective Payroll Deduction:    0 days
Payroll Treatment:              Full Monthly Rate
```

Compensatory leave remains separate from physical attendance. It may protect
salary coverage, but it does not increase the number of days actually worked.

## Freelancer account improvements

The attendance page now includes a monthly summary showing:

- Days physically worked
- Approved leave taken
- Compensatory leave applied
- Payable workday equivalents
- Compensatory credits earned, used, and remaining
- Current DTR status

This gives freelancers the same clear terminology used by Finance.

## Time presentation

Visible durations now use hours and minutes instead of decimal hours.

Examples:

```text
7h 30m
1h 15m
45m
```

Daily-task input may still accept a compact decimal entry such as `4.5` hours,
but saved and reviewed results are displayed as `4h 30m`.

## Excel export

The DTR workbook has been rewritten for Finance clarity.

The main worksheet is now **Finance Summary** and includes whole-day attendance
and payroll treatment. Duration columns use hours and minutes.

The workbook no longer presents a decimal payroll multiplier as the primary
Finance result.

## Project-member mapping protection

A regression test now confirms that project-member mappings survive:

- Repeated full synchronization snapshots
- Differences in capitalization
- Leading or trailing spaces in source member names
- New project tasks received after the mapping was created

The release does not modify `projects.db`.

## Database and deployment compatibility

- SQLite remains supported for development and isolated testing.
- PostgreSQL remains the production database for Render.
- No new business table or column is introduced by Release 20.6.
- Running `alembic upgrade head` remains safe and is retained in the build.
- Existing data, accounts, project mappings, attendance, leave, overtime,
  compensatory-credit ledgers, and DTR records are preserved.

## Reliability improvements

SQLite development connections now use explicit cleanup and `NullPool`, removing
the connection cleanup warnings that appeared in the earlier automated suite.

## Automated validation

Release 20.6 passed:

```text
60 tests
0 failures
```

It also passed an integrated workflow check covering:

- Administrator login
- Finance Center
- DTR summary
- Excel generation
- Freelancer login
- Freelancer monthly attendance summary
- A scenario with 22 physical workdays, 1 compensatory leave day,
  23 payable workday equivalents, and 31 of 31 salary-covered calendar days

## Important acceptance requirement

The release was validated in an isolated test environment. Before relying on it
for payroll, management and Finance should verify the displayed results against
one completed real month in the production PostgreSQL database.
