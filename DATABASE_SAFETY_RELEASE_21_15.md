# Database Safety — Release 21.15

## Scope

Release 21.15 performs a targeted correction for Gabrielle Gameng's July 2026 compensatory-leave calculation.

## Records changed

The migration may update or create only the following records associated with Gab:

- July 1, 2026 leave record
- July 2, 2026 leave record
- July 3, 2026 leave record
- July 6, 2026 leave record
- Compensatory-credit ledger transactions required for two complete leave-day credits
- Non-finalized July 2026 DTR snapshot and its dependent snapshot rows
- One system audit-log entry

## Credit protection

Existing approved-overtime ledger credits are counted first. The migration adds only the shortfall needed to provide two whole 8-hour compensatory credits. It does not blindly add another 960 minutes when the existing overtime ledger already contains sufficient credit.

## Result

- Four approved July leave dates remain recorded.
- Two leave days are covered by compensatory credits.
- Two leave days remain deductible.
- Existing attendance punches are not modified.
- Existing approved overtime claims are not modified.
- Existing task, project, payroll, password, account, and Work Order records are not modified.

## Finalized DTR protection

Finalized DTR snapshots are preserved. Only non-finalized July DTR snapshots are invalidated so they can be regenerated using the corrected source records.

## Backup recommendation

Confirm that the paid Render PostgreSQL database and current backup process are active before deployment. The migration is idempotent through stable transaction source keys and an Alembic revision lock.
