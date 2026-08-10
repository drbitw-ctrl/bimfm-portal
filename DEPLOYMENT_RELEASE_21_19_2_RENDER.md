# Deploy Release 21.19.2 to Render

Use Release 21.19.1 as the source baseline. Back up PostgreSQL before deployment.

Build command:

```text
pip install -r requirements.txt && alembic upgrade head
```

Start command:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Expected migration:

```text
Running upgrade 20260804_0015 -> 20260805_0016, Add attendance correction requests and overnight exception flags.
```

After Render reports Live, verify:

1. Freelancer submits a correction request for a previous date.
2. Administrator approves it from Attendance > Correction Requests.
3. Administrator directly corrects an attendance record without a request.
4. Administrator adds previous OT from Overtime Approval Center.
5. An unresolved overnight record is flagged after 06:00 local time and cannot be finalized as OT until corrected.
