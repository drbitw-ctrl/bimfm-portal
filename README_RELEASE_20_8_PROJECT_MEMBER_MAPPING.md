# BIMFM Portal Release 20.8

**Application version:** `2.3.3-release20.8-project-member-mapping`  
**Release date:** 2026-08-01  
**Base:** Release 20.7 PostgreSQL-native project deployment

## Correction delivered

Release 20.7 incorrectly treated the old Task Manager member list as if every
record were already an HR freelancer profile. As a result, the portal had no
separate PostgreSQL member directory and could not show **Unmapped Members**.

Release 20.8 restores the intended structure:

```text
Project Member identity
        ↓ optional mapping
HR Freelancer profile
```

Both sides are stored in PostgreSQL. This does not restore `projects.db`
synchronization.

## New PostgreSQL table

The additive Alembic revision `20260801_0003` creates:

```text
project_member_directory
```

It records:

- Original project-member name and member code
- Active status and available email
- The existing imported `LEGACY-*` placeholder used by project/task foreign keys
- Optional mapped HR freelancer
- Mapping administrator and timestamp

## Safe automatic backfill

During deployment, Alembic builds the directory from the data already present in
PostgreSQL. It checks, in order:

1. Historical `project_source_members` records, preserving valid old mappings
2. An original `members` table when that table exists in the converted database
3. `LEGACY-*` freelancer placeholders created by the earlier SQLite migration
4. Historical synchronized task names only as a final fallback

The backfill normalizes capitalization and repeated spaces to avoid duplicate
member rows.

## Mapping behavior

The Administrator page `/admin/project-team` now shows:

- Project Members
- Unmapped Members
- Mapped Members
- Imported project and task counts for each member
- HR freelancer selection and **Save Mapping** action

An unmapped member remains visible with imported assignments preserved.

Mapping does not rewrite or delete the original project/task assignments. The
portal resolves the mapping when presenting workload and freelancer projects.
This makes mapping reversible and keeps the original imported records auditable.

After mapping:

- The selected HR freelancer sees the project member's active assignments.
- Workload counts are attributed to that HR freelancer.
- Open-task registers display `Project Member → HR Freelancer`.

After unmapping:

- The HR freelancer no longer sees those source assignments.
- The source assignments remain unchanged in PostgreSQL.

## HR presentation cleanup

Imported `LEGACY-*` project placeholders are excluded from the main HR account,
attendance, DTR, calendar, and workload selections. They remain in PostgreSQL as
safe assignment anchors and are managed through the Project Member Directory.

## No synchronization requirement

Release 20.8 continues to operate entirely from PostgreSQL:

```text
project_member_directory
freelancers
portal_projects
portal_project_members
portal_tasks
portal_task_assignments
```

The Project Sync Agent and `BIMFM_PROJECT_SYNC_TOKEN` are not required for normal
operation.

## Database safety

The Release 20.8 migration is additive. It does not delete, re-import, or rewrite:

- Freelancers or accounts
- Projects or tasks
- Project memberships or task assignments
- Attendance or corrections
- DTR records
- Leave or overtime
- Compensatory-credit ledgers
- Finance records

Do not rerun the original SQLite-to-PostgreSQL migration.

## Validation

Release 20.8 passed:

```text
75 automated tests
0 failures
0 errors
```

It also passed an end-to-end acceptance workflow covering:

- Administrator login
- Unmapped project-member display
- Mapping a project member to an HR freelancer
- Preserving the source task assignment
- HR freelancer project visibility after mapping
- Setup-status member counts
- Fresh migration to Alembic revision `20260801_0003`
- Upgrade simulation from a Release 20.7 database
- Backfill from both `LEGACY-*` placeholders and an existing `members` table

The live Render PostgreSQL database was not accessed during development. Create a
current database backup before deployment and verify the resulting counts after
Alembic completes.
