"""Attendance and DTR web routes extracted from the legacy application.

Milestone 3 keeps the existing behavior intact while moving attendance endpoints
out of ``app.main``. Shared helpers remain in ``app.main`` temporarily and are
injected during router creation; later milestones will move those helpers into
services and dependencies.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.auth.permissions import Permission, has_permission, normalize_role


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
                rows.append(
                    build_admin_attendance_row(
                        freelancer,
                        record,
                        local_date,
                        correction_count,
                        get_calculation(database, record.id) if record else None,
                    )
                )

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
        freelancer_id: Optional[int] = None,
    ):
        selected_month = month.strip() or current_month_key(DEFAULT_TIMEZONE)
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
            if freelancer_id is not None:
                query = query.where(Freelancer.id == freelancer_id)

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
                    selected_freelancer_id=freelancer_id,
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

            if (
                corrected_time_in is not None
                and corrected_time_out is not None
                and corrected_time_out <= corrected_time_in
            ):
                set_flash(
                    request,
                    "Corrected Time Out must be later than Time In.",
                    "error",
                )
                return RedirectResponse(redirect_path, status_code=303)

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
                row for row in hr_freelancer_choices(database) if row.is_active
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
                    row for row in hr_freelancer_choices(database) if row.is_active
                ]
            else:
                freelancer = database.get(Freelancer, freelancer_id)
                freelancers = [freelancer] if freelancer is not None else []

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
            lines = list(
                database.scalars(
                    select(DTRDailyLine)
                    .where(DTRDailyLine.monthly_dtr_id == dtr.id)
                    .order_by(DTRDailyLine.attendance_date)
                ).all()
            )
            names = admin_name_map(database)
            review_allowed, review_message = dtr_can_be_reviewed(dtr)
            return templates.TemplateResponse(
                request=request,
                name="admin_dtr_detail.html",
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
            return templates.TemplateResponse(
                request=request,
                name="admin_dtr_details.html",
                context=template_context(
                    request, admin=admin, dtr=dtr, freelancer=freelancer,
                    lines=[dtr_line_row(line, dtr.timezone_name) for line in attendance],
                    overtime=[dtr_line_row(line, dtr.timezone_name) for line in overtime],
                    tasks=tasks, comp_lines=comp_lines, leave_lines=leave_lines,
                    compact=compact_dtr_metrics(database, dtr),
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

            records = list(
                database.scalars(
                    select(DailyAttendance)
                    .where(
                        DailyAttendance.freelancer_id
                        == account.freelancer_id
                    )
                    .order_by(
                        DailyAttendance.attendance_date.desc()
                    )
                    .limit(31)
                ).all()
            )

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

            return templates.TemplateResponse(
                request=request,
                name="attendance_history.html",
                context=template_context(
                    request,
                    account=account,
                    history_rows=build_history_rows(
                        records,
                        account.freelancer.timezone_name,
                        calculation_map,
                    ),
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



    return router
