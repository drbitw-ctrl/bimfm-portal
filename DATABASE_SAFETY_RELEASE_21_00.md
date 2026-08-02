# Version 21.00 Database Safety

## Schema migration

Version 21.00 adds Alembic revision:

```text
20260802_0008_work_orders_and_reminders
```

Expected deployment log:

```text
Running upgrade 20260802_0007 -> 20260802_0008
```

New tables:

```text
task_work_sessions
task_reminders
```

No existing column is removed or renamed.

## Normal deployment behavior

Deployment does not automatically rewrite or delete:

- Projects or portal tasks.
- Task assignments.
- Task status, progress, completion date, or Quality Score.
- Attendance or DTR data.
- Daily Task history.
- Leave or overtime.
- Payroll or Finance summaries.
- Freelancer or staff accounts.
- HR policies.

## Work-order writes

A freelancer explicitly starting work creates one active work-session record. Stopping work:

1. Calculates elapsed minutes on the server.
2. Stops the work-session record.
3. Creates one linked Daily Task record.
4. Leaves the portal task's management-controlled status and progress unchanged.

A partial unique index prevents more than one active timer for the same freelancer.

## Reminder writes

Sending a reminder creates one `task_reminders` row. In-app delivery is independent of SMTP. Email success or failure is stored with the reminder.

## Protected-account purge

Protected-account deletion is the only intentionally destructive Version 21.00 operation. It does not run automatically.

It requires:

- An authenticated Administrator.
- Review of linked-record counts.
- Exact member-name confirmation.
- Explicit acknowledgement of historical deletion.
- A second confirmation within ten minutes.
- The current Administrator password.
- The exact phrase `PURGE <FREELANCER_CODE>`.

The operation deletes records directly owned by the selected freelancer in one transaction, then deletes the freelancer login and profile. Shared projects and portal tasks remain.

Purging can permanently change attendance, DTR, payroll, utilization, and historical reports. Use it only for confirmed testing accounts and confirm a current production PostgreSQL backup first.

## Rollback

Application rollback can redeploy the previous Git commit. Because Version 21.00 adds tables, do not manually downgrade or delete the tables in production merely to roll back the interface. Leaving the new unused tables in place is safer than destructive schema rollback.

Restore a database backup only when an explicit purge or other production write must be reversed.
