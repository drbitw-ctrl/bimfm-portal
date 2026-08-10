# Database Safety — Release 21.19.2

Alembic revision: `20260805_0016`.

Adds one table: `attendance_correction_requests`.

Adds four fields to `daily_attendance`: missed-time-out flag, missed-work-order-stop flag, overtime-unavailable flag, and exception timestamp.

Adds two fields to `task_work_sessions`: missed-stop flag and exception timestamp.

The migration does not rewrite existing attendance, overtime, Work Order, leave, DTR, Finance, project, task, password, or account data. Existing records receive safe false/null defaults.
