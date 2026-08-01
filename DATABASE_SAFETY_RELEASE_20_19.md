# Database Safety — Release 20.19

## Schema

Release 20.19 introduces no database schema change and no new Alembic revision.
The existing build command remains safe:

```text
pip install -r requirements.txt && alembic upgrade head
```

## Dashboard queries

The Team Command Center reads existing PostgreSQL records from:

- Active freelancer profiles
- Portal task assignments
- Portal tasks
- Portal projects
- Existing project-member mappings
- Today’s attendance records

The Dashboard does not write to these records.

Legacy imported assignment identities are resolved using the existing
project-member mapping logic. Duplicate task assignment rows are collapsed in
memory by task ID for display purposes only.

## Availability definition

Dashboard availability is derived from active task assignments:

- **Available:** zero active tasks
- **Busy:** one or more active tasks

Attendance status is shown separately and does not change the workload-derived
Available or Busy classification.

## Tasks register presentation

The smaller Progress bar and removal of duplicate percentage text are HTML and
CSS changes only. They do not change:

- `portal_tasks.progress`
- `portal_tasks.quality_score`
- Quick-edit validation
- Quick-edit permissions
- Audit records
- Performance calculations

## Preserved data behavior

Release 20.19 does not rewrite:

- Projects
- Tasks or assignments
- Member mappings
- Progress or Quality Scores
- Attendance or DTR records
- Leave or overtime records
- Payroll or Finance results

## Backup recommendation

Confirm a current PostgreSQL backup before deployment. No manual migration,
database reset, or backfill is required.
