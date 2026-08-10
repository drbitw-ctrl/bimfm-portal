# BIM Portal Release 21.21.4

## Project Utilization correction

Planned time is now always calculated from **Start Date through Deadline** using active workdays at 8 hours per workday.

When actual Work Order / Daily Task hours exist, those recorded hours remain the actual time.

When no actual hours exist and the task is completed, estimated actual time is calculated from **Start Date through Completion Date**. This means utilization is no longer forced to 100%:

- completed early: below 100%
- completed on the deadline: 100%
- completed late: above 100%

Active tasks without actual hours and without a completion date remain at zero actual hours instead of being automatically shown as 100%.

## Assignable Task Supervisor

Administrators can now create an assignable task-member identity for any staff account from **Administration → Staff Access**.

Select **Enable Task Assignment** beside the Administrator account. The portal creates a linked Task Supervisor member profile and adds it to the project-member directory. The staff account keeps all existing Administrator permissions and login behavior, but can also be selected in task assignment dropdowns just like other task members.

This linked profile does not create a second login and is not treated as a normal freelancer payroll or attendance account.

## Database migration

Alembic revision: `20260806_0017`

New nullable field:

- `hr_admin_accounts.task_freelancer_id`

No existing task, attendance, payroll, DTR, leave, overtime, or project records are rewritten.
