# BIMFM Portal Release 20.13 — Historical Quality Score Recovery

**Application version:** `2.3.8-release20.13-quality-score-recovery`  
**Release date:** 2026-08-01  
**Base:** Release 20.12 Editable Task Register

## Purpose

Release 20.13 restores historical task Quality Scores that were preserved in
PostgreSQL task descriptions during the original SQLite migration but were not
copied into the dedicated `portal_tasks.quality_score` column introduced in
Release 20.12.

The user interface and Task Register presentation are unchanged.

## Corrected behavior

A historical task with preserved metadata such as:

```text
Legacy quality score: 90
```

is upgraded to:

```text
portal_tasks.quality_score = 90
```

The Task Register then displays:

```text
90%
```

instead of `Not Rated`.

## Safety rules

The backfill:

- Updates only tasks whose current `quality_score` is null.
- Never overwrites a score entered through the web portal.
- Accepts only whole-number scores from 1 to 100.
- Does not guess, round, or convert invalid historical values.
- Does not delete the preserved source description.
- Can be run safely only once through Alembic; its update logic is also
  idempotent.

## Database migration

Release 20.13 adds one data-only Alembic revision:

```text
20260801_0005 → 20260801_0006
```

It does not add, remove, or rename any table or column.

## Future migration correction

The legacy SQLite import tool now writes valid Quality Scores directly to the
`quality_score` field when that field exists. This prevents the same omission
in future isolated migration work.

Do not rerun the old SQLite-to-PostgreSQL migration on the live database.

## Validation

Release 20.13 passed:

```text
100 tests
0 failures
0 errors
```

An additional Alembic upgrade simulation confirmed that a task at revision
`20260801_0005` with `Legacy quality score: 93` was upgraded to:

```text
quality_score = 93
alembic_version = 20260801_0006
```
