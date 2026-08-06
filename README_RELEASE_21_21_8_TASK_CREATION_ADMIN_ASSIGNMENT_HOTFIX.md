# Release 21.21.8

Code-only hotfix for two production regressions:

1. New task creation crashed because `task.status` was read before `task` existed.
2. Administrator task assignment crashed when an older deployed ORM model did not expose `task_freelancer_id`.

The administrator mapping now uses a deterministic task-supervisor code (`TS-<account id>`) and does not require a schema change.

No Alembic migration, table change, column change, data deletion, or backfill is included.
