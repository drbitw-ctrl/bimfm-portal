"""Production hardening utilities for BIMFM Portal.

This module intentionally uses only the Python standard library so the
hardening layer is available during early startup and deployment diagnostics.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
import json
import logging
import os
import sys
import threading
import time
from typing import Deque

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


@dataclass(frozen=True)
class EnvironmentCheck:
    name: str
    ok: bool
    message: str


def configure_structured_logging(level: str = "INFO") -> None:
    """Configure compact JSON logs suitable for Render and log aggregators."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)

    class JsonFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            payload = {
                "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }
            for key in ("request_id", "method", "path", "status_code", "duration_ms", "client_ip"):
                value = getattr(record, key, None)
                if value is not None:
                    payload[key] = value
            if record.exc_info:
                payload["exception"] = self.formatException(record.exc_info)
            return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(numeric_level)


def validate_environment(*, production: bool, session_secret: str, sync_token: str = "", cookie_https_only: bool, database_url: str) -> list[EnvironmentCheck]:
    # ``sync_token`` is accepted for backward-compatible callers, but Release
    # 20.7 no longer requires project synchronization in production.
    del sync_token
    checks = [
        EnvironmentCheck("session_secret", len(session_secret) >= 32 and "CHANGE-THIS" not in session_secret, "BIMFM_SESSION_SECRET must be a non-default value of at least 32 characters."),
        EnvironmentCheck("postgresql_native_projects", True, "Project data is read directly from portal-managed records."),
        EnvironmentCheck("secure_cookie", cookie_https_only or not production, "BIMFM_COOKIE_HTTPS_ONLY must be true in production."),
        EnvironmentCheck("production_database", not production or not database_url.startswith("sqlite"), "Use a production-grade database instead of SQLite in production."),
    ]
    failures = [check.message for check in checks if not check.ok]
    if production and failures:
        raise RuntimeError("Production environment validation failed: " + " ".join(failures))
    return checks


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Apply conservative browser security headers to every response."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), display-capture=(self)")
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'; font-src 'self' data:; connect-src 'self'; "
            "frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
        )
        if request.url.scheme == "https":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, logger_name: str = "bimfm.request"):
        super().__init__(app)
        self.logger = logging.getLogger(logger_name)

    async def dispatch(self, request: Request, call_next):
        started = time.perf_counter()
        response = None
        try:
            response = await call_next(request)
            return response
        finally:
            self.logger.info(
                "request_complete",
                extra={
                    "request_id": getattr(request.state, "request_id", "unknown"),
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": getattr(response, "status_code", 500),
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                    "client_ip": request.client.host if request.client else "unknown",
                },
            )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Small in-memory fixed-window limiter for API and authentication routes.

    For a multi-instance deployment, replace this implementation with a shared
    Redis-backed limiter while keeping the same response contract.
    """

    def __init__(self, app, requests_per_minute: int = 120, login_requests_per_minute: int = 20):
        super().__init__(app)
        self.requests_per_minute = max(1, requests_per_minute)
        self.login_requests_per_minute = max(1, login_requests_per_minute)
        self._events: dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _limit_for(self, path: str) -> int | None:
        if path in {"/login", "/admin/login"}:
            return self.login_requests_per_minute
        if path.startswith("/api/"):
            return self.requests_per_minute
        return None

    async def dispatch(self, request: Request, call_next):
        limit = self._limit_for(request.url.path)
        if limit is None:
            return await call_next(request)

        now = time.monotonic()
        identity = request.client.host if request.client else "unknown"
        key = f"{identity}:{request.url.path}"
        with self._lock:
            events = self._events[key]
            while events and now - events[0] >= 60:
                events.popleft()
            if len(events) >= limit:
                retry_after = max(1, int(60 - (now - events[0])))
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": {"code": "rate_limit_exceeded", "message": "Too many requests. Please retry later.", "details": None},
                        "meta": {"request_id": getattr(request.state, "request_id", "unknown"), "api_version": "v1"},
                    },
                    headers={"Retry-After": str(retry_after)},
                )
            events.append(now)
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - len(self._events[key])))
        return response
