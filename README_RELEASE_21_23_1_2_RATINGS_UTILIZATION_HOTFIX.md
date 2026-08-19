# BIM Portal Release 21.23.1.2 — Ratings & Utilization Hotfix

## Scope

This Render release is based on Release 21.23.1.1 and makes two reporting-only changes requested for production use.

### 1. Administrator accounts are excluded from Ratings

The Performance / Ratings reporting layer now excludes identities representing `HRAdminAccount` rows whose role is `ADMIN`.

The exclusion covers both supported administrator-to-task identity forms:

- a direct `HRAdminAccount.task_freelancer_id` link; and
- the deterministic internal review/task identity `TS-###` created for that administrator.

This is a report-time filter only. No administrator, freelancer, assignment, task, score, or historical record is deleted or modified.

Supervisor and Finance roles are not excluded by this change because the request specifically targets Administrator accounts.

### 2. Project Utilization includes saved review time

Task Time Utilization now calculates utilization effort as:

`Production time + Saved review time`

Production time remains:

- recorded Work Order / linked Daily Task time when available; or
- the existing Start-to-Completion reporting estimate for completed tasks that have no recorded production time.

Saved review time comes from already-existing stopped Review Work Order timer sessions. Active review timers are included after they are stopped and their duration is saved.

The utilization page and Excel export now show Production Time and Review Time separately while using their combined total for utilization.

## Database boundary

No schema or data migration is introduced.

- No Alembic revision
- No model change
- No table change
- No column change
- No database backfill
- No seed data
- `app/database.py` unchanged from Release 21.22.10
- `requirements.txt` unchanged from Release 21.22.10
- bundled `data/hr.db` restored byte-for-byte from Release 21.22.10

Production PostgreSQL remains the authoritative database.

## Validation

- Python compilation: PASS
- Full pytest regression suite: 109 passed, 0 failed
- Administrator ratings exclusion regression: PASS
- Recorded production + review utilization regression: PASS
- Completion fallback + review utilization regression: PASS
- Database/model/migration comparison against Release 21.22.10: PASS
