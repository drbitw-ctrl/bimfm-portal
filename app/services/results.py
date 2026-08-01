"""Language-neutral service result types."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ServiceResult:
    ok: bool
    message_key: str
    redirect_month: str | None = None

    @classmethod
    def success(cls, message_key: str, redirect_month: str | None = None) -> "ServiceResult":
        return cls(True, message_key, redirect_month)

    @classmethod
    def failure(cls, message_key: str, redirect_month: str | None = None) -> "ServiceResult":
        return cls(False, message_key, redirect_month)
