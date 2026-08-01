from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common import utc_now


class ProjectMember(Base):
    """Project-side member identity imported into PostgreSQL.

    A project member is deliberately separate from an HR freelancer profile.
    ``source_freelancer_id`` points to the temporary ``LEGACY-*`` placeholder
    created by the original SQLite migration so existing project/task foreign
    keys remain intact. ``freelancer_id`` is the optional HR account mapping.
    """

    __tablename__ = "project_member_directory"
    __table_args__ = (
        UniqueConstraint("source_key", name="uq_project_member_source_key"),
        UniqueConstraint(
            "normalized_member_name",
            name="uq_project_member_normalized_name",
        ),
        Index("ix_project_member_freelancer", "freelancer_id"),
        Index("ix_project_member_source_freelancer", "source_freelancer_id"),
        Index("ix_project_member_active_mapping", "is_active", "freelancer_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_key: Mapped[str] = mapped_column(String(160), nullable=False)
    member_code: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    member_name: Mapped[str] = mapped_column(String(200), nullable=False)
    normalized_member_name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(320), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    source_freelancer_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("freelancers.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )
    freelancer_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("freelancers.id", ondelete="SET NULL"),
        nullable=True,
    )
    mapped_by_admin_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("hr_admin_accounts.id", ondelete="SET NULL"),
        nullable=True,
    )
    mapped_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
