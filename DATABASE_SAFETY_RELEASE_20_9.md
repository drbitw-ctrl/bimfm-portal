# Database Safety — Release 20.9

Release 20.9 is a visual and presentation update only.

It contains no Alembic migration and does not create, alter, backfill, or delete
PostgreSQL tables or records.

The deployment retains the existing Release 20.8 project-member mapping data,
including the repaired `project_member_directory`, project memberships, and task
assignments.

Do not rerun the legacy SQLite migration or the one-time project-member repair
utility as part of this release.

Keep the current populated `DATABASE_URL` in Render. A rollback requires only a
previous application commit; no database restore is expected for this visual
release.
