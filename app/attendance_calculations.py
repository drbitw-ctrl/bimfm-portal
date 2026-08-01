from datetime import date, datetime, time as clock_time, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import DEFAULT_TIMEZONE
from app.models import (
    AttendanceCalculation,
    AttendanceMonthLock,
    DailyAttendance,
    Freelancer,
    WorkSchedule,
)


DAY_FIELDS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalized_utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def safe_zone(timezone_name: str):
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        try:
            return ZoneInfo(DEFAULT_TIMEZONE)
        except ZoneInfoNotFoundError:
            return timezone(timedelta(hours=8), name="UTC+08:00")


def parse_hhmm(value: str) -> clock_time:
    try:
        parsed = clock_time.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Time must use the HH:MM format.") from exc
    return parsed.replace(second=0, microsecond=0)


def minutes_label(minutes: int) -> str:
    value = max(0, int(minutes or 0))
    hours, remaining = divmod(value, 60)
    if hours:
        return f"{hours}h {remaining:02d}m"
    return f"{remaining}m"


def ensure_default_schedule(database: Session) -> WorkSchedule:
    schedule = database.scalar(
        select(WorkSchedule)
        .where(WorkSchedule.is_active.is_(True))
        .order_by(WorkSchedule.id)
    )
    if schedule is not None:
        return schedule

    schedule = WorkSchedule(
        name="Standard Freelancer Schedule",
        timezone_name=DEFAULT_TIMEZONE,
        start_time_text="09:00",
        end_time_text="18:00",
        grace_minutes=15,
        break_minutes=60,
        break_trigger_minutes=300,
        monday=True,
        tuesday=True,
        wednesday=True,
        thursday=True,
        friday=True,
        saturday=False,
        sunday=False,
        is_active=True,
    )
    database.add(schedule)
    database.commit()
    database.refresh(schedule)
    return schedule


def get_active_schedule(database: Session) -> WorkSchedule:
    return ensure_default_schedule(database)


def is_scheduled_workday(schedule: WorkSchedule, attendance_date: date) -> bool:
    return bool(getattr(schedule, DAY_FIELDS[attendance_date.weekday()]))


def get_calculation(
    database: Session,
    daily_attendance_id: int,
) -> Optional[AttendanceCalculation]:
    return database.scalar(
        select(AttendanceCalculation).where(
            AttendanceCalculation.daily_attendance_id == daily_attendance_id
        )
    )


