# Database Safety — Release 20.12

Release 20.12 does not access or modify the live Render database during package
creation.

The deployment runs:

```text
alembic upgrade head
```

The only new schema change is:

```text
ALTER portal_tasks ADD COLUMN quality_score INTEGER NULL
```

The migration does not:

- Delete records
- Re-import SQLite data
- Rebuild member mappings
- Change project codes or project names
- Change project-member directory records
- Modify task assignments automatically
- Modify attendance, DTR, leave, overtime, compensatory-credit, Finance, or
  account records

Task data changes occur only when an authorized user submits the New Task, Edit
Task, or Delete Task forms.

Before production deployment, keep a current PostgreSQL backup or restore point.
