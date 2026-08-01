"""Store project engineer names independently from portal staff accounts.

Revision ID: 20260801_0004
Revises: 20260801_0003

The migration is additive. It does not delete or rewrite project assignments,
member mappings, attendance, DTR, leave, overtime, or finance records.
"""
from __future__ import annotations

import re

from alembic import op
import sqlalchemy as sa

revision = "20260801_0004"
down_revision = "20260801_0003"
branch_labels = None
depends_on = None

_ENGINEER_PATTERN = re.compile(r"(?:^|\n)Legacy engineer:\s*([^\n]+)", re.IGNORECASE)


def _clean_engineer(value: object) -> str:
    return " ".join(str(value or "").strip().split())[:200]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("portal_projects")}
    if "project_engineer" not in columns:
        with op.batch_alter_table("portal_projects") as batch_op:
            batch_op.add_column(sa.Column("project_engineer", sa.String(length=200), nullable=True))

    # Recover engineer names from imported task metadata where possible. The
    # text remains untouched; this only gives existing projects a proper field.
    project_rows = bind.execute(sa.text("SELECT id, project_engineer FROM portal_projects")).mappings().all()
    for project in project_rows:
        if _clean_engineer(project.get("project_engineer")):
            continue
        descriptions = bind.execute(
            sa.text(
                "SELECT description FROM portal_tasks "
                "WHERE project_id = :project_id AND description IS NOT NULL "
                "ORDER BY id"
            ),
            {"project_id": project["id"]},
        ).scalars().all()
        names: list[str] = []
        for description in descriptions:
            match = _ENGINEER_PATTERN.search(str(description or ""))
            if not match:
                continue
            name = _clean_engineer(match.group(1))
            if name and name.casefold() not in {item.casefold() for item in names}:
                names.append(name)
        if names:
            bind.execute(
                sa.text(
                    "UPDATE portal_projects SET project_engineer = :engineer "
                    "WHERE id = :project_id"
                ),
                {
                    "engineer": " / ".join(names)[:200],
                    "project_id": project["id"],
                },
            )


def downgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("portal_projects")}
    if "project_engineer" in columns:
        with op.batch_alter_table("portal_projects") as batch_op:
            batch_op.drop_column("project_engineer")
