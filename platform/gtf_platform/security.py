"""Browser session checks for the loopback API.

The session value is stored in process memory and sent only as an HttpOnly cookie.
It is not accepted from a query string, a JSON body, or localStorage.
"""

from __future__ import annotations

import hashlib
import secrets
import threading
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone

from starlette.requests import Request
from starlette.responses import Response

from gtf_platform.config import Settings
from gtf_platform.errors import ApiError

REQUEST_HEADER = "x-gtf-request"
REQUEST_VALUE = "1"
SAFE_FETCH_SITES = frozenset({"none", "same-origin", "same-site"})


class SessionStore:
    """In-memory sessions. The raw token is returned once to the cookie writer and is not logged."""

    def __init__(self) -> None:
        self._until: dict[str, datetime] = {}
        self._lock = threading.Lock()

    def issue(self, ttl: timedelta | None = None, *, replace_all: bool = False) -> str:
        if ttl is None:
            ttl = timedelta(hours=18)
        if ttl.total_seconds() <= 0:
            raise ValueError("session ttl must be positive")
        token = secrets.token_urlsafe(32)
        with self._lock:
            if replace_all:
                self._until.clear()
            self._until[_digest(token)] = datetime.now(timezone.utc) + ttl
        return token

    def valid(self, token: str | None) -> bool:
        if not token:
            return False
        digest = _digest(token)
        with self._lock:
            expires = self._until.get(digest)
            if expires is None:
                return False
            if datetime.now(timezone.utc) >= expires:
                self._until.pop(digest, None)
                return False
        return True

    def expire(self, token: str | None) -> None:
        """Mark one session expired. Used by tests; the token is not stored."""
        if token:
            digest = _digest(token)
            with self._lock:
                if digest in self._until:
                    self._until[digest] = datetime.now(timezone.utc) - timedelta(seconds=1)

    def revoke(self, token: str | None) -> None:
        if token:
            with self._lock:
                self._until.pop(_digest(token), None)

    def revoke_all(self) -> None:
        with self._lock:
            self._until.clear()

    def active_count(self) -> int:
        """Test helper: number of unexpired digests currently held."""
        now = datetime.now(timezone.utc)
        with self._lock:
            return sum(1 for expires in self._until.values() if expires > now)


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def check_host(request: Request, settings: Settings) -> None:
    host = request.headers.get("host", "")
    if host != settings.expected_host():
        raise ApiError(403, "HOST_REJECTED", "Host is not the local application")
    client = request.client.host if request.client else ""
    allowed = {"127.0.0.1", "::1"}
    if settings.testing:
        allowed.add("testclient")
    if client not in allowed:
        raise ApiError(403, "HOST_REJECTED", "Client is not loopback")


def check_origin(request: Request, settings: Settings) -> None:
    origin = request.headers.get("origin")
    if origin is None:
        return
    if origin.rstrip("/") not in settings.allowed_origins():
        raise ApiError(403, "ORIGIN_REJECTED", "Origin is not the local application")


def check_fetch_site(request: Request) -> None:
    site = request.headers.get("sec-fetch-site")
    if site is None:
        return
    if site.lower() not in SAFE_FETCH_SITES:
        raise ApiError(403, "ORIGIN_REJECTED", "Cross-site request refused")


def check_marker(request: Request) -> None:
    if request.headers.get(REQUEST_HEADER) != REQUEST_VALUE:
        raise ApiError(403, "CSRF_REJECTED", "Missing application request marker")


def require_session(request: Request, settings: Settings, sessions: SessionStore) -> None:
    token = request.cookies.get(settings.cookie_name)
    if not sessions.valid(token):
        raise ApiError(401, "UNAUTHENTICATED", "Session is missing or expired")


def authorize(request: Request, *, public: bool) -> None:
    settings: Settings = request.app.state.settings
    sessions: SessionStore = request.app.state.sessions
    check_host(request, settings)
    check_origin(request, settings)
    check_fetch_site(request)
    if request.method == "OPTIONS":
        return
    check_marker(request)
    if not public:
        require_session(request, settings, sessions)


def apply_session_cookie(response: Response, settings: Settings, token: str) -> None:
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        httponly=True,
        samesite="strict",
        secure=settings.cookie_secure,
        path="/",
        max_age=settings.session_ttl_seconds,
    )


def clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.cookie_name,
        path="/",
        httponly=True,
        samesite="strict",
        secure=settings.cookie_secure,
    )


def cors_headers(request: Request, settings: Settings) -> dict[str, str]:
    origin = request.headers.get("origin")
    if not origin or origin.rstrip("/") not in settings.allowed_origins():
        return {}
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Credentials": "true",
        "Vary": "Origin",
    }


def preflight(request: Request, settings: Settings) -> Response:
    check_host(request, settings)
    origin = request.headers.get("origin")
    if not origin or origin.rstrip("/") not in settings.allowed_origins():
        raise ApiError(403, "ORIGIN_REJECTED", "Origin is not the local application")
    headers = cors_headers(request, settings)
    headers["Access-Control-Allow-Headers"] = "X-GTF-Request, Content-Type, Idempotency-Key"
    headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, DELETE, OPTIONS"
    headers["Access-Control-Max-Age"] = "600"
    return Response(status_code=204, headers=headers)


def session_token_from(cookies: Mapping[str, str], settings: Settings) -> str | None:
    return cookies.get(settings.cookie_name)
