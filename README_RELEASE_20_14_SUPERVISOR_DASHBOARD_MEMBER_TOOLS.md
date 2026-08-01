# BIMFM Portal Release 20.14

## Supervisor Dashboard and Member Tools

**Application version:** `2.3.9-release20.14-supervisor-dashboard-member-tools`  
**Release date:** 2026-08-01  
**Source base:** Release 20.13 Quality Score Recovery

Release 20.14 keeps the established BIMFM visual system and adds operational dashboard highlights, a read-only Supervisor role, and safer account-management tools.

## Dashboard highlights

The management dashboard now gives visual priority to three daily operating conditions:

- **Team Availability** — members with no active task, members with active work, members without project assignments, and members with overdue work.
- **Active Tasks** — all open tasks, overdue tasks, unassigned open tasks, and the project count.
- **Attendance Today** — members currently working, completed attendance, no-record count, and total recorded attendance.

The existing dashboard design, navigation, tables, themes, and responsive behavior are retained.

## Read-only Supervisor

Administrators can now create a staff account with role:

```text
SUPERVISOR
```

A Supervisor can view:

- Management dashboard
- Project and task records
- Team availability and workload
- Attendance records
- Monthly DTR records
- Leave requests
- Overtime claims
- Finance records

A Supervisor cannot:

- Create or edit tasks
- Approve or reject requests
- Correct attendance
- Generate, review, or finalize DTR records
- Delete records
- Manage freelancer or staff accounts
- Change HR settings
- Perform other staff write actions

The restriction is enforced by the authorization middleware, not only by hiding buttons.

## Reset freelancer password

Administrators can issue a new temporary password from **Freelancer Accounts**.

The reset operation:

- Replaces the existing password hash with a new Argon2 hash.
- Requires a temporary password of at least 10 characters.
- Forces the member to change the temporary password at the next login.
- Clears failed-login counts and account lockout.
- Records an audit event.

Passwords are never displayed or recoverable from their stored hashes.

## Delete unused testing member

Administrators can permanently delete a member only when the profile has no operational or project history.

Deletion is blocked when the member has records such as:

- Attendance
- Leave or overtime
- DTR or daily task reports
- Compensatory-credit transactions
- Payroll summaries
- Project membership or task assignments
- Project-member directory links

Protected members must be disabled instead. Permanent deletion requires typing the member’s complete name and is recorded in the audit log.

## Database safety

Release 20.14 has:

```text
No Alembic migration
No schema change
No data backfill
No SQLite re-import
No project-member repair
```

Existing PostgreSQL projects, tasks, members, mappings, quality scores, attendance, DTR, leave, overtime, compensatory credits, Finance records, and accounts remain unchanged during deployment.

Database writes occur only when an authorized Administrator explicitly creates a Supervisor account, resets a member password, changes account status, or confirms deletion of an unused member.

## Validation

Release 20.14 passed:

```text
105 tests
0 failures
0 errors
```

The validation includes an integrated workflow covering:

- Dashboard operational highlights
- Administrator login
- Supervisor account presentation
- Supervisor access to operational pages
- Rejection of Supervisor write requests
- Password reset and forced password change
- Deletion of an unused test member
- Protection of a member with project history
- Preservation of Release 20.13 quality-score recovery
