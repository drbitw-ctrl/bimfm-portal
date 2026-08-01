# BIMFM Portal — PostgreSQL Production Application

Current release: **20.7 — PostgreSQL-Native Projects**  
Application version: `2.3.2-release20.7-postgresql-native-projects`

BIMFM Portal combines attendance, daily task reporting, leave, overtime,
compensatory credit, DTR, Finance reporting, member accounts, projects, and task
assignments in one PostgreSQL-backed application.

## Production architecture

PostgreSQL is the live source of truth. Project pages read:

```text
freelancers
portal_projects
portal_project_members
portal_tasks
portal_task_assignments
```

The original `projects.db` migration is a one-time operation. Routine project
synchronization is retired in Release 20.7.

## Local verification

```powershell
pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python tools\acceptance_release_20_7.py
python -m compileall app tools tests
```

## Render deployment

Use the existing populated PostgreSQL database through `DATABASE_URL`.

```text
Build: pip install -r requirements.txt && alembic upgrade head
Start: uvicorn app.main:app --host 0.0.0.0 --port $PORT
Health: /health/ready
```

The included `render.yaml` does not create another database.

## Important

Do not rerun the SQLite-to-PostgreSQL migration against a database that already
contains migrated production data.

See:

- `README_RELEASE_20_7_POSTGRESQL_NATIVE_PROJECTS.md`
- `DEPLOYMENT_RELEASE_20_7_RENDER.md`
- `DATABASE_SAFETY_RELEASE_20_7.md`
- `TEST_REPORT_RELEASE_20_7.txt`
