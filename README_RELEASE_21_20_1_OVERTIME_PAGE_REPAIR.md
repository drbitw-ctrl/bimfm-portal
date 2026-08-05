# Release 21.20.1 — Overtime Page Repair

This patch repairs the Release 21.20 Overtime Approval Center regression.

## Fixes

- The Add Previous Overtime form now submits to the registered `/admin/overtime/historical` endpoint.
- The active, mapped freelancer list is passed to the template, so the Member dropdown is populated.
- The approval register defaults to showing all statuses for the selected month, preventing pending or recently approved claims from appearing to disappear.
- Month and status filters are restored.
- Overtime claims are shown newest first.
- Release 21.20 overnight actual-time and approved-minute behavior remains unchanged.

No database migration or data backfill is required.
