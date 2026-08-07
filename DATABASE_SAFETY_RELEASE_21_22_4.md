# Database Safety — Release 21.22.4

This release contains no schema migration.

It does not add/drop/rename tables or columns and does not rewrite historical records in bulk.

The only new database write is part of normal DTR generation: an idempotent `USED_ABSENCE` compensatory-credit ledger transaction may be created or adjusted for a member/month when approved credit covers ABSENT time. The transaction uses the existing `comp_leave_transactions` table and a deterministic source key, so DTR regeneration cannot create duplicates.
