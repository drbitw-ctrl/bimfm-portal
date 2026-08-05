# Database Safety — Release 21.19.1

Release 21.19.1 changes query authorization only.

## No schema migration

The Alembic head remains:

```text
20260804_0015
```

No migration file was added or changed.

## No record changes

Deployment does not modify:

- Projects or tasks
- Project memberships or task assignments
- Freelancer/member mappings
- Work Orders or Daily Task entries
- Attendance or DTR records
- Leave or overtime records
- Finance or payroll records
- Accounts, passwords, or roles
- Quality Scores or reporting data

## Query-only behavior

For employee principals, the API adds correlated assignment filters before
counting, paginating, and returning project/task records. Staff behavior remains
unchanged.

## Rollback

Because there is no database migration, rollback requires only reverting the
Release 21.19.1 application commit and redeploying the previous application
version. No Alembic downgrade is required.
