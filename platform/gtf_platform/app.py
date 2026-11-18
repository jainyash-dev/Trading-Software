"""FastAPI application. Research eligibility is not implemented here."""

from __future__ import annotations

import json
import logging
import secrets
import threading
from datetime import timedelta
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from gtf_platform import SCHEMA
from gtf_platform.config import Settings
from gtf_platform.db import connect, probe
from gtf_platform.errors import ApiError, error_body, reject_mixed_fixture
from gtf_platform.integration import research, schedule
from gtf_platform.jobs import JobRunner, interrupt_stale, utcnow
from gtf_platform.logsafe import install as install_log_filter
from gtf_platform.routes import register
from gtf_platform.security import (
    SessionStore,
    apply_session_cookie,
    authorize,
    clear_session_cookie,
    cors_headers,
    preflight,
)
from gtf_platform.store import latest_scan

log = logging.getLogger("gtf_platform.api")

NOT_IMPLEMENTED = (
    "fills",
    "assistant",
    "paper",
)

PUBLIC_API = frozenset({("POST", "/api/v1/session/bootstrap")})


def create_app(settings: Settings, web_dist: Path | None = None) -> FastAPI:
    if settings.advertised_port <= 0:
        raise ValueError("advertised_port must be the bound port")
    app = FastAPI(title="GTF Trading Intelligence Platform", version="0.1.0", docs_url=None, redoc_url=None)
    install_log_filter()
    app.state.settings = settings
    app.state.sessions = SessionStore()
    connection = connect(settings.platform_db)
    lock = threading.Lock()
    with lock:
        interrupt_stale(connection, utcnow(), timedelta(seconds=30))
        _repair_plan_journal_mirror(settings, connection)
    app.state.db = connection
    app.state.db_lock = lock
    runner = JobRunner(
        connection,
        lock,
        lambda stored: research.execute(settings, stored),
        lambda stored: research.session_ready(settings, stored),
    )
    app.state.runner = runner
    if not settings.testing:
        runner.start(lambda: schedule.consider(settings, connection, lock))

    @app.middleware("http")
    async def boundary(request: Request, call_next):
        path = request.url.path
        if request.method in {"POST", "PUT", "PATCH"}:
            request.state.raw_body = await request.body()
        else:
            request.state.raw_body = b""
        try:
            if path.startswith("/api/"):
                if request.method == "OPTIONS":
                    response = preflight(request, settings)
                    return _stamp(response)
                public = (request.method, path) in PUBLIC_API
                authorize(request, public=public)
            else:
                from gtf_platform.security import check_host

                check_host(request, settings)
        except ApiError as exc:
            response = JSONResponse(status_code=exc.status, content=error_body(exc))
            return _stamp(response, request)
        response = await call_next(request)
        return _stamp(response, request)

    @app.exception_handler(ApiError)
    async def on_api_error(_request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(status_code=exc.status, content=error_body(exc))

    @app.exception_handler(RequestValidationError)
    async def on_validation(_request: Request, _exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content=error_body(ApiError(400, "REQUEST_INVALID", "Malformed request")),
        )

    @app.exception_handler(Exception)
    async def on_unexpected(request: Request, exc: Exception) -> JSONResponse:
        from gtf_platform.logsafe import redact

        error_id = "err-%s" % secrets.token_hex(4)
        log.error(
            "internal path=%s error_id=%s kind=%s detail=%s",
            request.url.path,
            error_id,
            type(exc).__name__,
            redact(str(exc))[:300],
        )
        return JSONResponse(
            status_code=500,
            content=error_body(ApiError(500, "INTERNAL", "The request failed", {"error_id": error_id})),
        )

    @app.get("/api/v1/health")
    def health() -> dict:
        platform_db = probe(settings.platform_db)
        research_db = probe(settings.research_db)
        scan = None
        with lock:
            row = latest_scan(connection, fixture=False)
            if row is not None:
                scan = {
                    "scan_key": row["scan_key"],
                    "as_of": row["as_of"],
                    "completeness": row["completeness"],
                    "dataset_id": row["dataset_id"],
                }
        ingest = _ingest_date(settings)
        limitations = _limitations(settings)
        from gtf_platform.integration.desk import evaluate_data_ready

        readiness = evaluate_data_ready(settings)
        if not platform_db["reachable"]:
            outcome = "FAIL"
        elif scan is not None and (settings.research_db is None or research_db["reachable"]):
            outcome = "OK"
        else:
            outcome = "WARNING"
        scheduler_state = "RUNNING" if settings.scheduler_enabled and not settings.testing else "STOPPED"
        return _ok(
            {
                "outcome": outcome,
                "scheduler_state": scheduler_state,
                "database_files": {"platform": platform_db, "research": research_db},
                "last_successful_ingest_date": ingest,
                "last_scan_run_id": None if scan is None else scan["scan_key"],
                "last_scan": scan,
                "last_scan_state": "UNAVAILABLE" if scan is None else scan["completeness"],
                "data_limitations": list(dict.fromkeys(list(limitations) + list(readiness.get("limitations") or []))),
                "data_ready": bool(readiness["data_ready"]),
                "data_ready_reason": readiness["data_ready_reason"],
                "readiness_state": readiness["readiness_state"],
                "certified_p0_data": bool(readiness.get("certified_p0_data")),
                "orders_placed": False,
            }
        )

    register(app)

    @app.get("/api/v1/session")
    def session_state() -> dict:
        return _ok({"authenticated": True, "auth": "cookie"})

    @app.post("/api/v1/session/bootstrap")
    async def bootstrap(request: Request) -> JSONResponse:
        raw = await request.body()
        if raw and request.headers.get("content-type", "").startswith("application/json"):
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                raise ApiError(400, "REQUEST_INVALID", "Malformed JSON") from None
            reject_mixed_fixture(parsed)
        # D57 single-owner: a re-bootstrap replaces every prior in-memory session so a
        # restart/recovery path cannot leave stale privileges alive beside a new cookie.
        token = app.state.sessions.issue(
            timedelta(seconds=settings.session_ttl_seconds),
            replace_all=True,
        )
        response = JSONResponse(
            content=_ok(
                {
                    "authenticated": True,
                    "auth": "cookie",
                    "session_recovery": "REBOOTSTRAP",
                    "durable_state": "JOURNAL_ON_DISK",
                }
            )
        )
        apply_session_cookie(response, settings, token)
        return response

    @app.post("/api/v1/session/logout")
    def logout(request: Request) -> JSONResponse:
        token = request.cookies.get(settings.cookie_name)
        app.state.sessions.revoke(token)
        response = JSONResponse(content=_ok({"authenticated": False, "auth": "cookie"}))
        clear_session_cookie(response, settings)
        return response

    @app.get("/api/v1/meta")
    def meta() -> dict:
        return _ok(
            {
                "auth": "cookie",
                "bind": "loopback",
                "fixture_policy": "explicit",
                "orders_placed": False,
                "eligibility": "research-pipeline",
                "routes_not_implemented": list(NOT_IMPLEMENTED),
            }
        )

    dist = web_dist
    if dist is not None and (dist / "index.html").is_file():
        assets = dist / "assets"
        if assets.is_dir():
            app.mount("/assets", StaticFiles(directory=assets), name="assets")

        @app.get("/")
        def index() -> FileResponse:
            return FileResponse(dist / "index.html")

        @app.get("/{full_path:path}")
        def spa(full_path: str) -> FileResponse:
            candidate = (dist / full_path).resolve()
            root = dist.resolve()
            if root == candidate or root in candidate.parents:
                if candidate.is_file():
                    return FileResponse(candidate)
            return FileResponse(dist / "index.html")
    else:

        @app.get("/")
        def waiting() -> JSONResponse:
            return JSONResponse(
                content=_ok(
                    {
                        "ui": "not-built",
                        "message": "The web build is not on this process. Start the Vite dev server, or build platform/web.",
                        "orders_placed": False,
                    }
                )
            )

    app.openapi = lambda: _openapi(app)  # type: ignore[method-assign]
    return app


def _repair_plan_journal_mirror(settings: Settings, connection) -> None:
    """P4-IR-04 recovery: mirror journal CANCELLED/EXPIRED left unmirrored by an interruption.

    Idempotent. A failure here is logged and left for the repair-on-read path; it never
    blocks startup and never edits the journal.
    """
    from gtf_platform.integration import desk

    try:
        connection.execute("BEGIN IMMEDIATE")
        report = desk.sync_plans_from_journal(settings, connection)
        connection.commit()
        if report["synced"]:
            log.info("plan journal mirror repaired %d plan(s) at startup", len(report["synced"]))
    except Exception:
        connection.rollback()
        log.warning("plan journal mirror repair skipped at startup; repair-on-read remains active")


def _openapi(app: FastAPI) -> dict:
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
    components = schema.setdefault("components", {})
    components["securitySchemes"] = {
        "cookieSession": {
            "type": "apiKey",
            "in": "cookie",
            "name": "gtf_session",
            "description": (
                "HttpOnly session cookie from POST /api/v1/session/bootstrap. "
                "Not a query parameter."
            ),
        }
    }
    for path, methods in schema.get("paths", {}).items():
        for method, operation in methods.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            if path.startswith("/api/") and not (path == "/api/v1/session/bootstrap" and method == "post"):
                operation["security"] = [{"cookieSession": []}]
            else:
                operation["security"] = []
    app.openapi_schema = schema
    return schema


def _ingest_date(settings: Settings):
    try:
        from gtf_platform.integration import sources

        newest = sources.newest_session(settings)
    except Exception:
        return None
    return None if newest is None else newest.isoformat()


def _limitations(settings: Settings) -> list[str]:
    try:
        from gtf_platform.integration.reference import limitation_list

        return limitation_list(settings)
    except Exception:
        return ["DATA_LIMITATIONS_UNAVAILABLE", "DATA_READY_NOT_CLAIMED"]


def _ok(data: dict) -> dict:
    return {"platform_schema": SCHEMA, "data": data, "meta": {"fixture": False}}


def _stamp(response: Response, request: Request | None = None) -> Response:
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Cache-Control", "no-store")
    if request is not None and request.url.path.startswith("/api/"):
        settings: Settings = request.app.state.settings
        for key, value in cors_headers(request, settings).items():
            response.headers.setdefault(key, value)
    return response
