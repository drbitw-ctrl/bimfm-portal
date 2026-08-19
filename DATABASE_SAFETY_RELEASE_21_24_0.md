# Database Safety — Release 21.24.0

## Important difference from Releases 21.23.x

Release 21.24.0 intentionally contains **one additive database schema migration** because editable freelancer bank details must persist securely in the portal database.

### New migration

- `alembic/versions/20260819_0018_freelancer_bank_details.py`
- Revises: `20260806_0017`

### Columns added to `freelancers`

All are nullable:

- `bank_account_name` VARCHAR(200)
- `bank_account_number` VARCHAR(120)
- `bank_name` VARCHAR(200)
- `bank_swift_code` VARCHAR(50)
- `bank_branch_address` TEXT

### What the migration does NOT do

- No table deletion
- No row deletion
- No existing-column rename
- No existing-column type change
- No backfill
- No update to existing freelancer values
- No attendance changes
- No DTR changes
- No leave/overtime changes
- No project/task changes
- No payroll changes
- No screen-sharing storage

### Validation performed

A temporary database was migrated to revision `20260806_0017`, an existing freelancer record was inserted, and the database was upgraded to `20260819_0018`.

Before upgrade:

`SAFE-001 | Existing Freelancer | safe@example.com`

After upgrade:

The same ID, freelancer code, name, and email remained unchanged. The five new bank fields were all NULL.

Alembic revision after upgrade: `20260819_0018`.

The packaged `data/hr.db` is restored byte-for-byte to the Release 21.23.1.2 input copy and is not pre-migrated or seeded by this release.

SHA-256 of packaged `data/hr.db`:

`c249cad105139ccbd85bdced8b86263734b152523d02390c18d2bb50fe33f354`

## Production deployment

Your Render PostgreSQL remains authoritative. The existing build command:

`pip install -r requirements.txt && alembic upgrade head`

will apply revision 0018 once.

## Rollback guidance

For a quick application rollback, use Render's previous successful deployment and **leave migration 0018 in the database**. Older application code ignores the extra nullable columns.

Do not run an Alembic downgrade merely to roll back the UI/application. A schema downgrade would drop the five bank-detail columns and any bank values entered after deployment.

If performing a Git-based code rollback later, keep the `20260819_0018_freelancer_bank_details.py` migration file in the repository so Alembic still recognizes the database's current revision.
