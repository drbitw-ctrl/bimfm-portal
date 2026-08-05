# Database Safety — Release 21.04

Release 21.04 changes only reporting-selection logic.

```text
New tables: None
New columns: None
New indexes: None
New Alembic revision: None
Data backfill: None
Attendance rewrite: None
DTR rewrite: None
Account rewrite: None
```

The query now joins active freelancer profiles to active freelancer login
accounts before computing Finance My Work attendance and DTR summaries.
