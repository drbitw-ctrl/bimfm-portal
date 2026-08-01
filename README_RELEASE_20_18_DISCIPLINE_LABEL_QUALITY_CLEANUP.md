# BIMFM Portal Release 20.18

**Application version:** `2.3.13-release20.18-discipline-label-quality-cleanup`  
**Release date:** 2026-08-01  
**Source base:** Release 20.17 task table and member assignment fixes

## Purpose

Release 20.18 makes two focused presentation changes without expanding the
inline-edit scope introduced in Release 20.16:

1. Quality keeps its percentage value and inline dropdown but no longer shows a
   percentage bar.
2. Architecture and Structure are displayed consistently as **AR** and **ST**
   throughout the portal.

## Quality presentation

On the Tasks sidebar page:

- Quality remains editable inline.
- The selected whole-number percentage remains visible.
- `Not Rated` remains available.
- The Quality percentage bar is removed.
- The Progress percentage bar remains unchanged.

The quick-edit API, validation, permissions, audit logging, and database field
remain unchanged.

## Discipline presentation

Portal presentation now uses these compact labels:

| Stored or received value | Portal label |
| --- | --- |
| Architecture / Architectural / AR | AR |
| Structure / Structural / ST | ST |

This applies to task registers, project cards, freelancer task pages, monthly
task review, task edit inputs, and task creation/edit selector labels.

Other disciplines, including MEP and GE, keep their existing labels.

Portal task and project discipline records are not automatically rewritten.
Task creation and administrator task editing continue to submit the established
`Architecture` and `Structure` values while showing AR and ST to the user.

## Preserved Release 20.17 behavior

- Project column remains pinned on the left of the Tasks register.
- Action or Completed remains accessible on the right.
- New freelancer accounts remain assignable to tasks.
- Inline editing remains limited to Status, Progress, Quality, and Completed.
- Progress retains its percentage bar.

## Database impact

- No new table
- No new column
- No Alembic schema revision
- No automatic discipline-value migration
- No task, project, assignment, attendance, DTR, leave, payroll, or Finance backfill

## Deployment acceptance

After deployment:

1. Open Tasks and hard-refresh the page.
2. Confirm Progress still has a loading-style percentage bar.
3. Confirm Quality shows only the dropdown and percentage value.
4. Confirm Quality inline editing still saves after refresh.
5. Confirm Architecture is shown as AR and Structure is shown as ST.
6. Check New Task and Edit Task and confirm their discipline options show AR and ST.
7. Confirm MEP, GE, and other discipline labels are unchanged.
