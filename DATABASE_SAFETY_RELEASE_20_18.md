# Database Safety — Release 20.18

## Schema

Release 20.18 introduces no database schema change and no new Alembic revision.
The existing build command remains safe:

```text
pip install -r requirements.txt && alembic upgrade head
```

## Discipline labels

The AR and ST change is a presentation rule. Existing portal task and project
values such as `Architecture` and `Structure` are not automatically rewritten.

Administrator task forms retain the established stored values while displaying
AR and ST as the option labels. Existing MEP, GE, and other discipline values
remain unchanged.

## Quality presentation

Removing the Quality percentage bar changes only HTML and CSS presentation.
It does not change:

- `portal_tasks.quality_score`
- Quality Score validation
- Quick-edit permissions
- Audit records
- Performance calculations

## Preserved data behavior

Release 20.18 does not rewrite:

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
