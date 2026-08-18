"""Work Order-linked WebRTC screen sharing for Release 21.23.1.

No screen media passes through FastAPI. FastAPI relays WebRTC signaling and
maintains ephemeral in-memory presence only. Screen media is never written to
the database or filesystem.

A freelancer may publish only while an active Work Order exists. Screen sharing
is supplementary: losing or stopping the screen never stops the Work Order.
"""
from __future__ import annotations

import asyncio
import secrets
from dataclasses import dataclass, field
from typing import Any

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.config import BASE_DIR
from app.database import SessionLocal
from app.models import Freelancer, FreelancerAccount, HRAdminAccount
from app.web_helpers import get_current_admin, template_context
from app.live_work_overview import merge_active_work_orders
from app.work_order_service import active_work_session

router = APIRouter(tags=["Live Work Screen Sharing"])
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

VIEWER_ROLES = {"ADMIN", "SUPERVISOR", "FINANCE"}


@dataclass
class ShareRoom:
    freelancer_id: int
    freelancer_name: str
    publisher: WebSocket
    viewers: dict[str, WebSocket] = field(default_factory=dict)


class ScreenShareRegistry:
    """Ephemeral signaling registry for one application process."""

    def __init__(self) -> None:
        self.rooms: dict[int, ShareRoom] = {}
        self.watchers: set[WebSocket] = set()
        self.lock = asyncio.Lock()

    async def snapshot(self) -> list[dict[str, Any]]:
        """Return active Work Orders merged with ephemeral screen presence."""
        async with self.lock:
            room_state = {
                freelancer_id: {
                    "freelancer_name": room.freelancer_name,
                    "viewer_count": len(room.viewers),
                    "screen_live": True,
                }
                for freelancer_id, room in self.rooms.items()
            }
        return merge_active_work_orders(room_state)

    async def broadcast_presence(self) -> None:
        payload = {"type": "presence", "rooms": await self.snapshot()}
        stale: list[WebSocket] = []
        for socket in list(self.watchers):
            try:
                await socket.send_json(payload)
            except Exception:
                stale.append(socket)
        if stale:
            async with self.lock:
                for socket in stale:
                    self.watchers.discard(socket)


registry = ScreenShareRegistry()


def _websocket_freelancer(websocket: WebSocket) -> tuple[int, str] | None:
    account_id = websocket.session.get("freelancer_account_id")
    if not account_id:
        return None
    with SessionLocal() as database:
        account = database.scalar(
            select(FreelancerAccount)
            .options(joinedload(FreelancerAccount.freelancer))
            .where(FreelancerAccount.id == int(account_id))
        )
        if (
            account is None
            or not account.is_active
            or account.freelancer is None
            or not account.freelancer.is_active
        ):
            return None
        return int(account.freelancer_id), str(account.freelancer.full_name)


def _has_active_work_order(freelancer_id: int) -> bool:
    with SessionLocal() as database:
        return active_work_session(database, int(freelancer_id)) is not None


def _websocket_staff(websocket: WebSocket) -> HRAdminAccount | None:
    account_id = websocket.session.get("admin_id")
    if not account_id:
        return None
    with SessionLocal() as database:
        account = database.get(HRAdminAccount, int(account_id))
        if account is None or not account.is_active:
            return None
        if str(account.role or "").strip().upper() not in VIEWER_ROLES:
            return None
        # Return detached data only; all fields used below are already loaded.
        database.expunge(account)
        return account


@router.get("/portal/live-work/room", response_class=HTMLResponse)
def live_work_room_page(request: Request):
    with SessionLocal() as database:
        account = get_current_admin(request, database)
        if account is None:
            return RedirectResponse("/admin/login", status_code=303)
        if str(account.role or "").strip().upper() not in VIEWER_ROLES:
            return RedirectResponse("/portal/my-work", status_code=303)
        return templates.TemplateResponse(
            request=request,
            name="screen_share_test.html",
            context=template_context(
                request,
                account=account,
                page_title="Live Work Room",
                page_description="Live operational visibility for active Work Orders.",
            ),
        )


@router.get("/portal/screen-share/live-test")
def legacy_screen_share_test_redirect(request: Request):
    del request
    return RedirectResponse("/portal/live-work/room", status_code=303)


