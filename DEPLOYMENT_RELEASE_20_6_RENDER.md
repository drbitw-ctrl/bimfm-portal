# BIMFM Portal Release 20.6 — Render Deployment Guide

## Files provided

Two application packages are supplied:

1. **Source package**
   - Application source
   - Tests
   - Migration and diagnostic tools
   - Project Sync Agent
   - Release documentation

2. **Render deployment package**
   - Runtime application
   - Templates and static files
   - Alembic migration files
   - Render Blueprint
   - Production requirements
   - Release documentation

A separate Project Sync Agent package is also provided for the company-side
computer that can read `projects.db`.

## Before deployment

### 1. Back up production PostgreSQL

Create or confirm a current PostgreSQL backup before deploying.

Release 20.6 does not add a schema migration, but a backup is still required
because Finance and HR information is business-critical.

### 2. Preserve environment variables

Do not replace the current production secrets. The existing Render service
should keep its current values for:

```text
DATABASE_URL
BIMFM_SESSION_SECRET
BIMFM_PROJECT_SYNC_TOKEN
BIMFM_ENV
BIMFM_LOG_LEVEL
BIMFM_COOKIE_HTTPS_ONLY
BIMFM_BOOTSTRAP_ADMIN_USERNAME
BIMFM_BOOTSTRAP_ADMIN_DISPLAY_NAME
BIMFM_BOOTSTRAP_ADMIN_PASSWORD
```

The ZIP contains only `.env.example`; it contains no production password,
database URL, session secret, or synchronization token.

### 3. Preserve the existing PostgreSQL database

Do not create a new database when updating an existing Render service.

The `render.yaml` file can describe a complete new Blueprint, but an existing
deployment should continue using its existing Web Service and PostgreSQL
instance.

## Deployment through the existing GitHub repository

### 1. Extract the Render deployment ZIP

Copy its contents into the local folder connected to the current BIMFM Portal
GitHub repository.

### 2. Review changes

Run:

```powershell
git status
git diff
```

Confirm that no `.env`, database file, project-sync private configuration, or
other secret is staged.

### 3. Commit and push

```powershell
git add .
git commit -m "Release 20.6 finance clarity"
git push
```

When Auto-Deploy is enabled, Render will start a deployment automatically.

## Render commands

The included `render.yaml` uses:

```text
Build:
pip install -r requirements.txt && alembic upgrade head

Start:
uvicorn app.main:app --host 0.0.0.0 --port $PORT

Health check:
/health/ready
```

No manual database command is normally needed because the build command already
runs Alembic.

## Post-deployment checks

Wait until Render reports the deployment as **Live**, then verify:

```text
https://YOUR-SERVICE.onrender.com/health
https://YOUR-SERVICE.onrender.com/health/ready
https://YOUR-SERVICE.onrender.com/api/v1/health
https://YOUR-SERVICE.onrender.com/docs
```

Expected result:

- `/health` returns a successful service response.
- `/health/ready` confirms that PostgreSQL is available.
- `/api/v1/health` returns HTTP 200.
- `/docs` loads the API documentation.

## Functional acceptance checklist

Log in with an Administrator or authorized management account and verify:

1. Finance Center loads.
2. Decimal payroll multiplier is not displayed.
3. Days Physically Worked is a whole number.
4. Compensatory Leave Applied is separate from worked days.
5. Salary-Covered Calendar Days shows a value such as `31 of 31`.
6. Payroll Treatment shows `Full Monthly Rate` or a reduced-rate result.
7. DTR details use the same terminology.
8. Excel export opens and the first worksheet is `Finance Summary`.
9. Visible durations use `Hh Mm`.
10. Freelancer attendance page shows the monthly attendance and leave summary.
11. Existing project-member mappings remain present.
12. Project synchronization still shows the correct assigned tasks.

## Recommended Finance validation

Before using the release for a live payment cycle, compare one finalized month
against the previous manual computation.

Verify at minimum:

```text
Days physically worked
Approved leave taken
Compensatory leave applied
Payable workday equivalents
Salary-covered calendar days
Effective deduction
Approved overtime
Compensatory-credit balance
```

## Rollback

When a serious issue appears:

1. Stop the deployment or redeploy the previous known-good Git commit.
2. Do not delete the PostgreSQL database.
3. Restore the database backup only when data was modified incorrectly and a
   restore is genuinely required.
4. Record the failed deployment logs and the exact affected record.
5. Keep Release 20.6 source available for diagnosis.

Because Release 20.6 has no new schema revision, application rollback is simpler
than a release that changes database structure.

## Local test command

For development:

```powershell
python -m unittest discover -s tests -v
```

Expected Release 20.6 baseline:

```text
Ran 60 tests
OK
```
