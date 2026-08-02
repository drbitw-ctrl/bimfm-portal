# BIMFM Portal Release 21.06

**Version:** `3.0.6-release21.06-password-work-order-safeguard`  
**Release date:** 2026-08-02

## Purpose

Release 21.06 fixes self-service password changes for every account type, renames the staff sign-in page to **Administration Login**, and introduces Administrator-controlled fallback protection for forgotten Work Order timers.

## 1. Password change fix for all accounts

The Supervisor password page route was already permitted, but the read-only Supervisor presentation rule hid every POST form that was not explicitly marked as a self-service exception. This caused the password form to disappear even though the account was correctly redirected to the page.

The Change Password form is now explicitly allowed for self-service use.

Validated account types:

- Administrator
- Supervisor
- Finance Head
- Freelancer

Each account can change only its own password. Administrator-only reset permissions remain unchanged.

### Forced first-login flow

New and reset accounts still follow the existing security process:

1. Sign in with the temporary password.
2. Redirect to Change Password.
3. Enter the current temporary password.
4. Create and confirm a personal password.
5. Continue to the appropriate workspace.

## 2. Administration Login wording

The staff login page now displays:

- **Administration Login**
- **Administration Access**
- Authorized administration, supervision, and finance access.
- Sign in to Administration

The Freelancer Login page now links to **Administration Login** instead of **HR Administrator Login**.

This wording covers Administrator, Supervisor, and Finance Head accounts without implying that the page belongs only to HR.

## 3. Administrator-only Work Order fallback

Release 21.06 adds two safeguards for forgotten active Work Order timers.

### Attendance Time Out safeguard

When a freelancer records Attendance Time Out while a Work Order is active, the portal automatically:

- Stops the active Work Order at the official Attendance Time Out timestamp.
- Calculates the elapsed time.
- Creates the linked Daily Task record.
- Updates Task Time Utilization data.
- Invalidates non-finalized monthly task-review and DTR snapshots so they can be regenerated with the corrected time.

The freelancer still uses the normal Start Working and Stop and Record Time controls. No fallback option, instruction, or timer-cap explanation is displayed in the freelancer interface.

### Stale timer safeguard

If a freelancer does not record Time Out and leaves a Work Order active, the system performs a low-frequency background check during normal portal traffic.

By default:

- A Work Order is capped after **16 hours**.
- The reconciliation check runs at most once every **5 minutes** per application process.
- The session is stopped at the configured cap rather than at the later detection time.
- A Daily Task record is created from the capped duration.
- Non-finalized task-review and DTR snapshots are invalidated.
- An Administrator audit entry is recorded.

The safeguard audit actions are omitted from the Supervisor dashboard activity stream. Administrators retain the audit record.

Optional environment settings:

```text
BIMFM_WORK_ORDER_MAX_ACTIVE_HOURS=16
BIMFM_WORK_ORDER_RECONCILE_INTERVAL_SECONDS=300
```

Accepted limits:

- Maximum active hours: 8–24 hours
- Reconciliation interval: 60–3600 seconds

## Database impact

No schema migration is added.

The Alembic head remains:

```text
20260802_0009
```

Deployment does not bulk-rewrite historical records. Runtime behavior can close an existing active Work Order when either condition occurs:

- The freelancer records Attendance Time Out.
- The active session already exceeds the configured maximum duration and the background safeguard runs.

Stopped safeguard sessions create normal Daily Task records and therefore affect Task Time Utilization and regenerated non-finalized DTR data.

Finalized DTR records are not deleted by the invalidation logic.

## Preserved features

Release 21.06 includes all Release 21.05 functionality, including:

- Role-based My Work pages
- Correct Finance attendance population
- Finance DTR generation
- Work Order timer system
- Task Time Utilization project metrics
- Modern Reminder Calendar
- HR Calendar holidays
- Task status colors and legends
- Progress and Quality column separation
- Official BIMFM Technology branding
- First-login password replacement
- Administrator-only account password reset

## Validation summary

- Password changes passed for Administrator, Supervisor, Finance Head, and Freelancer accounts.
- Supervisor Change Password form is visible and submit-enabled.
- First-login forced-password redirects passed.
- Administration Login wording passed.
- Attendance Time Out automatically stopped an active Work Order.
- Linked Daily Task creation passed.
- Stale Work Order 16-hour cap passed.
- Administrator audit creation passed.
- 48 Jinja templates parsed.
- 1,816 English and 1,816 Traditional Chinese localization keys matched.
- Python compilation passed.
- JavaScript syntax checks passed.
- Alembic head remained `20260802_0009`.
