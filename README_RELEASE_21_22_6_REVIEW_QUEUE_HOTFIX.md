# Release 21.22.6 — Review Queue Production Hotfix

Cumulative replacement for 21.22.5, based on the same review-queue feature set and compatible with the stable 21.22.4 database.

Fixes the `/admin` 500 caused by `review_minutes_by_task()` referencing `HRAdminAccount.task_freelancer_id` on a deployed model that does not expose that ORM attribute.

The review subsystem now uses the existing deterministic `TS-<admin id>` task-supervisor mapping and review-session `reviewer=<admin id>` markers. It does not require a schema migration.

Validation: Python compile PASS; 72 executable tests PASS.
