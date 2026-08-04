# Deploy BIM Portal Release 21.15 to Render

Release 21.15 is cumulative from Release 21.14 and adds the Gab July 2026 compensatory-credit correction.

## Render settings

Build command:

    pip install -r requirements.txt && alembic upgrade head

Start command:

    uvicorn app.main:app --host 0.0.0.0 --port $PORT

Expected migration:

    Running upgrade 20260803_0013 -> 20260804_0014, Correct Gab's July 2026 compensatory-leave calculation.

## Post-deployment check

1. Open Monthly DTR.
2. Select July 2026.
3. Generate or refresh Gabrielle Gameng's DTR.
4. Open the DTR summary or Finance Center.
5. Confirm:
   - Physical days worked: 19
   - Approved leave: 4
   - Comp leave applied: 2
   - Effective deduction: 2
   - Payable workday equivalents: 21
   - Salary-covered calendar days: 29 of 31

Finalized July DTRs are intentionally not replaced automatically.
