# Database Safety — Release 21.02

## Schema change

Release 21.02 adds one Boolean column through Alembic revision
`20260802_0009`:

```text
hr_admin_accounts.must_change_password
```

The column is non-nullable and defaults to `false`.

## Existing staff accounts

Existing Administrator, Supervisor, and Finance accounts receive `false` during
the migration. They are not forced to replace their current password merely
because the application was deployed.

The flag becomes `true` only when:

- An Administrator creates a new staff account; or
- An Administrator resets that staff account's password.

## Existing freelancer accounts

No freelancer schema change is made. Their existing
`freelancer_accounts.must_change_password` field and behavior are preserved.

## Records not modified by deployment

Release 21.02 does not rewrite:

- Password hashes
- Account roles or active states
- Freelancers
- Projects or tasks
- Assignments
- Attendance
- Daily Tasks or DTRs
- Leave or overtime
- Payroll or Finance records
- Work Order sessions
- Reminders
- Quality Scores
- HR policies

## Finance DTR generation

Finance DTR generation creates or refreshes draft Monthly DTR records only when
a Finance user explicitly submits the generation form. Finalized DTRs remain
protected and are skipped by the existing DTR-generation service.

## Rollback

Application rollback to 21.01 is possible, but the 21.01 ORM does not use the
new column. The column may safely remain in PostgreSQL during an application
rollback. Do not downgrade the database unless a coordinated schema rollback is
specifically required.
