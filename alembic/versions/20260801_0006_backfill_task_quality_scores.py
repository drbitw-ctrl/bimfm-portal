"""Backfill imported task quality scores from preserved migration metadata.

Revision ID: 20260801_0006
Revises: 20260801_0005
Create Date: 2026-08-01

This migration is data-preserving and idempotent. It only fills a null
``portal_tasks.quality_score`` when the same task description contains a valid
historical marker such as ``Legacy quality score: 90``. Existing manually
entered quality scores are never overwritten.
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Optional

from alembic import op
import sqlalchemy as sa

revision = "20260801_0006"
down_revision = "20260801_0005"
branch_labels = None
depends_on = None

_QUALITY_PATTERN = re.compile(
    r"(?:^|\n)\s*legacy\s+quality\s+score\s*:\s*"
    r"([0-9]+(?:\.[0-9]+)?)\s*%?\s*(?=\n|$)",
    re.IGNORECASE,
)


def _extract_legacy_quality_score(description: object) -> Optional[int]:
    """Return a valid whole-number legacy score without guessing or rounding."""
    match = _QUALITY_PATTERN.search(str(description or ""))
    if not match:
        return None
    try:
        value = Decimal(match.group(1))
    except (InvalidOperation, ValueError):
        return None
    if value != value.to_integral_value():
        return None
    score = int(value)
    return score if 1 <= score <= 100 else None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "portal_tasks" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("portal_tasks")}
    if "quality_score" not in columns or "description" not in columns:
        return

    rows = bind.execute(
        sa.text(
            "SELECT id, description FROM portal_tasks "
            "WHERE quality_score IS NULL AND description IS NOT NULL"
        )
    ).mappings().all()

    for row in rows:
        score = _extract_legacy_quality_score(row.get("description"))
        if score is None:
            continue
        bind.execute(
            sa.text(
                "UPDATE portal_tasks SET quality_score = :quality_score "
                "WHERE id = :task_id AND quality_score IS NULL"
            ),
            {"quality_score": score, "task_id": row["id"]},
        )


def downgrade() -> None:
    # The historical source marker remains in the task description, but a
    # downgrade must not erase a score that could have been edited after the
    # upgrade. This data backfill is therefore intentionally non-destructive.
    return
