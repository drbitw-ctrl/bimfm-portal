# BIMFM Portal Release 21.04 — Render Deployment

## Files changed

- `app/config.py`
- `app/my_work_service.py`
- Release 21.04 documentation

## Database

Release 21.04 has no Alembic migration. Keep the existing PostgreSQL database
and existing Render environment variables.

## Render commands

Build:

```text
pip install -r requirements.txt && alembic upgrade head
```

Start:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Post-deployment check

1. Sign in as Finance Head.
2. Open My Work.
3. Confirm Attendance Recorded Today uses only enabled freelancer login accounts.
4. Confirm legacy placeholder identities and disabled test accounts are absent.
5. Confirm monthly attendance and DTR counts use the same population.
