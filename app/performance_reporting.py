"""Performance leaderboard and project-report analytics.

Release 20.20 keeps source task and quality values unchanged.  Quality scores
use a management reporting scale for presentation while preserving original task ratings
from the user's previous desktop dashboard.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Iterable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    DailyTask,
    Freelancer,
    HRAdminAccount,
    PortalProject,
    PortalTask,
    PortalTaskAssignment,
    ProjectMember,
)

CLOSED_TASK_STATUSES = {"COMPLETED", "CANCELLED"}
FINAL_COMPLETED_STATUS = "COMPLETED"
FOR_REVIEW_STATUS = "FOR_REVIEW"

QUALITY_SCORE_WEIGHT = 0.70
QUALITY_SCORE_BASE = 22.0
QUALITY_SCORE_MAXIMUM = 92.0
QUALITY_SCORE_MINIMUM = 0.0

QUALITY_EXCELLENT_THRESHOLD = 88.0
QUALITY_STRONG_THRESHOLD = 80.0
QUALITY_ACCEPTABLE_THRESHOLD = 70.0

OVERALL_QUALITY_WEIGHT = 0.60
OVERALL_SPEED_WEIGHT = 0.40


DISCIPLINE_ALIASES = {
    "ARCHITECTURE": "AR",
    "ARCHITECTURAL": "AR",
    "AR": "AR",
    "STRUCTURE": "ST",
    "STRUCTURAL": "ST",
    "ST": "ST",
    "AS": "AS",
    "AR+ST": "AS",
    "AS (AR+ST)": "AS",
    "AS (AR + ST)": "AS",
    "MEP": "MEP",
    "E&M": "E&M",
    "EM": "E&M",
    "RFA": "RFA",
    "CDR": "CDR",
    "GE": "GE",
    "CIVIL WORKS": "CIVIL WORKS",
}

SPECIALTY_SPECS = (
    {"key": "MEP", "label": "MEP", "kind": "discipline"},
    {"key": "AR", "label": "AR", "kind": "discipline"},
    {"key": "ST", "label": "ST", "kind": "discipline"},
    {"key": "MRT", "label": "MRT", "kind": "category"},
    {"key": "安居", "label": "安居", "kind": "category"},
    {"key": "BRIDGE", "label": "Bridge", "kind": "category"},
    {"key": "RFA", "label": "RFA", "kind": "discipline"},
)


def normalize_discipline(value: Any) -> str:
    text = " ".join(str(value or "").strip().split()).upper()
    return DISCIPLINE_ALIASES.get(text, text)


def normalize_project_category(value: Any) -> str:
    text = " ".join(str(value or "").strip().split())
    if not text:
        return ""
    upper = text.upper()
    if upper == "BRIDGE":
        return "BRIDGE"
    if upper == "MRT":
        return "MRT"
    return text


def _record_matches_specialty(record: dict[str, Any], *, key: str, kind: str) -> bool:
    task = record["task"]
    project = record.get("project")
    if kind == "category":
        return normalize_project_category(getattr(project, "project_category", None)) == key
    discipline = normalize_discipline(
        getattr(task, "discipline", None) or getattr(project, "discipline", None)
    )
    if key == "AR":
        return discipline in {"AR", "AS"}
    if key == "ST":
        return discipline in {"ST", "AS"}
    return discipline == key


def _specialty_metric(records: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [
        record for record in records
        if str(record["task"].status or "").upper() == FINAL_COMPLETED_STATUS
    ]
    scores = [
        score for record in completed
        if (score := parse_quality_score(record["task"].quality_score)) is not None
    ]
    adjusted = [calibrate_quality_score(score) for score in scores]
    differences = [
        int(record["days_difference"]) for record in completed
        if record["days_difference"] is not None
    ]
    quality = round(sum(adjusted) / len(adjusted), 1) if adjusted else None
    speed = round(sum(1 for value in differences if value <= 0) / len(differences) * 100, 1) if differences else None
    overall = (
        round(float(quality) * OVERALL_QUALITY_WEIGHT + float(speed) * OVERALL_SPEED_WEIGHT, 1)
        if quality is not None and speed is not None else None
    )
    return {
        "completed_tasks": len(completed),
        "rated_tasks": len(adjusted),
        "measured_tasks": len(differences),
        "quality": quality,
        "speed": speed,
        "overall": overall,
        "eligible": len(completed) >= 3 and len(adjusted) >= 2 and len(differences) >= 2,
    }


def build_specialty_recommendations(database: Session) -> list[dict[str, Any]]:
    records_by_member, identities, _tasks, _projects = _task_records_by_member(database)
    results: list[dict[str, Any]] = []
    for spec in SPECIALTY_SPECS:
        candidates: list[dict[str, Any]] = []
        for member_key, task_records in records_by_member.items():
            identity = identities[member_key]
            if not identity.get("is_active"):
                continue
            matched = [
                record for record in task_records.values()
                if _record_matches_specialty(record, key=spec["key"], kind=spec["kind"])
            ]
            metric = _specialty_metric(matched)
            if metric["completed_tasks"] == 0:
                continue
            candidates.append({**identity, **metric})
        candidates.sort(key=lambda row: (
            not row["eligible"],
            row["overall"] is None,
            -(row["overall"] if row["overall"] is not None else -1),
            -row["completed_tasks"],
            str(row["name"]).casefold(),
        ))
        leader = candidates[0] if candidates else None
        results.append({
            **spec,
            "leader": leader,
            "has_reliable_data": bool(leader and leader["eligible"]),
            "candidate_count": len(candidates),
        })
    return results


def build_assignment_suggestions(
    database: Session,
    *,
    discipline: str = "",
    project_category: str = "",
) -> list[dict[str, Any]]:
    """Rank active members by specialty history and current availability."""
    from app.my_work_service import team_availability_rows

    records_by_member, identities, _tasks, _projects = _task_records_by_member(database)
    availability = {int(row["freelancer_id"]): row for row in team_availability_rows(database)}
    member_directory = list(database.scalars(
        select(ProjectMember).where(
            ProjectMember.is_active.is_(True),
            ProjectMember.freelancer_id.is_not(None),
        ).order_by(ProjectMember.member_name, ProjectMember.id)
    ).all())
    member_by_hr: dict[int, ProjectMember] = {}
    for member in member_directory:
        member_by_hr.setdefault(int(member.freelancer_id), member)

    normalized_discipline = normalize_discipline(discipline)
    normalized_category = normalize_project_category(project_category)
    rows: list[dict[str, Any]] = []
    availability_bonus = {"available": 15.0, "assigned": 5.0, "working": 0.0, "overdue": -25.0}
    for hr_id, member in member_by_hr.items():
        identity = identities.get(f"hr:{hr_id}")
        if not identity or not identity.get("is_active"):
            continue
        records = list(records_by_member.get(f"hr:{hr_id}", {}).values())
        discipline_metric = None
        category_metric = None
        if normalized_discipline:
            discipline_metric = _specialty_metric([
                record for record in records
                if _record_matches_specialty(record, key=normalized_discipline, kind="discipline")
            ])
        if normalized_category:
            category_metric = _specialty_metric([
                record for record in records
                if _record_matches_specialty(record, key=normalized_category, kind="category")
            ])
        component_scores = [
            metric["overall"] for metric in (discipline_metric, category_metric)
            if metric and metric["overall"] is not None
        ]
        specialty_score = round(sum(component_scores) / len(component_scores), 1) if component_scores else None
        matched_tasks = sum(
            metric["completed_tasks"] for metric in (discipline_metric, category_metric) if metric
        )
        avail = availability.get(hr_id, {
            "state": "available", "availability": "Available", "active_tasks": 0,
            "overdue_tasks": 0, "working_task": "No active task", "working_project": "—",
        })
        state = str(avail.get("state") or "available")
        ranking_score = (specialty_score if specialty_score is not None else 0.0)
        ranking_score += availability_bonus.get(state, 0.0)
        ranking_score -= min(20, int(avail.get("active_tasks") or 0) * 2)
        if specialty_score is not None and state == "available":
            recommendation = "Strong specialty match and currently available"
        elif specialty_score is not None:
            recommendation = "Specialty match; review current workload"
        elif state == "available":
            recommendation = "Available; limited specialty history"
        else:
            recommendation = "Current workload should be reviewed"
        rows.append({
            "project_member_id": int(member.id),
            "freelancer_id": hr_id,
            "name": identity["name"],
            "code": identity["code"],
            "availability": avail.get("availability", "Available"),
            "state": state,
            "active_tasks": int(avail.get("active_tasks") or 0),
            "overdue_tasks": int(avail.get("overdue_tasks") or 0),
            "working_task": str(avail.get("working_task") or "No active task"),
            "working_project": str(avail.get("working_project") or "—"),
            "specialty_score": specialty_score,
            "matched_tasks": matched_tasks,
            "recommendation": recommendation,
            "ranking_score": round(ranking_score, 2),
        })
    rows.sort(key=lambda row: (
        -row["ranking_score"],
        row["overdue_tasks"],
        row["active_tasks"],
        str(row["name"]).casefold(),
    ))
    for index, row in enumerate(rows, start=1):
        row["rank"] = index
    return rows


def calibrate_quality_score(raw_score: Any) -> float:
    """Return a conservative display score without modifying stored data."""
    try:
        score = float(raw_score)
    except (TypeError, ValueError):
        return 0.0
    score = max(0.0, min(100.0, score))
    adjusted = score * QUALITY_SCORE_WEIGHT + QUALITY_SCORE_BASE
    adjusted = max(QUALITY_SCORE_MINIMUM, min(QUALITY_SCORE_MAXIMUM, adjusted))
    return round(adjusted, 1)


def parse_quality_score(value: Any) -> Optional[int]:
    if value is None:
        return None
    text = str(value).strip().replace("%", "")
    if not text:
        return None
    try:
        score = float(text)
    except (TypeError, ValueError):
        return None
    if not score.is_integer():
        return None
    integer = int(score)
    return integer if 1 <= integer <= 100 else None


def _as_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _completion_date(task: PortalTask) -> Optional[date]:
    completed = _as_date(task.completed_at)
    if completed is not None:
        return completed
    if str(task.status or "").upper() == FINAL_COMPLETED_STATUS:
        # Historical imported records occasionally have no completed_at value.
        # updated_at is used only as a reporting fallback and is never persisted.
        return _as_date(task.updated_at)
    return None


def _days_difference(task: PortalTask) -> Optional[int]:
    completed = _completion_date(task)
    due = _as_date(task.due_date)
    if completed is None or due is None:
        return None
    return (completed - due).days


def _administrator_rating_exclusions(database: Session) -> tuple[set[int], set[str]]:
    """Return freelancer identities that represent Administrator accounts.

    Ratings are intended to measure production members, not portal
    administrators.  Staff review timers can create deterministic ``TS-*``
    freelancer identities, and older deployments may also link an
    ``HRAdminAccount.task_freelancer_id`` directly.  Both representations are
    excluded at report time only; no account or assignment data is modified.
    """
    excluded_ids: set[int] = set()
    excluded_codes: set[str] = set()
    for account in database.scalars(select(HRAdminAccount)).all():
        if str(account.role or "").strip().upper() != "ADMIN":
            continue
        if account.task_freelancer_id is not None:
            excluded_ids.add(int(account.task_freelancer_id))
        if account.id is not None:
            excluded_codes.add(f"TS-{int(account.id):03d}")

    if excluded_codes:
        for profile in database.scalars(select(Freelancer)).all():
            if str(profile.freelancer_code or "").strip().upper() in excluded_codes:
                excluded_ids.add(int(profile.id))
    return excluded_ids, excluded_codes


def _member_identity_maps(database: Session) -> tuple[
    dict[int, int],
    set[int],
    dict[int, dict[str, Any]],
    dict[int, dict[str, Any]],
    set[int],
]:
    """Return source mappings and display identities for HR and legacy members."""
    excluded_admin_ids, excluded_admin_codes = _administrator_rating_exclusions(database)
    directory = list(database.scalars(select(ProjectMember)).all())
    placeholder_ids = {
        int(member.source_freelancer_id)
        for member in directory
        if member.source_freelancer_id is not None
    }
    source_to_hr = {
        int(member.source_freelancer_id): int(member.freelancer_id)
        for member in directory
        if member.source_freelancer_id is not None and member.freelancer_id is not None
    }

    profiles = list(database.scalars(select(Freelancer)).all())
    hr_identities: dict[int, dict[str, Any]] = {}
    for profile in profiles:
        if int(profile.id) in placeholder_ids:
            continue
        if (
            int(profile.id) in excluded_admin_ids
            or str(profile.freelancer_code or "").strip().upper() in excluded_admin_codes
        ):
            continue
        hr_identities[int(profile.id)] = {
            "key": f"hr:{int(profile.id)}",
            "id": int(profile.id),
            "name": str(profile.full_name or profile.freelancer_code),
            "code": str(profile.freelancer_code or ""),
            "is_active": bool(profile.is_active),
            "is_legacy": False,
        }

    legacy_identities: dict[int, dict[str, Any]] = {}
    for member in directory:
        if member.source_freelancer_id is None:
            continue
        source_id = int(member.source_freelancer_id)
        if source_id in source_to_hr:
            continue
        legacy_identities[source_id] = {
            "key": f"legacy:{source_id}",
            "id": source_id,
            "name": str(member.member_name or member.member_code or f"Member {source_id}"),
            "code": str(member.member_code or ""),
            "is_active": bool(member.is_active),
            "is_legacy": True,
        }
    return source_to_hr, placeholder_ids, hr_identities, legacy_identities, excluded_admin_ids


def _owner_key(
    assignment_id: int,
    *,
    source_to_hr: dict[int, int],
    placeholder_ids: set[int],
) -> tuple[str, int] | None:
    assignment_id = int(assignment_id)
    if assignment_id in source_to_hr:
        return "hr", int(source_to_hr[assignment_id])
    if assignment_id in placeholder_ids:
        return "legacy", assignment_id
    return "hr", assignment_id


def _task_records_by_member(database: Session) -> tuple[
    dict[str, dict[int, dict[str, Any]]],
    dict[str, dict[str, Any]],
    list[PortalTask],
    dict[int, PortalProject],
]:
    source_to_hr, placeholder_ids, hr_identities, legacy_identities, excluded_admin_ids = _member_identity_maps(database)
    identities: dict[str, dict[str, Any]] = {
        item["key"]: item for item in hr_identities.values()
    }
    identities.update({item["key"]: item for item in legacy_identities.values()})

    projects = {
        int(project.id): project
        for project in database.scalars(select(PortalProject)).all()
    }
    tasks = list(database.scalars(select(PortalTask)).all())
    task_map = {int(task.id): task for task in tasks}
    records_by_member: dict[str, dict[int, dict[str, Any]]] = defaultdict(dict)

    statement = select(
        PortalTaskAssignment.task_id,
        PortalTaskAssignment.freelancer_id,
    )
    for task_id, assignment_id in database.execute(statement).all():
        task = task_map.get(int(task_id))
        if task is None:
            continue
        owner = _owner_key(
            int(assignment_id),
            source_to_hr=source_to_hr,
            placeholder_ids=placeholder_ids,
        )
        if owner is None:
            continue
        owner_type, owner_id = owner
        if owner_type == "hr" and owner_id in excluded_admin_ids:
            continue
        key = f"{owner_type}:{owner_id}"
        if key not in identities:
            # Direct assignments can exist before a complete member directory
            # repair. Keep the record visible with a stable fallback label.
            profile = database.get(Freelancer, owner_id) if owner_type == "hr" else None
            identities[key] = {
                "key": key,
                "id": owner_id,
                "name": str(profile.full_name if profile else f"Member {owner_id}"),
                "code": str(profile.freelancer_code if profile else ""),
                "is_active": bool(profile.is_active) if profile else False,
                "is_legacy": owner_type == "legacy",
            }
        project = projects.get(int(task.project_id))
        records_by_member[key][int(task.id)] = {
            "task": task,
            "project": project,
            "completion_date": _completion_date(task),
            "days_difference": _days_difference(task),
        }

    # Keep active HR members visible even when they have no task history.
    for key, identity in identities.items():
        if identity.get("is_active"):
            records_by_member.setdefault(key, {})

    return records_by_member, identities, tasks, projects


def _quality_recommendation(metric: dict[str, Any]) -> str:
    if metric["rated_tasks"] == 0:
        return "No Quality Scores yet"
    average = float(metric["average_quality"])
    if average >= QUALITY_EXCELLENT_THRESHOLD:
        return "Excellent quality performance"
    if average >= QUALITY_STRONG_THRESHOLD:
        return "Consistently good quality"
    if average >= QUALITY_ACCEPTABLE_THRESHOLD:
        return "Acceptable with room to improve"
    return "Strengthen quality control"


def _task_recommendation(metric: dict[str, Any]) -> str:
    if metric["total_tasks"] == 0:
        return "No assigned tasks"
    if metric["total_tasks"] >= 10 and metric["completion_rate"] >= 70:
        return "High output with good completion"
    if metric["active_tasks"] >= 5:
        return "Currently carrying a high workload"
    if metric["completion_rate"] >= 70:
        return "Reliable task completion"
    return "Continue monitoring task progress"


def _speed_recommendation(metric: dict[str, Any]) -> str:
    if metric["measured_tasks"] == 0:
        return "No measurable completed tasks"
    average_days = float(metric["average_days"])
    if average_days <= -1 and metric["delivery_rate"] >= 90:
        return "Fast delivery; suitable for urgent tasks"
    if average_days <= 0:
        return "Usually on time or early"
    if average_days <= 1:
        return "Close to on time; continue improving"
    return "Delivery is often delayed"




def _overall_recommendation(metric: dict[str, Any]) -> str:
    if metric["overall_score"] is None:
        return "Complete both Quality and Speed records"
    score = float(metric["overall_score"])
    if score >= 88:
        return "Excellent overall performance"
    if score >= 80:
        return "Strong and dependable performance"
    if score >= 70:
        return "Good performance with room to improve"
    return "Prioritize quality and delivery improvement"


def _format_average_days(value: float, measured: int) -> str:
    if measured <= 0:
        return "—"
    value = float(value or 0)
    if abs(value) < 0.01:
        return "On time"
    if value < 0:
        return f"{abs(value):.1f} days early"
    return f"{value:.1f} days late"


def build_performance_dashboard(database: Session) -> dict[str, Any]:
    """Build all-time member leaderboard data for the Performance page."""
    records_by_member, identities, tasks, _projects = _task_records_by_member(database)
    member_metrics: list[dict[str, Any]] = []

    for key, task_records in records_by_member.items():
        identity = identities[key]
        records = list(task_records.values())
        relevant_records = [
            record for record in records
            if str(record["task"].status or "").upper() != "CANCELLED"
        ]
        total_tasks = len(relevant_records)
        completed_records = [
            record for record in relevant_records
            if str(record["task"].status or "").upper() == FINAL_COMPLETED_STATUS
        ]
        active_records = [
            record for record in relevant_records
            if str(record["task"].status or "").upper() not in CLOSED_TASK_STATUSES
        ]
        review_records = [
            record for record in relevant_records
            if str(record["task"].status or "").upper() == FOR_REVIEW_STATUS
        ]
        raw_scores = [
            score
            for record in relevant_records
            if (score := parse_quality_score(record["task"].quality_score)) is not None
        ]
        adjusted_scores = [calibrate_quality_score(score) for score in raw_scores]
        differences = [
            int(record["days_difference"])
            for record in completed_records
            if record["days_difference"] is not None
        ]
        early = sum(1 for value in differences if value < 0)
        on_time = sum(1 for value in differences if value == 0)
        late = sum(1 for value in differences if value > 0)
        measured = len(differences)
        rated = len(adjusted_scores)
        completed = len(completed_records)
        average_quality = sum(adjusted_scores) / rated if rated else 0.0
        average_days = sum(differences) / measured if measured else 0.0
        completion_rate = completed / total_tasks * 100 if total_tasks else 0.0
        delivery_rate = (early + on_time) / measured * 100 if measured else 0.0
        coverage = rated / total_tasks * 100 if total_tasks else 0.0

        overall_score = (
            average_quality * OVERALL_QUALITY_WEIGHT
            + delivery_rate * OVERALL_SPEED_WEIGHT
            if rated and measured
            else None
        )

        metric: dict[str, Any] = {
            **identity,
            "total_tasks": total_tasks,
            "completed_tasks": completed,
            "for_review_tasks": len(review_records),
            "active_tasks": len(active_records),
            "rated_tasks": rated,
            "average_quality": round(average_quality, 1),
            "highest_quality": round(max(adjusted_scores), 1) if adjusted_scores else 0.0,
            "lowest_quality": round(min(adjusted_scores), 1) if adjusted_scores else 0.0,
            "quality_coverage": round(coverage, 1),
            "measured_tasks": measured,
            "early_tasks": early,
            "on_time_tasks": on_time,
            "late_tasks": late,
            "average_days": round(average_days, 2),
            "average_days_label": _format_average_days(average_days, measured),
            "delivery_rate": round(delivery_rate, 1),
            "completion_rate": round(completion_rate, 1),
            "overall_score": round(overall_score, 1) if overall_score is not None else None,
        }
        metric["quality_recommendation"] = _quality_recommendation(metric)
        metric["task_recommendation"] = _task_recommendation(metric)
        metric["speed_recommendation"] = _speed_recommendation(metric)
        metric["overall_recommendation"] = _overall_recommendation(metric)
        member_metrics.append(metric)

    overall_ranked = sorted(
        member_metrics,
        key=lambda item: (
            item["overall_score"] is None,
            -(item["overall_score"] if item["overall_score"] is not None else -1),
            -item["average_quality"],
            -item["delivery_rate"],
            str(item["name"]).casefold(),
        ),
    )
    quality_ranked = sorted(
        member_metrics,
        key=lambda item: (
            item["rated_tasks"] == 0,
            -item["average_quality"],
            -item["rated_tasks"],
            -item["total_tasks"],
            str(item["name"]).casefold(),
        ),
    )
    task_ranked = sorted(
        member_metrics,
        key=lambda item: (
            -item["total_tasks"],
            -item["completed_tasks"],
            -item["completion_rate"],
            str(item["name"]).casefold(),
        ),
    )
    speed_ranked = sorted(
        member_metrics,
        key=lambda item: (
            item["measured_tasks"] == 0,
            item["average_days"],
            -item["delivery_rate"],
            -item["measured_tasks"],
            str(item["name"]).casefold(),
        ),
    )

    unique_relevant_tasks = [
        task for task in tasks if str(task.status or "").upper() != "CANCELLED"
    ]
    unique_scores = [
        score
        for task in unique_relevant_tasks
        if (score := parse_quality_score(task.quality_score)) is not None
    ]
    unique_adjusted = [calibrate_quality_score(score) for score in unique_scores]
    unique_completed = [
        task for task in unique_relevant_tasks
        if str(task.status or "").upper() == FINAL_COMPLETED_STATUS
    ]
    unique_differences = [
        difference
        for task in unique_completed
        if (difference := _days_difference(task)) is not None
    ]

    eligible_overall = [
        item for item in member_metrics if item["overall_score"] is not None
    ]
    overall_summary = {
        "leader": overall_ranked[0]["name"] if overall_ranked and overall_ranked[0]["overall_score"] is not None else "—",
        "team_average": round(
            sum(float(item["overall_score"]) for item in eligible_overall) / len(eligible_overall),
            1,
        ) if eligible_overall else None,
        "eligible_members": len(eligible_overall),
        "total_members": len(member_metrics),
    }

    quality_summary = {
        "leader": quality_ranked[0]["name"] if quality_ranked and quality_ranked[0]["rated_tasks"] else "—",
        "team_average": round(sum(unique_adjusted) / len(unique_adjusted), 1) if unique_adjusted else None,
        "rated_tasks": len(unique_adjusted),
        "coverage": round(len(unique_adjusted) / len(unique_relevant_tasks) * 100, 1) if unique_relevant_tasks else 0.0,
    }
    task_summary = {
        "leader": task_ranked[0]["name"] if task_ranked and task_ranked[0]["total_tasks"] else "—",
        "total_tasks": len(unique_relevant_tasks),
        "completed_tasks": len(unique_completed),
        "active_tasks": sum(
            1 for task in unique_relevant_tasks
            if str(task.status or "").upper() not in CLOSED_TASK_STATUSES
        ),
    }
    delivery_summary = {
        "leader": speed_ranked[0]["name"] if speed_ranked and speed_ranked[0]["measured_tasks"] else "—",
        "average_days": round(sum(unique_differences) / len(unique_differences), 2) if unique_differences else None,
        "delivery_rate": round(sum(1 for value in unique_differences if value <= 0) / len(unique_differences) * 100, 1) if unique_differences else None,
        "measured_tasks": len(unique_differences),
    }

    return {
        "overall_ranked": overall_ranked,
        "quality_ranked": quality_ranked,
        "task_ranked": task_ranked,
        "speed_ranked": speed_ranked,
        "overall_summary": overall_summary,
        "quality_summary": quality_summary,
        "task_summary": task_summary,
        "delivery_summary": delivery_summary,
        "specialty_recommendations": build_specialty_recommendations(database),
        "overall_formula": "Overall Performance = 40% Speed + 60% Quality",
        "quality_formula": "Quality Score as calculated",
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def _parse_month(month_key: str) -> date:
    try:
        return datetime.strptime(str(month_key or ""), "%Y-%m").date().replace(day=1)
    except ValueError:
        return date.today().replace(day=1)


def _add_months(value: date, months: int) -> date:
    month_index = value.year * 12 + (value.month - 1) + months
    year, month_zero = divmod(month_index, 12)
    return date(year, month_zero + 1, 1)


def _period_bounds(period: str, month_key: str) -> tuple[str, date | None, date | None, str]:
    normalized = str(period or "month").strip().lower()
    selected_month = _parse_month(month_key)
    if normalized == "12m":
        start = _add_months(selected_month, -11)
        end = _add_months(selected_month, 1)
        return "12m", start, end, f"{start.strftime('%b %Y')} – {selected_month.strftime('%b %Y')}"
    if normalized == "all":
        return "all", None, None, "All time"
    start = selected_month
    end = _add_months(selected_month, 1)
    return "month", start, end, selected_month.strftime("%B %Y")


def _in_period(value: Optional[date], start: Optional[date], end: Optional[date]) -> bool:
    if value is None:
        return False
    if start is not None and value < start:
        return False
    if end is not None and value >= end:
        return False
    return True


def _bucket_definitions(
    *,
    period: str,
    start: Optional[date],
    end: Optional[date],
    relevant_dates: Iterable[date],
) -> list[dict[str, Any]]:
    if period == "month" and start is not None and end is not None:
        buckets: list[dict[str, Any]] = []
        cursor = start
        while cursor < end:
            buckets.append({
                "key": cursor.isoformat(),
                "label": cursor.strftime("%d %b"),
                "start": cursor,
                "end": cursor + timedelta(days=1),
            })
            cursor += timedelta(days=1)
        return buckets

    if period == "12m" and start is not None and end is not None:
        buckets = []
        cursor = start
        while cursor < end:
            next_month = _add_months(cursor, 1)
            buckets.append({
                "key": cursor.strftime("%Y-%m"),
                "label": cursor.strftime("%b %Y"),
                "start": cursor,
                "end": next_month,
            })
            cursor = next_month
        return buckets

    dates = sorted(set(relevant_dates))
    first = (dates[0].replace(day=1) if dates else date.today().replace(day=1))
    last = (dates[-1].replace(day=1) if dates else date.today().replace(day=1))
    buckets = []
    cursor = first
    while cursor <= last:
        next_month = _add_months(cursor, 1)
        buckets.append({
            "key": cursor.strftime("%Y-%m"),
            "label": cursor.strftime("%b %Y"),
            "start": cursor,
            "end": next_month,
        })
        cursor = next_month
    return buckets


def _bucket_key(value: date, period: str) -> str:
    return value.isoformat() if period == "month" else value.strftime("%Y-%m")


def build_project_reports(
    database: Session,
    *,
    period: str = "month",
    month_key: str = "",
) -> dict[str, Any]:
    """Build period-based member, project, and trend reporting."""
    normalized_period, start, end, period_label = _period_bounds(period, month_key)
    selected_month = _parse_month(month_key)

    records_by_member, identities, tasks, projects = _task_records_by_member(database)
    completed_tasks = [
        task for task in tasks
        if str(task.status or "").upper() == FINAL_COMPLETED_STATUS
        and _in_period(_completion_date(task), start, end)
    ]
    active_tasks = [
        task for task in tasks
        if str(task.status or "").upper() not in CLOSED_TASK_STATUSES
    ]
    today = date.today()
    overdue_tasks = [
        task for task in active_tasks
        if _as_date(task.due_date) is not None and _as_date(task.due_date) < today
    ]

    completed_task_ids = {int(task.id) for task in completed_tasks}
    member_rows: list[dict[str, Any]] = []

    daily_rows = list(database.scalars(select(DailyTask)).all())
    daily_in_period = [
        row for row in daily_rows if _in_period(_as_date(row.task_date), start, end)
    ]
    minutes_by_hr: dict[int, int] = defaultdict(int)
    for row in daily_in_period:
        minutes_by_hr[int(row.freelancer_id)] += max(0, int(row.minutes_spent or 0))

    for key, task_records in records_by_member.items():
        identity = identities[key]
        records = list(task_records.values())
        delivered = [record for record in records if int(record["task"].id) in completed_task_ids]
        active = [
            record for record in records
            if str(record["task"].status or "").upper() not in CLOSED_TASK_STATUSES
        ]
        scores = [
            score for record in delivered
            if (score := parse_quality_score(record["task"].quality_score)) is not None
        ]
        adjusted = [calibrate_quality_score(score) for score in scores]
        differences = [
            int(record["days_difference"])
            for record in delivered if record["days_difference"] is not None
        ]
        overdue = sum(
            1 for record in active
            if _as_date(record["task"].due_date) is not None
            and _as_date(record["task"].due_date) < today
        )
        owner_minutes = minutes_by_hr.get(int(identity["id"]), 0) if not identity.get("is_legacy") else 0
        if not delivered and not active and owner_minutes == 0 and not identity.get("is_active"):
            continue
        member_rows.append({
            **identity,
            "delivered_tasks": len(delivered),
            "active_tasks": len(active),
            "overdue_tasks": overdue,
            "rated_tasks": len(adjusted),
            "average_quality": round(sum(adjusted) / len(adjusted), 1) if adjusted else None,
            "measured_tasks": len(differences),
            "on_time_rate": round(sum(1 for value in differences if value <= 0) / len(differences) * 100, 1) if differences else None,
            "average_days": round(sum(differences) / len(differences), 2) if differences else None,
            "average_days_label": _format_average_days(
                sum(differences) / len(differences) if differences else 0,
                len(differences),
            ),
            "logged_minutes": owner_minutes,
            "logged_hours": round(owner_minutes / 60, 1),
        })

    member_rows.sort(
        key=lambda item: (
            -item["delivered_tasks"],
            -(item["on_time_rate"] if item["on_time_rate"] is not None else -1),
            -(item["average_quality"] if item["average_quality"] is not None else -1),
            str(item["name"]).casefold(),
        )
    )
    for index, row in enumerate(member_rows, start=1):
        row["rank"] = index

    project_minutes: dict[int, int] = defaultdict(int)
    project_name_lookup = {
        " ".join(str(project.name or "").casefold().split()): int(project.id)
        for project in projects.values()
    }
    project_code_lookup = {
        " ".join(str(project.project_code or "").casefold().split()): int(project.id)
        for project in projects.values()
    }
    task_to_project = {int(task.id): int(task.project_id) for task in tasks}
    freelancer_lookup = {
        int(row.id): row for row in database.scalars(select(Freelancer)).all()
    }
    monthly_project_minutes: dict[tuple[str, int], int] = defaultdict(int)
    monthly_project_member_minutes: dict[tuple[str, int], dict[int, int]] = defaultdict(lambda: defaultdict(int))

    for row in daily_in_period:
        project_id: Optional[int] = None
        if row.portal_task_id is not None:
            project_id = task_to_project.get(int(row.portal_task_id))
        if project_id is None:
            project_id = project_code_lookup.get(
                " ".join(str(row.project_code or "").casefold().split())
            )
        if project_id is None:
            project_id = project_name_lookup.get(
                " ".join(str(row.project_name or "").casefold().split())
            )
        if project_id is not None:
            minutes = max(0, int(row.minutes_spent or 0))
            project_minutes[project_id] += minutes
            task_date = _as_date(row.task_date)
            if task_date is not None:
                monthly_key = task_date.strftime("%Y-%m")
                monthly_project_minutes[(monthly_key, project_id)] += minutes
                monthly_project_member_minutes[(monthly_key, project_id)][int(row.freelancer_id)] += minutes

    monthly_project_time_rows: list[dict[str, Any]] = []
    for (monthly_key, project_id), total_minutes in monthly_project_minutes.items():
        project = projects.get(project_id)
        if project is None:
            continue
        members = []
        for freelancer_id, minutes in monthly_project_member_minutes[(monthly_key, project_id)].items():
            freelancer = freelancer_lookup.get(freelancer_id)
            members.append({
                "freelancer_id": freelancer_id,
                "name": str(getattr(freelancer, "full_name", None) or f"Member {freelancer_id}"),
                "code": str(getattr(freelancer, "freelancer_code", None) or ""),
                "minutes": minutes,
                "hours": round(minutes / 60, 2),
                "label": f"{minutes // 60}h {minutes % 60:02d}m",
            })
        members.sort(key=lambda item: (-item["minutes"], item["name"].casefold()))
        monthly_project_time_rows.append({
            "month": monthly_key,
            "project_id": project_id,
            "project_name": str(project.name or project.project_code or f"Project {project_id}"),
            "project_code": str(project.project_code or ""),
            "total_minutes": total_minutes,
            "total_hours": round(total_minutes / 60, 2),
            "total_label": f"{total_minutes // 60}h {total_minutes % 60:02d}m",
            "members": members,
        })
    monthly_project_time_rows.sort(key=lambda item: item["project_name"].casefold())
    monthly_project_time_rows.sort(key=lambda item: item["month"], reverse=True)

    tasks_by_project: dict[int, list[PortalTask]] = defaultdict(list)
    for task in tasks:
        tasks_by_project[int(task.project_id)].append(task)

    project_rows: list[dict[str, Any]] = []
    for project_id, project in projects.items():
        project_tasks = tasks_by_project.get(project_id, [])
        delivered = [task for task in project_tasks if int(task.id) in completed_task_ids]
        active = [
            task for task in project_tasks
            if str(task.status or "").upper() not in CLOSED_TASK_STATUSES
        ]
        scores = [
            score for task in delivered
            if (score := parse_quality_score(task.quality_score)) is not None
        ]
        adjusted = [calibrate_quality_score(score) for score in scores]
        differences = [
            difference for task in delivered
            if (difference := _days_difference(task)) is not None
        ]
        overdue = sum(
            1 for task in active
            if _as_date(task.due_date) is not None and _as_date(task.due_date) < today
        )
        minutes = project_minutes.get(project_id, 0)
        if not delivered and not active and minutes == 0 and normalized_period != "all":
            continue
        project_rows.append({
            "id": project_id,
            "name": str(project.name or project.project_code),
            "code": str(project.project_code or ""),
            "project_engineer": str(project.project_engineer or "—"),
            "discipline": str(project.discipline or "—"),
            "status": str(project.status or "ACTIVE"),
            "progress": max(0, min(100, int(project.progress or 0))),
            "delivered_tasks": len(delivered),
            "active_tasks": len(active),
            "overdue_tasks": overdue,
            "rated_tasks": len(adjusted),
            "average_quality": round(sum(adjusted) / len(adjusted), 1) if adjusted else None,
            "measured_tasks": len(differences),
            "on_time_rate": round(sum(1 for value in differences if value <= 0) / len(differences) * 100, 1) if differences else None,
            "logged_minutes": minutes,
            "logged_hours": round(minutes / 60, 1),
        })
    project_rows.sort(
        key=lambda item: (
            -item["delivered_tasks"],
            -item["active_tasks"],
            item["overdue_tasks"],
            str(item["name"]).casefold(),
        )
    )

    unique_scores = [
        score for task in completed_tasks
        if (score := parse_quality_score(task.quality_score)) is not None
    ]
    adjusted_scores = [calibrate_quality_score(score) for score in unique_scores]
    unique_differences = [
        difference for task in completed_tasks
        if (difference := _days_difference(task)) is not None
    ]

    relevant_dates = [
        value for task in completed_tasks
        if (value := _completion_date(task)) is not None
    ] + [
        value for row in daily_in_period
        if (value := _as_date(row.task_date)) is not None
    ]
    if normalized_period == "all":
        # Include all dated task/daily history so empty months remain visible.
        relevant_dates = [
            value for task in tasks if (value := _completion_date(task)) is not None
        ] + [
            value for row in daily_rows if (value := _as_date(row.task_date)) is not None
        ]

    bucket_defs = _bucket_definitions(
        period=normalized_period,
        start=start,
        end=end,
        relevant_dates=relevant_dates,
    )
    bucket_data: dict[str, dict[str, Any]] = {
        bucket["key"]: {
            "label": bucket["label"],
            "delivered": 0,
            "quality_values": [],
            "on_time": 0,
            "measured": 0,
            "minutes": 0,
        }
        for bucket in bucket_defs
    }

    trend_completed_tasks = completed_tasks if normalized_period != "all" else [
        task for task in tasks if str(task.status or "").upper() == FINAL_COMPLETED_STATUS
    ]
    trend_daily_rows = daily_in_period if normalized_period != "all" else daily_rows

    for task in trend_completed_tasks:
        completed = _completion_date(task)
        if completed is None:
            continue
        key = _bucket_key(completed, normalized_period)
        bucket = bucket_data.get(key)
        if bucket is None:
            continue
        bucket["delivered"] += 1
        score = parse_quality_score(task.quality_score)
        if score is not None:
            bucket["quality_values"].append(calibrate_quality_score(score))
        difference = _days_difference(task)
        if difference is not None:
            bucket["measured"] += 1
            if difference <= 0:
                bucket["on_time"] += 1

    for row in trend_daily_rows:
        task_date = _as_date(row.task_date)
        if task_date is None:
            continue
        key = _bucket_key(task_date, normalized_period)
        bucket = bucket_data.get(key)
        if bucket is not None:
            bucket["minutes"] += max(0, int(row.minutes_spent or 0))

    trend = []
    for bucket_def in bucket_defs:
        bucket = bucket_data[bucket_def["key"]]
        quality_values = bucket.pop("quality_values")
        trend.append({
            "label": bucket["label"],
            "delivered": bucket["delivered"],
            "quality": round(sum(quality_values) / len(quality_values), 1) if quality_values else None,
            "on_time": round(bucket["on_time"] / bucket["measured"] * 100, 1) if bucket["measured"] else None,
            "hours": round(bucket["minutes"] / 60, 1),
        })

    summary = {
        "delivered_tasks": len(completed_tasks),
        "active_tasks": len(active_tasks),
        "overdue_tasks": len(overdue_tasks),
        "quality_average": round(sum(adjusted_scores) / len(adjusted_scores), 1) if adjusted_scores else None,
        "rated_tasks": len(adjusted_scores),
        "on_time_rate": round(sum(1 for value in unique_differences if value <= 0) / len(unique_differences) * 100, 1) if unique_differences else None,
        "measured_tasks": len(unique_differences),
        "logged_hours": round(sum(max(0, int(row.minutes_spent or 0)) for row in daily_in_period) / 60, 1),
    }

    return {
        "period": normalized_period,
        "selected_month": selected_month.strftime("%Y-%m"),
        "period_label": period_label,
        "summary": summary,
        "trend": trend,
        "member_rows": member_rows,
        "project_rows": project_rows,
        "monthly_project_time_rows": monthly_project_time_rows,
        "top_member_output": [
            {"label": row["name"], "value": row["delivered_tasks"]}
            for row in member_rows if row["delivered_tasks"] > 0
        ][:10],
        "top_project_output": [
            {"label": row["name"], "value": row["delivered_tasks"]}
            for row in project_rows if row["delivered_tasks"] > 0
        ][:10],
        "specialty_recommendations": build_specialty_recommendations(database),
        "overall_formula": "Overall Performance = 40% Speed + 60% Quality",
        "quality_formula": "Quality Score as calculated",
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
