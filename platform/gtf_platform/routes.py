"""Authenticated API routes. Session checks stay in the application middleware."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from gtf_platform import SCHEMA
from gtf_platform.config import Settings
from gtf_platform.errors import ApiError, reject_mixed_fixture
from gtf_platform.integration import candles, reference, research
from gtf_platform.opportunity import (
    add_note,
    apply_transition,
    get_opportunity,
    ingest_scan,
    list_history,
    list_notes,
    list_opportunities,
)
from gtf_platform.opportunity.lifecycle import WORKFLOW_STATES
from gtf_platform.store import (
    accept_job,
    accept_object,
    bind_object,
    body_hash,
    delete_drawing,
    delete_watchlist,
    drawing_view,
    find_scan_by_research_key,
    get_job,
    get_scan,
    insert_drawing,
    insert_scan_config,
    insert_watchlist,
    list_audit,
    list_drawings,
    list_scan_configs,
    list_scans,
    list_watchlists,
    patch_settings,
    read_settings,
    record_audit,
    request_cancel,
    scan_summary,
    update_drawing,
    update_watchlist,
)

log = logging.getLogger("gtf_platform.api")

DRAWING_TYPES = {"horizontal", "trend", "rectangle", "text"}
SETTING_KEYS = {
    "capital": (str, int, float, type(None)),
    "risk_stage": (str, type(None)),
    "rpt_pct": (str, int, float, type(None)),
    "scheduler_enabled": (bool,),
    "assistant_enabled": (bool,),
    "assistant_payload_policy": (str,),
    "backup_directory": (str, type(None)),
    "log_retention_days": (int,),
}
JOB_STATE = {
    "RUN": "VALIDATING",
    "PENDING_DATA": "PENDING_DATA",
    "SKIPPED_HOLIDAY": "SKIPPED_HOLIDAY",
    "SKIPPED_UNRESOLVED_CALENDAR": "SKIPPED_UNRESOLVED_CALENDAR",
}


def register(app: FastAPI) -> None:
    app.add_api_route("/api/v1/overview", overview, methods=["GET"])
    app.add_api_route("/api/v1/instruments", instruments, methods=["GET"])
    app.add_api_route("/api/v1/universe", universe, methods=["GET"])
    app.add_api_route("/api/v1/calendar", calendar, methods=["GET"])
    app.add_api_route("/api/v1/datasets", datasets, methods=["GET"])
    app.add_api_route("/api/v1/candles", candle_route, methods=["GET"])
    app.add_api_route("/api/v1/scans", create_scan, methods=["POST"])
    app.add_api_route("/api/v1/scans", list_scan_route, methods=["GET"])
    app.add_api_route("/api/v1/scans/{scan_key}", get_scan_route, methods=["GET"])
    app.add_api_route("/api/v1/scans/{scan_key}/symbols", scan_symbols, methods=["GET"])
    app.add_api_route("/api/v1/scans/{scan_key}/cancel", cancel_scan, methods=["POST"])
    app.add_api_route("/api/v1/symbols/{symbol}/bundle", bundle, methods=["GET"])
    app.add_api_route("/api/v1/watchlists", watchlists, methods=["GET"])
    app.add_api_route("/api/v1/watchlists", create_watchlist, methods=["POST"])
    app.add_api_route("/api/v1/watchlists/{watchlist_id}", patch_watchlist, methods=["PATCH"])
    app.add_api_route("/api/v1/watchlists/{watchlist_id}", remove_watchlist, methods=["DELETE"])
    app.add_api_route("/api/v1/opportunities", opportunities, methods=["GET"])
    app.add_api_route("/api/v1/opportunities/ingest", ingest_opportunities, methods=["POST"])
    app.add_api_route("/api/v1/opportunities/{opportunity_id}", get_opportunity_route, methods=["GET"])
    app.add_api_route("/api/v1/opportunities/{opportunity_id}/transition", transition_opportunity, methods=["POST"])
    app.add_api_route("/api/v1/opportunities/{opportunity_id}/notes", opportunity_notes, methods=["GET"])
    app.add_api_route("/api/v1/opportunities/{opportunity_id}/notes", add_opportunity_note, methods=["POST"])
    app.add_api_route("/api/v1/opportunities/{opportunity_id}/history", opportunity_history, methods=["GET"])
    app.add_api_route("/api/v1/scan-configs", scan_configs, methods=["GET"])
    app.add_api_route("/api/v1/scan-configs", create_scan_config, methods=["POST"])
    app.add_api_route("/api/v1/drawings", drawings, methods=["GET"])
    app.add_api_route("/api/v1/drawings", create_drawing, methods=["POST"])
    app.add_api_route("/api/v1/drawings/{drawing_id}", patch_drawing, methods=["PATCH"])
    app.add_api_route("/api/v1/drawings/{drawing_id}", remove_drawing, methods=["DELETE"])
    app.add_api_route("/api/v1/settings", get_settings, methods=["GET"])
    app.add_api_route("/api/v1/settings", patch_settings_route, methods=["PATCH"])
    app.add_api_route("/api/v1/jobs/{job_id}", get_job_route, methods=["GET"])
    app.add_api_route("/api/v1/audit", audit, methods=["GET"])
    app.add_api_route("/api/v1/symbols/{symbol}/explain", explain_symbol, methods=["GET"])
    app.add_api_route("/api/v1/plans", list_plans_route, methods=["GET"])
    app.add_api_route("/api/v1/plans", create_plan_route, methods=["POST"])
    app.add_api_route("/api/v1/plans/{plan_id}", preview_plan_route, methods=["GET"])
    app.add_api_route("/api/v1/plans/{plan_id}/approve", approve_plan_route, methods=["POST"])
    app.add_api_route("/api/v1/plans/{plan_id}/submit", submit_plan_route, methods=["POST"])
    app.add_api_route("/api/v1/plans/{plan_id}/reject", reject_plan_route, methods=["POST"])
    app.add_api_route("/api/v1/plans/{plan_id}/cancel", cancel_plan_route, methods=["POST"])
    app.add_api_route("/api/v1/plans/{plan_id}/reopen", reopen_plan_route, methods=["POST"])
    app.add_api_route("/api/v1/plans/{plan_id}/rationale", plan_rationale_route, methods=["POST"])
    app.add_api_route("/api/v1/plans/{plan_id}/notes", plan_notes_route, methods=["GET"])
    app.add_api_route("/api/v1/plans/{plan_id}/notes", add_plan_note_route, methods=["POST"])
    app.add_api_route("/api/v1/plans/{plan_id}/history", plan_history_route, methods=["GET"])
    app.add_api_route("/api/v1/journal", journal_route, methods=["GET"])
    app.add_api_route("/api/v1/journal/performance", journal_performance_route, methods=["GET"])
    app.add_api_route("/api/v1/journal/export", journal_export_route, methods=["GET"])
    app.add_api_route("/api/v1/journal/{entry_id}", journal_detail_route, methods=["GET"])
    app.add_api_route("/api/v1/journal/{entry_id}/order", submit_order_route, methods=["POST"])
    app.add_api_route("/api/v1/journal/{entry_id}/events", record_event_route, methods=["POST"])
    app.add_api_route("/api/v1/journal/{entry_id}/executions", record_execution_route, methods=["POST"])
    app.add_api_route("/api/v1/journal/{entry_id}/charges", record_charges_route, methods=["POST"])
    app.add_api_route("/api/v1/journal/{entry_id}/notes", journal_note_route, methods=["POST"])
    app.add_api_route("/api/v1/journal/{entry_id}/reviews", journal_review_route, methods=["POST"])
    app.add_api_route("/api/v1/journal/{entry_id}/attachments", journal_attachment_route, methods=["POST"])
    app.add_api_route("/api/v1/journal/{entry_id}/attachments/{attachment_id}", journal_attachment_get_route, methods=["GET"])
    app.add_api_route("/api/v1/portfolio", portfolio_route, methods=["GET"])
    app.add_api_route("/api/v1/scans/{scan_key}/reports/{name}", export_route, methods=["GET"])
    app.add_api_route("/api/v1/backup", backup_route, methods=["POST"])
    app.add_api_route("/api/v1/restore-check", restore_route, methods=["POST"])
    app.add_api_route("/api/v1/backtests", backtest_route, methods=["POST"])


def overview(request: Request, as_of: str | None = None) -> dict:
    settings = _settings(request)
    with _lock(request):
        from gtf_platform.store import latest_scan

        row = latest_scan(request.app.state.db, fixture=False)
    calendar_row = None
    if as_of:
        calendar_row = reference.calendar_payload(settings, as_of[:10])
    if row is None:
        counts = None
        state = "UNAVAILABLE"
        dataset_id = None
        scan_as_of = None
    else:
        envelope = json.loads(row["envelope_json"])
        counts = (envelope.get("counts") or {})
        state = row["completeness"]
        dataset_id = row["dataset_id"]
        scan_as_of = row["as_of"]
    from gtf_platform.integration import desk

    desk_facts = desk.overview_facts(
        request.app.state.db,
        envelope if row is not None else None,
        None if row is None else row["scan_key"],
        settings,
    )
    return _ok(
        {
            "state": state,
            "as_of": as_of or scan_as_of,
            "dataset_id": dataset_id,
            "counts": counts,
            "calendar": calendar_row,
            "index": None,
            "sector": None,
            "breadth": None,
            "index_state": "UNAVAILABLE",
            "sector_state": "UNAVAILABLE",
        "breadth_state": "UNAVAILABLE",
        **desk_facts,
        "coverage": reference.corporate_action_limitations(settings),
    }
    )


def instruments(request: Request, query: str = "") -> dict:
    return _ok({"instruments": reference.search_instruments(_settings(request), query)})


def universe(request: Request, as_of: str = "") -> dict:
    return _ok(reference.universe_payload(_settings(request), as_of))


def calendar(request: Request, date: str = "") -> dict:
    return _ok(reference.calendar_payload(_settings(request), date))


def datasets(request: Request) -> JSONResponse:
    payload = reference.datasets(_settings(request))
    fixture = bool(payload.pop("fixture"))
    return _json(payload, fixture=fixture)


def candle_route(request: Request, symbol: str = "", timeframe: str = "", as_of: str = "", dataset_id: str = "") -> JSONResponse:
    settings = _settings(request)
    payload = candles.read_candles(
        settings,
        symbol=symbol,
        timeframe=timeframe,
        as_of_text=as_of,
        dataset_id=dataset_id,
    )
    source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
    label = source.get("source")
    text = label.upper() if isinstance(label, str) else ""
    fixture = bool(settings.fixture_mode or "FIXTURE" in settings.source_label.upper() or "SYNTHETIC" in settings.source_label.upper() or "FIXTURE" in text or "SYNTHETIC" in text)
    return _json(payload, fixture=fixture)


def create_scan(request: Request) -> JSONResponse:
    body = _json_body(request)
    key = _idempotency(request)
    plan = research.prepare(_settings(request), body)
    payload_hash = body_hash(research.canonical_plan_body(body))
    state = JOB_STATE[plan.disposition]
    with _tx(request) as connection:
        existing = None
        if plan.research_key and plan.disposition == "RUN":
            found = find_scan_by_research_key(connection, plan.research_key)
            if found is not None and found["completeness"] in {"COMPLETE", "PARTIAL"}:
                existing = found
        kind, job = accept_job(
            connection,
            idempotency_key=key,
            payload_hash=payload_hash,
            kind="SCAN",
            state=state,
            request=plan.stored,
            fixture=plan.fixture,
            research_key=plan.research_key,
            progress_total=plan.progress_total,
            error_code=plan.error_code,
            error_message=plan.error_message,
            existing_scan=existing,
        )
        if kind == "conflict":
            raise ApiError(409, "CONFLICT", "Idempotency-Key was reused with a different body")
    log.info("scan request job %s state %s dataset %s", job.get("job_id"), job.get("state"), plan.stored.get("dataset_id"))
    return _json(job, status=202, fixture=plan.fixture)


def list_scan_route(request: Request, limit: int = 50, cursor: str | None = None, include_fixtures: bool = False) -> JSONResponse:
    if limit < 1 or limit > 100:
        raise ApiError(400, "REQUEST_INVALID", "limit must be from 1 to 100")
    with _lock(request):
        rows, next_cursor = list_scans(
            request.app.state.db,
            limit=limit,
            cursor=cursor,
            include_fixtures=include_fixtures,
        )
    items = [scan_summary(row) for row in rows]
    fixture = any(item["fixture"] for item in items)
    return _json({"scans": items, "next_cursor": next_cursor}, fixture=fixture)


def get_scan_route(request: Request, scan_key: str, include_fixtures: bool = False) -> JSONResponse:
    row = _load_scan(request, scan_key, include_fixtures)
    envelope = json.loads(row["envelope_json"])
    return _json(envelope, fixture=bool(row["fixture"]), engine=True)


def scan_symbols(request: Request, scan_key: str, include_fixtures: bool = False) -> JSONResponse:
    row = _load_scan(request, scan_key, include_fixtures)
    envelope = json.loads(row["envelope_json"])
    symbols = [research.with_deciding_gates(symbol) for symbol in envelope.get("symbols") or []]
    return _json(
        {"scan_key": scan_key, "symbols": symbols, "symbols_not_opened": envelope.get("symbols_not_opened") or []},
        fixture=bool(row["fixture"]),
        engine=True,
    )


def cancel_scan(request: Request, scan_key: str) -> JSONResponse:
    _idempotency(request)
    with _tx(request) as connection:
        kind, job = request_cancel(connection, scan_key)
    if kind == "missing":
        raise ApiError(404, "NOT_FOUND", "Scan was not found")
    if kind == "finished":
        raise ApiError(409, "CONFLICT", "A finished scan cannot be cancelled")
    return _json(job, status=202)


def bundle(
    request: Request,
    symbol: str,
    as_of: str = "",
    dataset_id: str = "",
    trade_type: str = "",
    scan_key: str = "",
    include_fixtures: bool = False,
) -> JSONResponse:
    if not scan_key:
        raise ApiError(
            400,
            "REQUEST_INVALID",
            "scan_key is required. A new run is POST /scans and does not rewrite an older scan",
        )
    row = _load_scan(request, scan_key, include_fixtures)
    envelope = json.loads(row["envelope_json"])
    wanted = symbol.strip().upper()
    found = None
    for item in envelope.get("symbols") or []:
        if item.get("symbol") == wanted:
            found = item
            break
    if found is None:
        raise ApiError(404, "NOT_FOUND", "Symbol is not in the stored scan")
    if as_of and as_of[:10] != str(envelope.get("as_of") or "")[:10]:
        raise ApiError(409, "CONFLICT", "as_of does not match the stored scan")
    if dataset_id and dataset_id != envelope.get("dataset_id"):
        raise ApiError(409, "CONFLICT", "dataset_id does not match the stored scan")
    if trade_type and trade_type != envelope.get("trade_type"):
        raise ApiError(409, "CONFLICT", "trade_type does not match the stored scan")
    payload = {
        "scan_key": row["scan_key"],
        "dataset_id": envelope.get("dataset_id"),
        "as_of": envelope.get("as_of"),
        "trade_type": envelope.get("trade_type"),
        "invocation": envelope.get("invocation"),
        "completeness": envelope.get("completeness"),
        "full_universe_scan": envelope.get("full_universe_scan"),
        "symbols_not_opened": envelope.get("symbols_not_opened") or [],
        "limitations": envelope.get("limitations") or [],
        "authorises_order": envelope.get("authorises_order"),
        "replay": envelope.get("invocation"),
        "stored": research.with_deciding_gates(found),
    }
    return _json(payload, fixture=bool(row["fixture"]), engine=True)


def watchlists(request: Request) -> dict:
    with _lock(request):
        return _ok({"watchlists": list_watchlists(request.app.state.db)})


def create_watchlist(request: Request) -> JSONResponse:
    body = _object(request)
    key = _idempotency(request)
    name, symbols, items = _watch_body(body, require_name=True)
    payload = body_hash({"name": name, "symbols": symbols, "items": items})
    with _tx(request) as connection:
        kind, object_id = accept_object(connection, idempotency_key=key, payload_hash=payload, kind="WATCHLIST")
        if kind == "conflict":
            raise ApiError(409, "CONFLICT", "Idempotency-Key was reused with a different body")
        if kind == "existing" and object_id:
            view = _watch_or_404(connection, object_id)
            return _json(view, status=200)
        view = insert_watchlist(connection, name, symbols, items=items)
        bind_object(connection, idempotency_key=key, payload_hash=payload, kind="WATCHLIST", object_id=view["watchlist_id"])
        record_audit(connection, actor="owner", action="watchlist.create", object_id=view["watchlist_id"], after=view)
    return _json(view, status=201)


def patch_watchlist(request: Request, watchlist_id: str) -> dict:
    body = _object(request)
    if set(body) - {"name", "symbols", "items"}:
        raise ApiError(400, "REQUEST_INVALID", "watchlist patch contains an unknown field")
    if not body:
        raise ApiError(400, "REQUEST_INVALID", "watchlist patch is empty")
    name = body.get("name")
    symbols = body.get("symbols")
    items = body.get("items")
    if name is not None:
        name = _name(name)
    if symbols is not None:
        symbols = _symbols(symbols)
    if items is not None:
        items = _watch_items(items)
        if symbols is None:
            symbols = [item["symbol"] for item in items]
    with _tx(request) as connection:
        before = _watch_or_404(connection, watchlist_id)
        view = update_watchlist(connection, watchlist_id, name=name, symbols=symbols, items=items)
        record_audit(connection, actor="owner", action="watchlist.patch", object_id=watchlist_id, before=before, after=view)
    return _ok(view)


def remove_watchlist(request: Request, watchlist_id: str) -> dict:
    with _tx(request) as connection:
        before = _watch_or_404(connection, watchlist_id)
        if not delete_watchlist(connection, watchlist_id):
            raise ApiError(404, "NOT_FOUND", "Watchlist not found")
        record_audit(connection, actor="owner", action="watchlist.delete", object_id=watchlist_id, before=before, after=None)
    return _ok({"deleted": True, "watchlist_id": watchlist_id, "authorises_order": False})


def opportunities(
    request: Request,
    symbol: str | None = None,
    workflow_state: str | None = None,
    canonical_status: str | None = None,
    timeframe: str | None = None,
    source_quality: str | None = None,
    scan_key: str | None = None,
    watchlist_id: str | None = None,
    include_fixtures: bool = False,
    q: str | None = None,
    sort: str = "priority",
    limit: int = 100,
    offset: int = 0,
) -> dict:
    if workflow_state and workflow_state not in WORKFLOW_STATES:
        raise ApiError(400, "REQUEST_INVALID", "Unknown workflow_state filter")
    if sort not in {"priority", "symbol", "discovered", "updated"}:
        raise ApiError(400, "REQUEST_INVALID", "sort must be priority, symbol, discovered, or updated")
    with _lock(request):
        payload = list_opportunities(
            request.app.state.db,
            symbol=(symbol or "").strip().upper() or None,
            workflow_state=workflow_state,
            canonical_status=canonical_status,
            timeframe=timeframe,
            source_quality=source_quality,
            scan_key=scan_key,
            watchlist_id=watchlist_id,
            include_fixtures=bool(include_fixtures),
            q=(q or "").strip() or None,
            sort=sort,
            limit=limit,
            offset=offset,
        )
    fixture = any(item.get("fixture") for item in payload.get("opportunities") or [])
    return _ok(payload, fixture=fixture)


def ingest_opportunities(request: Request) -> JSONResponse:
    body = _object(request)
    if set(body) - {"scan_key", "include_rejected"}:
        raise ApiError(400, "REQUEST_INVALID", "ingest body contains an unknown field")
    scan_key = body.get("scan_key")
    if not isinstance(scan_key, str) or not scan_key.strip():
        raise ApiError(400, "REQUEST_INVALID", "scan_key is required")
    include_rejected = body.get("include_rejected", True)
    if not isinstance(include_rejected, bool):
        raise ApiError(400, "REQUEST_INVALID", "include_rejected must be a boolean")
    key = _optional_key(request)
    payload = body_hash({"scan_key": scan_key.strip(), "include_rejected": include_rejected})
    with _tx(request) as connection:
        if key:
            kind, object_id = accept_object(connection, idempotency_key=key, payload_hash=payload, kind="OPP_INGEST")
            if kind == "conflict":
                raise ApiError(409, "CONFLICT", "Idempotency-Key was reused with a different body")
            if kind == "existing" and object_id:
                # Re-run is idempotent at the row level; return a fresh summary.
                result = ingest_scan(connection, scan_key.strip(), include_rejected=include_rejected)
                return _json(result, status=200, fixture=bool(result.get("fixture")))
        result = ingest_scan(connection, scan_key.strip(), include_rejected=include_rejected)
        if key:
            bind_object(
                connection,
                idempotency_key=key,
                payload_hash=payload,
                kind="OPP_INGEST",
                object_id=scan_key.strip(),
            )
    return _json(result, status=201, fixture=bool(result.get("fixture")))


def get_opportunity_route(request: Request, opportunity_id: str) -> dict:
    with _lock(request):
        view = get_opportunity(request.app.state.db, opportunity_id)
    if view is None:
        raise ApiError(404, "NOT_FOUND", "Opportunity not found")
    return _ok(view, fixture=bool(view.get("fixture")))


def transition_opportunity(request: Request, opportunity_id: str) -> dict:
    body = _object(request)
    if set(body) - {"to_state", "reason"}:
        raise ApiError(400, "REQUEST_INVALID", "transition body contains an unknown field")
    to_state = body.get("to_state")
    if not isinstance(to_state, str):
        raise ApiError(400, "REQUEST_INVALID", "to_state is required")
    reason = body.get("reason")
    if reason is not None and not isinstance(reason, str):
        raise ApiError(400, "REQUEST_INVALID", "reason must be a string")
    with _tx(request) as connection:
        view = apply_transition(
            connection,
            opportunity_id,
            to_state=to_state,
            actor="owner",
            reason=reason,
        )
    return _ok(view, fixture=bool(view.get("fixture")))


def opportunity_notes(request: Request, opportunity_id: str) -> dict:
    with _lock(request):
        if get_opportunity(request.app.state.db, opportunity_id) is None:
            raise ApiError(404, "NOT_FOUND", "Opportunity not found")
        notes = list_notes(request.app.state.db, opportunity_id)
    return _ok({"notes": notes, "disclaimer": "Research notes are not GTF methodology decisions."})


def add_opportunity_note(request: Request, opportunity_id: str) -> JSONResponse:
    body = _object(request)
    if set(body) - {"body"}:
        raise ApiError(400, "REQUEST_INVALID", "note body contains an unknown field")
    text = body.get("body")
    if not isinstance(text, str):
        raise ApiError(400, "REQUEST_INVALID", "body is required")
    with _tx(request) as connection:
        if get_opportunity(connection, opportunity_id) is None:
            raise ApiError(404, "NOT_FOUND", "Opportunity not found")
        try:
            note = add_note(connection, opportunity_id, actor="owner", body=text)
        except ValueError as exc:
            raise ApiError(400, "REQUEST_INVALID", str(exc)) from exc
        record_audit(connection, actor="owner", action="opportunity.note", object_id=opportunity_id, after=note)
    return _json(note, status=201)


def opportunity_history(request: Request, opportunity_id: str) -> dict:
    with _lock(request):
        if get_opportunity(request.app.state.db, opportunity_id) is None:
            raise ApiError(404, "NOT_FOUND", "Opportunity not found")
        history = list_history(request.app.state.db, opportunity_id)
    return _ok({"history": history})


def scan_configs(request: Request) -> dict:
    with _lock(request):
        return _ok({"scan_configs": list_scan_configs(request.app.state.db)})


def create_scan_config(request: Request) -> JSONResponse:
    body = _object(request)
    key = _idempotency(request)
    if set(body) - {"name", "parameters"}:
        raise ApiError(400, "REQUEST_INVALID", "scan config contains an unknown field")
    name = _name(body.get("name"))
    parameters = body.get("parameters")
    research.saved_parameters_ok(parameters)
    payload = body_hash({"name": name, "parameters": parameters})
    with _tx(request) as connection:
        kind, object_id = accept_object(connection, idempotency_key=key, payload_hash=payload, kind="SCAN_CONFIG")
        if kind == "conflict":
            raise ApiError(409, "CONFLICT", "Idempotency-Key was reused with a different body")
        if kind == "existing" and object_id:
            rows = [item for item in list_scan_configs(connection) if item["config_id"] == object_id]
            return _json(rows[0], status=200)
        view = insert_scan_config(connection, name, parameters)
        bind_object(connection, idempotency_key=key, payload_hash=payload, kind="SCAN_CONFIG", object_id=view["config_id"])
    return _json(view, status=201)


def drawings(request: Request, symbol: str = "", timeframe: str = "") -> dict:
    if not symbol or timeframe not in {"M", "W", "D"}:
        raise ApiError(400, "REQUEST_INVALID", "symbol and timeframe M, W, or D are required")
    with _lock(request):
        return _ok({"drawings": list_drawings(request.app.state.db, symbol.strip().upper(), timeframe)})


def create_drawing(request: Request) -> JSONResponse:
    body = _object(request)
    key = _idempotency(request)
    if set(body) - {"symbol", "timeframe", "geometry", "as_of"}:
        raise ApiError(400, "REQUEST_INVALID", "drawing contains an unknown field")
    symbol = str(body.get("symbol") or "").strip().upper()
    timeframe = body.get("timeframe")
    geometry = body.get("geometry")
    from gtf_platform.integration.research import SYMBOL_RE

    if not SYMBOL_RE.match(symbol) or timeframe not in {"M", "W", "D"}:
        raise ApiError(400, "REQUEST_INVALID", "drawing symbol or timeframe is invalid")
    if not isinstance(geometry, dict) or geometry.get("type") not in DRAWING_TYPES:
        raise ApiError(400, "REQUEST_INVALID", "drawing geometry type is invalid")
    payload = body_hash(body)
    with _tx(request) as connection:
        kind, object_id = accept_object(connection, idempotency_key=key, payload_hash=payload, kind="DRAWING")
        if kind == "conflict":
            raise ApiError(409, "CONFLICT", "Idempotency-Key was reused with a different body")
        if kind == "existing" and object_id:
            view = drawing_view(connection, object_id)
            return _json(view, status=200)
        view = insert_drawing(connection, symbol, timeframe, body.get("as_of"), geometry)
        bind_object(connection, idempotency_key=key, payload_hash=payload, kind="DRAWING", object_id=view["drawing_id"])
    return _json(view, status=201)


def patch_drawing(request: Request, drawing_id: str) -> dict:
    body = _object(request)
    if set(body) - {"geometry"}:
        raise ApiError(400, "REQUEST_INVALID", "drawing patch accepts only geometry")
    geometry = body.get("geometry")
    if not isinstance(geometry, dict) or geometry.get("type") not in DRAWING_TYPES:
        raise ApiError(400, "REQUEST_INVALID", "drawing geometry is invalid")
    with _tx(request) as connection:
        existing = drawing_view(connection, drawing_id)
        if existing is None:
            raise ApiError(404, "NOT_FOUND", "Drawing was not found")
        view = update_drawing(connection, drawing_id, geometry)
        record_audit(connection, actor="owner", action="drawing.patch", object_id=drawing_id)
    return _ok(view)


def remove_drawing(request: Request, drawing_id: str) -> dict:
    with _tx(request) as connection:
        if not delete_drawing(connection, drawing_id):
            raise ApiError(404, "NOT_FOUND", "Drawing was not found")
        record_audit(connection, actor="owner", action="drawing.delete", object_id=drawing_id)
    return _ok({"deleted": True, "drawing_id": drawing_id})


def get_settings(request: Request) -> dict:
    with _lock(request):
        return _ok(read_settings(request.app.state.db))


def patch_settings_route(request: Request) -> dict:
    body = _object(request)
    if not body:
        raise ApiError(400, "REQUEST_INVALID", "settings patch is empty")
    unknown = set(body) - set(SETTING_KEYS)
    if unknown:
        raise ApiError(400, "REQUEST_INVALID", "settings patch contains an unknown field")
    changes = {}
    for key, value in body.items():
        if not isinstance(value, SETTING_KEYS[key]):
            raise ApiError(400, "REQUEST_INVALID", "settings field %s has the wrong type" % key)
        if key == "risk_stage" and value is not None and value not in {"LEARNING", "INTERMEDIATE", "PROFESSIONAL"}:
            raise ApiError(400, "REQUEST_INVALID", "risk_stage is not a known stage")
        if key == "log_retention_days" and (isinstance(value, bool) or value < 1 or value > 3650):
            raise ApiError(400, "REQUEST_INVALID", "log_retention_days is out of range")
        if key == "assistant_payload_policy" and value not in {"citations-only", "disabled"}:
            raise ApiError(400, "REQUEST_INVALID", "assistant_payload_policy is not supported")
        changes[key] = value
    with _tx(request) as connection:
        _before, after = patch_settings(connection, changes)
    return _ok(after)


def get_job_route(request: Request, job_id: str) -> dict:
    with _lock(request):
        row = get_job(request.app.state.db, job_id)
    if row is None:
        raise ApiError(404, "NOT_FOUND", "Job was not found")
    from gtf_platform.store import job_view

    return _ok(job_view(row))


def audit(request: Request, object_id: str = "") -> dict:
    if not object_id:
        raise ApiError(400, "REQUEST_INVALID", "object_id is required")
    with _lock(request):
        return _ok({"events": list_audit(request.app.state.db, object_id)})


def explain_symbol(request: Request, symbol: str, scan_key: str = "", include_fixtures: bool = False) -> dict:
    if not scan_key:
        raise ApiError(400, "REQUEST_INVALID", "scan_key is required")
    row = _load_scan(request, scan_key, include_fixtures)
    envelope = json.loads(row["envelope_json"])
    from gtf_platform.integration import desk

    return _ok(desk.explain_symbol(envelope, symbol))


def list_plans_route(
    request: Request,
    state: str = "",
    symbol: str = "",
    scan_key: str = "",
    limit: int = 100,
) -> dict:
    from gtf_platform.integration import desk
    from gtf_platform.planning import service as planning

    with _tx(request) as connection:
        report = desk.sync_plans_from_journal(_settings(request), connection)
        listed = planning.list_plans(
            connection,
            state=state or None,
            symbol=symbol or None,
            scan_key=scan_key or None,
            limit=limit,
        )
    listed["plans"] = [desk.annotate_journal(item, report) for item in listed["plans"]]
    listed["journal_synced"] = report["synced"]
    return _ok(listed)


def create_plan_route(request: Request) -> JSONResponse:
    body = _object(request)
    scan_key = body.get("scan_key")
    symbol = body.get("symbol")
    zone_id = body.get("zone_id")
    if not isinstance(scan_key, str) or not isinstance(symbol, str) or not isinstance(zone_id, str):
        raise ApiError(400, "REQUEST_INVALID", "scan_key, symbol, and zone_id are required")
    opportunity_id = body.get("opportunity_id")
    if opportunity_id is not None and not isinstance(opportunity_id, str):
        raise ApiError(400, "REQUEST_INVALID", "opportunity_id must be a string when supplied")
    rationale = body.get("rationale")
    if rationale is not None and not isinstance(rationale, str):
        raise ApiError(400, "REQUEST_INVALID", "rationale must be a string when supplied")
    include = request.query_params.get("include_fixtures") == "true"
    row = _load_scan(request, scan_key, include)
    envelope = json.loads(row["envelope_json"])
    from gtf_platform.integration import desk

    with _tx(request) as connection:
        view = desk.create_plan(
            connection,
            envelope,
            scan_key,
            symbol,
            zone_id,
            opportunity_id=opportunity_id,
            rationale=rationale,
            fixture=bool(row["fixture"]),
        )
    return _json(view, status=201, fixture=bool(row["fixture"]))


def preview_plan_route(request: Request, plan_id: str) -> dict:
    from gtf_platform.integration import desk

    with _tx(request) as connection:
        report = desk.sync_plans_from_journal(_settings(request), connection, plan_ids=[plan_id])
        view = desk.preview_plan(_settings(request), connection, plan_id)
    return _ok(desk.annotate_journal(view, report))


def approve_plan_route(request: Request, plan_id: str) -> dict:
    body = _object(request)
    from gtf_platform.integration import desk

    with _lock(request):
        row = request.app.state.db.execute("SELECT scan_key FROM trade_plan WHERE plan_id = ?", (plan_id,)).fetchone()
    if row is None:
        raise ApiError(404, "NOT_FOUND", "Plan was not found")
    with _lock(request):
        stored = get_scan(request.app.state.db, row["scan_key"])
    if stored is None:
        raise ApiError(404, "NOT_FOUND", "Scan was not found")
    envelope = json.loads(stored["envelope_json"])
    scan = envelope.get("scan")
    if not isinstance(scan, dict):
        raise ApiError(422, "DATA_INSUFFICIENT", "The stored envelope has no scan record")
    with _tx(request) as connection:
        view = desk.approve_plan(_settings(request), connection, plan_id, body, scan)
        report = desk.sync_plans_from_journal(_settings(request), connection, plan_ids=[plan_id])
    return _ok(desk.annotate_journal(view, report))


def submit_plan_route(request: Request, plan_id: str) -> dict:
    body = _object(request)
    from gtf_platform.planning import service as planning

    with _tx(request) as connection:
        return _ok(planning.submit_for_review(connection, plan_id, note=body.get("note")))


def reject_plan_route(request: Request, plan_id: str) -> dict:
    body = _object(request)
    from gtf_platform.planning import service as planning

    with _tx(request) as connection:
        return _ok(planning.reject_plan(connection, plan_id, reason=body.get("reason") or ""))


def cancel_plan_route(request: Request, plan_id: str) -> dict:
    body = _object(request)
    from gtf_platform.integration import desk
    from gtf_platform.planning import service as planning

    with _tx(request) as connection:
        # P4-IR-04: mirror a journal-side cancel first, so a cancel after it is idempotent.
        report = desk.sync_plans_from_journal(_settings(request), connection, plan_ids=[plan_id])
        view = planning.cancel_plan(connection, plan_id, reason=body.get("reason") or "")
    return _ok(desk.annotate_journal(view, report))


def reopen_plan_route(request: Request, plan_id: str) -> dict:
    from gtf_platform.planning import service as planning

    with _tx(request) as connection:
        return _ok(planning.reopen_draft(connection, plan_id))


def plan_rationale_route(request: Request, plan_id: str) -> dict:
    body = _object(request)
    from gtf_platform.planning import service as planning

    with _tx(request) as connection:
        return _ok(planning.set_rationale(connection, plan_id, body.get("rationale") if isinstance(body.get("rationale"), str) else ""))


def plan_notes_route(request: Request, plan_id: str) -> dict:
    from gtf_platform.planning import service as planning

    with _lock(request):
        return _ok(planning.list_notes(request.app.state.db, plan_id))


def add_plan_note_route(request: Request, plan_id: str) -> dict:
    body = _object(request)
    from gtf_platform.planning import service as planning

    with _tx(request) as connection:
        return _ok(planning.add_note(connection, plan_id, body.get("body") or ""))


def plan_history_route(request: Request, plan_id: str) -> dict:
    from gtf_platform.integration import desk
    from gtf_platform.planning import service as planning

    with _tx(request) as connection:
        desk.sync_plans_from_journal(_settings(request), connection, plan_ids=[plan_id])
        return _ok(planning.history(connection, plan_id))


def _journal_filters(request: Request) -> dict:
    q = request.query_params
    filters: dict = {}
    for key in (
        "symbol", "state", "month", "trade_type", "direction", "review_status",
        "mistake_category", "outcome_class", "setup_label", "charges_state",
        "sort", "order",
    ):
        if key in q and q.get(key) not in (None, ""):
            filters[key] = q.get(key)
    if "open" in q and q.get("open") not in (None, ""):
        raw = q.get("open", "").lower()
        if raw not in ("true", "false", "1", "0"):
            raise ApiError(400, "REQUEST_INVALID", "open must be true or false")
        filters["open"] = raw in ("true", "1")
    if "limit" in q and q.get("limit") not in (None, ""):
        try:
            filters["limit"] = int(q.get("limit"))
        except ValueError as exc:
            raise ApiError(400, "REQUEST_INVALID", "limit must be an integer") from exc
    if "offset" in q and q.get("offset") not in (None, ""):
        try:
            filters["offset"] = int(q.get("offset"))
        except ValueError as exc:
            raise ApiError(400, "REQUEST_INVALID", "offset must be an integer") from exc
    return filters


def journal_route(request: Request) -> dict:
    from gtf_platform.integration import desk

    return _ok(desk.journal_rows(_settings(request), _journal_filters(request)))


def journal_detail_route(request: Request, entry_id: int) -> dict:
    from gtf_platform.integration import desk

    return _ok(desk.journal_detail(_settings(request), entry_id))


def journal_performance_route(request: Request) -> dict:
    from gtf_platform.integration import desk

    return _ok(desk.journal_performance_view(_settings(request), _journal_filters(request)))


def journal_export_route(request: Request) -> dict:
    from gtf_platform.integration import desk

    return _ok(desk.journal_export_view(_settings(request), _journal_filters(request)))


def journal_note_route(request: Request, entry_id: int) -> dict:
    from gtf_platform.integration import desk

    return _ok(desk.add_journal_note(_settings(request), entry_id, _object(request), _optional_key(request)))


def journal_review_route(request: Request, entry_id: int) -> dict:
    from gtf_platform.integration import desk

    return _ok(desk.add_journal_review(_settings(request), entry_id, _object(request), _optional_key(request)))


def journal_attachment_route(request: Request, entry_id: int) -> dict:
    from gtf_platform.integration import desk

    return _ok(desk.add_journal_attachment(_settings(request), entry_id, _object(request), _optional_key(request)))


def journal_attachment_get_route(request: Request, entry_id: int, attachment_id: str):
    import base64

    from gtf_platform.integration import desk

    payload, content_type, filename = desk.read_journal_attachment(
        _settings(request), entry_id, attachment_id,
    )
    return _ok({
        "entry_id": entry_id,
        "attachment_id": attachment_id,
        "filename": filename,
        "content_type": content_type,
        "content_base64": base64.b64encode(payload).decode("ascii"),
        "authorises_order": False,
    })


def submit_order_route(request: Request, entry_id: int) -> dict:
    from gtf_platform.integration import desk

    return _ok(desk.submit_order(_settings(request), entry_id, _object(request), _optional_key(request)))


def record_event_route(request: Request, entry_id: int) -> dict:
    from gtf_platform.integration import desk

    result = desk.record_event(_settings(request), entry_id, _object(request), _optional_key(request))
    # The journal event is committed and authoritative. Mirror it onto linked plans now;
    # if this step fails, the next plan read or startup repairs it (P4-IR-04).
    try:
        with _tx(request) as connection:
            report = desk.sync_plans_from_journal(_settings(request), connection, entry_id=entry_id)
        result["plan_sync"] = {"status": "APPLIED", "synced": report["synced"]}
    except Exception:
        result["plan_sync"] = {"status": "PENDING_REPAIR_ON_READ", "synced": []}
    return _ok(result)


def record_execution_route(request: Request, entry_id: int) -> dict:
    from gtf_platform.integration import desk

    return _ok(desk.record_execution(_settings(request), entry_id, _object(request), _optional_key(request)))


def record_charges_route(request: Request, entry_id: int) -> dict:
    from gtf_platform.integration import desk

    return _ok(desk.record_charges(_settings(request), entry_id, _object(request), _optional_key(request)))


def portfolio_route(request: Request, at: str = "") -> dict:
    from gtf_platform.integration import desk

    return _ok(desk.portfolio_view(_settings(request), at))


def export_route(request: Request, scan_key: str, name: str) -> dict:
    from gtf_platform.integration import desk

    payload, _media = desk.export_report(_settings(request), scan_key, name)
    text = payload.decode("utf-8")
    return _ok({"filename": name, "body": text, "bytes_match_stored_file": True})


def backup_route(request: Request) -> dict:
    from gtf_platform.integration import desk

    body = _object(request)
    raw = body.get("directory")
    if isinstance(raw, str) and raw:
        directory = Path(raw)
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        directory = _settings(request).data_dir / "backups" / stamp
    return _ok(desk.backup_to(_settings(request), directory))


def restore_route(request: Request) -> dict:
    from gtf_platform.integration import desk

    body = _object(request)
    raw = body.get("directory")
    if not isinstance(raw, str) or not raw:
        raise ApiError(400, "REQUEST_INVALID", "directory is required")
    return _ok(desk.restore_copy(_settings(request), Path(raw)))


def backtest_route(request: Request) -> dict:
    from gtf_platform.integration import desk

    return _ok(desk.run_backtest(_settings(request), _object(request)))


def _load_scan(request: Request, scan_key: str, include_fixtures: bool):
    with _lock(request):
        row = get_scan(request.app.state.db, scan_key)
    if row is None or (row["fixture"] and not include_fixtures):
        raise ApiError(404, "NOT_FOUND", "Scan was not found")
    return row


def _watch_or_404(connection, watchlist_id: str) -> dict:
    from gtf_platform.store import watchlist_view

    row = connection.execute(
        "SELECT watchlist_id FROM watchlist WHERE watchlist_id = ?",
        (watchlist_id,),
    ).fetchone()
    if row is None:
        raise ApiError(404, "NOT_FOUND", "Watchlist was not found")
    return watchlist_view(connection, watchlist_id)


def _watch_body(body: dict, require_name: bool) -> tuple[str, list[str], list[dict] | None]:
    if set(body) - {"name", "symbols", "items"}:
        raise ApiError(400, "REQUEST_INVALID", "watchlist contains an unknown field")
    name = _name(body.get("name")) if require_name or body.get("name") is not None else ""
    items = _watch_items(body["items"]) if body.get("items") is not None else None
    if body.get("symbols") is not None:
        symbols = _symbols(body.get("symbols") or [])
    elif items is not None:
        symbols = [item["symbol"] for item in items]
    else:
        symbols = []
    return name, symbols, items


def _watch_items(values) -> list[dict]:
    if not isinstance(values, list):
        raise ApiError(400, "REQUEST_INVALID", "items must be a list")
    from gtf_platform.integration.research import SYMBOL_RE

    cleaned: list[dict] = []
    seen: set[str] = set()
    for item in values:
        if not isinstance(item, dict):
            raise ApiError(400, "REQUEST_INVALID", "items must be objects")
        if set(item) - {"symbol", "reason", "note"}:
            raise ApiError(400, "REQUEST_INVALID", "watchlist item contains an unknown field")
        symbol_raw = item.get("symbol")
        if not isinstance(symbol_raw, str):
            raise ApiError(400, "REQUEST_INVALID", "item.symbol is required")
        symbol = symbol_raw.strip().upper()
        if not SYMBOL_RE.match(symbol):
            raise ApiError(400, "REQUEST_INVALID", "A symbol is not a usable ticker")
        if symbol in seen:
            continue
        seen.add(symbol)
        reason = item.get("reason")
        note = item.get("note")
        if reason is not None and not isinstance(reason, str):
            raise ApiError(400, "REQUEST_INVALID", "item.reason must be a string")
        if note is not None and not isinstance(note, str):
            raise ApiError(400, "REQUEST_INVALID", "item.note must be a string")
        cleaned.append(
            {
                "symbol": symbol,
                "reason": None if reason is None else reason.strip()[:500] or None,
                "note": None if note is None else note.strip()[:2000] or None,
            }
        )
    return cleaned


def _name(value) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 80:
        raise ApiError(400, "REQUEST_INVALID", "name is required")
    return value.strip()


def _symbols(values) -> list[str]:
    if not isinstance(values, list):
        raise ApiError(400, "REQUEST_INVALID", "symbols must be a list")
    from gtf_platform.integration.research import SYMBOL_RE

    cleaned = []
    for item in values:
        if not isinstance(item, str):
            raise ApiError(400, "REQUEST_INVALID", "symbols must be strings")
        symbol = item.strip().upper()
        if not SYMBOL_RE.match(symbol):
            raise ApiError(400, "REQUEST_INVALID", "A symbol is not a usable ticker")
        if symbol not in cleaned:
            cleaned.append(symbol)
    return cleaned


def _json_body(request: Request) -> dict:
    raw = getattr(request.state, "raw_body", None)
    if raw is None:
        raise ApiError(400, "REQUEST_INVALID", "JSON object is required")
    try:
        body = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ApiError(400, "REQUEST_INVALID", "Malformed JSON") from exc
    reject_mixed_fixture(body)
    if not isinstance(body, dict):
        raise ApiError(400, "REQUEST_INVALID", "JSON object is required")
    return body


def _object(request: Request) -> dict:
    body = _json_body(request)
    return body


def _optional_key(request: Request) -> str | None:
    key = request.headers.get("idempotency-key", "").strip()
    if not key:
        return None
    if len(key) > 200:
        raise ApiError(400, "REQUEST_INVALID", "Idempotency-Key is too long")
    return key


def _idempotency(request: Request) -> str:
    key = request.headers.get("idempotency-key", "").strip()
    if not key or len(key) > 200:
        raise ApiError(400, "REQUEST_INVALID", "Idempotency-Key is required")
    return key


def _settings(request: Request) -> Settings:
    return request.app.state.settings


def _lock(request: Request):
    return request.app.state.db_lock


class _tx:
    def __init__(self, request: Request) -> None:
        self.request = request
        self.connection = request.app.state.db
        self.lock = request.app.state.db_lock

    def __enter__(self):
        self.lock.acquire()
        self.connection.execute("BEGIN IMMEDIATE")
        return self.connection

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            if exc_type is None:
                self.connection.commit()
            else:
                self.connection.rollback()
        finally:
            self.lock.release()


def _ok(data: dict, fixture: bool = False) -> dict:
    meta = {"fixture": fixture}
    if fixture:
        meta["fixture_label"] = "FIXTURE_NOT_MARKET_DATA"
    return {"platform_schema": SCHEMA, "data": data, "meta": meta}


def _json(data: dict, status: int = 200, fixture: bool = False, engine: bool = False) -> JSONResponse:
    meta = {"fixture": bool(fixture)}
    if fixture:
        meta["fixture_label"] = "FIXTURE_NOT_MARKET_DATA"
    if engine:
        meta["engine_schema"] = "research-pipeline/1"
    return JSONResponse(status_code=status, content={"platform_schema": SCHEMA, "data": data, "meta": meta})
