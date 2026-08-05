# Release 21.20 Render Deployment

1. Confirm a recent PostgreSQL backup exists.
2. Copy the release into the existing Git repository with robocopy, excluding .git, .env, databases, uploads, logs, and virtual environments.
3. Review `git status` and `git diff --stat`.
4. Stage the Release 21.20 files, commit, and push to `main`.
5. Keep Render build command: `pip install -r requirements.txt && alembic upgrade head`.
6. Keep start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
7. After Live, hard refresh and verify version `v3.0.20-release21.20-ot-clarity-attendance-welcome`.
