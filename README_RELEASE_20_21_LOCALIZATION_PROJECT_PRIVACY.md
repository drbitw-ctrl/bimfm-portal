# BIMFM Portal Release 20.21

**Application version:** `2.3.16-release20.21-localization-project-privacy`  
**Release date:** 2026-08-02  
**Source base:** Release 20.20 performance leaderboards and reporting

## Purpose

Release 20.21 improves Traditional Chinese consistency throughout the portal,
prioritizes current freelancer project assignments, adds a personal recently
completed task page, and gives management control over whether Project Engineer
names are visible to freelancers.

## Traditional Chinese consistency

The Traditional Chinese catalog now covers:

- All literal translation keys used by the current templates
- Visible hard-coded labels, headings, helper text, form placeholders, and table text
- Flash and validation messages produced by portal routes
- Newly added freelancer project, completed-task, and HR-policy controls

Names, project titles, task descriptions, product names, technical acronyms, and
hard technical terms remain unchanged. Examples include BIMFM Portal,
PostgreSQL, DTR, OT, AR, ST, MEP, GE, API, Excel, and projects.db.

The Chinese terminology has also been normalized so `Freelancer` consistently
appears as `自由工作者` and HR references appear as `人資` in the Chinese UI.

## Assigned Projects ordering

The freelancer Assigned Projects page now always places projects with active
assigned tasks first.

After the current assignments, the freelancer may sort the remaining project
cards by:

- Deadline
- Project Name
- Priority
- Progress
- Status

Both ascending and descending order are available. The current-assignment-first
rule remains active regardless of the selected sort.

## Freelancer Recently Completed Tasks

A new freelancer sidebar item opens:

```text
/projects/completed
```

This page displays only completed portal tasks assigned to the signed-in
freelancer, including assignments inherited through the existing project-member
mapping. It does not display completed tasks belonging only to other members.

The table includes:

- Project
- Task
- Discipline
- Priority
- Quality
- Deadline
- Completion Date

The columns remain sortable in the browser.

## Project Engineer privacy policy

Project Engineer names are hidden from freelancers by default.

Administrators can control visibility from:

```text
Administration → HR Policy
```

The policy option is:

```text
Show Project Engineer names to freelancers
```

When disabled, the Project Engineer name is not rendered on the freelancer
Assigned Projects page. When enabled, the name is displayed with the project.
Staff-facing project and report pages remain unchanged.

## Database change

Release 20.21 adds one Boolean HR-policy column:

```text
hr_policies.show_project_engineer_to_freelancers
```

Default value:

```text
false
```

The migration is additive and does not rewrite project, task, assignment,
attendance, DTR, leave, overtime, finance, or quality-score records.

## Validation

Release 20.21 passed 95 validation checks covering:

- Python compilation
- JavaScript syntax
- JSON catalog validity
- 39 Jinja templates
- Traditional Chinese key and visible-text coverage
- Flash-message localization coverage
- Fresh database migration
- Release 20.20 to 20.21 migration
- Project sorting in every supported direction
- Current-assignment-first behavior
- Freelancer Project Engineer privacy
- HR Policy toggle persistence
- Freelancer-only completed-task isolation
- Chinese labels with member names preserved

