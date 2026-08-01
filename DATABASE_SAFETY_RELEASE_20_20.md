# Database Safety — Release 20.20

Release 20.20 is a presentation and reporting release.

## Schema

```text
New tables:       None
New columns:      None
New indexes:      None
Alembic revision: None
Backfill:         None
```

## Stored-data protection

The release does not automatically modify:

- Portal projects
- Portal tasks
- Task assignments
- Project-member mappings
- Freelancer accounts
- Quality Scores
- Completion dates
- Daily task reports
- Attendance
- DTR
- Leave
- Overtime
- Finance records

The conservative Quality Score formula is applied only in Python when building
Performance and Project Reports. Raw `portal_tasks.quality_score` values remain
unchanged.

Task-table sorting occurs in the browser and does not send a save request.

## Deployment

The existing command remains safe:

```text
pip install -r requirements.txt && alembic upgrade head
```

No Release 20.20 migration line is expected.
