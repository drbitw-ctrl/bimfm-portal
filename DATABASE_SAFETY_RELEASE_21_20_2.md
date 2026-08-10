# Database Safety — Release 21.20.2

- New migration: none
- New tables: none
- New columns: none
- Automatic data backfill: none
- Existing OT records rewritten at deployment: no
- Existing comp-credit transactions rewritten at deployment: no

When an Administrator adjusts an approved OT claim, the portal updates the existing `OVERTIME_CLAIM:<id>` credit transaction. It does not create a second credit transaction.
