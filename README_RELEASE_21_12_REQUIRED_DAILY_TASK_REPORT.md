# BIMFM Portal Release 21.12

## Required Work Order Daily Task Reports

Release 21.12 is a cumulative update based on Release 21.11. It preserves the all-member Live Work Orders display and changes the freelancer Work Order stop workflow so the activity report is required.

## Freelancer workflow

1. Open an assigned task.
2. Select **Start working**.
3. Perform the assigned work.
4. Before stopping the timer, enter the activities, outputs, or areas completed.
5. Select **Stop and submit daily report**.

The timer cannot be stopped through the normal freelancer workflow until a meaningful activity report of at least 10 characters is provided. The maximum report length is 1,000 characters.

## Daily Task Report integration

Each normally completed Work Order creates one Daily Task record containing:

- Work date
- Project
- Task
- Discipline
- Actual minutes
- Management-controlled task progress
- Freelancer activity report

The activity report is stored as the Daily Task **Accomplishment / Output** and is included in monthly DTR generation and Excel DTR exports.

The Daily Task date is based on the local date when the Work Order was started. This keeps the work session under the day on which the freelancer began the activity, including sessions that end after midnight.

## Portal presentation

The freelancer Work Orders page now includes:

- A required multiline Daily Task Report field
- Clear work-activity instructions
- A **Stop and submit daily report** button
- Daily Task Report details in Today’s Work Sessions
- Daily Task Report details in Recorded Work History

The interface is available in English and Traditional Chinese.

## Management controls

Official task status, progress, completion, and project accomplishment remain controlled by management. The freelancer activity report documents work performed but does not change official task progress.

Existing Administrator-controlled timer safeguards remain unchanged and are not described in the freelancer interface.

## Database impact

- No new migration
- No new tables
- No new columns
- No existing records rewritten
- Existing Work Order and Daily Task records remain unchanged

Current Alembic head: `20260803_0013`.

## Version

`v3.0.12-release21.12-required-daily-task-report`
