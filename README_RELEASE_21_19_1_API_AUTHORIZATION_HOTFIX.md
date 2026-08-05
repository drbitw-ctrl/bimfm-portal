# BIM Portal Release 21.19.1

## API authorization hotfix

Release 21.19.1 is a narrow security hotfix built directly from Release 21.19.
It corrects assignment filtering for the authenticated JSON API without changing
the normal freelancer portal workflow.

## Corrected endpoints

The following endpoints now apply assignment-level visibility to freelancer
accounts:

```text
GET /api/v1/projects
GET /api/v1/tasks
```

A freelancer can retrieve only:

- Projects where the freelancer has an active project-membership record.
- Projects containing a task assigned to the freelancer.
- Tasks assigned directly to the freelancer.
- Tasks assigned through the existing active legacy-member mapping.

A freelancer cannot use the `project_id`, `status`, pagination, or direct API URL
parameters to retrieve another member's project or task.

## Retained staff access

Existing organization-wide read access is retained for authorized management
roles:

- Administrator
- Supervisor
- Finance

No staff permission was removed or broadened.

## Retained freelancer behavior

The normal freelancer pages remain unchanged:

- My Projects
- My Tasks
- Completed Tasks
- Work Orders
- Attendance
- Leave and overtime

The hotfix reuses the same `resolved_assignment_ids` mapping already used by the
freelancer portal, so existing direct assignments and repaired legacy-member
assignments continue to work.

## Fail-closed behavior

If an employee identity has no valid freelancer mapping, the project and task
API returns an empty result instead of organization-wide data. A staff account
accidentally assigned the `EMPLOYEE` role also fails closed.

## Database impact

No database migration is included. The Alembic head remains:

```text
20260804_0015
```

The hotfix does not create, delete, update, or backfill any database record.

## Changed application files

```text
app/api/v1/router.py
app/config.py
```

## Added regression tests

```text
tests/test_api_v1_freelancer_scope.py
```

The regression suite verifies direct assignments, active project membership,
legacy-member mapping, unrelated-record exclusion, filter-bypass prevention,
staff visibility, and fail-closed behavior.

## Scope boundary

Release 21.19.1 addresses only the project/task API visibility issue. Other
production-safety recommendations from the broader Release 21.19 audit remain
separate work and are not represented as fixed by this package.
