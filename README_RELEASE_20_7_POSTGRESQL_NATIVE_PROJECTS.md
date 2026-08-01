# BIMFM Portal Release 20.7 — PostgreSQL-Native Projects

**Application version:** `2.3.2-release20.7-postgresql-native-projects`  
**Release date:** 2026-08-01  
**Upgrade base:** BIMFM Portal Release 20.6

## Purpose

Release 20.7 corrects the project architecture after the one-time migration from
`projects.db` to PostgreSQL.

PostgreSQL is now the live source of truth for:

- Members and freelancer accounts
- Projects and project memberships
- Tasks and task assignments
- Freelancer assigned-project views
- Administrator project workload and assignment reporting
- Daily task records linked to portal tasks

Routine `projects.db` synchronization and member-name mapping are no longer
required.

## Corrected data flow

The primary project pages now read the PostgreSQL-native tables populated by the
migration:

```text
freelancers
portal_projects
portal_project_members
portal_tasks
portal_task_assignments
```

They no longer use these legacy synchronization tables for current project
presentation:

```text
project_source_members
synced_project_tasks
project_sync_runs
```

The legacy tables are left untouched for historical compatibility. They are not
deleted, migrated again, or used as the live project source.

## Member visibility

The Project Team page now shows every active freelancer, including members with:

- Active project assignments
- Project membership but no active task
- Task assignments migrated without a matching historical membership row
- No current project assignment

A member no longer has to appear in a mapping table before being visible.

## New project presentation

Release 20.7 adds a PostgreSQL-native Project Team view containing:

- All active members
- Assigned project count
- Active task count
- Completed task count
- Overdue task count
- Assignment status
- Project register
- Active task register and assignees
- Project-data integrity indicators

The administrator dashboard now reports:

- Projects stored in PostgreSQL
- Members with project or task assignments
- Members without current assignments
- Open tasks without assignees
- Projects without active members

## Freelancer project experience

The freelancer Assigned Projects page now reads directly from
`portal_task_assignments`. A daily task created from an assigned project is
linked through `daily_tasks.portal_task_id`.

Existing daily task records that use the old nullable
`synced_project_task_id` field remain readable.

## Retired synchronization behavior

- The project snapshot upload endpoint now returns HTTP `410 Gone`.
- The synchronization status endpoint reports `postgresql_native` mode.
- The old mapping screen redirects to the Project Team page.
- `BIMFM_PROJECT_SYNC_TOKEN` is no longer required for production startup.
- The Project Sync Agent is not included in this release.

## Database change

Release 20.7 contains one additive Alembic migration:

```text
Revision: 20260801_0002
Adds: daily_tasks.portal_task_id
Foreign key: portal_tasks.id
Deletion behavior: SET NULL
Index: ix_daily_tasks_portal_task_id
```

The new field is nullable. Existing attendance, DTR, Finance, leave, overtime,
member, project, task, and account records are preserved.

Do not rerun the original SQLite-to-PostgreSQL migration against a database that
already contains the migrated data.

## Render deployment behavior

The included `render.yaml` defines only the Web Service. It does not create a
new PostgreSQL database. `DATABASE_URL` must continue pointing to the populated
existing Render database.

Required production variables:

```text
DATABASE_URL
BIMFM_SESSION_SECRET
BIMFM_ENV=production
BIMFM_COOKIE_HTTPS_ONLY=true
```

`BIMFM_PROJECT_SYNC_TOKEN` may remain in Render without effect or may be removed.

## Validation

Release 20.7 passed:

```text
68 automated tests
0 failures
0 errors
```

It also passed:

- Administrator login and dashboard
- All-active-member visibility
- Project Team page
- PostgreSQL-native workload page
- Freelancer assigned-project page
- Retired synchronization status
- Upgrade from an existing Release 20.6 schema
- Fresh Release 20.7 schema creation
- Python source compilation

## Live database statement

The release was built and tested against isolated databases. No tool used while
building this package connected to or modified the user's live Render
PostgreSQL database.
