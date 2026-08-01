"""Restore PostgreSQL-native project-member directory and HR mapping.

Revision ID: 20260801_0003
Revises: 20260801_0002

This migration is additive. It does not delete or rewrite project, task, HR,
attendance, leave, DTR, overtime, compensatory-credit, or finance records.
"""
from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any

from alembic import op
import sqlalchemy as sa

revision = "20260801_0003"
down_revision = "20260801_0002"
branch_labels = None
depends_on = None


def _normalize_name(value: Any) -> str:
    return " ".join(str(value or "").strip().split()).casefold()[:200]


def _clean(value: Any, limit: int) -> str:
    return " ".join(str(value or "").strip().split())[:limit]


def _active(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return True
    return str(value).strip().casefold() not in {
        "0", "false", "no", "inactive", "disabled", "archived",
    }


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _create_table_if_missing(bind) -> None:
    inspector = sa.inspect(bind)
    if "project_member_directory" in inspector.get_table_names():
        return

    op.create_table(
        "project_member_directory",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_key", sa.String(length=160), nullable=False),
        sa.Column("member_code", sa.String(length=80), nullable=True),
        sa.Column("member_name", sa.String(length=200), nullable=False),
        sa.Column("normalized_member_name", sa.String(length=200), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "source_freelancer_id",
            sa.Integer(),
            sa.ForeignKey("freelancers.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "freelancer_id",
            sa.Integer(),
            sa.ForeignKey("freelancers.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "mapped_by_admin_id",
            sa.Integer(),
            sa.ForeignKey("hr_admin_accounts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("mapped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source_key", name="uq_project_member_source_key"),
        sa.UniqueConstraint(
            "normalized_member_name",
            name="uq_project_member_normalized_name",
        ),
        sa.UniqueConstraint(
            "source_freelancer_id",
            name="uq_project_member_source_freelancer",
        ),
    )
    op.create_index(
        "ix_project_member_freelancer",
        "project_member_directory",
        ["freelancer_id"],
        unique=False,
    )
    op.create_index(
        "ix_project_member_source_freelancer",
        "project_member_directory",
        ["source_freelancer_id"],
        unique=False,
    )
    op.create_index(
        "ix_project_member_active_mapping",
        "project_member_directory",
        ["is_active", "freelancer_id"],
        unique=False,
    )


def _backfill(bind) -> None:
    metadata = sa.MetaData()
    metadata.reflect(bind=bind)
    tables = metadata.tables
    directory = tables["project_member_directory"]
    freelancers = tables["freelancers"]

    current_rows = bind.execute(sa.select(directory)).mappings().all()
    by_normalized = {
        str(row["normalized_member_name"]): dict(row) for row in current_rows
    }
    source_keys = {str(row["source_key"]) for row in current_rows}

    legacy_rows = bind.execute(
        sa.select(
            freelancers.c.id,
            freelancers.c.freelancer_code,
            freelancers.c.full_name,
            freelancers.c.email,
            freelancers.c.is_active,
        ).where(freelancers.c.freelancer_code.like("LEGACY-%"))
    ).mappings().all()
    legacy_by_normalized = {
        _normalize_name(row["full_name"]): dict(row)
        for row in legacy_rows
        if _normalize_name(row["full_name"])
    }
    legacy_freelancer_ids = {int(row["id"]) for row in legacy_rows}

    def upsert_member(
        *,
        source_key: str,
        member_name: Any,
        member_code: Any = None,
        email: Any = None,
        is_active: Any = True,
        source_freelancer_id: int | None = None,
        freelancer_id: int | None = None,
    ) -> None:
        name = _clean(member_name, 200)
        normalized = _normalize_name(name)
        if not normalized:
            return
        now = _now()
        existing = by_normalized.get(normalized)
        if existing is not None:
            values: dict[str, Any] = {"updated_at": now}
            if not existing.get("member_code") and member_code:
                values["member_code"] = _clean(member_code, 80)
            if not existing.get("email") and email:
                values["email"] = _clean(email, 320)
            if existing.get("source_freelancer_id") is None and source_freelancer_id:
                values["source_freelancer_id"] = int(source_freelancer_id)
            if existing.get("freelancer_id") is None and freelancer_id:
                values["freelancer_id"] = int(freelancer_id)
                values["mapped_at"] = now
            if is_active is not None:
                values["is_active"] = _active(is_active)
            bind.execute(
                directory.update()
                .where(directory.c.id == existing["id"])
                .values(**values)
            )
            existing.update(values)
            return

        unique_source_key = source_key[:160]
        if unique_source_key in source_keys:
            suffix = 2
            base = unique_source_key[:150]
            while f"{base}:{suffix}" in source_keys:
                suffix += 1
            unique_source_key = f"{base}:{suffix}"

        values = {
            "source_key": unique_source_key,
            "member_code": _clean(member_code, 80) or None,
            "member_name": name,
            "normalized_member_name": normalized,
            "email": _clean(email, 320) or None,
            "is_active": _active(is_active),
            "source_freelancer_id": int(source_freelancer_id)
            if source_freelancer_id
            else None,
            "freelancer_id": int(freelancer_id) if freelancer_id else None,
            "mapped_by_admin_id": None,
            "mapped_at": now if freelancer_id else None,
            "created_at": now,
            "updated_at": now,
        }
        result = bind.execute(directory.insert().values(**values))
        new_id = result.inserted_primary_key[0]
        values["id"] = new_id
        by_normalized[normalized] = values
        source_keys.add(unique_source_key)

    # Preserve prior mapping records when an earlier portal version created them.
    if "project_source_members" in tables:
        source_members = tables["project_source_members"]
        for row in bind.execute(sa.select(source_members)).mappings().all():
            name = row.get("source_member_name")
            normalized = _normalize_name(name)
            legacy = legacy_by_normalized.get(normalized)
            upsert_member(
                source_key=f"project-source-member:{row['id']}",
                member_name=name,
                member_code=f"SOURCE-{row['id']}",
                is_active=row.get("is_active", True),
                source_freelancer_id=(legacy or {}).get("id"),
                freelancer_id=(
                    int(row["freelancer_id"])
                    if row.get("freelancer_id") is not None
                    and int(row["freelancer_id"]) not in legacy_freelancer_ids
                    else None
                ),
            )

    # Some converted PostgreSQL databases retained the original members table.
    # Detect common legacy column names and import it without assuming one schema.
    if "members" in tables:
        members = tables["members"]
        column_names = set(members.c.keys())
        id_name = next((x for x in ("id", "member_id") if x in column_names), None)
        person_name = next(
            (x for x in ("name", "full_name", "member_name") if x in column_names),
            None,
        )
        email_name = next((x for x in ("email", "email_address") if x in column_names), None)
        active_name = next((x for x in ("is_active", "active", "status") if x in column_names), None)
        code_name = next((x for x in ("member_code", "code") if x in column_names), None)
        if id_name and person_name:
            for row in bind.execute(sa.select(members)).mappings().all():
                normalized = _normalize_name(row.get(person_name))
                legacy = legacy_by_normalized.get(normalized)
                upsert_member(
                    source_key=f"members:{row.get(id_name)}",
                    member_name=row.get(person_name),
                    member_code=row.get(code_name) if code_name else f"MEMBER-{row.get(id_name)}",
                    email=row.get(email_name) if email_name else None,
                    is_active=row.get(active_name) if active_name else True,
                    source_freelancer_id=(legacy or {}).get("id"),
                )

    # The Release 20.5 migration encoded old members as LEGACY-* freelancer
    # placeholders. Restore their separate project-member identities here.
    for row in legacy_rows:
        match = re.search(r"(\d+)$", str(row["freelancer_code"] or ""))
        legacy_id = match.group(1) if match else str(row["id"])
        upsert_member(
            source_key=f"legacy-member:{legacy_id}",
            member_name=row["full_name"],
            member_code=row["freelancer_code"],
            email=row["email"],
            is_active=row["is_active"],
            source_freelancer_id=row["id"],
        )

    # Final fallback for historical sync rows that have a member name but no
    # source-member record or LEGACY placeholder.
    if "synced_project_tasks" in tables:
        synced_tasks = tables["synced_project_tasks"]
        statement = sa.select(
            synced_tasks.c.source_member_name,
            synced_tasks.c.normalized_member_name,
        ).distinct()
        for index, row in enumerate(bind.execute(statement).mappings().all(), 1):
            name = row.get("source_member_name")
            normalized = _normalize_name(name)
            legacy = legacy_by_normalized.get(normalized)
            upsert_member(
                source_key=f"synced-member:{index}:{normalized[:100]}",
                member_name=name,
                member_code=None,
                source_freelancer_id=(legacy or {}).get("id"),
            )


def upgrade() -> None:
    bind = op.get_bind()
    _create_table_if_missing(bind)
    _backfill(bind)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "project_member_directory" not in inspector.get_table_names():
        return
    op.drop_table("project_member_directory")
