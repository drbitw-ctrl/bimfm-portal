# Database Safety — Release 21.11

Release 21.11 is an application and presentation hotfix only.

## Database changes

- New migration: None
- New tables: None
- New columns: None
- New indexes: None
- Data backfill: None
- Existing Work Order rows rewritten: No

The application reads all active Work Order sessions and presents one current row per freelancer. It does not start, stop, delete, or modify a timer while loading the Dashboard.

The existing Alembic head remains `20260803_0013`.
