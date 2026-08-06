# Database Safety — Release 21.21.6

Release 21.21.6 contains no new Alembic revision and performs no automatic backfill.

It changes request handling only:

- enabling a Task Supervisor mapping when an Administrator explicitly submits the Staff Access form;
- safely redirecting accidental GET requests to that action; and
- preventing task edit failures before the existing transaction commits.

Existing projects, tasks, assignments, attendance, leave, overtime, DTR, Finance, payroll, and audit records are not rewritten during deployment.
