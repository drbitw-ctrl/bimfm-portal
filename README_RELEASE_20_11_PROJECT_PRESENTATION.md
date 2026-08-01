# BIMFM Portal Release 20.11 — Project Presentation and Freelancer Access

**Application version:** `2.3.6-release20.11-project-presentation`  
**Release date:** 2026-08-01  
**Source base:** Release 20.10 Connected Task Workspace

## Purpose

Release 20.11 keeps the Release 20.10 visual design while simplifying project
identity and correcting the freelancer Attendance and Assigned Projects pages.

## Project names only

Project codes remain internal database identifiers, but they are no longer
shown in the normal portal interface.

The portal now displays project identity as a project name such as:

```text
220.桃園長庚醫院
```

This applies to:

- New Task project selection
- Project Register
- Task Register
- Active and completed task views
- Calendar entries
- Workload and project reports
- Freelancer Attendance assignments
- Freelancer Assigned Projects
- Daily Task Report task presentation
- Finance-facing DTR task presentation
- DTR Excel export

The Project Team page was intentionally left structurally unchanged, as
requested. Its member mapping workflow and assignment data are preserved.

## Manually entered Project Engineer

A Project Engineer is no longer selected from portal administrator or
supervisor accounts.

The New Task form now provides a manual text field for the actual Project
Engineer or operational contact. The value belongs to the project and is shown
where the project is presented.

Existing imported projects are backfilled from migration notes such as
`Legacy engineer: Joy Chen` when that information is available. Those migration
labels are removed from user-visible task descriptions.

## Member presentation

Project-facing forms and records display member names without imported
`LEGACY-*` placeholder branding. Internal source identities remain in the
database only to preserve repaired PostgreSQL assignment relationships.

The Project Team mapping page remains available for connecting imported project
members to HR freelancer profiles.

## Freelancer page corrections

The following pages now use PostgreSQL-native membership and assignment queries:

```text
/attendance
/projects
```

The corrected queries support:

- Direct HR freelancer assignments
- Assignments through a mapped imported project member
- Repaired task assignments with multiple rows
- Project memberships even when there is no currently active task
- Projects discovered through either membership or task assignment

The Assigned Projects page now shows project name, Project Engineer, assignment
status, active-task count, progress, and the next active task when available.

## New Task behavior

For a new project, the user enters:

- Project name
- Project Engineer
- Task information
- Assigned project member

The application generates a hidden internal project identifier automatically.
The identifier is not shown to portal users.

For an existing project, the project name is shown by itself. The manually
entered Project Engineer can be updated when saving the task.

## Database changes

Release 20.11 includes one additive Alembic migration:

```text
20260801_0003 -> 20260801_0004
```

It adds the nullable field:

```text
portal_projects.project_engineer
```

The migration does not remove or rename any existing field, table, project,
task, member, mapping, attendance record, DTR, leave record, overtime record,
Finance record, or account.

## Validation

Release 20.11 passed:

```text
90 tests
0 failures
0 errors
```

The regression suite includes authenticated checks for `/attendance` and
`/projects`, mapped-member assignment resolution, membership-only projects,
manual Project Engineer entry, hidden project-code presentation, and the
additive database upgrade.
