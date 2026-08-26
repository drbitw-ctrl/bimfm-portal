# BIM Portal Release 21.24.3.1 — Dashboard Leave Availability Hotfix

## Purpose
Correct the Team Command Center availability board so a member with an approved leave record for the member's current local date is not presented as Available.

## Behavior
- Approved leave today creates a dedicated **On Leave Today** lane.
- On-leave members are removed from **Available Now**.
- The existing member-card layout is retained.
- The card shows the approved leave type, approved duration, and any active task count that remains assigned.
- If a member has an active Work Order/live work session, **Working Now** takes precedence over the leave display because actual live activity is occurring.
- No leave records, attendance records, tasks, or assignments are changed by this release.

## Visual treatment
Leave is treated as an informational status rather than a warning/error:
- soft violet lane
- violet status badge
- English: On Leave / On Leave Today
- Traditional Chinese: 請假中 / 今日請假

## Database
No database schema or data changes. No migration.
