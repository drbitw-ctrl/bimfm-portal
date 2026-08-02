# BIMFM Portal Version 21.00

**Application version:** `3.0.0-release21.00-work-order-operations`  
**Release type:** Major operations workflow, localization, account cleanup, and notification release

## Purpose

Version 21.00 changes freelancer time reporting from manual time entry to a work-order timer. A freelancer opens an assigned task, starts work, and stops the timer when changing or ending the work session. The recorded duration is written into the existing Daily Task data used by DTR and Task Time Utilization.

This release also adds real-time work visibility for Administrators and Supervisors, email-style task reminders, a controlled two-step override for protected freelancer deletion, stronger dashboard state colors, more complete Traditional Chinese presentation, and compact project-operation page headers.

## Freelancer work orders

The former Daily Tasks page is presented as **Work Orders**. Manual freelancer time-entry, editing, and deletion routes are disabled so actual time is generated only by the Start/Stop workflow.

A freelancer can:

1. Open an active assigned task.
2. Select **Start working**.
3. Work with one active timer.
4. Select **Stop and record time** when changing tasks or ending the work session.
5. Optionally add a brief work note.

The server calculates elapsed time. Partial minutes are rounded upward and a genuine stopped session records at least one minute.

Only one active work timer is allowed for each freelancer. A second task cannot be started until the current timer is stopped.

## Data written by the timer

Stopping a work order creates:

- One stopped `task_work_sessions` record.
- One linked `daily_tasks` record containing the calculated minutes.
- A link between the work session, freelancer, portal task, and project.

The resulting Daily Task record is automatically included in:

- Monthly DTR data.
- Daily Task history.
- Task Time Utilization.
- Project-level actual-time totals.

## Project accomplishment remains management-controlled

Starting or stopping a timer does **not** change:

- Portal task status.
- Portal task progress.
- Portal task completion date.
- Project accomplishment.
- Project progress.

The timer copies the current management-entered progress into the time record for context only. Project and task accomplishment continue to depend on Administrator task editing and the project-list controls.

## Live work visibility

Administrators and Supervisors can see active work timers in:

- The Dashboard **Working now** panel.
- Freelancer workload cards.
- **Team Availability**.
- `/portal/live-work.json` used by the portal's live dashboard refresh.

The board shows:

- Freelancer name and code.
- Current project.
- Current task.
- Discipline.
- Start time.
- Live elapsed time.
- Current Administrator-controlled progress.

Elapsed clocks update every second in the browser. The active-session list refreshes from the server every 15 seconds.

## Email-style task reminders

Administrators and Supervisors can select **Remind** from an open task or a live work card.

Every reminder is delivered to the freelancer's in-app reminder inbox. When SMTP is configured and the freelancer has an email address, the portal also attempts to send an email copy.

Optional Render environment variables:

```text
BIMFM_SMTP_HOST
BIMFM_SMTP_PORT
BIMFM_SMTP_USERNAME
BIMFM_SMTP_PASSWORD
BIMFM_SMTP_FROM_EMAIL
BIMFM_SMTP_USE_TLS
```

SMTP credentials must be stored only in Render Environment settings and must never be committed to GitHub. When SMTP is not configured or delivery fails, the in-app reminder remains available and the delivery result is recorded.

## Two-step protected-account deletion

Protected freelancer accounts are no longer permanently hard-locked from deletion. Administrators may explicitly override the protection through two verification steps.

### Step 1 — Review and acknowledge

The portal shows the linked-record counts, including attendance, DTR, Daily Tasks, payroll, leave, overtime, assignments, work timers, reminders, and project-member links.

The Administrator must:

- Enter the member's complete name.
- Acknowledge that linked history will also be removed.

### Step 2 — Re-authenticate and purge

Within ten minutes, the Administrator must:

- Enter the current Administrator password.
- Enter `PURGE <FREELANCER_CODE>` exactly.

The purge runs in one database transaction. It removes records directly owned by the selected freelancer, the login account, and the freelancer profile. Shared portal projects and shared portal tasks remain. Other freelancers' assignments remain.

This is an irreversible cleanup tool intended for testing accounts. Purging a real account can change attendance, payroll, DTR, utilization, and historical reports. A current PostgreSQL backup must be confirmed before using it.

## Traditional Chinese improvements

Dynamic values are translated in Traditional Chinese, including:

- Normal, Urgent, High, Medium, Low, and Critical priorities.
- Assigned, Available, Busy, and Working Now states.
- No active task, No active timer, and assignment-health states.
- Attendance states and operational card labels.
- Team Availability table values.
- Dashboard cards, legends, action areas, and quick-launch labels.
- Work Orders, reminders, and protected-deletion screens.

Member names, project names, task descriptions, company names, and technical labels such as PostgreSQL, DTR, OT, AR, ST, MEP, GE, API, and Excel remain unchanged.

## Compact project-operation headers

The top sections for these staff pages use one consistent compact layout:

- Tasks.
- Team Availability.
- Active Tasks.
- Recently Completed Tasks.
- Projects.

The page title, description, action buttons, and summary figures are grouped into a smaller header so the working table appears higher on the screen.

## Stronger dashboard state colors

Freelancer cards now use stronger state treatments:

- Green: available for assignment.
- Blue: actively timing work.
- Yellow: assigned work but no active timer.
- Red: overdue work requiring attention.

The existing workload logic is unchanged; only the visual differentiation is strengthened.

## Database changes

Version 21.00 adds Alembic revision `20260802_0008` and two tables:

```text
task_work_sessions
task_reminders
```

It does not rewrite existing project, task, quality, attendance, DTR, leave, overtime, payroll, or HR-policy data during deployment.

## Validation

Version 21.00 passed 52 integrated workflow assertions with 0 failures and 0 errors, plus the following static and migration checks:

- Python compilation across the application.
- Parsing of all 43 Jinja templates.
- JavaScript syntax checks.
- English and Traditional Chinese catalog parity.
- Upgrade from a real Version 20.23 schema at revision `20260802_0007`.
- Rejection of manual freelancer time entry.
- Work-order start and stop workflow.
- One-active-timer enforcement.
- Server-calculated duration and Daily Task creation.
- Task progress/status preservation.
- Task Time Utilization data compatibility.
- Administrator and Supervisor live-work access.
- In-app reminder delivery and optional-email state.
- Freelancer reminder inbox.
- Traditional Chinese priority, availability, and compact page-header labels.
- Two-step protected-account purge.
- Preservation of shared projects, shared tasks, and other member assignments.
