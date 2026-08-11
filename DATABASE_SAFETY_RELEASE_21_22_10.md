# Database Safety — Release 21.22.10

Release 21.22.10 is a code-only self-service reporting update.

- New Alembic migration: **NO**
- New table: **NO**
- New column: **NO**
- Schema alteration: **NO**
- Data backfill: **NO**
- Record deletion: **NO**
- Historical attendance rewrite: **NO**
- Historical DTR rewrite: **NO**

The packaged SQLite database is restored byte-for-byte from the Release 21.22.9 baseline before packaging. Deployment commands also exclude local database files from `robocopy`.

The new freelancer-facing endpoints are read-only and restrict DTR access to `dtr.freelancer_id == signed_in_account.freelancer_id`.
