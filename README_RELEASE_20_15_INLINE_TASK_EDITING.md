# BIMFM Portal Release 20.15 — Inline Task Editing

**Application version:** `2.3.10-release20.15-inline-task-editing`  
**Release date:** 2026-08-01  
**Source base:** Release 20.14 Render deployment package

## Purpose

Release 20.15 makes the complete Task Register faster to maintain. Staff with
Project Edit permission can update common task fields directly in the task list
without opening the full Edit Task page for every change.

## Inline-editable fields

- Project
- Task title
- Assigned member
- Status
- Priority
- Discipline
- Progress
- Quality score
- Start date
- Deadline
- Completion date

Project, member, status, priority, discipline, progress, and quality use dropdown
controls. Dates use native date controls. The task title saves when the user
leaves the field or presses Enter.

## Save behavior

- Dropdown and date changes save automatically.
- Each row shows Saving, Saved, or an error message.
- Invalid values are rejected and the previous value is restored in the browser.
- Status rules remain enforced:
  - Completed and For Review use 100% progress.
  - Completed receives a completion date when one is missing.
  - Unassigned uses 0% progress and clears task assignments.
- Selecting a member for an Unassigned task changes the status to Not Started.
- Existing multiple-member assignments are preserved when unrelated fields are
  changed. The member dropdown shows a multiple-member notice until a user
  explicitly chooses a replacement member.

## Permissions and security

- Inline controls are rendered only for accounts with Project Edit permission.
- Read-only Supervisor and Finance views remain read-only.
- Every inline save validates the existing session CSRF token.
- Each successful inline change writes an audit-log entry.

## Database compatibility

- No database table or column is added.
- No Alembic schema revision is required.
- Existing PostgreSQL task, project, member, assignment, and audit data are kept.

## Validation completed

The modified package passed:

- Python compile checks for the application
- Jinja parsing for all templates
- JavaScript syntax validation for the rendered inline editor
- Administrator inline-edit workflow tests
- Status, progress, project, title, and completion-date persistence tests
- Invalid date and invalid CSRF rejection tests
- Multiple-assignee preservation tests
- Read-only Supervisor rendering tests
