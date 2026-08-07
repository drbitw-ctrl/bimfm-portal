# Database Safety — Release 21.22

Release 21.22 is code-only and does not change the PostgreSQL schema.

It does not add, drop, rename, or alter database tables or columns and does not include a new Alembic migration. Existing attendance, project, task, DTR, Work Order, leave, overtime, payroll, Finance, account, and audit records are not backfilled or rewritten during deployment.

Normal portal operations continue to write records when users perform ordinary actions, such as starting/stopping a Work Order or generating a DTR.

Because there is no schema migration, a Render application rollback does not require a database downgrade for this release.
