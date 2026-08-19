# Database Safety — Release 21.23.1.2

Release 21.23.1.2 contains application/reporting changes only.

## Verified unchanged from the uploaded Release 21.22.10 Render baseline

- `alembic/` migration tree
- `app/models/`
- `app/database.py`
- `requirements.txt`
- bundled `data/hr.db`

Bundled SQLite SHA-256 in both 21.22.10 baseline and 21.23.1.2:

`c249cad105139ccbd85bdced8b86263734b152523d02390c18d2bb50fe33f354`

## No database action in this release

There is no new migration, schema modification, data correction, seed, or backfill.

Administrator exclusion is applied only while building the Ratings report.
Review time is read from existing stopped review `TaskWorkSession` records and added only in utilization reporting calculations.

Production PostgreSQL data must not be replaced with the bundled SQLite database.
