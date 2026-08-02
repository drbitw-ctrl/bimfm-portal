# Database Safety — Release 20.23

Release 20.23 does not change the database schema.

## Preserved data

The release does not automatically modify or rewrite:

- Projects
- Portal tasks
- Task assignments
- Freelancer accounts
- Quality Scores
- Daily Task reports
- Attendance and DTR records
- Leave and overtime records
- Finance records
- HR policy values

## Staff account deletion

Permanent staff-account deletion is an explicit Administrator action. It is
blocked when the account:

- Is the current signed-in account
- Is the last active Administrator
- Is referenced by any table column linked to `hr_admin_accounts.id`

Referenced accounts must be disabled to preserve operational attribution.

## Time-utilization estimate

The completion-date fallback is calculated at report-read time only. It does not
insert or update Daily Task rows and does not write estimated minutes to the
database.
