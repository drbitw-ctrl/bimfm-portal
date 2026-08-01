"""BIMFM Portal v2 finance routes.

Extracted from the verified legacy application without changing route behavior.
Dependencies are injected during application startup as a compatibility bridge.
"""
from __future__ import annotations

from fastapi import APIRouter


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
            rows = finance_rows(database, selected_month)
            # Final route-level safety: Finance must never receive fractional day
            # values, even if old summaries remain in the database. This conversion
            # happens after every database/service calculation and before rendering.
            whole_day_fields = (
                "calendar_days", "worked_days", "regular_leave_taken_days",
                "leave_days", "comp_credit_days_applied", "effective_unpaid_leave_days",
                "payroll_numerator_days", "regular_leave_days", "comp_leave_days",
                "payable_days", "non_payable_days", "rest_days", "holiday_days",
            )
            for row in rows:
                for field in whole_day_fields:
                    row[field] = int(row.get(field) or 0)
            totals = {
                "employees": len(rows),
                "ready": sum(1 for x in rows if x["status"] == "READY"),
                "pending": sum(1 for x in rows if x["status"] != "READY"),
                "calendar_days": sum(x["calendar_days"] for x in rows),
                "worked_days": sum(x["worked_days"] for x in rows),
                "regular_leave_taken_days": sum(x["regular_leave_taken_days"] for x in rows),
                "regular_leave_days": sum(x["regular_leave_days"] for x in rows),
                "comp_leave_days": sum(x["comp_leave_days"] for x in rows),
                "payable_days": sum(x["payable_days"] for x in rows),
                "payable_workday_equivalents": sum(x["payable_workday_equivalents"] for x in rows),
                "salary_covered_days": sum(x["salary_covered_days"] for x in rows),
                "approved_ot_minutes": sum(x["approved_ot_minutes"] for x in rows),
                "closing_minutes": sum(x["closing_minutes"] for x in rows),
                "leave_days": sum(x["leave_days"] for x in rows),
                "comp_credit_days_applied": sum(x["comp_credit_days_applied"] for x in rows),
                "effective_unpaid_leave_days": sum(x["effective_unpaid_leave_days"] for x in rows),
                "month_calendar_days": max((x["calendar_days"] for x in rows), default=0),
                "full_month_count": sum(1 for x in rows if x["effective_unpaid_leave_days"] == 0),
                "reduced_month_count": sum(1 for x in rows if x["effective_unpaid_leave_days"] > 0),
            }
            totals["full_multiplier_count"] = totals["full_month_count"]
            totals["closing_label"] = minutes_label(totals["closing_minutes"])
            for row in rows:
                row["closing_label"] = minutes_label(row["closing_minutes"])
                row["earned_label"] = minutes_label(row["comp_earned_minutes"])
                row["approved_ot_label"] = minutes_label(row["approved_ot_minutes"])
            return templates.TemplateResponse(
                request=request, name="admin_finance_center.html",
                context=template_context(request, admin=admin, selected_month=selected_month, rows=rows, totals=totals),
            )

    return router
