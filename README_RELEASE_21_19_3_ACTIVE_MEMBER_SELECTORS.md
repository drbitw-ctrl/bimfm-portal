# BIMFM Portal Release 21.19.3

## Active portal member selectors

The **Add Previous Overtime** member dropdown now shows only active freelancers who have an active BIMFM Portal account.

Legacy imported identities and unmapped freelancer rows remain in the database for migration, history, and project-assignment compatibility, but they no longer appear in this HR selector.

## Behavior

- Shows only `freelancers.is_active = true`.
- Requires a linked active `freelancer_accounts` record.
- Sorts members alphabetically.
- Prevents manual submission of an inactive or unmapped freelancer ID.
- Does not delete, merge, rename, or rewrite any existing member record.
- Does not change project/task legacy mapping behavior.

## Database impact

- New tables: none
- New columns: none
- Alembic migration: none
- Data backfill: none
- Existing assignments rewritten: no

## Validation

- Python compilation passed.
- Existing Release 21.19.1 API authorization tests passed.
- Existing Release 21.19.2 overnight/attendance tests passed.
- Three active-member selector tests passed.
- Total executable tests: 15 passed.
