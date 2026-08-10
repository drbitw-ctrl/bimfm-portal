# BIMFM Portal Release 21.20.2

## Overtime approval correction

Final verified overtime is no longer capped by the originally planned minutes. It is capped by the verified actual duration and the active HR policy maximum.

For Carlo's case:

- Planned: 18:00–23:00 = 300 minutes
- Verified actual end: 02:30 next day
- Verified actual duration: 510 minutes
- Correct approved OT: 510 minutes
- Correct comp credit: 510 minutes

Already-approved records can be corrected by an Administrator using **Adjust approved overtime**. The existing comp-credit transaction is updated instead of adding a duplicate transaction.

## Overtime credit balances

A new page is available at:

`/admin/overtime/credits`

It displays active portal members and their:

- total earned credit;
- used credit;
- available balance;
- whole 8-hour redeemable days;
- remaining minutes; and
- latest credit activity.

## Database impact

No new table, column, migration, or backfill is included. Existing approved OT is changed only when an Administrator submits the adjustment form.
