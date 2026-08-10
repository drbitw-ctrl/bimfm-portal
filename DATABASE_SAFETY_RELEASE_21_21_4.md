# Database Safety — Release 21.21.4

This release adds one nullable mapping field to staff accounts through Alembic revision `20260806_0017`.

The migration does not automatically create a Task Supervisor member. The member is created only when an Administrator selects **Enable Task Assignment** on the Staff Access page.

Before deployment, confirm a restorable Render PostgreSQL backup exists.

Rollback of only the web service does not remove the new nullable database field. The previous application version will ignore it. A database downgrade is normally unnecessary.
