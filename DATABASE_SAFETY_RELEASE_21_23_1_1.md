# Database Safety — Release 21.23.1.1

Release 21.23.1.1 is a screen-sharing UI/WebRTC hotfix only.

Verified release boundaries:

- no new Alembic migration;
- no model/schema change;
- no new table or column;
- no data backfill;
- no account/test seed;
- `app/database.py` unchanged from the Release 21.22.10 Render baseline;
- `app/models/` unchanged from the Release 21.22.10 Render baseline;
- `alembic/` unchanged from the Release 21.22.10 Render baseline;
- `requirements.txt` unchanged from the Release 21.22.10 Render baseline;
- packaged `data/hr.db` is restored from the Release 21.22.10 Render baseline after validation and is not part of the production deployment procedure.

Production PostgreSQL remains the authoritative database. The deployment instructions intentionally copy/stage only the application files required for Release 21.23.1.1 and never copy `data/`, `alembic/`, `app/models/`, or `.env` into the Render-connected repository.
