"""Attendance and DTR web routes extracted from the legacy application.

Milestone 3 keeps the existing behavior intact while moving attendance endpoints
out of ``app.main``. Shared helpers remain in ``app.main`` temporarily and are
injected during router creation; later milestones will move those helpers into
services and dependencies.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.auth.permissions import Permission, has_permission, normalize_role
from app.task_hourly_mode import is_task_hourly_member, task_hourly_month_ledger


def create_attendance_router(legacy_namespace: dict[str, object]) -> APIRouter:
    """Build the attendance router using the existing application dependencies."""
    # Route bodies below are intentionally preserved verbatim. Injecting the
    # existing namespace lets us refactor safely before splitting services.
    globals().update(legacy_namespace)
    attendance_router = APIRouter(tags=["Attendance and DTR"])
    globals()["router"] = attendance_router
    return attendance_router


# ``configure_attendance_routes`` installs the preserved route functions after
# the application has defined all legacy helpers.
def configure_attendance_routes(legacy_namespace: dict[str, object]) -> APIRouter:
    router = create_attendance_router(legacy_namespace)
    @router.get("/admin/attendance/today", response_class=HTMLResponse)
    def admin_attendance_today(request: Request):
        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", status_code=303)

            hr_ids = [row.id for row in hr_freelancer_choices(database)]
            freelancers = list(
                database.scalars(
                    select(Freelancer)
                    .options(joinedload(Freelancer.account))
                    .where(Freelancer.id.in_(hr_ids))
                    .order_by(Freelancer.full_name)
                ).unique().all()
            ) if hr_ids else []

            rows: list[dict[str, object]] = []
            for freelancer in freelancers:
                local_date = current_attendance_date(freelancer.timezone_name)
                record = get_daily_attendance(database, freelancer.id, local_date)
                correction_count = 0
                if record is not None:
                    correction_count = int(
                        database.scalar(
                            select(func.count(AttendanceCorrection.id)).where(
                                AttendanceCorrection.daily_attendance_id == record.id
                            )
                        ) or 0
                    )
                attendance_row = build_admin_attendance_row(
                    freelancer,
                    record,
                    local_date,
                    correction_count,
                    get_calculation(database, record.id) if record else None,
                )
                if is_task_hourly_member(freelancer):
                    attendance_row["status"] = "Task-Hourly"
                    attendance_row["time_in"] = "Not required"
                    attendance_row["time_out"] = "Not required"
                    attendance_row["elapsed"] = "See Work Orders"
                rows.append(attendance_row)

            summary = {
                "complete": sum(row["status"] == "Complete" for row in rows),
                "working": sum(
                    row["status"] == "Currently Working" for row in rows
                ),
                "no_record": sum(row["status"] == "No Record" for row in rows),
                "disabled": sum(
                    row["status"] == "Account Disabled" for row in rows
                ),
            }

            management_now = utc_now().astimezone(
                freelancer_zone(DEFAULT_TIMEZONE)
            )

            return templates.TemplateResponse(
                request=request,
                name="admin_attendance_today.html",
                context=template_context(
                    request,
                    admin=admin,
                    rows=rows,
                    summary=summary,
                    management_date=management_now.strftime("%A, %B %d, %Y"),
                    management_time=management_now.strftime("%I:%M:%S %p").lstrip("0"),
                ),
            )


    @router.get("/admin/attendance/monthly", response_class=HTMLResponse)
    def admin_attendance_monthly(
        request: Request,
        month: str = "",
        freelancer_id: str = "",
    ):
        selected_month = month.strip() or current_month_key(DEFAULT_TIMEZONE)
        selected_freelancer_id: Optional[int] = None
        raw_freelancer_id = (freelancer_id or "").strip()
        if raw_freelancer_id:
            try:
                selected_freelancer_id = int(raw_freelancer_id)
            except (TypeError, ValueError):
                set_flash(request, "Invalid freelancer selection.", "error")
                return RedirectResponse(
                    f"/admin/attendance/monthly?month={selected_month}",
                    status_code=303,
                )
        month_range = parse_month_key(selected_month)
        if month_range is None:
            set_flash(request, "Invalid month. Use YYYY-MM.", "error")
            return RedirectResponse(
                f"/admin/attendance/monthly?month={current_month_key()}",
                status_code=303,
            )

        start_date, next_month = month_range

        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", status_code=303)

            freelancers = hr_freelancer_choices(database)

            query = (
                select(DailyAttendance, Freelancer)
                .join(Freelancer, Freelancer.id == DailyAttendance.freelancer_id)
                .where(
                    DailyAttendance.attendance_date >= start_date,
                    DailyAttendance.attendance_date < next_month,
                )
                .order_by(
                    DailyAttendance.attendance_date.desc(),
                    Freelancer.full_name,
                )
            )
            if selected_freelancer_id is not None:
                query = query.where(Freelancer.id == selected_freelancer_id)

            results = list(database.execute(query).all())
            daily_ids = [record.id for record, _ in results]
            correction_counts: dict[int, int] = {}
            if daily_ids:
                correction_counts = {
                    int(daily_id): int(count)
                    for daily_id, count in database.execute(
                        select(
                            AttendanceCorrection.daily_attendance_id,
                            func.count(AttendanceCorrection.id),
                        )
                        .where(
                            AttendanceCorrection.daily_attendance_id.in_(daily_ids)
                        )
                        .group_by(AttendanceCorrection.daily_attendance_id)
                    ).all()
                }

            calculation_map: dict[int, AttendanceCalculation] = {}
            if daily_ids:
                calculation_map = {
                    calculation.daily_attendance_id: calculation
                    for calculation in database.scalars(
                        select(AttendanceCalculation).where(
                            AttendanceCalculation.daily_attendance_id.in_(daily_ids)
                        )
                    ).all()
                }

            rows = [
                build_admin_attendance_row(
                    freelancer,
                    record,
                    record.attendance_date,
                    correction_counts.get(record.id, 0),
                    calculation_map.get(record.id),
                )
                for record, freelancer in results
            ]

            summary = {
                "total": len(rows),
                "complete": sum(row["status"] == "Complete" for row in rows),
                "missing": sum(
                    row["status"] in {"Missing Time Out", "Invalid Record"}
                    for row in rows
                ),
                "corrected": sum(row["correction_count"] > 0 for row in rows),
                "rendered_minutes": sum(
                    row["calculation"]["rendered_minutes"] for row in rows
                ),
                "late_minutes": sum(
                    row["calculation"]["late_minutes"] for row in rows
                ),
                "undertime_minutes": sum(
                    row["calculation"]["undertime_minutes"] for row in rows
                ),
                "overtime_minutes": sum(
                    row["calculation"]["overtime_minutes"] for row in rows
                ),
            }

            month_lock = get_month_lock(database, selected_month)

            return templates.TemplateResponse(
                request=request,
                name="admin_attendance_monthly.html",
                context=template_context(
                    request,
                    admin=admin,
                    freelancers=freelancers,
                    selected_month=selected_month,
                    selected_freelancer_id=selected_freelancer_id,
                    rows=rows,
                    summary=summary,
                    month_lock=month_lock,
                    current_month=current_month_key(DEFAULT_TIMEZONE),
                    schedule=get_active_schedule(database),
                    rendered_total=minutes_label(summary["rendered_minutes"]),
                    late_total=minutes_label(summary["late_minutes"]),
                    undertime_total=minutes_label(summary["undertime_minutes"]),
                    overtime_total=minutes_label(summary["overtime_minutes"]),
                ),
            )


    @router.get(
        "/admin/attendance/{freelancer_id}/{attendance_date_text}/correct",
        response_class=HTMLResponse,
    )
    def admin_attendance_correction_page(
        freelancer_id: int,
        attendance_date_text: str,
        request: Request,
    ):
        try:
            attendance_date = date.fromisoformat(attendance_date_text)
        except ValueError:
            set_flash(request, "Invalid attendance date.", "error")
            return RedirectResponse("/admin/attendance/today", status_code=303)

        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", status_code=303)

            freelancer = database.get(Freelancer, freelancer_id)
            if freelancer is None:
                set_flash(request, "Freelancer was not found.", "error")
                return RedirectResponse("/admin/attendance/today", status_code=303)

            record = get_daily_attendance(database, freelancer_id, attendance_date)
            corrections = list(
                database.scalars(
                    select(AttendanceCorrection)
                    .where(
                        AttendanceCorrection.freelancer_id == freelancer_id,
                        AttendanceCorrection.attendance_date == attendance_date,
                    )
                    .order_by(AttendanceCorrection.created_at.desc())
                ).all()
            )
            admin_ids = {
                item.corrected_by_admin_id for item in corrections
            }
            admin_names: dict[int, str] = {}
            if admin_ids:
                admin_names = {
                    item.id: item.display_name
                    for item in database.scalars(
                        select(HRAdminAccount).where(
                            HRAdminAccount.id.in_(admin_ids)
                        )
                    ).all()
                }

            return templates.TemplateResponse(
                request=request,
                name="admin_attendance_correction.html",
                context=template_context(
                    request,
                    admin=admin,
                    freelancer=freelancer,
                    attendance_date=attendance_date,
                    time_in_value=utc_to_time_input(
                        record.time_in_utc if record else None,
                        freelancer.timezone_name,
                    ),
                    time_out_value=utc_to_time_input(
                        record.time_out_utc if record else None,
                        freelancer.timezone_name,
                    ),
                    current_status=attendance_status(record),
                    locked=month_is_locked(
                        database,
                        attendance_date.strftime("%Y-%m"),
                    ),
                    correction_history=correction_history_rows(
                        corrections,
                        freelancer.timezone_name,
                        admin_names,
                    ),
                ),
            )


    @router.post("/admin/attendance/{freelancer_id}/{attendance_date_text}/correct")
    def admin_attendance_correction_submit(
        freelancer_id: int,
        attendance_date_text: str,
        request: Request,
        csrf: str = Form(...),
        time_in: str = Form(""),
        time_out: str = Form(""),
        reason: str = Form(...),
    ):
        redirect_path = (
            f"/admin/attendance/{freelancer_id}/"
            f"{attendance_date_text}/correct"
        )
        if not validate_csrf(request, csrf):
            set_flash(request, "Invalid form token.", "error")
            return RedirectResponse(redirect_path, status_code=303)

        try:
            attendance_date = date.fromisoformat(attendance_date_text)
        except ValueError:
            set_flash(request, "Invalid attendance date.", "error")
            return RedirectResponse("/admin/attendance/today", status_code=303)

        reason = reason.strip()
        if len(reason) < 5:
            set_flash(
                request,
                "A correction reason of at least 5 characters is required.",
                "error",
            )
            return RedirectResponse(redirect_path, status_code=303)

        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", status_code=303)

            freelancer = database.get(Freelancer, freelancer_id)
            if freelancer is None:
                set_flash(request, "Freelancer was not found.", "error")
                return RedirectResponse("/admin/attendance/today", status_code=303)

            month_key = attendance_date.strftime("%Y-%m")
            if month_is_locked(database, month_key):
                set_flash(
                    request,
                    "This attendance month is locked. Unlock it before correcting records.",
                    "error",
                )
                return RedirectResponse(redirect_path, status_code=303)

            try:
                corrected_time_in = local_time_to_utc(
                    attendance_date,
                    time_in,
                    freelancer.timezone_name,
                )
                corrected_time_out = local_time_to_utc(
                    attendance_date,
                    time_out,
                    freelancer.timezone_name,
                )
            except ValueError as exc:
                set_flash(request, str(exc), "error")
                return RedirectResponse(redirect_path, status_code=303)

            if corrected_time_out is not None and corrected_time_in is None:
                set_flash(
                    request,
                    "Time Out cannot exist without a Time In.",
                    "error",
                )
                return RedirectResponse(redirect_path, status_code=303)

            if corrected_time_in is not None and corrected_time_out is not None and corrected_time_out <= corrected_time_in:
                corrected_time_out = local_time_to_utc(
                    attendance_date + timedelta(days=1), time_out, freelancer.timezone_name
                )

            record = get_daily_attendance(database, freelancer_id, attendance_date)
            if record is None and corrected_time_in is None:
                set_flash(
                    request,
                    "Enter at least a Time In when creating a manual attendance record.",
                    "error",
                )
                return RedirectResponse(redirect_path, status_code=303)

            original_time_in = record.time_in_utc if record else None
            original_time_out = record.time_out_utc if record else None

            if (
                normalized_utc(original_time_in) == normalized_utc(corrected_time_in)
                and normalized_utc(original_time_out) == normalized_utc(corrected_time_out)
            ):
                set_flash(request, "No attendance changes were entered.", "error")
                return RedirectResponse(redirect_path, status_code=303)

            if record is None:
                record = DailyAttendance(
                    freelancer_id=freelancer_id,
                    attendance_date=attendance_date,
                )
                database.add(record)
                database.flush()

            record.time_in_utc = corrected_time_in
            record.time_out_utc = corrected_time_out
            record.review_status = "CORRECTED"
            if corrected_time_in is None:
                record.status = "NO_RECORD"
            elif corrected_time_out is None:
                record.status = "MISSING_TIME_OUT"
            else:
                record.status = "COMPLETE"

            calculate_attendance_record(
                database,
                record,
                freelancer,
                source="ADMIN_CORRECTION",
                admin_id=admin.id,
            )
            if corrected_time_out is not None:
                repaired = repair_flagged_work_session(
                    database, freelancer=freelancer, attendance_date=attendance_date,
                    corrected_stop=corrected_time_out, notes=f"Administrator correction: {reason}",
                )
                if repaired is not None:
                    _, repaired_task = repaired
                    invalidate_task_review(database, freelancer.id, repaired_task.task_date.strftime("%Y-%m"))
            record.missed_time_out_flag = False
            record.missed_work_order_stop_flag = False
            record.overtime_unavailable = False
            record.exception_flagged_at = None

            correction = AttendanceCorrection(
                daily_attendance_id=record.id,
                freelancer_id=freelancer_id,
                attendance_date=attendance_date,
                original_time_in_utc=original_time_in,
                original_time_out_utc=original_time_out,
                corrected_time_in_utc=corrected_time_in,
                corrected_time_out_utc=corrected_time_out,
                reason=reason,
                corrected_by_admin_id=admin.id,
            )
            database.add(correction)
            database.flush()

            invalidate_dtr(database, freelancer_id, month_key)

            write_audit(
                database,
                actor_type="HR_ADMIN",
                actor_id=admin.id,
                action="CORRECT_ATTENDANCE",
                request=request,
                target_type="ATTENDANCE_CORRECTION",
                target_id=correction.id,
                details=(
                    f"Freelancer {freelancer.freelancer_code}; "
                    f"date {attendance_date.isoformat()}; reason: {reason}"
                ),
            )
            database.commit()

        set_flash(request, "Attendance correction saved.", "success")
        return RedirectResponse(redirect_path, status_code=303)


    @router.post("/admin/attendance/month/{month_key}/lock")
    def lock_attendance_month(
        month_key: str,
        request: Request,
        csrf: str = Form(...),
        reason: str = Form(...),
    ):
        redirect_path = f"/admin/attendance/monthly?month={month_key}"
        if not validate_csrf(request, csrf):
            set_flash(request, "Invalid form token.", "error")
            return RedirectResponse(redirect_path, status_code=303)

        month_range = parse_month_key(month_key)
        if month_range is None:
            set_flash(request, "Invalid month.", "error")
            return RedirectResponse("/admin/attendance/monthly", status_code=303)

        reason = reason.strip()
        if len(reason) < 5:
            set_flash(
                request,
                "A lock reason of at least 5 characters is required.",
                "error",
            )
            return RedirectResponse(redirect_path, status_code=303)

        if month_key >= current_month_key(DEFAULT_TIMEZONE):
            set_flash(
                request,
                "Only a completed past month can be locked.",
                "error",
            )
            return RedirectResponse(redirect_path, status_code=303)

        start_date, next_month = month_range

        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", status_code=303)

            incomplete_count = int(
                database.scalar(
                    select(func.count(DailyAttendance.id)).where(
                        DailyAttendance.attendance_date >= start_date,
                        DailyAttendance.attendance_date < next_month,
                        DailyAttendance.time_in_utc.is_not(None),
                        DailyAttendance.time_out_utc.is_(None),
                    )
                ) or 0
            )
            if incomplete_count:
                set_flash(
                    request,
                    f"Resolve {incomplete_count} missing Time Out record(s) before locking.",
                    "error",
                )
                return RedirectResponse(redirect_path, status_code=303)

            pending_ot_count = int(
                database.scalar(
                    select(func.count(OvertimeClaim.id)).where(
                        OvertimeClaim.attendance_date >= start_date,
                        OvertimeClaim.attendance_date < next_month,
                        OvertimeClaim.status == "PENDING",
                    )
                ) or 0
            )
            if pending_ot_count:
                set_flash(
                    request,
                    f"Review {pending_ot_count} pending overtime claim(s) before locking.",
                    "error",
                )
                return RedirectResponse(redirect_path, status_code=303)

            pending_leave_count = int(
                database.scalar(
                    select(func.count(LeaveRequest.id)).where(
                        LeaveRequest.leave_date >= start_date,
                        LeaveRequest.leave_date < next_month,
                        LeaveRequest.status == "PENDING",
                    )
                ) or 0
            )
            if pending_leave_count:
                set_flash(
                    request,
                    f"Review {pending_leave_count} pending leave request(s) before locking.",
                    "error",
                )
                return RedirectResponse(redirect_path, status_code=303)

            policy = get_policy(database)
            if policy.require_daily_task_for_dtr:
                completed_records = list(
                    database.scalars(
                        select(DailyAttendance).where(
                            DailyAttendance.attendance_date >= start_date,
                            DailyAttendance.attendance_date < next_month,
                            DailyAttendance.time_in_utc.is_not(None),
                            DailyAttendance.time_out_utc.is_not(None),
                        )
                    ).all()
                )
                missing_task_count = 0
                involved_freelancer_ids: set[int] = set()
                for attendance_record in completed_records:
                    involved_freelancer_ids.add(attendance_record.freelancer_id)
                    if task_minutes_for_date(
                        database,
                        attendance_record.freelancer_id,
                        attendance_record.attendance_date,
                    ) <= 0:
                        missing_task_count += 1

                task_freelancer_ids = set(
                    database.scalars(
                        select(DailyTask.freelancer_id)
                        .where(
                            DailyTask.task_date >= start_date,
                            DailyTask.task_date < next_month,
                        )
                        .distinct()
                    ).all()
                )
                involved_freelancer_ids.update(task_freelancer_ids)

                if missing_task_count:
                    set_flash(
                        request,
                        f"Complete {missing_task_count} missing daily-task report(s) before locking.",
                        "error",
                    )
                    return RedirectResponse(redirect_path, status_code=303)

                unreviewed_task_months = 0
                for involved_freelancer_id in involved_freelancer_ids:
                    task_review = get_task_review(
                        database,
                        involved_freelancer_id,
                        month_key,
                    )
                    if task_review is None or task_review.status != "REVIEWED":
                        unreviewed_task_months += 1

                if unreviewed_task_months:
                    set_flash(
                        request,
                        f"Review {unreviewed_task_months} freelancer monthly task report(s) before locking.",
                        "error",
                    )
                    return RedirectResponse(redirect_path, status_code=303)

            month_lock = get_month_lock(database, month_key)
            if month_lock is None:
                month_lock = AttendanceMonthLock(
                    month_key=month_key,
                    is_locked=True,
                    locked_by_admin_id=admin.id,
                    locked_at=utc_now(),
                    lock_reason=reason,
                )
                database.add(month_lock)
            elif month_lock.is_locked:
                set_flash(request, "This month is already locked.", "error")
                return RedirectResponse(redirect_path, status_code=303)
            else:
                month_lock.is_locked = True
                month_lock.locked_by_admin_id = admin.id
                month_lock.locked_at = utc_now()
                month_lock.lock_reason = reason
                month_lock.unlocked_by_admin_id = None
                month_lock.unlocked_at = None
                month_lock.unlock_reason = None

            database.execute(
                DailyAttendance.__table__.update()
                .where(
                    DailyAttendance.attendance_date >= start_date,
                    DailyAttendance.attendance_date < next_month,
                )
                .values(is_locked=True)
            )

            write_audit(
                database,
                actor_type="HR_ADMIN",
                actor_id=admin.id,
                action="LOCK_ATTENDANCE_MONTH",
                request=request,
                target_type="ATTENDANCE_MONTH",
                details=f"Month {month_key}; reason: {reason}",
            )
            database.commit()

        set_flash(request, f"Attendance month {month_key} locked.", "success")
        return RedirectResponse(redirect_path, status_code=303)


    @router.post("/admin/attendance/month/{month_key}/unlock")
    def unlock_attendance_month(
        month_key: str,
        request: Request,
        csrf: str = Form(...),
        reason: str = Form(...),
    ):
        redirect_path = f"/admin/attendance/monthly?month={month_key}"
        if not validate_csrf(request, csrf):
            set_flash(request, "Invalid form token.", "error")
            return RedirectResponse(redirect_path, status_code=303)

        if parse_month_key(month_key) is None:
            set_flash(request, "Invalid month.", "error")
            return RedirectResponse("/admin/attendance/monthly", status_code=303)

        reason = reason.strip()
        if len(reason) < 5:
            set_flash(
                request,
                "An unlock reason of at least 5 characters is required.",
                "error",
            )
            return RedirectResponse(redirect_path, status_code=303)

        start_date, next_month = parse_month_key(month_key)  # type: ignore[misc]

        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", status_code=303)

            finalized_dtr_count = int(
                database.scalar(
                    select(func.count(MonthlyDTR.id)).where(
                        MonthlyDTR.month_key == month_key,
                        MonthlyDTR.status == "FINALIZED",
                    )
                ) or 0
            )
            if finalized_dtr_count:
                set_flash(
                    request,
                    "This month contains finalized Finance DTRs and cannot be unlocked. "
                    "A controlled DTR-reopening workflow is required.",
                    "error",
                )
                return RedirectResponse(redirect_path, status_code=303)

            month_lock = get_month_lock(database, month_key)
            if month_lock is None or not month_lock.is_locked:
                set_flash(request, "This month is not locked.", "error")
                return RedirectResponse(redirect_path, status_code=303)

            month_lock.is_locked = False
            month_lock.unlocked_by_admin_id = admin.id
            month_lock.unlocked_at = utc_now()
            month_lock.unlock_reason = reason

            database.execute(
                DailyAttendance.__table__.update()
                .where(
                    DailyAttendance.attendance_date >= start_date,
                    DailyAttendance.attendance_date < next_month,
                )
                .values(is_locked=False)
            )

            write_audit(
                database,
                actor_type="HR_ADMIN",
                actor_id=admin.id,
                action="UNLOCK_ATTENDANCE_MONTH",
                request=request,
                target_type="ATTENDANCE_MONTH",
                details=f"Month {month_key}; reason: {reason}",
            )
            database.commit()

        set_flash(request, f"Attendance month {month_key} unlocked.", "success")
        return RedirectResponse(redirect_path, status_code=303)



    @router.post("/admin/attendance/month/{month_key}/recalculate")
    def recalculate_attendance_month(
        month_key: str,
        request: Request,
        csrf: str = Form(...),
        reason: str = Form(...),
    ):
        redirect_path = f"/admin/attendance/monthly?month={month_key}"
        if not validate_csrf(request, csrf):
            set_flash(request, "Invalid form token.", "error")
            return RedirectResponse(redirect_path, status_code=303)

        month_range = parse_month_key(month_key)
        if month_range is None:
            set_flash(request, "Invalid month.", "error")
            return RedirectResponse("/admin/attendance/monthly", status_code=303)

        reason = reason.strip()
        if len(reason) < 5:
            set_flash(
                request,
                "A recalculation reason of at least 5 characters is required.",
                "error",
            )
            return RedirectResponse(redirect_path, status_code=303)

        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", status_code=303)
            if month_is_locked(database, month_key):
                set_flash(
                    request,
                    "This month is locked. Unlock it before recalculating.",
                    "error",
                )
                return RedirectResponse(redirect_path, status_code=303)

            start_date, next_month = month_range
            count = recalculate_month(
                database,
                start_date,
                next_month,
                admin_id=admin.id,
            )
            database.execute(
                delete(MonthlyDTR).where(
                    MonthlyDTR.month_key == month_key,
                    MonthlyDTR.status != "FINALIZED",
                )
            )
            write_audit(
                database,
                actor_type="HR_ADMIN",
                actor_id=admin.id,
                action="RECALCULATE_ATTENDANCE_MONTH",
                request=request,
                target_type="ATTENDANCE_MONTH",
                details=f"Month {month_key}; records {count}; reason: {reason}",
            )
            database.commit()

        set_flash(
            request,
            f"Recalculated {count} attendance record(s) for {month_key}.",
            "success",
        )
        return RedirectResponse(redirect_path, status_code=303)


    @router.get("/admin/dtr", response_class=HTMLResponse)
    def dtr_dashboard(
        request: Request,
        month: str = "",
    ):
        selected_month = month if parse_month_key(month) else current_month_key()
        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", status_code=303)

            freelancers = [
                row for row in hr_freelancer_choices(database)
                if row.is_active and not str(row.freelancer_code or "").upper().startswith("TS-")
            ]
            freelancer_map = {row.id: row for row in freelancers}
            dtrs = list(
                database.scalars(
                    select(MonthlyDTR)
                    .where(MonthlyDTR.month_key == selected_month)
                    .order_by(MonthlyDTR.freelancer_id)
                ).all()
            )
            rows = [
                dtr_summary_row(dtr, freelancer_map[dtr.freelancer_id])
                for dtr in dtrs
                if dtr.freelancer_id in freelancer_map
            ]
            generated_ids = {dtr.freelancer_id for dtr in dtrs}
            missing_freelancers = [
                row for row in freelancers if row.id not in generated_ids
            ]

            return templates.TemplateResponse(
                request=request,
                name="admin_dtr_dashboard.html",
                context=template_context(
                    request,
                    admin=admin,
                    selected_month=selected_month,
                    rows=rows,
                    freelancers=freelancers,
                    missing_freelancers=missing_freelancers,
                    month_locked=month_is_locked(database, selected_month),
                ),
            )


    @router.post("/admin/dtr/generate")
    def generate_dtr_route(
        request: Request,
        csrf: str = Form(...),
        month_key: str = Form(...),
        freelancer_id: int = Form(...),
        reason: str = Form(...),
    ):
        redirect_path = f"/admin/dtr?month={month_key}"
        if not validate_csrf(request, csrf):
            set_flash(request, "Invalid form token.", "error")
            return RedirectResponse(redirect_path, status_code=303)
        if parse_month_key(month_key) is None:
            set_flash(request, "Invalid DTR month.", "error")
            return RedirectResponse("/admin/dtr", status_code=303)

        reason = reason.strip()
        if len(reason) < 5:
            set_flash(request, "A generation reason of at least 5 characters is required.", "error")
            return RedirectResponse(redirect_path, status_code=303)

        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", status_code=303)
            if not has_permission(normalize_role(admin.role), Permission.DTR_GENERATE):
                set_flash(request, "Permission required.", "error")
                return RedirectResponse("/access-denied", status_code=303)

            if freelancer_id == 0:
                freelancers = [
                    row for row in hr_freelancer_choices(database)
                    if row.is_active and not str(row.freelancer_code or "").upper().startswith("TS-")
                ]
            else:
                freelancer = database.get(Freelancer, freelancer_id)
                freelancers = [
                    freelancer
                ] if (freelancer is not None and not str(freelancer.freelancer_code or "").upper().startswith("TS-")) else []

            generated = 0
            skipped = 0
            for freelancer in freelancers:
                existing = get_monthly_dtr(database, freelancer.id, month_key)
                if existing is not None and existing.status == "FINALIZED":
                    skipped += 1
                    continue
                generate_monthly_dtr(
                    database,
                    freelancer=freelancer,
                    month_key=month_key,
                    admin_id=admin.id,
                    reason=reason,
                )
                generated += 1

            write_audit(
                database,
                actor_type="HR_ADMIN",
                actor_id=admin.id,
                action="GENERATE_MONTHLY_DTR",
                request=request,
                target_type="MONTHLY_DTR",
                details=f"Month {month_key}; generated {generated}; skipped {skipped}; reason: {reason}",
            )
            database.commit()

        message = f"Generated or refreshed {generated} DTR record(s)."
        if skipped:
            message += f" {skipped} finalized DTR(s) were skipped."
        set_flash(request, message, "success")
        return RedirectResponse(redirect_path, status_code=303)


    @router.get("/admin/dtr/{dtr_id}", response_class=HTMLResponse)
    def dtr_detail(dtr_id: int, request: Request):
        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", status_code=303)
            dtr = database.get(MonthlyDTR, dtr_id)
            if dtr is None:
                set_flash(request, "DTR not found.", "error")
                return RedirectResponse("/admin/dtr", status_code=303)
            freelancer = database.get(Freelancer, dtr.freelancer_id)
            if freelancer is None:
                set_flash(request, "Freelancer not found.", "error")
                return RedirectResponse("/admin/dtr", status_code=303)
            if str(freelancer.freelancer_code or "").upper().startswith("TS-"):
                set_flash(request, "Administrator and Supervisor review/task identities do not require a Daily Time Record (DTR).", "info")
                return RedirectResponse(f"/admin/dtr?month={dtr.month_key}", status_code=303)
            lines = list(
                database.scalars(
                    select(DTRDailyLine)
                    .where(DTRDailyLine.monthly_dtr_id == dtr.id)
                    .order_by(DTRDailyLine.attendance_date)
                ).all()
            )
            names = admin_name_map(database)
            review_allowed, review_message = dtr_can_be_reviewed(dtr)
            task_hourly_mode = is_task_hourly_member(freelancer)
            task_hourly_ledger = (
                task_hourly_month_ledger(database, freelancer=freelancer, month_key=dtr.month_key)
                if task_hourly_mode else None
            )
            range_start, range_end = parse_month_key(dtr.month_key)
            actual_leave_history = list(
                database.scalars(
                    select(LeaveRecord)
                    .where(
                        LeaveRecord.freelancer_id == freelancer.id,
                        LeaveRecord.leave_date >= range_start,
                        LeaveRecord.leave_date < range_end,
                        LeaveRecord.status == "APPROVED",
                    )
                    .order_by(LeaveRecord.leave_date, LeaveRecord.id)
                ).all()
            )
            month_overtime_claims = list(
                database.scalars(
                    select(OvertimeClaim)
                    .where(
                        OvertimeClaim.freelancer_id == freelancer.id,
                        OvertimeClaim.attendance_date >= range_start,
                        OvertimeClaim.attendance_date < range_end,
                    )
                    .order_by(OvertimeClaim.attendance_date, OvertimeClaim.id)
                ).all()
            )
            actual_overtime_history = [
                claim for claim in month_overtime_claims
                if claim.final_submitted_at is not None
                or str(claim.status or "").upper() in {"APPROVED", "REJECTED"}
            ]
            return templates.TemplateResponse(
                request=request,
                name=("admin_dtr_task_hourly.html" if task_hourly_mode else "admin_dtr_detail.html"),
                context=template_context(
                    request,
                    admin=admin,
                    dtr=dtr,
                    freelancer=freelancer,
                    lines=[dtr_line_row(line, dtr.timezone_name) for line in lines],
                    generated_by=names.get(dtr.generated_by_admin_id, "HR Administrator"),
                    reviewed_by=names.get(dtr.reviewed_by_admin_id) if dtr.reviewed_by_admin_id else None,
                    finalized_by=names.get(dtr.finalized_by_admin_id) if dtr.finalized_by_admin_id else None,
                    review_allowed=review_allowed,
                    review_message=review_message,
                    compact=compact_dtr_metrics(database, dtr),
                    month_locked=month_is_locked(database, dtr.month_key),
                    task_hourly_mode=task_hourly_mode,
                    task_hourly_ledger=task_hourly_ledger,
                    actual_leave_history=actual_leave_history,
                    actual_overtime_history=actual_overtime_history,
                    format_local_datetime=format_local_datetime,
                ),
            )


    @router.get("/admin/dtr/{dtr_id}/details", response_class=HTMLResponse)
    def dtr_details(dtr_id: int, request: Request):
        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", status_code=303)
            dtr = database.get(MonthlyDTR, dtr_id)
            if dtr is None:
                set_flash(request, "DTR not found.", "error")
                return RedirectResponse("/admin/dtr", status_code=303)
            freelancer = database.get(Freelancer, dtr.freelancer_id)
            if freelancer is None:
                set_flash(request, "Freelancer not found.", "error")
                return RedirectResponse("/admin/dtr", status_code=303)
            if str(freelancer.freelancer_code or "").upper().startswith("TS-"):
                set_flash(request, "Administrator and Supervisor review/task identities do not require a Daily Time Record (DTR).", "info")
                return RedirectResponse(f"/admin/dtr?month={dtr.month_key}", status_code=303)
            attendance = list(database.scalars(
                select(DTRDailyLine).where(DTRDailyLine.monthly_dtr_id == dtr.id).order_by(DTRDailyLine.attendance_date)
            ).all())
            tasks = list(database.scalars(
                select(DTRTaskLine).where(DTRTaskLine.monthly_dtr_id == dtr.id).order_by(DTRTaskLine.task_date, DTRTaskLine.id)
            ).all())
            overtime = [line for line in attendance if int(line.potential_overtime_minutes or 0) or int(line.approved_overtime_minutes or 0)]
            comp_lines = list(database.scalars(
                select(DTRCompLine).where(DTRCompLine.monthly_dtr_id == dtr.id).order_by(DTRCompLine.transaction_date, DTRCompLine.id)
            ).all())
            leave_lines = list(database.scalars(
                select(DTRLeaveLine).where(DTRLeaveLine.monthly_dtr_id == dtr.id).order_by(DTRLeaveLine.leave_date, DTRLeaveLine.id)
            ).all())
            task_hourly_mode = is_task_hourly_member(freelancer)
            task_hourly_ledger = (
                task_hourly_month_ledger(database, freelancer=freelancer, month_key=dtr.month_key)
                if task_hourly_mode else None
            )
            return templates.TemplateResponse(
                request=request,
                name=("admin_dtr_task_hourly.html" if task_hourly_mode else "admin_dtr_details.html"),
                context=template_context(
                    request, admin=admin, dtr=dtr, freelancer=freelancer,
                    lines=[dtr_line_row(line, dtr.timezone_name) for line in attendance],
                    overtime=[dtr_line_row(line, dtr.timezone_name) for line in overtime],
                    tasks=tasks, comp_lines=comp_lines, leave_lines=leave_lines,
                    compact=compact_dtr_metrics(database, dtr),
                    task_hourly_mode=task_hourly_mode,
                    task_hourly_ledger=task_hourly_ledger,
                    generated_by="HR Administrator",
                    reviewed_by=None,
                    finalized_by=None,
                    review_allowed=True,
                    review_message="",
                    month_locked=month_is_locked(database, dtr.month_key),
                ),
            )


    @router.post("/admin/dtr/{dtr_id}/review")
    def review_dtr(
        dtr_id: int,
        request: Request,
        csrf: str = Form(...),
        reason: str = Form(...),
    ):
        redirect_path = f"/admin/dtr/{dtr_id}"
        if not validate_csrf(request, csrf):
            set_flash(request, "Invalid form token.", "error")
            return RedirectResponse(redirect_path, status_code=303)
        reason = reason.strip()
        if len(reason) < 5:
            set_flash(request, "A review reason of at least 5 characters is required.", "error")
            return RedirectResponse(redirect_path, status_code=303)

        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", status_code=303)
            dtr = database.get(MonthlyDTR, dtr_id)
            if dtr is None:
                set_flash(request, "DTR not found.", "error")
                return RedirectResponse("/admin/dtr", status_code=303)
            if not month_is_locked(database, dtr.month_key):
                set_flash(request, "Lock the attendance month before reviewing the DTR.", "error")
                return RedirectResponse(redirect_path, status_code=303)
            allowed, message = dtr_can_be_reviewed(dtr)
            if not allowed:
                set_flash(request, message, "error")
                return RedirectResponse(redirect_path, status_code=303)

            dtr.status = "REVIEWED"
            dtr.reviewed_by_admin_id = admin.id
            dtr.reviewed_at = utc_now()
            dtr.review_reason = reason
            write_audit(
                database,
                actor_type="HR_ADMIN",
                actor_id=admin.id,
                action="REVIEW_MONTHLY_DTR",
                request=request,
                target_type="MONTHLY_DTR",
                target_id=dtr.id,
                details=f"Month {dtr.month_key}; reason: {reason}",
            )
            database.commit()

        set_flash(request, "DTR marked as reviewed.", "success")
        return RedirectResponse(redirect_path, status_code=303)


    @router.post("/admin/dtr/{dtr_id}/finalize")
    def finalize_dtr(
        dtr_id: int,
        request: Request,
        csrf: str = Form(...),
        reason: str = Form(...),
    ):
        redirect_path = f"/admin/dtr/{dtr_id}"
        if not validate_csrf(request, csrf):
            set_flash(request, "Invalid form token.", "error")
            return RedirectResponse(redirect_path, status_code=303)
        reason = reason.strip()
        if len(reason) < 5:
            set_flash(request, "A finalization reason of at least 5 characters is required.", "error")
            return RedirectResponse(redirect_path, status_code=303)

        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", status_code=303)
            dtr = database.get(MonthlyDTR, dtr_id)
            if dtr is None:
                set_flash(request, "DTR not found.", "error")
                return RedirectResponse("/admin/dtr", status_code=303)
            if dtr.status != "REVIEWED":
                set_flash(request, "Review the DTR before finalizing it.", "error")
                return RedirectResponse(redirect_path, status_code=303)
            if not month_is_locked(database, dtr.month_key):
                set_flash(request, "The attendance month must remain locked.", "error")
                return RedirectResponse(redirect_path, status_code=303)

            dtr.status = "FINALIZED"
            dtr.finalized_by_admin_id = admin.id
            dtr.finalized_at = utc_now()
            dtr.finalization_reason = reason
            write_audit(
                database,
                actor_type="HR_ADMIN",
                actor_id=admin.id,
                action="FINALIZE_MONTHLY_DTR",
                request=request,
                target_type="MONTHLY_DTR",
                target_id=dtr.id,
                details=f"Month {dtr.month_key}; reason: {reason}",
            )
            database.commit()

        set_flash(request, "DTR finalized. It can no longer be regenerated.", "success")
        return RedirectResponse(redirect_path, status_code=303)


    @router.get("/admin/dtr/{dtr_id}/export.xlsx")
    def export_dtr_xlsx(dtr_id: int, request: Request):
        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", status_code=303)
            dtr = database.get(MonthlyDTR, dtr_id)
            if dtr is None:
                set_flash(request, "DTR not found.", "error")
                return RedirectResponse("/admin/dtr", status_code=303)
            freelancer = database.get(Freelancer, dtr.freelancer_id)
            if freelancer is None:
                set_flash(request, "Freelancer not found.", "error")
                return RedirectResponse("/admin/dtr", status_code=303)
            if str(freelancer.freelancer_code or "").upper().startswith("TS-"):
                set_flash(request, "Administrator and Supervisor review/task identities do not require a Daily Time Record (DTR).", "info")
                return RedirectResponse(f"/admin/dtr?month={dtr.month_key}", status_code=303)
            lines = list(
                database.scalars(
                    select(DTRDailyLine)
                    .where(DTRDailyLine.monthly_dtr_id == dtr.id)
                    .order_by(DTRDailyLine.attendance_date)
                ).all()
            )
            names = admin_name_map(database)
            workbook_bytes = build_dtr_workbook(
                dtr=dtr,
                freelancer=freelancer,
                lines=lines,
                generated_by=names.get(dtr.generated_by_admin_id, "HR Administrator"),
                reviewed_by=names.get(dtr.reviewed_by_admin_id) if dtr.reviewed_by_admin_id else None,
                finalized_by=names.get(dtr.finalized_by_admin_id) if dtr.finalized_by_admin_id else None,
                zone_getter=freelancer_zone,
            )
            write_audit(
                database,
                actor_type="HR_ADMIN",
                actor_id=admin.id,
                action="EXPORT_MONTHLY_DTR_XLSX",
                request=request,
                target_type="MONTHLY_DTR",
                target_id=dtr.id,
                details=f"Month {dtr.month_key}; freelancer {freelancer.freelancer_code}",
            )
            database.commit()

        filename = f"DTR_{freelancer.freelancer_code}_{dtr.month_key}.xlsx"
        return StreamingResponse(
            iter([workbook_bytes]),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )












    @router.get("/attendance", response_class=HTMLResponse)
    def attendance_page(request: Request):
        with SessionLocal() as database:
            account = get_current_freelancer_account(
                request,
                database,
            )
            if account is None:
                return RedirectResponse(
                    "/login",
                    status_code=303,
                )

            if account.must_change_password:
                return RedirectResponse(
                    "/change-password",
                    status_code=303,
                )

            official_utc = utc_now()
            timezone_name = account.freelancer.timezone_name
            attendance_date = current_attendance_date(
                timezone_name,
                official_utc,
            )
            record = get_daily_attendance(
                database,
                account.freelancer_id,
                attendance_date,
            )
            view = build_attendance_view(
                record,
                timezone_name,
            )
            local_now = official_utc.astimezone(
                freelancer_zone(timezone_name)
            )
            assigned_tasks = current_freelancer_portal_tasks(
                database,
                freelancer_id=account.freelancer_id,
                limit=3,
            )
            assigned_task_rows = [
                {
                    "id": row.id,
                    "project_name": row.project_name,
                    "project_engineer": row.project_engineer or "",
                    "deadline": (
                        row.deadline.isoformat()
                        if row.deadline
                        else "No deadline"
                    ),
                    "status": row.project_status or "—",
                    "progress": row.progress,
                    "task_description": (
                        row.task_description
                        or "No task description provided."
                    ),
                }
                for row in assigned_tasks
            ]
            summary_month = attendance_date.strftime("%Y-%m")
            task_hourly_mode = is_task_hourly_member(account.freelancer)
            task_hourly_ledger = (
                task_hourly_month_ledger(
                    database, freelancer=account.freelancer, month_key=summary_month
                )
                if task_hourly_mode else None
            )
            monthly_dtr = get_monthly_dtr(
                database,
                account.freelancer_id,
                summary_month,
            )
            monthly_summary = (
                compact_dtr_metrics(database, monthly_dtr)
                if monthly_dtr is not None
                else None
            )

            return templates.TemplateResponse(
                request=request,
                name="attendance.html",
                context=template_context(
                    request,
                    account=account,
                    attendance_date=attendance_date.strftime(
                        "%A, %B %d, %Y"
                    ),
                    server_time=local_now.strftime(
                        "%I:%M:%S %p"
                    ).lstrip("0"),
                    attendance=view,
                    calculation=calculation_display(
                        get_calculation(database, record.id) if record else None
                    ),
                    assigned_tasks=assigned_task_rows,
                    monthly_summary=monthly_summary,
                    monthly_summary_month=summary_month,
                    monthly_dtr_status=(monthly_dtr.status if monthly_dtr else None),
                    task_hourly_mode=task_hourly_mode,
                    task_hourly_ledger=task_hourly_ledger,
                    correction_requests=([] if task_hourly_mode else list(database.scalars(select(AttendanceCorrectionRequest).where(AttendanceCorrectionRequest.freelancer_id == account.freelancer_id).order_by(AttendanceCorrectionRequest.requested_at.desc()).limit(20)).all())),
                ),
            )


    @router.post("/attendance/time-in")
    def time_in(
        request: Request,
        csrf: str = Form(...),
    ):
        if not validate_csrf(request, csrf):
            set_flash(
                request,
                "Invalid form token. Please try again.",
                "error",
            )
            return RedirectResponse(
                "/attendance",
                status_code=303,
            )

        with SessionLocal() as database:
            account = get_current_freelancer_account(
                request,
                database,
            )
            if account is None:
                return RedirectResponse(
                    "/login",
                    status_code=303,
                )

            if account.must_change_password:
                return RedirectResponse(
                    "/change-password",
                    status_code=303,
                )

            if is_task_hourly_member(account.freelancer):
                set_flash(
                    request,
                    "This member uses task-hourly work records and does not use Time In or Time Out.",
                    "info",
                )
                return RedirectResponse("/attendance", status_code=303)

            official_utc = utc_now()
            timezone_name = account.freelancer.timezone_name
            attendance_date = current_attendance_date(
                timezone_name,
                official_utc,
            )
            if month_is_locked(database, attendance_date.strftime("%Y-%m")):
                set_flash(
                    request,
                    "This attendance month is locked. Contact HR.",
                    "error",
                )
                return RedirectResponse("/attendance", status_code=303)

            record = get_daily_attendance(
                database,
                account.freelancer_id,
                attendance_date,
            )

            if record is not None and record.time_in_utc is not None:
                set_flash(
                    request,
                    "Time In has already been recorded for today.",
                    "error",
                )
                return RedirectResponse(
                    "/attendance",
                    status_code=303,
                )

            if record is None:
                record = DailyAttendance(
                    freelancer_id=account.freelancer_id,
                    attendance_date=attendance_date,
                    time_in_utc=official_utc,
                    status="PRESENT",
                )
                database.add(record)
            else:
                record.time_in_utc = official_utc
                record.status = "PRESENT"

            database.add(
                AttendanceEvent(
                    freelancer_id=account.freelancer_id,
                    account_id=account.id,
                    event_type="TIME_IN",
                    recorded_at_utc=official_utc,
                    attendance_date=attendance_date,
                    timezone_name=timezone_name,
                    ip_address=request_ip(request),
                    user_agent=request.headers.get("user-agent"),
                    source="FREELANCER_PORTAL",
                )
            )

            database.flush()

            calculate_attendance_record(
                database,
                record,
                account.freelancer,
                source="FREELANCER_TIME_IN",
            )
            invalidate_dtr(
                database,
                account.freelancer_id,
                attendance_date.strftime("%Y-%m"),
            )

            write_audit(
                database,
                actor_type="FREELANCER",
                actor_id=account.freelancer_id,
                action="TIME_IN",
                request=request,
                target_type="DAILY_ATTENDANCE",
                target_id=record.id,
                details=f"Official UTC timestamp: {official_utc.isoformat()}",
            )

            try:
                database.commit()
            except IntegrityError:
                database.rollback()
                set_flash(
                    request,
                    "Time In has already been recorded for today.",
                    "error",
                )
                return RedirectResponse(
                    "/attendance",
                    status_code=303,
                )

            confirmed_time = format_local_datetime(
                official_utc,
                timezone_name,
            )

        set_flash(
            request,
            f"Time In recorded at {confirmed_time}.",
            "success",
        )
        return RedirectResponse(
            "/attendance",
            status_code=303,
        )


    @router.post("/attendance/time-out")
    def time_out(
        request: Request,
        csrf: str = Form(...),
    ):
        if not validate_csrf(request, csrf):
            set_flash(
                request,
                "Invalid form token. Please try again.",
                "error",
            )
            return RedirectResponse(
                "/attendance",
                status_code=303,
            )

        with SessionLocal() as database:
            account = get_current_freelancer_account(
                request,
                database,
            )
            if account is None:
                return RedirectResponse(
                    "/login",
                    status_code=303,
                )

            if account.must_change_password:
                return RedirectResponse(
                    "/change-password",
                    status_code=303,
                )

            if is_task_hourly_member(account.freelancer):
                set_flash(
                    request,
                    "This member uses task-hourly work records and does not use Time In or Time Out.",
                    "info",
                )
                return RedirectResponse("/attendance", status_code=303)

            official_utc = utc_now()
            timezone_name = account.freelancer.timezone_name
            attendance_date = current_attendance_date(
                timezone_name,
                official_utc,
            )
            if month_is_locked(database, attendance_date.strftime("%Y-%m")):
                set_flash(
                    request,
                    "This attendance month is locked. Contact HR.",
                    "error",
                )
                return RedirectResponse("/attendance", status_code=303)

            record = get_daily_attendance(
                database,
                account.freelancer_id,
                attendance_date,
            )
            local_now = official_utc.astimezone(freelancer_zone(timezone_name))
            if (record is None or record.time_in_utc is None) and local_now.hour < 6:
                previous_date = attendance_date - timedelta(days=1)
                previous_record = get_daily_attendance(database, account.freelancer_id, previous_date)
                if previous_record is not None and previous_record.time_in_utc is not None and previous_record.time_out_utc is None:
                    record = previous_record
                    attendance_date = previous_date

            if record is None or record.time_in_utc is None:
                set_flash(
                    request,
                    "Time In must be recorded before Time Out.",
                    "error",
                )
                return RedirectResponse(
                    "/attendance",
                    status_code=303,
                )

            if record.time_out_utc is not None:
                set_flash(
                    request,
                    "Time Out has already been recorded for today.",
                    "error",
                )
                return RedirectResponse(
                    "/attendance",
                    status_code=303,
                )

            normalized_time_in = normalized_utc(record.time_in_utc)
            if (
                normalized_time_in is not None
                and official_utc <= normalized_time_in
            ):
                set_flash(
                    request,
                    "Time Out must be later than Time In.",
                    "error",
                )
                return RedirectResponse(
                    "/attendance",
                    status_code=303,
                )

            record.time_out_utc = official_utc
            record.status = "COMPLETE"

            # A trusted attendance Time Out also closes any active Work Order.
            # This is an Administrator control and is intentionally not exposed
            # as a freelancer-facing fallback option. Attendance must still save
            # even if the Work Order safeguard encounters an unexpected problem.
            auto_closed_work_order = None
            try:
                with database.begin_nested():
                    auto_closed_work_order = auto_stop_active_work_session(
                        database,
                        freelancer=account.freelancer,
                        stopped_at=official_utc,
                    )
                    if auto_closed_work_order is not None:
                        _, fallback_daily_task = auto_closed_work_order
                        invalidate_task_review(
                            database,
                            account.freelancer_id,
                            fallback_daily_task.task_date.strftime("%Y-%m"),
                        )
            except Exception:
                auto_closed_work_order = None

            database.add(
                AttendanceEvent(
                    freelancer_id=account.freelancer_id,
                    account_id=account.id,
                    event_type="TIME_OUT",
                    recorded_at_utc=official_utc,
                    attendance_date=attendance_date,
                    timezone_name=timezone_name,
                    ip_address=request_ip(request),
                    user_agent=request.headers.get("user-agent"),
                    source="FREELANCER_PORTAL",
                )
            )

            calculate_attendance_record(
                database,
                record,
                account.freelancer,
                source="FREELANCER_TIME_OUT",
            )
            invalidate_dtr(
                database,
                account.freelancer_id,
                attendance_date.strftime("%Y-%m"),
            )

            write_audit(
                database,
                actor_type="FREELANCER",
                actor_id=account.freelancer_id,
                action="TIME_OUT",
                request=request,
                target_type="DAILY_ATTENDANCE",
                target_id=record.id,
                details=f"Official UTC timestamp: {official_utc.isoformat()}",
            )
            if auto_closed_work_order is not None:
                fallback_session, _ = auto_closed_work_order
                write_audit(
                    database,
                    actor_type="SYSTEM",
                    actor_id=None,
                    action="AUTO_STOP_WORK_ORDER_AT_TIME_OUT",
                    request=request,
                    target_type="TASK_WORK_SESSION",
                    target_id=fallback_session.id,
                    details=(
                        f"Attendance Time Out closed {fallback_session.project_name} / "
                        f"{fallback_session.task_title}; recorded "
                        f"{fallback_session.duration_minutes} minutes."
                    ),
                )

            try:
                database.commit()
            except IntegrityError:
                database.rollback()
                set_flash(
                    request,
                    "Time Out has already been recorded for today.",
                    "error",
                )
                return RedirectResponse(
                    "/attendance",
                    status_code=303,
                )

            confirmed_time = format_local_datetime(
                official_utc,
                timezone_name,
            )

        set_flash(
            request,
            f"Time Out recorded at {confirmed_time}.",
            "success",
        )
        return RedirectResponse(
            "/attendance",
            status_code=303,
        )


    @router.get("/attendance/history", response_class=HTMLResponse)
    def attendance_history(request: Request):
        """Personal attendance archive and generated DTR history.

        The freelancer can browse recent records, a selected month, or the full
        attendance history without exposing another member's data. Generated
        MonthlyDTR records are listed on the same page for permanent self-service
        access.
        """
        with SessionLocal() as database:
            account = get_current_freelancer_account(
                request,
                database,
            )
            if account is None:
                return RedirectResponse(
                    "/login",
                    status_code=303,
                )

            if account.must_change_password:
                return RedirectResponse(
                    "/change-password",
                    status_code=303,
                )

            freelancer = account.freelancer
            timezone_name = freelancer.timezone_name
            period = (request.query_params.get("period") or "recent").strip().lower()
            selected_month = (request.query_params.get("month") or "").strip()

            if selected_month:
                bounds = parse_month_key(selected_month)
                if bounds is None:
                    set_flash(request, "Invalid attendance month.", "error")
                    return RedirectResponse("/attendance/history", status_code=303)
                range_start, range_end = bounds
                period = "month"
            elif period == "this_month":
                selected_month = current_month_key(timezone_name)
                range_start, range_end = parse_month_key(selected_month)
                period = "month"
            elif period == "last_month":
                today = current_attendance_date(timezone_name)
                previous_month_last_day = today.replace(day=1) - timedelta(days=1)
                selected_month = previous_month_last_day.strftime("%Y-%m")
                range_start, range_end = parse_month_key(selected_month)
                period = "month"
            elif period == "all":
                range_start = range_end = None
            else:
                period = "recent"
                range_start = range_end = None

            attendance_query = (
                select(DailyAttendance)
                .where(DailyAttendance.freelancer_id == account.freelancer_id)
                .order_by(DailyAttendance.attendance_date.desc())
            )
            if period == "month" and range_start is not None and range_end is not None:
                attendance_query = attendance_query.where(
                    DailyAttendance.attendance_date >= range_start,
                    DailyAttendance.attendance_date < range_end,
                )
            elif period == "recent":
                attendance_query = attendance_query.limit(31)

            records = list(database.scalars(attendance_query).all())
            record_ids = [record.id for record in records]
            calculation_map: dict[int, AttendanceCalculation] = {}
            if record_ids:
                calculation_map = {
                    calculation.daily_attendance_id: calculation
                    for calculation in database.scalars(
                        select(AttendanceCalculation).where(
                            AttendanceCalculation.daily_attendance_id.in_(record_ids)
                        )
                    ).all()
                }

            all_time_count = int(
                database.scalar(
                    select(func.count(DailyAttendance.id)).where(
                        DailyAttendance.freelancer_id == account.freelancer_id
                    )
                )
                or 0
            )
            first_date, latest_date = database.execute(
                select(
                    func.min(DailyAttendance.attendance_date),
                    func.max(DailyAttendance.attendance_date),
                ).where(DailyAttendance.freelancer_id == account.freelancer_id)
            ).one()

            dtrs = list(
                database.scalars(
                    select(MonthlyDTR)
                    .where(MonthlyDTR.freelancer_id == account.freelancer_id)
                    .order_by(MonthlyDTR.month_key.desc(), MonthlyDTR.id.desc())
                ).all()
            )
            dtr_rows = [
                {
                    "id": dtr.id,
                    "month_key": dtr.month_key,
                    "status": dtr.status,
                    "status_label": dtr_status_label(dtr.status),
                    "present_days": int(dtr.present_days or 0),
                    "absent_days": int(dtr.absent_days or 0),
                    "leave_days": int(dtr.leave_days or 0),
                    "late_days": int(dtr.late_days or 0),
                    "incomplete_days": int(dtr.incomplete_days or 0),
                    "rendered": minutes_label(int(dtr.rendered_minutes or 0)),
                    "task_time": minutes_label(int(dtr.daily_task_minutes or 0)),
                    "approved_overtime": minutes_label(int(dtr.approved_overtime_minutes or 0)),
                    "generated_at": format_local_datetime(dtr.generated_at, timezone_name),
                }
                for dtr in dtrs
            ]

            return templates.TemplateResponse(
                request=request,
                name="attendance_history.html",
                context=template_context(
                    request,
                    account=account,
                    history_rows=build_history_rows(
                        records,
                        timezone_name,
                        calculation_map,
                    ),
                    history_period=period,
                    selected_month=selected_month,
                    visible_record_count=len(records),
                    all_time_record_count=all_time_count,
                    first_attendance_date=(first_date.strftime("%b %d, %Y") if first_date else "—"),
                    latest_attendance_date=(latest_date.strftime("%b %d, %Y") if latest_date else "—"),
                    dtr_rows=dtr_rows,
                    task_hourly_mode=is_task_hourly_member(freelancer),
                ),
            )


    @router.get("/attendance/dtr/{dtr_id}", response_class=HTMLResponse)
    def freelancer_dtr_detail(dtr_id: int, request: Request):
        """Read-only Monthly DTR view restricted to the signed-in freelancer."""
        with SessionLocal() as database:
            account = get_current_freelancer_account(request, database)
            if account is None:
                return RedirectResponse("/login", status_code=303)
            if account.must_change_password:
                return RedirectResponse("/change-password", status_code=303)

            dtr = database.get(MonthlyDTR, dtr_id)
            if dtr is None or int(dtr.freelancer_id) != int(account.freelancer_id):
                set_flash(request, "DTR not found.", "error")
                return RedirectResponse("/attendance/history", status_code=303)

            freelancer = account.freelancer
            attendance_lines = list(
                database.scalars(
                    select(DTRDailyLine)
                    .where(DTRDailyLine.monthly_dtr_id == dtr.id)
                    .order_by(DTRDailyLine.attendance_date)
                ).all()
            )
            tasks = list(
                database.scalars(
                    select(DTRTaskLine)
                    .where(DTRTaskLine.monthly_dtr_id == dtr.id)
                    .order_by(DTRTaskLine.task_date, DTRTaskLine.id)
                ).all()
            )
            comp_lines = list(
                database.scalars(
                    select(DTRCompLine)
                    .where(DTRCompLine.monthly_dtr_id == dtr.id)
                    .order_by(DTRCompLine.transaction_date, DTRCompLine.id)
                ).all()
            )
            leave_lines = list(
                database.scalars(
                    select(DTRLeaveLine)
                    .where(DTRLeaveLine.monthly_dtr_id == dtr.id)
                    .order_by(DTRLeaveLine.leave_date, DTRLeaveLine.id)
                ).all()
            )
            overtime = [
                line for line in attendance_lines
                if int(line.potential_overtime_minutes or 0)
                or int(line.approved_overtime_minutes or 0)
            ]
            task_hourly_mode = is_task_hourly_member(freelancer)
            task_hourly_ledger = (
                task_hourly_month_ledger(database, freelancer=freelancer, month_key=dtr.month_key)
                if task_hourly_mode
                else None
            )

            return templates.TemplateResponse(
                request=request,
                name="freelancer_dtr_detail.html",
                context=template_context(
                    request,
                    account=account,
                    dtr=dtr,
                    freelancer=freelancer,
                    lines=[dtr_line_row(line, dtr.timezone_name) for line in attendance_lines],
                    overtime=[dtr_line_row(line, dtr.timezone_name) for line in overtime],
                    tasks=tasks,
                    comp_lines=comp_lines,
                    leave_lines=leave_lines,
                    compact=compact_dtr_metrics(database, dtr),
                    task_hourly_mode=task_hourly_mode,
                    task_hourly_ledger=task_hourly_ledger,
                ),
            )




    # BIMFM Portal v2 modular system and authentication routers
    from app.routers.system import router as system_router
    from app.routers.auth import create_auth_router

    app.include_router(system_router)
    app.include_router(create_auth_router(templates))


    # BIMFM Portal v2 modular project-management router
    from app.routers.portal import create_portal_router

    app.include_router(
        create_portal_router(
            templates=templates,
            get_current_admin=get_current_admin,
            template_context=template_context,
        )
    )




    @router.post("/attendance/correction-request")
    def request_previous_attendance_correction(
        request: Request, csrf: str = Form(...), attendance_date: str = Form(...),
        time_in: str = Form(""), time_out: str = Form(""), reason: str = Form(...),
    ):
        if not validate_csrf(request, csrf):
            return RedirectResponse("/attendance", 303)
        try:
            requested_date = date.fromisoformat(attendance_date)
        except ValueError:
            set_flash(request, "Invalid attendance date.", "error")
            return RedirectResponse("/attendance", 303)
        with SessionLocal() as database:
            account = get_current_freelancer_account(request, database)
            if account is None: return RedirectResponse("/login", 303)
            if is_task_hourly_member(account.freelancer):
                set_flash(request, "Attendance correction is not required for this task-hourly account.", "info")
                return RedirectResponse("/attendance", 303)
            today = current_attendance_date(account.freelancer.timezone_name)
            if requested_date >= today:
                set_flash(request, "Only previous attendance dates can be requested.", "error")
                return RedirectResponse("/attendance", 303)
            if len(reason.strip()) < 5:
                set_flash(request, "Enter a reason of at least 5 characters.", "error")
                return RedirectResponse("/attendance", 303)
            existing = database.scalar(select(AttendanceCorrectionRequest).where(AttendanceCorrectionRequest.freelancer_id==account.freelancer_id, AttendanceCorrectionRequest.attendance_date==requested_date, AttendanceCorrectionRequest.status=="PENDING"))
            if existing:
                set_flash(request, "A pending request already exists for this date.", "error")
                return RedirectResponse("/attendance", 303)
            try:
                requested_in = local_time_to_utc(requested_date, time_in, account.freelancer.timezone_name)
                requested_out = local_time_to_utc(requested_date, time_out, account.freelancer.timezone_name)
            except ValueError as exc:
                set_flash(request, str(exc), "error"); return RedirectResponse("/attendance", 303)
            if requested_out and not requested_in:
                set_flash(request, "Time Out cannot exist without Time In.", "error"); return RedirectResponse("/attendance", 303)
            if requested_in and requested_out and requested_out <= requested_in:
                requested_out = local_time_to_utc(requested_date + timedelta(days=1), time_out, account.freelancer.timezone_name)
            record = get_daily_attendance(database, account.freelancer_id, requested_date)
            row = AttendanceCorrectionRequest(freelancer_id=account.freelancer_id, daily_attendance_id=record.id if record else None, attendance_date=requested_date, requested_time_in_utc=requested_in, requested_time_out_utc=requested_out, reason=reason.strip(), status="PENDING")
            database.add(row); database.flush()
            write_audit(database, actor_type="FREELANCER", actor_id=account.freelancer_id, action="REQUEST_ATTENDANCE_CORRECTION", request=request, target_type="ATTENDANCE_CORRECTION_REQUEST", target_id=row.id, details=f"Date {requested_date.isoformat()}; reason: {reason.strip()}")
            database.commit()
        set_flash(request, "Attendance correction request submitted.", "success")
        return RedirectResponse("/attendance", 303)

    @router.get("/admin/attendance/correction-requests", response_class=HTMLResponse)
    def attendance_correction_requests_admin(request: Request):
        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None: return RedirectResponse("/admin/login", 303)
            requests = list(database.scalars(select(AttendanceCorrectionRequest).order_by(AttendanceCorrectionRequest.status, AttendanceCorrectionRequest.requested_at.desc())).all())
            freelancers = {f.id:f for f in database.scalars(select(Freelancer)).all()}
            return templates.TemplateResponse(request=request, name="admin_attendance_requests.html", context=template_context(request, admin=admin, requests=requests, freelancers=freelancers, format_local_datetime=format_local_datetime))

    @router.post("/admin/attendance/correction-requests/{request_id}/review")
    def review_attendance_correction_request(request_id: int, request: Request, csrf: str=Form(...), decision: str=Form(...), review_reason: str=Form(...)):
        if not validate_csrf(request, csrf): return RedirectResponse("/admin/attendance/correction-requests", 303)
        with SessionLocal() as database:
            admin=get_current_admin(request,database)
            if admin is None: return RedirectResponse("/admin/login",303)
            item=database.get(AttendanceCorrectionRequest,request_id)
            if item is None or item.status!="PENDING":
                set_flash(request,"Correction request is no longer pending.","error"); return RedirectResponse("/admin/attendance/correction-requests",303)
            if len(review_reason.strip())<5:
                set_flash(request,"Enter review notes of at least 5 characters.","error"); return RedirectResponse("/admin/attendance/correction-requests",303)
            item.reviewed_by_admin_id=admin.id; item.reviewed_at=utc_now(); item.review_reason=review_reason.strip()
            if decision.upper()=="APPROVE":
                freelancer=database.get(Freelancer,item.freelancer_id)
                record=get_daily_attendance(database,item.freelancer_id,item.attendance_date)
                if record is None:
                    record=DailyAttendance(freelancer_id=item.freelancer_id,attendance_date=item.attendance_date); database.add(record); database.flush()
                original_in, original_out=record.time_in_utc,record.time_out_utc
                record.time_in_utc=item.requested_time_in_utc; record.time_out_utc=item.requested_time_out_utc
                record.status="COMPLETE" if item.requested_time_out_utc else ("PRESENT" if item.requested_time_in_utc else "NO_RECORD")
                record.review_status="CORRECTED"; record.missed_time_out_flag=False; record.missed_work_order_stop_flag=False; record.overtime_unavailable=False; record.exception_flagged_at=None
                calculate_attendance_record(database,record,freelancer,source="APPROVED_CORRECTION_REQUEST",admin_id=admin.id)
                if item.requested_time_out_utc is not None:
                    repaired = repair_flagged_work_session(database, freelancer=freelancer, attendance_date=item.attendance_date, corrected_stop=item.requested_time_out_utc, notes=f"Approved attendance request: {item.reason}")
                    if repaired is not None:
                        _, repaired_task = repaired
                        invalidate_task_review(database, freelancer.id, repaired_task.task_date.strftime("%Y-%m"))
                correction=AttendanceCorrection(daily_attendance_id=record.id,freelancer_id=item.freelancer_id,attendance_date=item.attendance_date,original_time_in_utc=original_in,original_time_out_utc=original_out,corrected_time_in_utc=item.requested_time_in_utc,corrected_time_out_utc=item.requested_time_out_utc,reason=f"Approved request: {item.reason}; review: {review_reason.strip()}",corrected_by_admin_id=admin.id)
                database.add(correction); item.status="APPROVED"; invalidate_dtr(database,item.freelancer_id,item.attendance_date.strftime("%Y-%m"))
            else:
                item.status="REJECTED"
            write_audit(database,actor_type="HR_ADMIN",actor_id=admin.id,action=f"{item.status}_ATTENDANCE_CORRECTION_REQUEST",request=request,target_type="ATTENDANCE_CORRECTION_REQUEST",target_id=item.id,details=review_reason.strip())
            database.commit()
        set_flash(request,"Attendance correction request reviewed.","success")
        return RedirectResponse("/admin/attendance/correction-requests",303)

    return router
