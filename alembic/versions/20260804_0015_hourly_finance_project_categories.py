"""Add project categories and align Gab's July 2026 hourly comp-credit data.

Revision ID: 20260804_0015
Revises: 20260804_0014
Create Date: 2026-08-04
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "20260804_0015"
down_revision = "20260804_0014"
branch_labels = None
depends_on = None

_GAB_PATTERN = "%gabrielle%gameng%"
_TARGET_OPENING_MINUTES = 15 * 60
_PREVIOUS_OPENING_SOURCE = "RELEASE_21_15:GAB_OPENING_OT_CREDIT"
_JULY_LEAVE_DATES = (
    date(2026, 7, 1),
    date(2026, 7, 2),
    date(2026, 7, 3),
    date(2026, 7, 6),
)
_USAGE_PREFIX = "RELEASE_21_16:GAB_HOURLY_COMP"


def _column_exists(bind, table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def _admin_id(bind):
    return bind.execute(
        sa.text(
            "SELECT id FROM hr_admin_accounts WHERE is_active = :active "
            "ORDER BY CASE WHEN upper(role) = 'ADMIN' THEN 0 ELSE 1 END, id LIMIT 1"
        ),
        {"active": True},
    ).scalar()


def _gab_id(bind):
    return bind.execute(
        sa.text(
            "SELECT id FROM freelancers WHERE lower(full_name) LIKE :pattern "
            "ORDER BY id LIMIT 1"
        ),
        {"pattern": _GAB_PATTERN},
    ).scalar()


def _backfill_categories(bind):
    bind.execute(sa.text(
        "UPDATE portal_projects SET project_category = '安居' "
        "WHERE project_category IS NULL AND name LIKE '%安居%'"
    ))
    bind.execute(sa.text(
        "UPDATE portal_projects SET project_category = 'Bridge' "
        "WHERE project_category IS NULL AND (lower(name) LIKE '%bridge%' OR name LIKE '%橋%')"
    ))
    bind.execute(sa.text(
        "UPDATE portal_projects SET project_category = 'MRT' "
        "WHERE project_category IS NULL AND (lower(name) LIKE '%mrt%' OR name LIKE '%捷運%')"
    ))


def _normalize_gab_hourly_credit(bind, freelancer_id: int, admin_id: int, now: datetime):
    # Existing genuine positive credits before July are honored first. The prior
    # release adjustment is resized (or removed) so the confirmed opening total
    # is exactly 15 hours without duplicating approved OT transactions.
    genuine_positive = int(bind.execute(
        sa.text(
            "SELECT COALESCE(SUM(amount_minutes), 0) FROM comp_leave_transactions "
            "WHERE freelancer_id = :fid AND transaction_date <= :through_date "
            "AND amount_minutes > 0 AND source_key <> :previous_source"
        ),
        {"fid": freelancer_id, "through_date": date(2026, 6, 30), "previous_source": _PREVIOUS_OPENING_SOURCE},
    ).scalar() or 0)
    adjustment = max(0, _TARGET_OPENING_MINUTES - genuine_positive)
    existing_adjustment_id = bind.execute(
        sa.text("SELECT id FROM comp_leave_transactions WHERE source_key = :source"),
        {"source": _PREVIOUS_OPENING_SOURCE},
    ).scalar()
    if adjustment > 0:
        values = {
            "fid": freelancer_id,
            "tx_date": date(2026, 6, 30),
            "amount": adjustment,
            "source": _PREVIOUS_OPENING_SOURCE,
            "description": "Supervisor-confirmed 15-hour opening overtime credit for July 2026 hourly payroll treatment.",
            "admin_id": admin_id,
            "created_at": now,
        }
        if existing_adjustment_id is None:
            bind.execute(sa.text(
                "INSERT INTO comp_leave_transactions (freelancer_id, transaction_date, transaction_type, amount_minutes, source_key, description, created_by_admin_id, created_at) "
                "VALUES (:fid, :tx_date, 'OPENING_ADJUSTMENT', :amount, :source, :description, :admin_id, :created_at)"
            ), values)
        else:
            bind.execute(sa.text(
                "UPDATE comp_leave_transactions SET freelancer_id=:fid, transaction_date=:tx_date, "
                "transaction_type='OPENING_ADJUSTMENT', amount_minutes=:amount, description=:description, "
                "created_by_admin_id=:admin_id WHERE id=:id"
            ), {**values, "id": int(existing_adjustment_id)})
    elif existing_adjustment_id is not None:
        bind.execute(sa.text("DELETE FROM comp_leave_transactions WHERE id=:id"), {"id": int(existing_adjustment_id)})

    # Remove previous release-generated negative usage lines and canonical request
    # usage lines for the four July dates, then allocate 15 hours hour-for-hour.
    bind.execute(sa.text(
        "DELETE FROM comp_leave_transactions WHERE freelancer_id=:fid AND transaction_date IN (:d1,:d2,:d3,:d4) "
        "AND amount_minutes < 0 AND (source_key LIKE 'RELEASE_21_15:GAB_COMP_LEAVE:%' OR source_key LIKE 'RELEASE_21_16:GAB_HOURLY_COMP:%')"
    ), {"fid": freelancer_id, "d1": _JULY_LEAVE_DATES[0], "d2": _JULY_LEAVE_DATES[1], "d3": _JULY_LEAVE_DATES[2], "d4": _JULY_LEAVE_DATES[3]})

    remaining = _TARGET_OPENING_MINUTES
    applied_total = 0
    for leave_date in _JULY_LEAVE_DATES:
        leave = bind.execute(sa.text(
            "SELECT id, source_request_id FROM leave_records WHERE freelancer_id=:fid AND leave_date=:leave_date"
        ), {"fid": freelancer_id, "leave_date": leave_date}).mappings().first()
        if leave is None:
            continue
        apply_minutes = min(480, remaining)
        remaining -= apply_minutes
        applied_total += apply_minutes
        leave_type = "COMPENSATORY_LEAVE" if apply_minutes else "APPROVED_LEAVE"
        is_paid = apply_minutes >= 480
        note = (
            f"Supervisor-approved July 2026 leave; {apply_minutes} minute(s) covered by overtime credit under hourly payroll treatment."
            if apply_minutes else
            "Supervisor-approved July 2026 leave; no overtime credit applied to this date."
        )
        bind.execute(sa.text(
            "UPDATE leave_records SET leave_type=:leave_type, is_paid=:is_paid, duration_minutes=480, "
            "comp_leave_minutes_used=:used, notes=:notes, approved_by_admin_id=:admin_id, updated_at=:updated_at "
            "WHERE id=:leave_id"
        ), {"leave_type": leave_type, "is_paid": is_paid, "used": apply_minutes, "notes": note, "admin_id": admin_id, "updated_at": now, "leave_id": int(leave["id"])})

        request_id = leave["source_request_id"]
        if request_id is not None:
            bind.execute(sa.text(
                "UPDATE leave_requests SET leave_type=:leave_type, status='APPROVED', approved_minutes=480, "
                "reviewed_by_admin_id=:admin_id, reviewed_at=COALESCE(reviewed_at,:now), "
                "review_reason=COALESCE(NULLIF(review_reason,''),'Supervisor-approved hourly comp-credit correction.'), "
                "updated_at=:now WHERE id=:request_id"
            ), {"leave_type": leave_type, "admin_id": admin_id, "now": now, "request_id": int(request_id)})
            bind.execute(sa.text(
                "DELETE FROM comp_leave_transactions WHERE source_key=:source AND amount_minutes < 0"
            ), {"source": f"LEAVE_REQUEST:{int(request_id)}"})

        if apply_minutes:
            source = f"{_USAGE_PREFIX}:{leave_date.isoformat()}"
            bind.execute(sa.text(
                "INSERT INTO comp_leave_transactions (freelancer_id, transaction_date, transaction_type, amount_minutes, source_key, description, created_by_admin_id, created_at) "
                "VALUES (:fid,:tx_date,'USED_LEAVE',:amount,:source,:description,:admin_id,:created_at)"
            ), {
                "fid": freelancer_id,
                "tx_date": leave_date,
                "amount": -apply_minutes,
                "source": source,
                "description": f"Applied {apply_minutes} overtime-credit minutes to approved leave on {leave_date.isoformat()}.",
                "admin_id": admin_id,
                "created_at": now,
            })

    # Rebuild non-finalized July DTR/Finance snapshots after deployment.
    dtr_ids = [int(row[0]) for row in bind.execute(sa.text(
        "SELECT id FROM monthly_dtr WHERE freelancer_id=:fid AND month_key='2026-07' AND status <> 'FINALIZED'"
    ), {"fid": freelancer_id}).all()]
    for dtr_id in dtr_ids:
        for table in ("payroll_month_summary", "dtr_daily_lines", "dtr_task_lines", "dtr_comp_lines", "dtr_leave_lines"):
            bind.execute(sa.text(f"DELETE FROM {table} WHERE monthly_dtr_id=:dtr_id"), {"dtr_id": dtr_id})
        bind.execute(sa.text("DELETE FROM monthly_dtr WHERE id=:dtr_id"), {"dtr_id": dtr_id})

    bind.execute(sa.text(
        "INSERT INTO audit_log (actor_type, actor_id, action, target_type, target_id, details, ip_address, created_at) "
        "VALUES ('SYSTEM',NULL,'RELEASE_DATA_MIGRATION','GAB_JULY_2026_HOURLY_PAYROLL',:target_id,:details,NULL,:created_at)"
    ), {
        "target_id": freelancer_id,
        "details": (
            f"Release 21.16 confirmed 15 hours (900 minutes) of opening OT credit, applied {applied_total} minutes "
            "hour-for-hour to four July leave days, leaving 17 unpaid leave hours."
        ),
        "created_at": now,
    })


def upgrade() -> None:
    bind = op.get_bind()
    if not _column_exists(bind, "portal_projects", "project_category"):
        with op.batch_alter_table("portal_projects") as batch:
            batch.add_column(sa.Column("project_category", sa.String(length=100), nullable=True))
    _backfill_categories(bind)

    gab_id = _gab_id(bind)
    admin_id = _admin_id(bind)
    if gab_id is not None and admin_id is not None:
        _normalize_gab_hourly_credit(bind, int(gab_id), int(admin_id), datetime.now(timezone.utc))


def downgrade() -> None:
    bind = op.get_bind()
    if _column_exists(bind, "portal_projects", "project_category"):
        with op.batch_alter_table("portal_projects") as batch:
            batch.drop_column("project_category")
