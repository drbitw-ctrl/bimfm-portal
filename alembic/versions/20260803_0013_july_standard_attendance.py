"""Backfill supervisor-approved July 2026 standard attendance.

Revision ID: 20260803_0013
Revises: 20260803_0012
Create Date: 2026-08-03
"""
from __future__ import annotations

from datetime import date, datetime, time, timezone, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from alembic import op
import sqlalchemy as sa

revision = "20260803_0013"
down_revision = "20260803_0012"
branch_labels = None
depends_on = None

# The roster approved for the July historical attendance backfill. Raymond is
# intentionally excluded because his portal account is inactive.
_ROSTER_PATTERNS = (
    ("Alexsandria Santos", "%alexsandria%santos%"),
    ("Carlo Ninoy Nilo", "%carlo%ninoy%nilo%"),
    ("Gabrielle Gameng", "%gabrielle%gameng%"),
    ("Jonica Jomadiao", "%jonica%jomadiao%"),
    ("Kaizer Macatiag", "%kaizer%macatiag%"),
    ("Lander Samson", "%lander%samson%"),
)
_GAB_PATTERN = "%gabrielle%gameng%"
_GAB_LEAVE_DATES = {
    date(2026, 7, 1),
    date(2026, 7, 2),
    date(2026, 7, 3),
    date(2026, 7, 6),
}
_CARLO_PATTERN = "%carlo%ninoy%nilo%"
_CARLO_INCORRECT_LEAVE_DATE = date(2026, 7, 27)
_IMPORT_SOURCE = "SUPERVISOR_APPROVED_IMPORT"
_IMPORT_NOTE = (
    "Supervisor-approved July 2026 historical attendance backfill: "
    "09:00-18:00 with a 60-minute break."
)


def _safe_zone(timezone_name: str | None):
    try:
        return ZoneInfo((timezone_name or "Asia/Manila").strip())
    except (ZoneInfoNotFoundError, ValueError):
        return timezone(timedelta(hours=8), name="UTC+08:00")


def _local_utc(attendance_date: date, hour: int, timezone_name: str | None) -> datetime:
    local_value = datetime.combine(
        attendance_date,
        time(hour=hour, minute=0),
        tzinfo=_safe_zone(timezone_name),
    )
    return local_value.astimezone(timezone.utc)




def _as_date(value) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _find_member(bind, pattern: str):
    return bind.execute(
        sa.text(
            "SELECT f.id, f.full_name, f.timezone_name "
            "FROM freelancers f "
            "WHERE lower(f.full_name) LIKE :pattern "
            "AND f.is_active = :active "
            "AND EXISTS ("
            "  SELECT 1 FROM freelancer_accounts a "
            "  WHERE a.freelancer_id = f.id AND a.is_active = :active"
            ") "
            "ORDER BY f.id LIMIT 1"
        ),
        {"pattern": pattern, "active": True},
    ).mappings().first()


