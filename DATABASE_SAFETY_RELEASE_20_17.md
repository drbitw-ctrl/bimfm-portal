# Database Safety — Release 20.17

## Schema

Release 20.17 introduces no database schema change and no new Alembic revision.
The existing build command remains safe:

```text
pip install -r requirements.txt && alembic upgrade head
```

## Controlled directory repair

At startup, the application checks HR freelancer accounts against
`project_member_directory`.

For an HR freelancer that has no assignable project-member row, it performs one
of the following:

- Maps an existing unmapped source member with the same normalized name; or
- Creates a portal-native directory row linked to the freelancer's PostgreSQL ID.

This repair is limited to member identity and assignment availability.

## Data not modified by the repair

The startup repair does not rewrite:

- Projects
- Existing tasks
- Existing task assignments
- Progress or Quality Scores
- Attendance or DTR records
- Leave or overtime records
- Payroll or Finance results

## Existing assignment protection

Imported project-member rows keep their `source_freelancer_id`. When mapped to
an HR account, historical assignments remain attached to the original source
identity and are resolved to the HR freelancer by the existing assignment
resolution logic.

## Backup recommendation

As with every production deployment, confirm a current PostgreSQL backup before
pushing the release. No manual data migration or database reset is required.
