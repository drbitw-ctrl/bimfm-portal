# Database Safety — Release 21.24.1

Release 21.24.1 is an application/reporting-only release.

Verified against Release 21.24.0.2:
- Alembic migration tree: IDENTICAL
- `app/models/`: IDENTICAL
- `app/database.py`: IDENTICAL
- `requirements.txt`: IDENTICAL
- packaged `data/hr.db`: IDENTICAL

Packaged SQLite SHA-256:
`c249cad105139ccbd85bdced8b86263734b152523d02390c18d2bb50fe33f354`

There is no new migration, table, column, backfill, seed, or production data rewrite in this release. The existing 0018 freelancer bank-details migration remains unchanged.