def calculate_attendance_record(
    database: Session,
    record: DailyAttendance,
    freelancer: Freelancer,
    *,
    source: str = "AUTOMATIC",
    admin_id: Optional[int] = None,
    schedule: Optional[WorkSchedule] = None,
) -> AttendanceCalculation:
    schedule = schedule or get_active_schedule(database)
    calculation = get_calculation(database, record.id)
    if calculation is None:
        calculation = AttendanceCalculation(
            daily_attendance_id=record.id,
            freelancer_id=record.freelancer_id,
            attendance_date=record.attendance_date,
            schedule_name=schedule.name,
            scheduled_start_text=schedule.start_time_text,
            scheduled_end_text=schedule.end_time_text,
        )
        database.add(calculation)

    calculation.freelancer_id = record.freelancer_id
    calculation.attendance_date = record.attendance_date
    calculation.schedule_id = schedule.id
    calculation.schedule_name = schedule.name
    calculation.scheduled_start_text = schedule.start_time_text
    calculation.scheduled_end_text = schedule.end_time_text
    calculation.grace_minutes = schedule.grace_minutes
    calculation.scheduled_break_minutes = schedule.break_minutes
    calculation.is_workday = is_scheduled_workday(
        schedule,
        record.attendance_date,
    )
    calculation.calculation_source = source
    calculation.calculated_by_admin_id = admin_id
    calculation.calculated_at = utc_now()

    time_in = normalized_utc(record.time_in_utc)
    time_out = normalized_utc(record.time_out_utc)

    if time_in is None or time_out is None or time_out <= time_in:
        calculation.applied_break_minutes = 0
        calculation.gross_minutes = 0
        calculation.rendered_minutes = 0
        calculation.late_minutes = 0
        calculation.undertime_minutes = 0
        calculation.overtime_minutes = 0
        calculation.calculation_status = "INCOMPLETE"

        record.break_minutes = 0
        record.rendered_minutes = 0
        record.late_minutes = 0
        record.undertime_minutes = 0
        record.overtime_minutes = 0
        return calculation

    gross_minutes = max(0, int((time_out - time_in).total_seconds() // 60))
    applied_break = (
        schedule.break_minutes
        if gross_minutes >= schedule.break_trigger_minutes
        else 0
    )
    rendered_minutes = max(0, gross_minutes - applied_break)

    local_zone = safe_zone(freelancer.timezone_name)
    scheduled_start = datetime.combine(
        record.attendance_date,
        parse_hhmm(schedule.start_time_text),
        tzinfo=local_zone,
    )
    scheduled_end = datetime.combine(
        record.attendance_date,
        parse_hhmm(schedule.end_time_text),
        tzinfo=local_zone,
    )
    actual_in_local = time_in.astimezone(local_zone)
    actual_out_local = time_out.astimezone(local_zone)

    late_minutes = 0
    undertime_minutes = 0
    overtime_minutes = 0

    if calculation.is_workday:
        grace_end = scheduled_start + timedelta(minutes=schedule.grace_minutes)
        if actual_in_local > grace_end:
            late_minutes = max(
                0,
                int((actual_in_local - scheduled_start).total_seconds() // 60),
            )
        if actual_out_local < scheduled_end:
            undertime_minutes = max(
                0,
                int((scheduled_end - actual_out_local).total_seconds() // 60),
            )
        elif actual_out_local > scheduled_end:
            overtime_minutes = max(
                0,
                int((actual_out_local - scheduled_end).total_seconds() // 60),
            )
        status = "CALCULATED"
    else:
        # All rendered time on a non-workday is potential rest-day work.
        overtime_minutes = rendered_minutes
        status = "REST_DAY"

    calculation.applied_break_minutes = applied_break
    calculation.gross_minutes = gross_minutes
    calculation.rendered_minutes = rendered_minutes
    calculation.late_minutes = late_minutes
    calculation.undertime_minutes = undertime_minutes
    calculation.overtime_minutes = overtime_minutes
    calculation.calculation_status = status

    # Keep the existing daily table synchronized for DTR generation later.
    record.break_minutes = applied_break
    record.rendered_minutes = rendered_minutes
    record.late_minutes = late_minutes
    record.undertime_minutes = undertime_minutes
    record.overtime_minutes = overtime_minutes
    return calculation


def month_is_locked(database: Session, month_key: str) -> bool:
    lock = database.scalar(
        select(AttendanceMonthLock).where(
            AttendanceMonthLock.month_key == month_key,
            AttendanceMonthLock.is_locked.is_(True),
        )
    )
    return lock is not None


def initialize_missing_calculations(database: Session) -> int:
    schedule = get_active_schedule(database)
    records = list(
        database.scalars(
            select(DailyAttendance).order_by(DailyAttendance.id)
        ).all()
    )
    created = 0
    for record in records:
        if month_is_locked(database, record.attendance_date.strftime("%Y-%m")):
            continue
        if get_calculation(database, record.id) is not None:
            continue
        freelancer = database.get(Freelancer, record.freelancer_id)
        if freelancer is None:
            continue
        calculate_attendance_record(
            database,
            record,
            freelancer,
            source="STEP_06_MIGRATION",
            schedule=schedule,
        )
        created += 1
    if created:
        database.commit()
    return created


def recalculate_month(
    database: Session,
    month_start: date,
    next_month: date,
    *,
    admin_id: int,
    source: str = "ADMIN_MONTH_RECALCULATION",
) -> int:
    schedule = get_active_schedule(database)
    records = list(
        database.scalars(
            select(DailyAttendance).where(
                DailyAttendance.attendance_date >= month_start,
                DailyAttendance.attendance_date < next_month,
            )
        ).all()
    )
    count = 0
    for record in records:
        freelancer = database.get(Freelancer, record.freelancer_id)
        if freelancer is None:
            continue
        calculate_attendance_record(
            database,
            record,
            freelancer,
            source=source,
            admin_id=admin_id,
            schedule=schedule,
        )
        count += 1
    return count
