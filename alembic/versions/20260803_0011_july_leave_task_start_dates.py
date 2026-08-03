"""Correct July leave records and backfill task start dates.

Revision ID: 20260803_0011
Revises: 20260803_0010
Create Date: 2026-08-03
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "20260803_0011"
down_revision = "20260803_0010"
branch_labels = None
depends_on = None

_GAB_LEAVE_DATES = (
    date(2026, 7, 1),
    date(2026, 7, 2),
    date(2026, 7, 3),
    date(2026, 7, 6),
)
_CARLO_INCORRECT_LEAVE_DATE = date(2026, 7, 27)
_TASK_START_DATES = {
    233: date(2025, 6, 16),
    234: date(2025, 6, 20),
    235: date(2025, 7, 3),
    236: date(2025, 7, 15),
    237: date(2025, 7, 22),
}
_IMPORT_NOTE = "Imported from the confirmed July 2026 attendance correction in Release 21.08."


def _person_id(bind, full_name: str):
    return bind.execute(
        sa.text(
            "SELECT id FROM freelancers "
            "WHERE lower(trim(full_name)) = :full_name "
            "ORDER BY id LIMIT 1"
        ),
        {"full_name": full_name.casefold()},
    ).scalar()


def _admin_id(bind):
    admin_id = bind.execute(
        sa.text(
            "SELECT id FROM hr_admin_accounts "
            "WHERE is_active = :active "
            "ORDER BY CASE WHEN upper(role) = 'ADMIN' THEN 0 ELSE 1 END, id "
            "LIMIT 1"
        ),
        {"active": True},
    ).scalar()
    if admin_id is not None:
        return admin_id
    return bind.execute(
        sa.text("SELECT id FROM hr_admin_accounts ORDER BY id LIMIT 1")
    ).scalar()


def _invalidate_non_finalized_dtr(bind, freelancer_id: int) -> None:
    dtr_ids = [
        int(row[0])
        for row in bind.execute(
            sa.text(
                "SELECT id FROM monthly_dtr "
                "WHERE freelancer_id = :freelancer_id "
                "AND month_key = '2026-07' "
                "AND status <> 'FINALIZED'"
            ),
            {"freelancer_id": freelancer_id},
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


def upgrade() -> None:
    bind = op.get_bind()
    now = datetime.now(timezone.utc)

    # The exported task workbook supplied for this release contained five
    # formerly blank start dates. Existing non-null values are never overwritten.
    for task_id, start_date in _TASK_START_DATES.items():
        bind.execute(
            sa.text(
                "UPDATE portal_tasks SET start_date = :start_date, updated_at = :updated_at "
                "WHERE id = :task_id AND start_date IS NULL"
            ),
            {"task_id": task_id, "start_date": start_date, "updated_at": now},
        )

    gab_id = _person_id(bind, "gabrielle gameng")
    carlo_id = _person_id(bind, "carlo ninoy nilo")
    admin_id = _admin_id(bind)

    # Carlo has no leave on July 27. Remove the incorrect source record and any
    # corresponding request so the portal and regenerated DTR use the correction.
    if carlo_id is not None:
        bind.execute(
            sa.text(
                "DELETE FROM leave_records "
                "WHERE freelancer_id = :freelancer_id AND leave_date = :leave_date"
            ),
            {"freelancer_id": carlo_id, "leave_date": _CARLO_INCORRECT_LEAVE_DATE},
        )
        bind.execute(
            sa.text(
                "DELETE FROM leave_requests "
                "WHERE freelancer_id = :freelancer_id AND leave_date = :leave_date"
            ),
            {"freelancer_id": carlo_id, "leave_date": _CARLO_INCORRECT_LEAVE_DATE},
        )
        _invalidate_non_finalized_dtr(bind, carlo_id)

    # Approved leave records require an accountable staff record. Production
    # installations already have an Administration account; a missing account
    # leaves the dates untouched rather than creating unauditable records.
    if gab_id is not None and admin_id is not None:
        for leave_date in _GAB_LEAVE_DATES:
            exists = bind.execute(
                sa.text(
                    "SELECT id FROM leave_records "
                    "WHERE freelancer_id = :freelancer_id AND leave_date = :leave_date"
                ),
                {"freelancer_id": gab_id, "leave_date": leave_date},
            ).scalar()
            if exists is None:
                bind.execute(
                    sa.text(
                        "INSERT INTO leave_records ("
                        "freelancer_id, leave_date, leave_type, is_paid, status, "
                        "duration_minutes, comp_leave_minutes_used, source_request_id, notes, "
                        "approved_by_admin_id, created_at, updated_at"
                        ") VALUES ("
                        ":freelancer_id, :leave_date, :leave_type, :is_paid, :status, "
                        ":duration_minutes, :comp_leave_minutes_used, NULL, :notes, "
                        ":approved_by_admin_id, :created_at, :updated_at"
                        ")"
                    ),
                    {
                        "freelancer_id": gab_id,
                        "leave_date": leave_date,
                        "leave_type": "APPROVED_LEAVE",
                        "is_paid": False,
                        "status": "APPROVED",
                        "duration_minutes": 480,
                        "comp_leave_minutes_used": 0,
                        "notes": _IMPORT_NOTE,
                        "approved_by_admin_id": admin_id,
                        "created_at": now,
                        "updated_at": now,
                    },
                )
        _invalidate_non_finalized_dtr(bind, gab_id)

    bind.execute(
        sa.text(
            "INSERT INTO audit_log (actor_type, actor_id, action, target_type, details, ip_address, created_at) "
            "VALUES ('SYSTEM', NULL, 'RELEASE_DATA_MIGRATION', 'JULY_2026_CORRECTION', "
            ":details, NULL, :created_at)"
        ),
        {
            "details": (
                "Release 21.08 corrected Gabrielle Gameng leave dates, removed Carlo Ninoy Nilo "
                "July 27 leave when present, and backfilled task start dates 233-237."
            ),
            "created_at": now,
        },
    )


def downgrade() -> None:
    bind = op.get_bind()
    for task_id, start_date in _TASK_START_DATES.items():
        bind.execute(
            sa.text(
                "UPDATE portal_tasks SET start_date = NULL "
                "WHERE id = :task_id AND start_date = :start_date"
            ),
            {"task_id": task_id, "start_date": start_date},
        )

    gab_id = _person_id(bind, "gabrielle gameng")
    if gab_id is not None:
        bind.execute(
            sa.text(
                "DELETE FROM leave_records "
                "WHERE freelancer_id = :freelancer_id AND notes = :notes"
            ),
            {"freelancer_id": gab_id, "notes": _IMPORT_NOTE},
        )
