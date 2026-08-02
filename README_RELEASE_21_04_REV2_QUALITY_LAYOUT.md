# BIMFM Portal Release 21.04 Revision 2

**Application version:** `3.0.4-release21.04-r2-quality-layout`  
**Source base:** Release 21.04 Finance attendance-population hotfix  
**Release type:** Resent cumulative hotfix with Tasks-table layout and quality-report wording improvements

## Purpose

Release 21.04 Revision 2 preserves the corrected Finance Head attendance
population from the original 21.04 package and fixes the Tasks register layout
so Progress and Quality remain visually separate at normal desktop widths.

## Finance attendance population

The Finance My Work page continues to include only freelancer profiles that:

- are active;
- have a freelancer login account; and
- have an active login account.

Legacy project-import placeholders and disabled accounts remain excluded.

## Tasks table layout

The Tasks register now uses semantic widths based on column names instead of
column positions. This remains correct whether the optional Action column is
present or absent.

The Progress column now:

- has a dedicated wider column;
- stacks its percentage control/value above the progress bar;
- constrains the bar to the Progress cell; and
- cannot enter or overlap the Quality column.

The Quality column now:

- has its own fixed width;
- keeps the percentage value or inline selector fully inside the cell; and
- remains separate from the Progress bar.

The Project and final columns retain their sticky behavior.

## Quality reporting presentation

Management reports continue to use the established conservative management
reporting scale so unusually high task ratings do not dominate rankings.
Original task ratings remain unchanged in task records.

Prominent interface headings now use the simpler label **Quality Score** rather
than the technical word **Calibrated**. A concise note remains visible stating
that reports use a management reporting scale and preserve original task
ratings. This avoids presenting a transformed score as if it were the untouched
raw entry.

The existing reporting calculation is unchanged:

`Management reporting score = original task rating × 0.70 + 22, maximum 92`

## Database compatibility

- No new tables
- No new columns
- No Alembic migration
- No data backfill
- No Quality Score rewrite
- No attendance or DTR rewrite

## Validation

Release 21.04 Revision 2 passed Python compilation, application import, Jinja
template parsing, JavaScript syntax checks, English/Traditional Chinese catalog
parity, Finance-population regression testing, task-column contract checks, and
visible quality-label checks.