def _find_member_any_status(bind, pattern: str):
    return bind.execute(
        sa.text(
            "SELECT id, full_name, timezone_name FROM freelancers "
            "WHERE lower(full_name) LIKE :pattern ORDER BY id LIMIT 1"
        ),
        {"pattern": pattern},
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


def _active_holidays(bind) -> set[date]:
    return {
        _as_date(row[0])
        for row in bind.execute(
            sa.text(
                "SELECT holiday_date FROM holidays "
                "WHERE is_active = :active "
                "AND holiday_date >= :start_date AND holiday_date < :next_month"
            ),
            {
                "active": True,
                "start_date": date(2026, 7, 1),
                "next_month": date(2026, 8, 1),
            },
        ).all()
    }


def _leave_dates(bind, freelancer_id: int) -> set[date]:
    return {
        _as_date(row[0])
        for row in bind.execute(
            sa.text(
                "SELECT leave_date FROM leave_records "
                "WHERE freelancer_id = :freelancer_id "
                "AND status = 'APPROVED' "
                "AND leave_date >= :start_date AND leave_date < :next_month"
            ),
            {
                "freelancer_id": freelancer_id,
                "start_date": date(2026, 7, 1),
                "next_month": date(2026, 8, 1),
            },
        ).all()
    }


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


def _ensure_gab_leave(bind, admin_id: int | None, now: datetime) -> None:
    gab = _find_member_any_status(bind, _GAB_PATTERN)
    if gab is None or admin_id is None:
        return
    for leave_date in sorted(_GAB_LEAVE_DATES):
        existing = bind.execute(
            sa.text(
                "SELECT id FROM leave_records "
                "WHERE freelancer_id = :freelancer_id AND leave_date = :leave_date"
            ),
            {"freelancer_id": gab["id"], "leave_date": leave_date},
        ).scalar()
        if existing is None:
            bind.execute(
                sa.text(
                    "INSERT INTO leave_records ("
                    "freelancer_id, leave_date, leave_type, is_paid, status, "
                    "duration_minutes, comp_leave_minutes_used, source_request_id, notes, "
                    "approved_by_admin_id, created_at, updated_at"
                    ") VALUES ("
                    ":freelancer_id, :leave_date, 'APPROVED_LEAVE', :is_paid, 'APPROVED', "
                    "480, 0, NULL, :notes, :admin_id, :created_at, :updated_at"
                    ")"
                ),
                {
                    "freelancer_id": gab["id"],
                    "leave_date": leave_date,
                    "is_paid": False,
                    "notes": "Approved leave confirmed for July 2026.",
                    "admin_id": admin_id,
                    "created_at": now,
                    "updated_at": now,
                },
            )


def _remove_incorrect_carlo_leave(bind) -> None:
    carlo = _find_member_any_status(bind, _CARLO_PATTERN)
    if carlo is None:
        return
    for table_name in ("leave_records", "leave_requests"):
        bind.execute(
            sa.text(
                f"DELETE FROM {table_name} "
                "WHERE freelancer_id = :freelancer_id AND leave_date = :leave_date"
            ),
            {
                "freelancer_id": carlo["id"],
                "leave_date": _CARLO_INCORRECT_LEAVE_DATE,
            },
        )


def upgrade() -> None:
    bind = op.get_bind()
    metadata = sa.MetaData()
    daily_attendance = sa.Table("daily_attendance", metadata, autoload_with=bind)
    attendance_calculations = sa.Table(
        "attendance_calculations", metadata, autoload_with=bind
    )
    now = datetime.now(timezone.utc)
    admin_id = _admin_id(bind)

    _remove_incorrect_carlo_leave(bind)
    _ensure_gab_leave(bind, admin_id, now)

    holidays = _active_holidays(bind)
    inserted_count = 0
    filled_count = 0
    preserved_count = 0
    affected_members: list[int] = []

    for _label, pattern in _ROSTER_PATTERNS:
        member = _find_member(bind, pattern)
        if member is None:
            continue
        freelancer_id = int(member["id"])
        affected_members.append(freelancer_id)
        approved_leave = _leave_dates(bind, freelancer_id)

        for day_number in range(1, 32):
            attendance_date = date(2026, 7, day_number)
            if attendance_date.weekday() >= 5:
                continue
            if attendance_date in holidays or attendance_date in approved_leave:
                continue

            time_in_utc = _local_utc(attendance_date, 9, member["timezone_name"])
            time_out_utc = _local_utc(attendance_date, 18, member["timezone_name"])

            existing = bind.execute(
                sa.select(daily_attendance).where(
                    daily_attendance.c.freelancer_id == freelancer_id,
                    daily_attendance.c.attendance_date == attendance_date,
                )
            ).mappings().first()

            if existing is None:
                result = bind.execute(
                    daily_attendance.insert().values(
                        freelancer_id=freelancer_id,
                        attendance_date=attendance_date,
                        time_in_utc=time_in_utc,
                        time_out_utc=time_out_utc,
                        break_minutes=60,
                        rendered_minutes=480,
                        late_minutes=0,
                        undertime_minutes=0,
                        overtime_minutes=0,
                        status="COMPLETE",
                        review_status="REVIEWED",
                        is_locked=False,
                        created_at=now,
                        updated_at=now,
                    )
                )
                daily_id = int(result.inserted_primary_key[0])
                inserted_count += 1
            elif existing["time_in_utc"] is None and existing["time_out_utc"] is None:
                daily_id = int(existing["id"])
                bind.execute(
                    daily_attendance.update()
                    .where(daily_attendance.c.id == daily_id)
                    .values(
                        time_in_utc=time_in_utc,
                        time_out_utc=time_out_utc,
                        break_minutes=60,
                        rendered_minutes=480,
                        late_minutes=0,
                        undertime_minutes=0,
                        overtime_minutes=0,
                        status="COMPLETE",
                        review_status="REVIEWED",
                        updated_at=now,
                    )
                )
                filled_count += 1
            else:
                # Preserve any actual historical punch already stored.
                preserved_count += 1
                continue

            existing_calculation = bind.execute(
                sa.select(attendance_calculations.c.id).where(
                    attendance_calculations.c.daily_attendance_id == daily_id
                )
            ).scalar()
            calculation_values = {
                "daily_attendance_id": daily_id,
                "freelancer_id": freelancer_id,
                "attendance_date": attendance_date,
                "schedule_id": None,
                "schedule_name": "Supervisor-approved July 2026 schedule",
                "scheduled_start_text": "09:00",
                "scheduled_end_text": "18:00",
                "grace_minutes": 0,
                "scheduled_break_minutes": 60,
                "applied_break_minutes": 60,
                "is_workday": True,
                "gross_minutes": 540,
                "rendered_minutes": 480,
                "late_minutes": 0,
                "undertime_minutes": 0,
                "overtime_minutes": 0,
                "calculation_status": "CALCULATED",
                "calculation_source": _IMPORT_SOURCE,
                "calculated_by_admin_id": admin_id,
                "calculated_at": now,
                "updated_at": now,
            }
            if existing_calculation is None:
                bind.execute(attendance_calculations.insert().values(**calculation_values))
            else:
                calculation_values.pop("daily_attendance_id")
                bind.execute(
                    attendance_calculations.update()
                    .where(attendance_calculations.c.id == existing_calculation)
                    .values(**calculation_values)
                )

    for freelancer_id in affected_members:
        _invalidate_non_finalized_dtr(bind, freelancer_id)

    bind.execute(
        sa.text(
            "INSERT INTO audit_log ("
            "actor_type, actor_id, action, target_type, details, ip_address, created_at"
            ") VALUES ("
            "'SYSTEM', NULL, 'RELEASE_DATA_MIGRATION', 'JULY_2026_ATTENDANCE', "
            ":details, NULL, :created_at"
            ")"
        ),
        {
            "details": (
                f"{_IMPORT_NOTE} Inserted {inserted_count} records; filled "
                f"{filled_count} empty records; preserved {preserved_count} existing "
                "records. Gabrielle Gameng leave dates July 1-3 and 6 were excluded."
            ),
            "created_at": now,
        },
    )


def downgrade() -> None:
    # This is an approved historical data import. Downgrade intentionally does
    # not delete attendance records or restore the incorrect Carlo leave.
    pass
