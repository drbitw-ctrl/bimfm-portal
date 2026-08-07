# BIM Portal Release 21.22.4

## Comp Credit Can Cover ABSENT Days

Approved compensatory credit now offsets payroll deductions in this order:

1. Approved leave minutes
2. ABSENT minutes
3. Any remaining unused credit carries forward

This supports cases where a freelancer and administrator forgot to submit a leave request for an otherwise absent scheduled workday.

### Accounting behavior

The DTR generator creates or updates one auditable monthly compensatory-credit debit transaction with transaction type `USED_ABSENCE`. The source key is deterministic and month-specific, so regenerating a non-finalized DTR does not duplicate the deduction.

If attendance is later corrected and the absence disappears, regenerating the DTR reduces or removes the automatic absence-credit transaction.

Comp credit never raises payroll above 100%.

## Database safety

There is no Alembic migration, no new table, no new column, no backfill, and no bulk rewrite. Normal DTR generation may create/update/delete the existing `comp_leave_transactions` ledger row used to cover absence, which is the intended business transaction and uses the existing schema.
