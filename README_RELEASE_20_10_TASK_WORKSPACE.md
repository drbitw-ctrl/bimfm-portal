# BIMFM Portal Release 20.10 — Connected Task Workspace

**Application version:** `2.3.5-release20.10-task-workspace`  
**Release date:** 2026-08-01  
**Source base:** Release 20.9 Visual Refresh with the Release 20.8 PostgreSQL member directory and mapping architecture

## Purpose

Release 20.10 completes the visual refresh by connecting the freelancer navigation, adding a PostgreSQL-native **New Task** workspace, and applying a consistent responsive table presentation throughout the portal.

## Freelancer navigation correction

The freelancer sidebar is now a dedicated scrollable navigation area. It remains visible even on shorter screens and contains working links for:

- Today’s Attendance
- Attendance History
- Daily Task Reports
- Assigned Projects
- Overtime & Credits
- Leave Requests
- Change Password

The active page is indicated by both server-rendered state and a JavaScript fallback. On tablet and mobile screens, selecting a link closes the navigation drawer automatically.

## New Task workspace

Administrators and Supervisors with `PROJECT_EDIT` permission now have a highlighted **New Task** sidebar action.

The web form follows the functional structure of the desktop `project_form.py` task editor:

- Select an existing project or create a new project
- Project code and project name
- Project Engineer / Supervisor
- Task title
- Start date
- Deadline
- Completion date
- Status
- Priority
- Discipline
- Assigned project member
- Progress percentage
- Task description

### Form behavior

- Completed and For Review tasks are automatically set to 100% progress.
- Unassigned tasks are set to 0% and do not create an assignment.
- Completion date is required for Completed status.
- Start date cannot be later than the deadline.
- Completion date cannot be earlier than the start date.
- Duplicate project codes are rejected when creating a new project.
- Existing Project Member mappings remain intact.
- Unmapped project members may still receive project assignments through their preserved source assignment identity.
- When a project member is mapped later, the task becomes visible to the corresponding HR freelancer account without rewriting the original assignment.

New records are written directly to the PostgreSQL-native tables:

```text
portal_projects
portal_project_members
portal_tasks
portal_task_assignments
```

## Unified table presentation

All 27 data tables in the portal now use the same presentation system:

- Consistent typography, spacing, borders, and surface treatment
- Alternating row backgrounds
- Clear hover state
- Sticky and readable headers where applicable
- Status and priority chips
- Progress bars and metric pills
- Search controls on project, task, attendance, and daily-task registers
- Responsive mobile card presentation with automatic column labels
- Improved dark-theme presentation

The enhanced table system applies to management, attendance, DTR, Finance, project mapping, project modules, overtime, leave, staff accounts, and freelancer self-service pages.

## Database safety

Release 20.10 introduces **no Alembic migration** and performs no automatic repair or backfill.

It does not delete, replace, or re-import:

- Project members or mappings
- Projects or project assignments
- Tasks or task assignments
- Freelancer accounts
- Attendance and DTR records
- Leave and overtime records
- Compensatory-credit and Finance records
- Administrator accounts

Database writes occur only when an authorized user submits an ordinary application action such as creating a new task.

## Automated validation

Release 20.10 passed:

```text
85 tests
0 failures
0 errors
```

The integrated acceptance test verified:

- Administrator authentication
- New Task page permission and rendering
- New project and task creation
- Project membership creation
- Task assignment creation
- Task visibility in the project task register
- Freelancer authentication
- All seven freelancer sidebar destinations returning HTTP 200
- Sidebar navigation appearing on every freelancer page
- Preservation of the PostgreSQL member-mapping assignment model
- Compilation of all application and test Python modules

## Production acceptance

After deployment, verify one administrator account and one freelancer account before routine use. Confirm the member mapping directory, repaired project assignments, attendance history, DTR, leave, overtime, and Finance records remain visible.
