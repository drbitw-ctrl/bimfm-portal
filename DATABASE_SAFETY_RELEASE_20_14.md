# Release 20.14 Database Safety Statement

Release 20.14 does not introduce a database schema revision and does not automatically rewrite production records.

## Deployment effects

The normal Render build still runs:

```text
alembic upgrade head
```

Because Release 20.14 adds no migration, an already-current Release 20.13 database remains unchanged by this command.

## Existing data preserved

Deployment does not delete, recreate, import, or backfill:

- PostgreSQL projects and tasks
- Project members and HR mappings
- Quality scores
- Freelancer and staff accounts
- Attendance and corrections
- DTR records
- Leave and overtime records
- Compensatory-credit ledgers
- Finance and payroll summaries
- Audit history

## Explicit administrator actions

The following new tools intentionally write data only when an authorized Administrator submits the corresponding form:

### Password reset

Updates one freelancer login account by:

- Replacing the password hash
- Enabling forced password change
- Clearing failed-login count and lockout
- Writing an audit event

### Delete unused member

Permanent deletion is allowed only when the application finds no operational or project dependencies. Members with history or assignments are blocked and should be disabled instead.

Deletion requires exact-name confirmation and writes an audit event before removing the unused profile and login account.

## Supervisor restriction

Supervisor access is enforced as read-only by server-side permission checks and middleware. Hiding form controls is additional presentation protection, not the primary security control.

## Recommended production practice

Keep a current PostgreSQL backup and test delete/reset actions first with a noncritical testing account. Never delete a real member to remove portal access; disable the account so historical records remain intact.
