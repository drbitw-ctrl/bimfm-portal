"""Finance Center routes and finance reconciliation controls.

Release 21.24.3.11 keeps Finance/DTR persistence unchanged while adding two
controlled operations:

* a per-login Finance Center view exclusion (session only; no database write),
* Administrator-only correction of existing stopped Work Order timestamps.

Work Order corrections are audited and invalidate non-finalized task/DTR
snapshots so finance reporting cannot continue to show stale task time.
"""
from __future__ import annotations

from datetime import datetime, time as clock_time, timezone
import math

from fastapi import APIRouter


FINANCE_HIDDEN_SESSION_KEY = "finance_hidden_freelancer_ids_by_month"


def _hidden_member_ids(request, month_key: str) -> set[int]:
    raw_map = request.session.get(FINANCE_HIDDEN_SESSION_KEY, {})
    if not isinstance(raw_map, dict):
        return set()
    raw = raw_map.get(month_key, [])
    if not isinstance(raw, list):
        return set()
    result: set[int] = set()
    for value in raw:
        try:
            result.add(int(value))
        except (TypeError, ValueError):
            continue
    return result


def _store_hidden_member_ids(request, month_key: str, values: set[int]) -> None:
    raw_map = request.session.get(FINANCE_HIDDEN_SESSION_KEY, {})
    hidden_map = dict(raw_map) if isinstance(raw_map, dict) else {}
    if values:
        hidden_map[month_key] = sorted(int(value) for value in values)
    else:
        hidden_map.pop(month_key, None)
    request.session[FINANCE_HIDDEN_SESSION_KEY] = hidden_map


def _finance_totals(rows: list[dict]) -> dict:
    """Calculate only what is visible in the Finance Center table."""
    totals = {
        "employees": len(rows),
        "ready": sum(1 for x in rows if x["status"] == "READY"),
        "pending": sum(1 for x in rows if x["status"] != "READY"),
        "calendar_days": sum(x["calendar_days"] for x in rows),
        "worked_days": sum(x["worked_days"] for x in rows),
        "worked_hours": round(sum(x["worked_hours"] for x in rows), 2),
        "regular_leave_taken_days": sum(x["regular_leave_taken_days"] for x in rows),
        "approved_leave_hours": round(sum(x["approved_leave_hours"] for x in rows), 2),
        "comp_credit_hours_applied": round(sum(x["comp_credit_hours_applied"] for x in rows), 2),
        "effective_unpaid_leave_hours": round(sum(x["effective_unpaid_leave_hours"] for x in rows), 2),
        "absent_days": sum(x["absent_days"] for x in rows),
        "absent_hours": round(sum(x["absent_hours"] for x in rows), 2),
        "absence_comp_credit_hours_applied": round(sum(x["absence_comp_credit_hours_applied"] for x in rows), 2),
        "effective_absent_hours": round(sum(x["effective_absent_hours"] for x in rows), 2),
        "total_deduction_hours": round(sum(x["total_deduction_hours"] for x in rows), 2),
        "regular_leave_days": round(sum(x["regular_leave_days"] for x in rows), 3),
        "comp_leave_days": round(sum(x["comp_leave_days"] for x in rows), 3),
        "payable_days": round(sum(x["payable_days"] for x in rows), 3),
        "payable_workday_equivalents": round(sum(x["payable_workday_equivalents"] for x in rows), 3),
        "salary_covered_days": round(sum(x["salary_covered_days"] for x in rows), 3),
        "approved_ot_minutes": sum(x["approved_ot_minutes"] for x in rows),
        "closing_minutes": sum(x["closing_minutes"] for x in rows),
        "leave_days": sum(x["leave_days"] for x in rows),
        "comp_credit_days_applied": round(sum(x["comp_credit_days_applied"] for x in rows), 3),
        "effective_unpaid_leave_days": round(sum(x["effective_unpaid_leave_days"] for x in rows), 3),
        "month_calendar_days": max((x["calendar_days"] for x in rows), default=0),
        "full_month_count": sum(1 for x in rows if x["total_deduction_minutes"] == 0),
        "reduced_month_count": sum(1 for x in rows if x["total_deduction_minutes"] > 0),
    }
    totals["full_multiplier_count"] = totals["full_month_count"]
    totals["closing_label"] = minutes_label(totals["closing_minutes"])
    return totals


