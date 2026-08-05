"""Canonical member selectors for HR and administrative workflows.

Legacy imported identities may remain in integration tables for traceability, but
user-facing HR selectors must use only active freelancers with an active portal
account.  This prevents duplicate or unmapped legacy names from appearing in
attendance, overtime, payroll, and other personnel workflows.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Freelancer, FreelancerAccount


def active_freelancers_statement():
    """Return the canonical query for active, account-linked freelancers."""
    return (
        select(Freelancer)
        .join(
            FreelancerAccount,
            FreelancerAccount.freelancer_id == Freelancer.id,
        )
        .where(
            Freelancer.is_active.is_(True),
            FreelancerAccount.is_active.is_(True),
        )
        .order_by(Freelancer.full_name.asc(), Freelancer.id.asc())
    )


def get_active_freelancers(database: Session) -> list[Freelancer]:
    """Return active freelancers that have active BIMFM Portal accounts."""
    return list(database.scalars(active_freelancers_statement()).unique().all())


def get_active_freelancer(database: Session, freelancer_id: int) -> Freelancer | None:
    """Return one active, account-linked freelancer, or ``None``."""
    statement = active_freelancers_statement().where(Freelancer.id == freelancer_id)
    return database.scalar(statement)
