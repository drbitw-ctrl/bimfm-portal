"""Unified role-aware dashboard entry point."""
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.web_helpers import get_current_admin, get_current_freelancer_account

router = APIRouter(tags=["Dashboard"])

@router.get("/dashboard")
def dashboard_entry(request: Request):
    with SessionLocal() as database:
        if get_current_admin(request, database) is not None:
            return RedirectResponse("/admin", status_code=303)
        if get_current_freelancer_account(request, database) is not None:
            return RedirectResponse("/attendance", status_code=303)
    return RedirectResponse("/login", status_code=303)