def _local_input(value: datetime | None, timezone_name: str) -> str:
    if value is None:
        return ""
    normalized = normalized_utc(value)
    if normalized is None:
        return ""
    return normalized.astimezone(freelancer_zone(timezone_name)).strftime("%Y-%m-%dT%H:%M")


def _parse_local_input(value: str, timezone_name: str) -> datetime:
    clean = str(value or "").strip()
    if not clean:
        raise ValueError("Start and end time are required.")
    try:
        parsed = datetime.fromisoformat(clean)
    except ValueError as exc:
        raise ValueError("Use a valid date and time.") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=freelancer_zone(timezone_name))
    return parsed.astimezone(timezone.utc)


def _local_month_key(value: datetime | None, timezone_name: str) -> str:
    normalized = normalized_utc(value)
    if normalized is None:
        return ""
    return normalized.astimezone(freelancer_zone(timezone_name)).strftime("%Y-%m")


def configure_finance_routes(legacy_namespace: dict[str, object]) -> APIRouter:
    globals().update(legacy_namespace)
    router = APIRouter(tags=["Finance"])
    globals()["router"] = router

    @router.get("/admin/finance", response_class=HTMLResponse)
    def finance_center(request: Request, month: str = ""):
        selected_month = month if parse_month_key(month) else current_month_key()
        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", status_code=303)

            # Backfill summaries for DTRs created before Step 10.
            dtrs = list(database.scalars(select(MonthlyDTR).where(MonthlyDTR.month_key == selected_month)).all())
            for dtr in dtrs:
                sync_finance_summary(database, dtr)
            database.commit()

            all_rows = finance_rows(database, selected_month)
            hidden_ids = _hidden_member_ids(request, selected_month)
            hidden_rows: list[dict] = []
            rows: list[dict] = []

            # Finance rows historically expose DTR ids, not freelancer ids. Attach
            # the member id here without changing the finance service contract.
            for row in all_rows:
                dtr = database.get(MonthlyDTR, row["dtr_id"])
                row["freelancer_id"] = int(dtr.freelancer_id) if dtr else 0
                if row["freelancer_id"] in hidden_ids:
                    hidden_rows.append(row)
                else:
                    rows.append(row)

            totals = _finance_totals(rows)
            for row in rows:
                row["closing_label"] = minutes_label(row["closing_minutes"])
                row["earned_label"] = minutes_label(row["comp_earned_minutes"])
                row["approved_ot_label"] = minutes_label(row["approved_ot_minutes"])
                dtr = database.get(MonthlyDTR, row["dtr_id"])
                current_credit_minutes = comp_balance(database, dtr.freelancer_id) if dtr else 0
                row["current_credit_minutes"] = current_credit_minutes
                row["current_credit_label"] = minutes_label(current_credit_minutes)

            return templates.TemplateResponse(
                request=request,
                name="admin_finance_center.html",
                context=template_context(
                    request,
                    admin=admin,
                    selected_month=selected_month,
                    rows=rows,
                    hidden_rows=hidden_rows,
                    hidden_count=len(hidden_rows),
                    totals=totals,
                ),
            )

    @router.post("/admin/finance/hide/{freelancer_id}")
    def finance_hide_member(
        freelancer_id: int,
        request: Request,
        csrf: str = Form(...),
        month: str = Form(""),
    ):
        selected_month = month if parse_month_key(month) else current_month_key()
        if not validate_csrf(request, csrf):
            return RedirectResponse(f"/admin/finance?month={selected_month}", status_code=303)
        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", status_code=303)
            freelancer = database.get(Freelancer, freelancer_id)
            if freelancer is None:
                set_flash(request, "Freelancer not found.", "error")
                return RedirectResponse(f"/admin/finance?month={selected_month}", status_code=303)
            hidden_ids = _hidden_member_ids(request, selected_month)
            hidden_ids.add(int(freelancer_id))
            _store_hidden_member_ids(request, selected_month, hidden_ids)
            set_flash(request, f"{freelancer.full_name} is hidden from this Finance Center view. No records were deleted.", "info")
        return RedirectResponse(f"/admin/finance?month={selected_month}", status_code=303)

    @router.post("/admin/finance/show/{freelancer_id}")
    def finance_show_member(
        freelancer_id: int,
        request: Request,
        csrf: str = Form(...),
        month: str = Form(""),
    ):
        selected_month = month if parse_month_key(month) else current_month_key()
        if not validate_csrf(request, csrf):
            return RedirectResponse(f"/admin/finance?month={selected_month}", status_code=303)
        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", status_code=303)
            hidden_ids = _hidden_member_ids(request, selected_month)
            hidden_ids.discard(int(freelancer_id))
            _store_hidden_member_ids(request, selected_month, hidden_ids)
        set_flash(request, "Member restored to Finance Center view.", "success")
        return RedirectResponse(f"/admin/finance?month={selected_month}", status_code=303)

    @router.post("/admin/finance/show-all")
    def finance_show_all_members(
        request: Request,
        csrf: str = Form(...),
        month: str = Form(""),
    ):
        selected_month = month if parse_month_key(month) else current_month_key()
        if not validate_csrf(request, csrf):
            return RedirectResponse(f"/admin/finance?month={selected_month}", status_code=303)
        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", status_code=303)
        _store_hidden_member_ids(request, selected_month, set())
        set_flash(request, "All hidden members restored to Finance Center view.", "success")
        return RedirectResponse(f"/admin/finance?month={selected_month}", status_code=303)

    @router.get("/admin/finance/work-orders/{freelancer_id}", response_class=HTMLResponse)
    def finance_work_order_times(request: Request, freelancer_id: int, month: str = ""):
        selected_month = month if parse_month_key(month) else current_month_key()
        month_range = parse_month_key(selected_month)
        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", status_code=303)
            freelancer = database.get(Freelancer, freelancer_id)
            if freelancer is None:
                set_flash(request, "Freelancer not found.", "error")
                return RedirectResponse(f"/admin/finance?month={selected_month}", status_code=303)

            first_day, next_month = month_range
            zone = freelancer_zone(freelancer.timezone_name)
            start_utc = datetime.combine(first_day, clock_time.min, tzinfo=zone).astimezone(timezone.utc)
            end_utc = datetime.combine(next_month, clock_time.min, tzinfo=zone).astimezone(timezone.utc)
            sessions = list(database.scalars(
                select(TaskWorkSession).where(
                    TaskWorkSession.freelancer_id == freelancer.id,
                    TaskWorkSession.started_at >= start_utc,
                    TaskWorkSession.started_at < end_utc,
                ).order_by(TaskWorkSession.started_at.desc(), TaskWorkSession.id.desc())
            ).all())

            rows = []
            for session in sessions:
                daily_task = database.get(DailyTask, session.daily_task_id) if session.daily_task_id else None
                rows.append({
                    "session": session,
                    "daily_task": daily_task,
                    "started_local": _local_input(session.started_at, freelancer.timezone_name),
                    "stopped_local": _local_input(session.stopped_at, freelancer.timezone_name),
                    "started_display": format_local_datetime(session.started_at, freelancer.timezone_name),
                    "stopped_display": format_local_datetime(session.stopped_at, freelancer.timezone_name),
                    "duration_label": minutes_label(int(session.duration_minutes or 0)),
                    "can_edit": bool(session.status == "STOPPED" and session.stopped_at is not None),
                })

            dtr = database.scalar(select(MonthlyDTR).where(
                MonthlyDTR.freelancer_id == freelancer.id,
                MonthlyDTR.month_key == selected_month,
            ))
            return templates.TemplateResponse(
                request=request,
                name="admin_finance_work_order_times.html",
                context=template_context(
                    request,
                    admin=admin,
                    freelancer=freelancer,
                    selected_month=selected_month,
                    rows=rows,
                    month_locked=month_is_locked(database, selected_month),
                    dtr=dtr,
                    dtr_finalized=bool(dtr and dtr.status == "FINALIZED"),
                ),
            )

    @router.post("/admin/finance/work-orders/{session_id}/correct")
    def correct_finance_work_order_time(
        session_id: int,
        request: Request,
        csrf: str = Form(...),
        month: str = Form(""),
        started_at_local: str = Form(...),
        stopped_at_local: str = Form(...),
        reason: str = Form(...),
    ):
        selected_month = month if parse_month_key(month) else current_month_key()
        fallback = f"/admin/finance?month={selected_month}"
        if not validate_csrf(request, csrf):
            return RedirectResponse(fallback, status_code=303)

        with SessionLocal() as database:
            admin = get_current_admin(request, database)
            if admin is None:
                return RedirectResponse("/admin/login", status_code=303)
            if str(getattr(admin, "role", "ADMIN") or "ADMIN").upper() != "ADMIN":
                set_flash(request, "Work Order time corrections require an Administrator account.", "error")
                return RedirectResponse(fallback, status_code=303)

            session = database.get(TaskWorkSession, session_id)
            if session is None:
                set_flash(request, "Work Order not found.", "error")
                return RedirectResponse(fallback, status_code=303)
            freelancer = database.get(Freelancer, session.freelancer_id)
            if freelancer is None:
                set_flash(request, "Freelancer not found.", "error")
                return RedirectResponse(fallback, status_code=303)
            target = f"/admin/finance/work-orders/{freelancer.id}?month={selected_month}"

            if session.status != "STOPPED" or session.stopped_at is None:
                set_flash(request, "Only completed Work Orders can be corrected.", "error")
                return RedirectResponse(target, status_code=303)

            clean_reason = " ".join(str(reason or "").strip().split())
            if len(clean_reason) < 8:
                set_flash(request, "Enter a correction reason of at least 8 characters.", "error")
                return RedirectResponse(target, status_code=303)

            try:
                new_start = _parse_local_input(started_at_local, freelancer.timezone_name)
                new_stop = _parse_local_input(stopped_at_local, freelancer.timezone_name)
            except ValueError as exc:
                set_flash(request, str(exc), "error")
                return RedirectResponse(target, status_code=303)
            if new_stop <= new_start:
                set_flash(request, "The end time must be later than the start time.", "error")
                return RedirectResponse(target, status_code=303)

            duration_minutes = max(1, int(math.ceil((new_stop - new_start).total_seconds() / 60.0)))
            max_minutes = int(WORK_ORDER_MAX_ACTIVE_HOURS) * 60
            if duration_minutes > max_minutes:
                set_flash(request, f"A corrected Work Order cannot exceed {WORK_ORDER_MAX_ACTIVE_HOURS} hours.", "error")
                return RedirectResponse(target, status_code=303)

            old_start = normalized_utc(session.started_at)
            old_stop = normalized_utc(session.stopped_at)
            affected_months = {
                key for key in (
                    _local_month_key(old_start, freelancer.timezone_name),
                    _local_month_key(old_stop, freelancer.timezone_name),
                    _local_month_key(new_start, freelancer.timezone_name),
                    _local_month_key(new_stop, freelancer.timezone_name),
                ) if key
            }

            locked_months = [key for key in sorted(affected_months) if month_is_locked(database, key)]
            if locked_months:
                set_flash(request, f"Unlock attendance month(s) {', '.join(locked_months)} before correcting Work Order time.", "error")
                return RedirectResponse(target, status_code=303)

            finalized_months = list(database.scalars(select(MonthlyDTR.month_key).where(
                MonthlyDTR.freelancer_id == freelancer.id,
                MonthlyDTR.month_key.in_(sorted(affected_months)),
                MonthlyDTR.status == "FINALIZED",
            )).all()) if affected_months else []
            if finalized_months:
                set_flash(request, f"Finalized DTR month(s) {', '.join(sorted(set(finalized_months)))} cannot be changed.", "error")
                return RedirectResponse(target, status_code=303)

            overlap = database.scalar(select(TaskWorkSession).where(
                TaskWorkSession.freelancer_id == freelancer.id,
                TaskWorkSession.id != session.id,
                TaskWorkSession.started_at < new_stop,
                or_(
                    TaskWorkSession.stopped_at.is_(None),
                    TaskWorkSession.stopped_at > new_start,
                ),
            ).order_by(TaskWorkSession.started_at.asc()).limit(1))
            if overlap is not None:
                set_flash(request, f"The corrected interval overlaps Work Order #{overlap.id}. Adjust the times first.", "error")
                return RedirectResponse(target, status_code=303)

            old_duration = int(session.duration_minutes or 0)
            session.started_at = new_start
            session.stopped_at = new_stop
            session.duration_minutes = duration_minutes
            session.updated_at = utc_now()

            daily_task = database.get(DailyTask, session.daily_task_id) if session.daily_task_id else None
            if daily_task is None:
                task = database.get(PortalTask, session.portal_task_id) if session.portal_task_id else None
                portal_status = str(getattr(task, "status", "IN_PROGRESS") or "IN_PROGRESS").upper()
                daily_task = DailyTask(
                    freelancer_id=freelancer.id,
                    portal_task_id=session.portal_task_id,
                    synced_project_task_id=None,
                    task_date=new_start.astimezone(freelancer_zone(freelancer.timezone_name)).date(),
                    project_code=session.project_code,
                    project_name=session.project_name,
                    discipline=session.discipline,
                    task_description=session.task_title,
                    accomplishment=session.notes,
                    task_status="COMPLETED" if portal_status == "COMPLETED" else "IN_PROGRESS",
                    minutes_spent=duration_minutes,
                    completion_percentage=max(0, min(100, int(getattr(task, "progress", 0) or 0))),
                    notes="Created while reconciling an existing Work Order time correction.",
                )
                database.add(daily_task)
                database.flush()
                session.daily_task_id = daily_task.id
            else:
                daily_task.task_date = new_start.astimezone(freelancer_zone(freelancer.timezone_name)).date()
                daily_task.minutes_spent = duration_minutes
                daily_task.updated_at = utc_now()

            # Any pre-existing monthly task review/DTR snapshot is now stale.
            for key in sorted(affected_months):
                invalidate_task_review(database, freelancer.id, key)

            write_audit(
                database,
                actor_type="ADMIN",
                actor_id=admin.id,
                action="CORRECT_WORK_ORDER_TIME",
                request=request,
                target_type="TASK_WORK_SESSION",
                target_id=session.id,
                details=(
                    f"Member={freelancer.full_name}; "
                    f"old_start={old_start.isoformat() if old_start else ''}; "
                    f"old_stop={old_stop.isoformat() if old_stop else ''}; "
                    f"old_minutes={old_duration}; "
                    f"new_start={new_start.isoformat()}; new_stop={new_stop.isoformat()}; "
                    f"new_minutes={duration_minutes}; reason={clean_reason}"
                ),
            )
            database.commit()

        set_flash(request, "Work Order time corrected. Task review and non-finalized DTR snapshots were invalidated for regeneration.", "success")
        return RedirectResponse(target, status_code=303)

    return router
