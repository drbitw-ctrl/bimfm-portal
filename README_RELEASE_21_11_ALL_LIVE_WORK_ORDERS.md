# BIMFM Portal Release 21.11

## All Live Work Orders visibility hotfix

Release 21.11 corrects the management Dashboard so the **Live Work Orders** panel displays every active freelancer timer at the same time.

### Corrected behavior

- Every active freelancer Work Order is returned by the server.
- One card is shown for each freelancer who currently has a running timer.
- The list is not limited to one member.
- Cards automatically reflow across the available Dashboard width.
- The panel refreshes immediately when the page opens.
- The panel refreshes every 15 seconds.
- Returning to the browser tab triggers another immediate refresh.
- Browser and proxy caching are disabled for the live-work endpoint so an old one-member snapshot is not reused.

### Defensive data handling

The database already enforces one active Work Order per freelancer. Release 21.11 also handles a legacy duplicate safely by displaying the newest active session for that member while continuing to show every other active member.

### Preserved behavior

- Work Order start and stop actions are unchanged.
- One freelancer still cannot run two timers simultaneously.
- Administrators and Supervisors retain their existing live-work visibility.
- Reminder actions remain available according to role permissions.
- The attendance Time Out and stale-timer safeguards remain unchanged.
- Release 21.10 July attendance and Monthly Attendance Search fixes are preserved.

## Database impact

No migration is included.

- No tables added or removed.
- No columns or indexes changed.
- No Work Order records rewritten.
- No attendance, DTR, task, project, account, or payroll data changed.

The current Alembic head remains `20260803_0013`.
