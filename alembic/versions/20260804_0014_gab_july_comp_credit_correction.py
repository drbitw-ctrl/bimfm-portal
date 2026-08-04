"""Correct Gab's July 2026 compensatory-leave calculation.

Revision ID: 20260804_0014
Revises: 20260803_0013
Create Date: 2026-08-04
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "20260804_0014"
down_revision = "20260803_0013"
branch_labels = None
depends_on = None

_GAB_PATTERN = "%gabrielle%gameng%"
_JULY_MONTH = "2026-07"
_COMP_DAY_MINUTES = 480
_COMP_COVERED_DATES = (date(2026, 7, 1), date(2026, 7, 2))
_REGULAR_LEAVE_DATES = (date(2026, 7, 3), date(2026, 7, 6))
_OPENING_CREDIT_DATE = date(2026, 6, 30)
_OPENING_SOURCE = "RELEASE_21_15:GAB_OPENING_OT_CREDIT"
_USAGE_SOURCE_PREFIX = "RELEASE_21_15:GAB_COMP_LEAVE"


def _gab(bind):
    return bind.execute(
        sa.text(
            "SELECT id, full_name FROM freelancers "
            "WHERE lower(full_name) LIKE :pattern ORDER BY id LIMIT 1"
        ),
        {"pattern": _GAB_PATTERN},
    ).mappings().first()


def _admin_id(bind):
    return bind.execute(
        sa.text(
            "SELECT id FROM hr_admin_accounts "
            "WHERE is_active = :active "
            "ORDER BY CASE WHEN upper(role) = 'ADMIN' THEN 0 ELSE 1 END, id "
            "LIMIT 1"
        ),
        {"active": True},
    ).scalar()


def _ensure_leave(bind, *, freelancer_id: int, admin_id: int, leave_date: date, compensated: bool, now: datetime):
    row = bind.execute(
        sa.text(
            "SELECT id, source_request_id FROM leave_records "
            "WHERE freelancer_id = :freelancer_id AND leave_date = :leave_date"
        ),
        {"freelancer_id": freelancer_id, "leave_date": leave_date},
    ).mappings().first()

    leave_type = "COMPENSATORY_LEAVE" if compensated else "APPROVED_LEAVE"
    is_paid = bool(compensated)
    comp_used = _COMP_DAY_MINUTES if compensated else 0
    note = (
        "Supervisor-approved July 2026 correction: covered by one full-day "
        "compensatory credit from approved overtime."
        if compensated
        else "Supervisor-approved July 2026 regular leave."
    )

    if row is None:
        bind.execute(
            sa.text(
                "INSERT INTO leave_records ("
                "freelancer_id, leave_date, leave_type, is_paid, status, "
                "duration_minutes, comp_leave_minutes_used, source_request_id, notes, "
                "approved_by_admin_id, created_at, updated_at"
                ") VALUES ("
                ":freelancer_id, :leave_date, :leave_type, :is_paid, 'APPROVED', "
                ":duration_minutes, :comp_used, NULL, :notes, :admin_id, :created_at, :updated_at"
                ")"
            ),
            {
                "freelancer_id": freelancer_id,
                "leave_date": leave_date,
                "leave_type": leave_type,
                "is_paid": is_paid,
                "duration_minutes": _COMP_DAY_MINUTES,
                "comp_used": comp_used,
                "notes": note,
                "admin_id": admin_id,
                "created_at": now,
                "updated_at": now,
            },
        )
        leave_id = int(
            bind.execute(
                sa.text(
                    "SELECT id FROM leave_records WHERE freelancer_id = :freelancer_id "
                    "AND leave_date = :leave_date"
                ),
                {"freelancer_id": freelancer_id, "leave_date": leave_date},
            ).scalar()
        )
        source_request_id = None
    else:
        leave_id = int(row["id"])
        source_request_id = row["source_request_id"]
        bind.execute(
            sa.text(
                "UPDATE leave_records SET leave_type = :leave_type, is_paid = :is_paid, "
                "status = 'APPROVED', duration_minutes = :duration_minutes, "
                "comp_leave_minutes_used = :comp_used, notes = :notes, "
                "approved_by_admin_id = :admin_id, updated_at = :updated_at "
                "WHERE id = :leave_id"
            ),
            {
                "leave_type": leave_type,
                "is_paid": is_paid,
                "duration_minutes": _COMP_DAY_MINUTES,
                "comp_used": comp_used,
                "notes": note,
                "admin_id": admin_id,
                "updated_at": now,
                "leave_id": leave_id,
            },
        )

    # Keep a linked request consistent when one exists.
    if source_request_id is not None:
        bind.execute(
            sa.text(
                "UPDATE leave_requests SET leave_type = :leave_type, status = 'APPROVED', "
                "approved_minutes = :approved_minutes, reviewed_by_admin_id = :admin_id, "
                "reviewed_at = COALESCE(reviewed_at, :reviewed_at), "
                "review_reason = COALESCE(NULLIF(review_reason, ''), :review_reason), "
                "updated_at = :updated_at WHERE id = :request_id"
            ),
            {
                "leave_type": leave_type,
                "approved_minutes": _COMP_DAY_MINUTES,
                "admin_id": admin_id,
                "reviewed_at": now,
                "review_reason": "Supervisor-approved July 2026 correction.",
                "updated_at": now,
                "request_id": int(source_request_id),
            },
        )

    return leave_id, source_request_id


def _ensure_opening_credit(bind, *, freelancer_id: int, admin_id: int, now: datetime) -> int:
    """Ensure two whole-day credits are available for July leave coverage.

    Existing opening balance and approved-overtime ledger credits in July are
    honored. Only the shortfall needed to reach 960 minutes is added as a
    supervisor-confirmed adjustment.
    """
    existing_source_amount = bind.execute(
        sa.text(
            "SELECT amount_minutes FROM comp_leave_transactions WHERE source_key = :source_key"
        ),
        {"source_key": _OPENING_SOURCE},
    ).scalar()
    if existing_source_amount is not None:
        return int(existing_source_amount or 0)

    available_credit = int(
        bind.execute(
            sa.text(
                "SELECT COALESCE(SUM(amount_minutes), 0) FROM comp_leave_transactions "
                "WHERE freelancer_id = :freelancer_id AND transaction_date <= :through_date"
            ),
            {"freelancer_id": freelancer_id, "through_date": date(2026, 7, 31)},
        ).scalar()
        or 0
    )
    # Existing approved-overtime ledger credits in July are used first. The
    # migration adds only the shortfall, preventing duplicate credit when the
    # two approved OT outcomes are already recorded in production.
    shortfall = max(0, (2 * _COMP_DAY_MINUTES) - available_credit)
    if shortfall <= 0:
        return 0

    bind.execute(
        sa.text(
            "INSERT INTO comp_leave_transactions ("
            "freelancer_id, transaction_date, transaction_type, amount_minutes, "
            "source_key, description, created_by_admin_id, created_at"
            ") VALUES ("
            ":freelancer_id, :transaction_date, 'OPENING_ADJUSTMENT', :amount_minutes, "
            ":source_key, :description, :admin_id, :created_at"
            ")"
        ),
        {
            "freelancer_id": freelancer_id,
            "transaction_date": _OPENING_CREDIT_DATE,
            "amount_minutes": shortfall,
            "source_key": _OPENING_SOURCE,
            "description": (
                "Supervisor-confirmed opening compensatory credit from two approved "
                "overtime outcomes for July 2026 leave coverage."
            ),
            "admin_id": admin_id,
            "created_at": now,
        },
    )
    return shortfall


def _ensure_usage_transaction(
    bind,
    *,
    freelancer_id: int,
    admin_id: int,
    leave_date: date,
    source_request_id: int | None,
    now: datetime,
) -> None:
    # Reuse the canonical request source when available; otherwise use a stable
    # release source. This keeps the correction idempotent.
    source_key = (
        f"LEAVE_REQUEST:{int(source_request_id)}"
        if source_request_id is not None
        else f"{_USAGE_SOURCE_PREFIX}:{leave_date.isoformat()}"
    )
    existing = bind.execute(
        sa.text(
            "SELECT id FROM comp_leave_transactions WHERE source_key = :source_key"
        ),
        {"source_key": source_key},
    ).scalar()
    values = {
        "freelancer_id": freelancer_id,
        "transaction_date": leave_date,
        "transaction_type": "USED_LEAVE",
        "amount_minutes": -_COMP_DAY_MINUTES,
        "description": (
            f"Applied one full-day compensatory credit to approved leave on "
            f"{leave_date.isoformat()}."
        ),
        "admin_id": admin_id,
        "created_at": now,
        "source_key": source_key,
    }
    if existing is None:
        bind.execute(
            sa.text(
                "INSERT INTO comp_leave_transactions ("
                "freelancer_id, transaction_date, transaction_type, amount_minutes, "
                "source_key, description, created_by_admin_id, created_at"
                ") VALUES ("
                ":freelancer_id, :transaction_date, :transaction_type, :amount_minutes, "
                ":source_key, :description, :admin_id, :created_at"
                ")"
            ),
            values,
        )
    else:
        bind.execute(
            sa.text(
                "UPDATE comp_leave_transactions SET freelancer_id = :freelancer_id, "
                "transaction_date = :transaction_date, transaction_type = :transaction_type, "
                "amount_minutes = :amount_minutes, description = :description, "
                "created_by_admin_id = :admin_id WHERE id = :transaction_id"
            ),
            {**values, "transaction_id": int(existing)},
        )


def _remove_usage_transaction(
    bind, *, leave_date: date, source_request_id: int | None
) -> None:
    keys = [f"{_USAGE_SOURCE_PREFIX}:{leave_date.isoformat()}"]
    if source_request_id is not None:
        keys.append(f"LEAVE_REQUEST:{int(source_request_id)}")
    for source_key in keys:
        bind.execute(
            sa.text(
                "DELETE FROM comp_leave_transactions "
                "WHERE source_key = :source_key AND amount_minutes < 0"
            ),
            {"source_key": source_key},
        )



def _invalidate_non_finalized_dtr(bind, freelancer_id: int) -> int:
    dtr_ids = [
        int(row[0])
        for row in bind.execute(
            sa.text(
                "SELECT id FROM monthly_dtr WHERE freelancer_id = :freelancer_id "
                "AND month_key = :month_key AND status <> 'FINALIZED'"
            ),
            {"freelancer_id": freelancer_id, "month_key": _JULY_MONTH},
        ).all()
    ]
    for dtr_id in dtr_ids:
        for table_name in (
            "payroll_month_summary",
            "dtr_daily_lines",
            "dtr_task_lines",
            "dtr_comp_lines",
            "dtr_leave_lines",
        ):
            bind.execute(
                sa.text(f"DELETE FROM {table_name} WHERE monthly_dtr_id = :dtr_id"),
                {"dtr_id": dtr_id},
            )
        bind.execute(
            sa.text("DELETE FROM monthly_dtr WHERE id = :dtr_id"),
            {"dtr_id": dtr_id},
        )
    return len(dtr_ids)


def upgrade() -> None:
    bind = op.get_bind()
    now = datetime.now(timezone.utc)
    gab = _gab(bind)
    admin_id = _admin_id(bind)
    if gab is None or admin_id is None:
        return

    freelancer_id = int(gab["id"])
    added_opening_credit = _ensure_opening_credit(
        bind, freelancer_id=freelancer_id, admin_id=int(admin_id), now=now
    )

    for leave_date in _COMP_COVERED_DATES:
        _leave_id, request_id = _ensure_leave(
            bind,
            freelancer_id=freelancer_id,
            admin_id=int(admin_id),
            leave_date=leave_date,
            compensated=True,
            now=now,
        )
        _ensure_usage_transaction(
            bind,
            freelancer_id=freelancer_id,
            admin_id=int(admin_id),
            leave_date=leave_date,
            source_request_id=request_id,
            now=now,
        )

    for leave_date in _REGULAR_LEAVE_DATES:
        _leave_id, request_id = _ensure_leave(
            bind,
            freelancer_id=freelancer_id,
            admin_id=int(admin_id),
            leave_date=leave_date,
            compensated=False,
            now=now,
        )
        _remove_usage_transaction(
            bind, leave_date=leave_date, source_request_id=request_id
        )

    invalidated = _invalidate_non_finalized_dtr(bind, freelancer_id)

    bind.execute(
        sa.text(
            "INSERT INTO audit_log ("
            "actor_type, actor_id, action, target_type, target_id, details, ip_address, created_at"
            ") VALUES ("
            "'SYSTEM', NULL, 'RELEASE_DATA_MIGRATION', 'GAB_JULY_2026_DTR', :target_id, "
            ":details, NULL, :created_at"
            ")"
        ),
        {
            "target_id": freelancer_id,
            "details": (
                "Release 21.15 applied two whole-day compensatory credits to "
                "Gabrielle Gameng's four approved July 2026 leave dates. July 1 and "
                "July 2 are covered; July 3 and July 6 remain deductible. Added "
                f"{added_opening_credit} opening credit minute(s) only when needed; "
                f"invalidated {invalidated} non-finalized July DTR snapshot(s)."
            ),
            "created_at": now,
        },
    )


def downgrade() -> None:
    # This is a supervisor-approved historical accounting correction. Downgrade
    # intentionally does not reverse the leave classification or ledger entries.
    pass
