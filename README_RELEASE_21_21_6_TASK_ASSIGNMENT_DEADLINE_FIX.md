# BIM Portal Release 21.21.6

This stabilization release fixes two task-management regressions.

## Fixes

### Administrator task assignment

The Staff Access action is now backed by both:

- the required POST route used by the confirmation form; and
- a safe GET fallback that redirects back to Staff Access instead of returning a raw 404 response.

The POST action creates or refreshes the linked Task Supervisor member identity while preserving the Administrator account and permissions.

### Existing task deadline editing

Full task editing now captures the task's original status before changing form values. This prevents the undefined `previous_status` error that caused an Internal Server Error when editing a deadline or other task details.

Completion notifications continue to be generated only when a task actually transitions into Completed.

## Database impact

- New migration: none
- New table: none
- New column: none
- Data backfill: none
- Existing records rewritten automatically: no

The release uses the staff-to-task-member mapping introduced by migration `20260806_0017`.
