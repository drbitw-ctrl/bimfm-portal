# Database Safety — Release 21.14

Release 21.14 is an application and presentation update.

## Schema impact

- New migration: None
- New tables: None
- New columns: None
- New indexes: None
- Current Alembic head: `20260803_0013`

## Data impact

Deployment does not rewrite or delete:

- Freelancer or staff accounts
- Passwords
- Projects, tasks, assignments, deadlines, or progress
- Quality Scores
- Work Order sessions or Daily Task Reports
- Attendance, DTR, leave, overtime, credits, payroll, or Finance records
- Reminders or reminder read status

The Overall Performance report is calculated at page-load time from existing Speed and Quality data. It does not store a new score in the database.

Unread reminders are not automatically marked as read. A freelancer must use the existing Mark as Read action.
