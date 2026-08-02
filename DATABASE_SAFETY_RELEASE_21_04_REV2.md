# Release 21.04 Revision 2 — Database Safety

Release 21.04 Revision 2 changes interface layout, management-report wording,
and the Finance attendance population query only.

```text
New tables: None
New columns: None
New indexes: None
New Alembic migration: None
Data backfill: None
```

The release does not automatically modify:

- freelancer accounts;
- attendance or DTR records;
- projects, tasks, assignments, or Work Orders;
- stored task Quality Scores;
- payroll, leave, overtime, or HR policies.

The management reporting score is calculated only when reports are built. The
original task rating remains stored unchanged.
