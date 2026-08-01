from __future__ import annotations

import os
import re
from datetime import datetime, timezone

from sqlalchemy import func, select

from app.database import SessionLocal
from app.models.identity import HRAdminAccount
from app.security import hash_password


USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9._-]{3,80}$")


def required_environment_value(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def main() -> int:
    username = required_environment_value(
        "BIMFM_RESET_ADMIN_USERNAME"
    ).lower()
    display_name = required_environment_value(
        "BIMFM_RESET_ADMIN_DISPLAY_NAME"
    )
    password = required_environment_value(
        "BIMFM_RESET_ADMIN_PASSWORD"
    )

    if not USERNAME_PATTERN.fullmatch(username):
        raise SystemExit(
            "BIMFM_RESET_ADMIN_USERNAME must be 3-80 characters and use "
            "only letters, numbers, periods, underscores, or hyphens."
        )

    if len(password) < 12:
        raise SystemExit(
            "BIMFM_RESET_ADMIN_PASSWORD must contain at least 12 characters."
        )

    now = datetime.now(timezone.utc)

    with SessionLocal() as database:
        account = database.scalar(
            select(HRAdminAccount).where(
                func.lower(HRAdminAccount.username) == username
            )
        )

        if account is None:
            account = HRAdminAccount(
                username=username,
                display_name=display_name,
                role="ADMIN",
                password_hash=hash_password(password),
                is_active=True,
                failed_login_count=0,
                locked_until=None,
                last_login_at=None,
                created_at=now,
                updated_at=now,
            )
            database.add(account)
            action = "created"
        else:
            account.display_name = display_name
            account.role = "ADMIN"
            account.password_hash = hash_password(password)
            account.is_active = True
            account.failed_login_count = 0
            account.locked_until = None
            account.updated_at = now
            action = "reset and reactivated"

        database.commit()

    print(f"Administrator account '{username}' was {action}.")
    print("Remove the BIMFM_RESET_ADMIN_* variables and this script now.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
