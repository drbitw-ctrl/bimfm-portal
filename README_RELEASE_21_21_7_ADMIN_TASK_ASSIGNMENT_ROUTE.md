# Release 21.21.7 — Administrator Task Assignment Route Repair

This patch replaces the current-administrator task-assignment action with a dedicated static endpoint: `/admin/task-assignment/enable`. It avoids the failing dynamic URL and retains the existing per-account action for other staff accounts. No database migration is added.
