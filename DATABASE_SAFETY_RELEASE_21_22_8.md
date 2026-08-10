# Database Safety — Release 21.22.8

Release 21.22.8 contains **no new database migration**.

Deployment does not add/drop/rename tables or columns and does not backfill, delete, merge, or rewrite existing production records.

Normal application use can create ordinary operational records already supported by the current schema, including review assignment markers and review Work Order sessions. If a staff reviewer does not yet have its deterministic internal `TS-*` timer identity, starting review work can create that ordinary `freelancers` row. This is application data, not a schema change.

The release intentionally excludes `TS-*` staff identities from Daily Time Record generation and does not delete any previously generated DTR records.
