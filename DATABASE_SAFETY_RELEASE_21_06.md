# Release 21.06 Database Safety

## Schema

Release 21.06 adds no database migration.

Current Alembic head:

```text
20260802_0009
```

No tables, columns, indexes, or constraints are added or removed.

## Password data

Deployment does not alter existing password hashes or force existing accounts to change passwords.

Password data changes only when:

- A user successfully changes their own password.
- An Administrator performs an existing password-reset action.

Passwords continue to be stored as Argon2 hashes.

## Work Order runtime behavior

Release deployment performs no bulk conversion of Work Order history.

An active session may be finalized after deployment when:

1. Its freelancer records Attendance Time Out; or
2. It is older than the configured maximum active duration when the background safeguard runs.

Finalizing a session creates the same Daily Task record used by a normal manual Work Order stop.

This may change:

- Daily Task actual minutes
- Task Time Utilization totals
- Non-finalized monthly task-review data
- Non-finalized monthly DTR data after regeneration

This does not change:

- Project task progress
- Project accomplishment
- Task status
- Quality Score
- Finalized DTR snapshots
- Attendance Time In or Time Out values, except through the user's normal attendance action

## Transaction behavior

Attendance Time Out remains the primary operation. The Work Order auto-stop is isolated in a nested transaction so an unexpected Work Order problem does not prevent a valid Attendance Time Out from being recorded.

Stale-session reconciliation is committed only after all affected sessions and Daily Task records are prepared successfully. Errors are rolled back and logged without blocking the user's portal request.

## Recommended pre-deployment check

Before deployment, review the current Live Work Orders panel. Any timer already older than the configured cap may be finalized when normal portal traffic resumes.
