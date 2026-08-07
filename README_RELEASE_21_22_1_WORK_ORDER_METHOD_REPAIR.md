# Release 21.22.1 — Work Order Method Repair

This is a code-only hotfix for the `{"detail":"Method Not Allowed"}` response encountered while Belinda was opening or stopping a Work Order.

- Start and Stop state changes remain POST-only and CSRF-protected.
- Accidental GET navigation to those action URLs now redirects safely to the Work Orders page instead of returning FastAPI's JSON 405 response.
- Belinda's task-hourly mode and monthly task-time ledger are unchanged.
- No database migration, schema change, data backfill, or data rewrite is included.
