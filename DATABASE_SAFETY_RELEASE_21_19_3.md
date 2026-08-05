# Database Safety — Release 21.19.3

This release is query-only with respect to member selection.

It does not add or alter database schema, delete legacy members, merge duplicate records, or rewrite freelancer/account mappings. The old integration records remain available internally.

The historical overtime POST endpoint now rejects any freelancer ID that is not both:

1. an active `freelancers` record, and
2. linked to an active `freelancer_accounts` record.

No Alembic migration is required.
