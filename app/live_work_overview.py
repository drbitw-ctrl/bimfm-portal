"""Read-only Live Work Room projection for active Work Orders.

This module reads existing Work Order rows only. It creates no tables, performs
no migrations, and does not persist screen-sharing state.
"""
from __future__ import annotations
from typing import Any
from sqlalchemy import select
from app.database import SessionLocal
from app.models import Freelancer, TaskWorkSession


def merge_active_work_orders(room_state: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with SessionLocal() as database:
        active_rows = database.execute(
            select(TaskWorkSession, Freelancer)
            .join(Freelancer, Freelancer.id == TaskWorkSession.freelancer_id)
            .where(
                TaskWorkSession.status == "ACTIVE",
                TaskWorkSession.stopped_at.is_(None),
                Freelancer.is_active.is_(True),
            )
            .order_by(TaskWorkSession.started_at.asc(), TaskWorkSession.id.asc())
        ).all()
        active_ids: set[int] = set()
        for session, freelancer in active_rows:
            freelancer_id = int(freelancer.id)
            active_ids.add(freelancer_id)
            presence = room_state.get(freelancer_id, {})
            rows.append({
                "freelancer_id": freelancer_id,
                "freelancer_name": str(freelancer.full_name),
                "viewer_count": int(presence.get("viewer_count", 0)),
                "screen_live": bool(presence.get("screen_live", False)),
                "project_name": str(session.project_name or session.project_code or "—"),
                "project_code": str(session.project_code or ""),
                "task_title": str(session.task_title or "Active Work Order"),
                "discipline": str(session.discipline or ""),
                "started_at": session.started_at.isoformat() if session.started_at else "",
            })


    return sorted(rows, key=lambda row: (not row["screen_live"], row["freelancer_name"].casefold()))
