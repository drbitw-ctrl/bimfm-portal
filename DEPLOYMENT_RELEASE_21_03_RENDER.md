# BIMFM Portal Release 21.03 — Render Deployment

## Application version

`3.0.3-release21.03-role-based-my-work`

## Database migration

Release 21.03 has no new migration. The current Alembic head remains:

```text
20260802_0009
```

Keep the existing Render build and start commands unchanged.

### Build

```text
pip install -r requirements.txt && alembic upgrade head
```

### Start

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## Manual Git deployment

1. Extract the Release 21.03 ZIP to a folder separate from the Git repository.
2. Copy the release files into the existing repository while excluding `.git`, local environments, secrets, databases, logs, backups, and uploads.
3. Review `git status` and `git diff --stat`.
4. Stage only the Release 21.03 files listed in the release message.
5. Commit and push `main`.
6. When Render Auto-Deploy is disabled, select **Manual Deploy → Deploy latest commit**.
7. After the service reports **Live**, hard-refresh the browser with `Ctrl + Shift + R`.

## Acceptance checks

- Administrator My Work shows Active Tasks, Team Availability, and pending request summaries.
- Supervisor My Work shows Active Tasks and Team Availability without the request center.
- Finance My Work shows attendance, monthly summary, DTR status, DTR generation, and Finance Center shortcut.
- Task legends are visible.
- Completed rows are green, delayed rows are red, and in-progress/for-review rows are yellow.
- Visible pages no longer mention the database engine or retired database file.
- Sidebar version shows `v3.0.3-release21.03-role-based-my-work`.