@router.websocket("/ws/screen-share/publish")
async def screen_share_publish(websocket: WebSocket):
    identity = _websocket_freelancer(websocket)
    if identity is None:
        await websocket.close(code=4401)
        return
    freelancer_id, freelancer_name = identity
    if not _has_active_work_order(freelancer_id):
        await websocket.close(code=4409, reason="Active Work Order required")
        return
    await websocket.accept()

    # A newer publisher connection supersedes an older sharing session.
    old_room: ShareRoom | None = None
    async with registry.lock:
        old_room = registry.rooms.get(freelancer_id)
        registry.rooms[freelancer_id] = ShareRoom(
            freelancer_id=freelancer_id,
            freelancer_name=freelancer_name,
            publisher=websocket,
        )
    if old_room and old_room.publisher is not websocket:
        try:
            await old_room.publisher.close(code=4001, reason="Replaced by a new sharing session")
        except Exception:
            pass
        for viewer in list(old_room.viewers.values()):
            try:
                await viewer.send_json({"type": "publisher_left"})
                await viewer.close(code=4001)
            except Exception:
                pass

    await websocket.send_json({"type": "ready", "freelancer_id": freelancer_id})
    await registry.broadcast_presence()

    try:
        while True:
            message = await websocket.receive_json()
            kind = str(message.get("type") or "")
            if kind == "ping":
                if not _has_active_work_order(freelancer_id):
                    await websocket.send_json({"type": "work_order_ended"})
                    await websocket.close(code=4003, reason="Work Order ended")
                    break
                await websocket.send_json({"type": "pong"})
                continue
            viewer_id = str(message.get("viewer_id") or "")
            if kind not in {"offer", "ice"} or not viewer_id:
                continue
            async with registry.lock:
                room = registry.rooms.get(freelancer_id)
                viewer = room.viewers.get(viewer_id) if room and room.publisher is websocket else None
            if viewer is None:
                continue
            relay = {"type": kind}
            if kind == "offer":
                relay["sdp"] = message.get("sdp")
            else:
                relay["candidate"] = message.get("candidate")
            try:
                await viewer.send_json(relay)
            except Exception:
                pass
    except WebSocketDisconnect:
        pass
    finally:
        viewers: list[WebSocket] = []
        async with registry.lock:
            room = registry.rooms.get(freelancer_id)
            if room and room.publisher is websocket:
                viewers = list(room.viewers.values())
                registry.rooms.pop(freelancer_id, None)
        for viewer in viewers:
            try:
                await viewer.send_json({"type": "publisher_left"})
                await viewer.close(code=4002)
            except Exception:
                pass
        await registry.broadcast_presence()


@router.websocket("/ws/screen-share/watch")
async def screen_share_watch(websocket: WebSocket):
    if _websocket_staff(websocket) is None:
        await websocket.close(code=4403)
        return
    await websocket.accept()
    async with registry.lock:
        registry.watchers.add(websocket)
    await websocket.send_json({"type": "presence", "rooms": await registry.snapshot()})
    try:
        while True:
            # Heartbeats keep the socket healthy and refresh active Work Order presence.
            message = await websocket.receive_json()
            if message.get("type") == "ping":
                await websocket.send_json({"type": "presence", "rooms": await registry.snapshot()})
    except WebSocketDisconnect:
        pass
    finally:
        async with registry.lock:
            registry.watchers.discard(websocket)


@router.websocket("/ws/screen-share/view/{freelancer_id}")
async def screen_share_view(websocket: WebSocket, freelancer_id: int):
    staff = _websocket_staff(websocket)
    if staff is None:
        await websocket.close(code=4403)
        return

    async with registry.lock:
        room = registry.rooms.get(int(freelancer_id))
    if room is None:
        await websocket.close(code=4404)
        return

    await websocket.accept()
    viewer_id = secrets.token_urlsafe(18)
    async with registry.lock:
        room = registry.rooms.get(int(freelancer_id))
        if room is None:
            await websocket.close(code=4404)
            return
        room.viewers[viewer_id] = websocket
        publisher = room.publisher
        freelancer_name = room.freelancer_name

    await websocket.send_json({
        "type": "viewer_ready",
        "viewer_id": viewer_id,
        "freelancer_name": freelancer_name,
    })
    try:
        await publisher.send_json({"type": "viewer_joined", "viewer_id": viewer_id})
    except Exception:
        await websocket.send_json({"type": "publisher_left"})
        await websocket.close(code=4002)
        return
    await registry.broadcast_presence()

    try:
        while True:
            message = await websocket.receive_json()
            kind = str(message.get("type") or "")
            if kind not in {"answer", "ice"}:
                continue
            relay: dict[str, Any] = {"type": kind, "viewer_id": viewer_id}
            if kind == "answer":
                relay["sdp"] = message.get("sdp")
            else:
                relay["candidate"] = message.get("candidate")
            try:
                await publisher.send_json(relay)
            except Exception:
                break
    except WebSocketDisconnect:
        pass
    finally:
        current_publisher: WebSocket | None = None
        async with registry.lock:
            room = registry.rooms.get(int(freelancer_id))
            if room and room.viewers.get(viewer_id) is websocket:
                room.viewers.pop(viewer_id, None)
                current_publisher = room.publisher
        if current_publisher is not None:
            try:
                await current_publisher.send_json({"type": "viewer_left", "viewer_id": viewer_id})
            except Exception:
                pass
        await registry.broadcast_presence()
