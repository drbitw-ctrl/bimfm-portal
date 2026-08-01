"""Shared SQLAlchemy repository primitives.

Repositories own persistence operations. Services own business rules and decide
when a unit of work should be committed or rolled back.
"""
from __future__ import annotations

from typing import Any, Generic, TypeVar

ModelT = TypeVar("ModelT")


class SQLAlchemyRepository(Generic[ModelT]):
    def __init__(self, session: Any):
        self.session = session

    def get(self, model: type[ModelT], record_id: int) -> ModelT | None:
        return self.session.get(model, record_id)

    def add(self, record: ModelT) -> ModelT:
        self.session.add(record)
        return record

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()

    def flush(self) -> None:
        self.session.flush()
