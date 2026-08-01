"""API-specific dependencies."""
from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.auth.dependencies import Principal, database_session, require_authenticated_user
from app.auth.permissions import Permission, has_permission


def get_request_id(request: Request) -> str:
    return request.state.request_id


def require_api_permission(permission: Permission):
    def dependency(principal: Principal = Depends(require_authenticated_user)) -> Principal:
        if not has_permission(principal.role, permission):
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "permission_required", "permission": permission.value},
            )
        return principal
    return dependency


def get_database(database: Session = Depends(database_session)) -> Session:
    return database
