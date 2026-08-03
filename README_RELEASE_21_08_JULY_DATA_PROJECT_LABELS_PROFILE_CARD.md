# BIMFM Portal Release 21.08

## Purpose

Release 21.08 applies the confirmed July 2026 leave correction, backfills the five task start dates supplied in the updated All Tasks workbook, removes internal project identifiers from Project Team tables, and modernizes the freelancer Dashboard identity card.

## July 2026 attendance correction

The deployment applies these confirmed leave records to the portal:

- Gabrielle Gameng — July 1, 2, 3, and 6, 2026
- Carlo Ninoy Nilo — no leave on July 27, 2026

During migration, an existing Carlo leave record and request for July 27 are removed. Missing Gabrielle leave records are inserted as approved whole-day leave records. Non-finalized July DTR snapshots for the affected members are invalidated so they can be regenerated with the corrected data. Finalized DTR snapshots are not automatically altered.

The supplied July workbook does not contain actual Time In or Time Out values and its Member Code fields remain blank. Therefore, Release 21.08 does not fabricate or import attendance punches. The corrected workbook is provided separately for completion before any full historical-attendance import.

## Task start-date backfill

The five dates stored in the supplied Excel workbook are applied only when the corresponding portal task still has no Start Date:

| Task ID | Task | Start Date |
|---:|---|---|
| 233 | AS Modelling (1F-6F) | 2025-06-16 |
| 234 | MEP Modelling (Gas System) | 2025-06-20 |
| 235 | MEP File Separation | 2025-07-03 |
| 236 | AS model modification | 2025-07-15 |
| 237 | Family Modification | 2025-07-22 |

Existing non-empty Start Dates are not overwritten.

The dates are preserved exactly as supplied. Task IDs 236 and 237 have Start Dates later than their listed deadlines/completion dates in the workbook; management should confirm whether those historical dates are intentional.

## Project Team table cleanup

Internal project identifiers such as `220-1f7d9a53` remain stored in the database but are no longer displayed in the Project Team tables.

The following tables now show only the actual project name and number:

- Project Register
- Open Tasks and Assignees

Freelancer/member codes are unchanged because they identify people rather than projects.

## Freelancer Dashboard identity card

The freelancer Dashboard now uses a modern identity card showing:

- Full name
- Freelancer code
- Join date
- Account-active indicator
- Account timezone

The card is responsive and uses the current BIMFM visual system.

## Database impact

Release 21.08 adds Alembic revision `20260803_0011`.

No new tables, columns, or indexes are created. This is a controlled data migration that:

- removes Carlo's July 27 leave record/request when present;
- creates missing Gabrielle leave records for July 1–3 and 6;
- invalidates affected non-finalized July DTR snapshots;
- fills five blank task Start Dates.

No project names, project identifiers, assignments, progress, Quality Scores, Work Orders, passwords, or attendance punches are rewritten.

## Version

`v3.0.8-release21.08-july-data-project-labels-profile-card`
