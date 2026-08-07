# Database Safety — Release 21.22.3

This release is code-only.

- No Alembic revision was added.
- No tables are created, dropped, or renamed.
- No columns are created, dropped, or renamed.
- No production data backfill is included.
- No attendance, leave, OT, DTR, Finance, payroll, project, task, or account row is automatically rewritten by this release.

The payroll presentation reads the already-existing `MonthlyDTR.absent_days` value and includes it in salary-coverage calculations at runtime.

Render application rollback does not require a database downgrade for this release.
