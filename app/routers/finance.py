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
            # Working-day counts remain whole numbers. Payroll treatment is
            # hour-based, so leave and compensatory-credit values retain partial
            # day/hour precision.
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
            for row in rows:
                row["closing_label"] = minutes_label(row["closing_minutes"])
                row["earned_label"] = minutes_label(row["comp_earned_minutes"])
                row["approved_ot_label"] = minutes_label(row["approved_ot_minutes"])
            return templates.TemplateResponse(
                request=request, name="admin_finance_center.html",
                context=template_context(request, admin=admin, selected_month=selected_month, rows=rows, totals=totals),
            )

    return router
