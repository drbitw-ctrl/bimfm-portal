# BIMFM Portal Release 20.17

**Application version:** `2.3.12-release20.17-task-table-member-assignment`  
**Release date:** 2026-08-01  
**Source base:** Release 20.16 selective task quick edit

## Purpose

Release 20.17 keeps the Release 20.16 Tasks-page design and selective inline
editing, while fixing two production issues:

1. The wide Tasks register could hide edge columns on desktop screens.
2. A newly created freelancer account was not immediately available in the
   Assigned Member dropdown for new or edited tasks.

## Tasks register presentation

The Tasks sidebar page keeps the same visual design, filters, percentage bars,
and selective quick-edit controls.

The desktop table now:

- Uses compact, predictable column widths.
- Keeps the **Project** column pinned to the left during horizontal scrolling.
- Keeps the rightmost **Action** column pinned for editors.
- Keeps the rightmost **Completed** column pinned for read-only users.
- Retains horizontal scrolling when the available width is smaller than the
  complete register.
- Retains the existing mobile card layout below 760 pixels.

No columns are removed. Progress and Quality still show their percentage bars.

## Freelancer assignment repair

Creating a freelancer account now also creates or maps an assignable record in
`project_member_directory`.

This means the new member is immediately available in:

- New Task → Assigned Member
- Edit Task → Assigned Member
- Project membership and task assignment records

At application startup, Release 20.17 also repairs existing HR freelancer
accounts that were created before this fix and do not yet have an assignable
project-member row.

When an unmapped imported project member already has the same normalized name,
the release maps that source member to the HR freelancer instead of creating a
duplicate. This preserves historical assignment identities.

## Inline-edit scope remains unchanged

Inline editing remains available only on the Tasks sidebar page and only for:

- Status
- Progress
- Quality
- Completed

Project, Task, Assigned Member, Priority, Discipline, Start, and Deadline remain
read-only in the register and continue to use the full Edit page.

## Database impact

- No new table
- No new column
- No Alembic schema revision
- No task, project, attendance, DTR, leave, payroll, or Finance backfill
- Existing freelancer accounts missing an assignment-directory record receive
  one during startup

## Deployment acceptance

After deployment:

1. Open Tasks and confirm the Project column remains visible while scrolling.
2. Confirm the right edge of the register is accessible and the Edit action is
   visible for an Administrator.
3. Create a test freelancer account.
4. Open New Task and confirm the new member appears in Assigned Member.
5. Create a task assigned to that member and confirm it appears in the member's
   work view.
6. Confirm Status, Progress, Quality, and Completed still save inline.
