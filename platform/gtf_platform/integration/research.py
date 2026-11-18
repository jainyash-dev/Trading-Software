"""Call nse.research.pipeline and return its envelope unchanged.

This module does not import the scanner or the qualification gates. Status
strings are whatever the pipeline stored.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from gtf_platform.config import Settings
from gtf_platform.errors import ApiError
from gtf_platform.integration import sources

SYMBOL_RE = re.compile(r"^[A-Z0-9][A-Z0-9&.-]{0,24}$")
MODES = {"MANUAL": "manual", "SCHEDULED": "scheduled", "REPLAY": "replay"}
SECRET_KEYS = {"password", "otp", "token", "secret", "api_key", "cookie", "session"}


class WorkError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class Plan:
    disposition: str
    stored: dict
    fixture: bool
    progress_total: int | None
    error_code: str | None = None
    error_message: str | None = None
    research_key: str | None = None


def prepare(settings: Settings, body: dict) -> Plan:
    sources.assert_fixture_isolation(settings)
    mode = body.get("mode")
    if mode not in MODES:
        raise ApiError(400, "REQUEST_INVALID", "mode must be MANUAL, SCHEDULED, or REPLAY")
    trade_type = body.get("trade_type") or "MIT"
    as_of_text = body.get("as_of")
    if not isinstance(as_of_text, str) or not as_of_text.strip():
        raise ApiError(400, "REQUEST_INVALID", "as_of is required")
    dataset_id = body.get("dataset_id")
    if not isinstance(dataset_id, str) or not dataset_id.strip():
        raise ApiError(400, "REQUEST_INVALID", "dataset_id is required")
    identity = sources.dataset_identity(settings)
    if identity is None:
        raise ApiError(422, "DATA_INSUFFICIENT", "No accepted local market data is configured")
    if dataset_id != identity["dataset_id"]:
        raise ApiError(409, "CONFLICT", "dataset_id does not match the local files")
    if identity["fixture"] and not sources.fixture_source(settings):
        raise ApiError(422, "REQUEST_INVALID", "Fixture inputs are not a market dataset")
    symbols, universe_mode, universe_label = _universe_request(body.get("universe"))
    risk = _risk_request(body.get("risk"))
    sources.ensure_repo_on_path()
    from nse.research import inputs as inputs_mod
    from nse.research import models as models
    from nse.research import pipeline

    if trade_type not in models.TRADE_TYPES:
        raise ApiError(400, "REQUEST_INVALID", "trade_type is not a known research trade type")
    try:
        as_of = inputs_mod.parse_as_of(as_of_text.strip())
    except ValueError as exc:
        raise ApiError(400, "REQUEST_INVALID", "as_of is not a date or timestamp") from exc
    calendar = _calendar(settings)
    classification = _classify(calendar, as_of.date())
    if classification == "UNRESOLVED":
        return _terminal(
            "SKIPPED_UNRESOLVED_CALENDAR",
            settings,
            mode,
            as_of,
            trade_type,
            universe_mode,
            universe_label,
            symbols,
            dataset_id,
            risk,
            "CALENDAR_UNRESOLVED",
            "The calendar cannot classify this date",
        )
    if classification == "UNCOVERED":
        raise ApiError(422, "DATA_INSUFFICIENT", "The calendar does not cover as_of")
    if mode == "SCHEDULED" and calendar is None:
        raise ApiError(422, "DATA_INSUFFICIENT", "A scheduled scan needs the NSE calendar")
    if mode == "SCHEDULED" and classification in {"HOLIDAY", "WEEKEND", "EXCLUDED_MUHURAT", "EXCLUDED_SHORTENED"}:
        return _terminal(
            "SKIPPED_HOLIDAY",
            settings,
            mode,
            as_of,
            trade_type,
            universe_mode,
            universe_label,
            symbols,
            dataset_id,
            risk,
            "SKIPPED_HOLIDAY",
            "The NSE calendar does not treat this date as a normal session",
        )
    newest = sources.newest_session(settings)
    if newest is not None and as_of.date() > newest:
        raise ApiError(422, "DATA_INSUFFICIENT", "Accepted data does not cover as_of")
    if universe_mode == "SUPPORTED":
        symbols = _supported_symbols(settings, as_of.date())
    if not symbols:
        raise ApiError(422, "DATA_INSUFFICIENT", "The universe has no members at as_of")
    portfolio = _read_portfolio(settings, pipeline, as_of)
    research_key = _predict_key(
        pipeline,
        models.PIPELINE_VERSION,
        as_of,
        trade_type,
        dataset_id,
        MODES[mode],
        universe_label if universe_mode == "LIST" else "SUPPORTED",
        symbols,
        portfolio,
    )
    stored = _stored(
        mode,
        as_of,
        as_of_text.strip(),
        trade_type,
        universe_mode,
        universe_label if universe_mode == "LIST" else "SUPPORTED",
        symbols,
        dataset_id,
        risk,
        research_key,
        portfolio,
    )
    if mode == "SCHEDULED" and not sources.session_file_ready(settings, as_of.date()):
        return Plan("PENDING_DATA", stored, sources.fixture_source(settings), len(symbols), research_key=research_key)
    return Plan("RUN", stored, sources.fixture_source(settings), len(symbols), research_key=research_key)


def session_ready(settings: Settings, stored: dict) -> bool:
    sources.ensure_repo_on_path()
    from nse.research import inputs as inputs_mod

    if stored.get("mode") != "SCHEDULED":
        return True
    as_of = inputs_mod.parse_as_of(stored["as_of_text"])
    return sources.session_file_ready(settings, as_of.date())


def execute(settings: Settings, stored: dict) -> dict:
    """Run the pipeline. The returned envelope is the pipeline object, not a rewrite."""
    sources.assert_fixture_isolation(settings)
    sources.ensure_repo_on_path()
    from nse.research import inputs as inputs_mod
    from nse.research import marketdata
    from nse.research import models as models
    from nse.research import pipeline
    from nse.research import universe as universe_mod

    identity = sources.dataset_identity(settings)
    if identity is None or identity["dataset_id"] != stored["dataset_id"]:
        raise WorkError("DATA_INSUFFICIENT", "Local files no longer match dataset_id")
    as_of = inputs_mod.parse_as_of(stored["as_of_text"])
    trade_type = stored["trade_type"]
    symbols = list(stored["symbols"])
    if stored["universe_mode"] == "SUPPORTED":
        universe = universe_mod.load(str(settings.universe_path), name="SUPPORTED")
        symbols = [row.symbol for row in universe.members(as_of.date())]
    else:
        universe = universe_mod.adhoc(symbols)
    calendar = _calendar(settings)
    notes = list(stored.get("notes") or [])
    portfolio = _portfolio_from_stored(pipeline, stored.get("portfolio") or {}, as_of)
    risk_config = _risk_config(stored.get("risk"))
    if trade_type == models.MIT:
        try:
            loaded = inputs_mod.load(
                symbols,
                csv_dir=str(settings.csv_dir) if settings.csv_dir else None,
                bhavcopy_dir=str(settings.bhavcopy_dir) if settings.bhavcopy_dir else None,
                manifest=str(settings.eod_manifest) if settings.eod_manifest else None,
                series=settings.series,
                source_label=settings.source_label,
                price_adjustment=settings.price_adjustment,
                instrument_records=str(settings.instruments_path) if settings.instruments_path else None,
            )
        except inputs_mod.InputSourceError as exc:
            raise WorkError("DATA_INSUFFICIENT", str(exc)) from exc
    else:
        loaded = [
            marketdata.DailyInput(symbol, [], {"source": settings.source_label}, [], [])
            for symbol in symbols
        ]
    actions, coverage = _corporate_actions(settings, inputs_mod)
    # ScanConfig is the pipeline input record. pipeline.run is the only scan call.
    config = pipeline.scanner.ScanConfig(
        as_of=as_of,
        trade_type=trade_type,
        calendar=calendar,
        calendar_label="NSE" if calendar is not None else "NONE",
        generated_at=None,
        universe_label=stored["universe_label"],
        corporate_actions=actions,
        corporate_action_coverage=coverage,
    )
    done = pipeline.run(
        loaded,
        config,
        universe,
        risk_config,
        portfolio,
        stored["dataset_id"],
        notes,
        stored["invocation"],
        symbols,
    )
    envelope = done.envelope
    if envelope.get("authorises_order") not in (False,):
        raise WorkError("INTERNAL", "Research envelope did not keep authorises_order false")
    _attach_reports(settings, done, envelope, stored)
    text = pipeline.canonical(envelope)
    return {
        "completeness": envelope.get("completeness"),
        "scan_key": envelope.get("idempotency_key"),
        "dataset_id": envelope.get("dataset_id"),
        "envelope": envelope,
        "envelope_json": text,
        "fixture": _envelope_fixture(envelope, settings),
        "symbols_done": len(envelope.get("symbols") or []),
        "symbols_total": len(symbols),
    }


def _attach_reports(settings: Settings, done, envelope: dict, stored: dict) -> None:
    """Write the existing report files and a run manifest beside the scan. No second writer."""
    from nse.research import reports, run_manifest

    scan_key = envelope.get("idempotency_key") or "scan"
    folder = settings.data_dir / "reports" / str(scan_key)
    written = reports.write_all(done.result, str(folder))
    paths = run_manifest.scan_input_paths(_report_args(settings), loads_data=True)
    manifest = run_manifest.build(
        "research",
        envelope.get("as_of"),
        {"dataset_id": stored.get("dataset_id"), "trade_type": envelope.get("trade_type"), "invocation": stored.get("invocation")},
        paths,
        list(envelope.get("limitations") or []),
    )
    run_manifest.write(manifest, str(folder), written)
    envelope["manifest_id"] = manifest["run_id"]
    envelope["report_files"] = written


def _report_args(settings: Settings):
    return type("ReportArgs", (), {
        "csv_dir": str(settings.csv_dir) if settings.csv_dir else None,
        "bhavcopy_dir": str(settings.bhavcopy_dir) if settings.bhavcopy_dir else None,
        "manifest": str(settings.eod_manifest) if settings.eod_manifest else None,
        "calendar": str(settings.calendar_dir) if settings.calendar_dir else None,
        "universe": str(settings.universe_path) if settings.universe_path else None,
        "instruments": str(settings.instruments_path) if settings.instruments_path else None,
        "corporate_actions": str(settings.corporate_actions_path) if settings.corporate_actions_path else None,
    })()


def _envelope_fixture(envelope: dict, settings: Settings) -> bool:
    if sources.fixture_source(settings):
        return True
    limitations = envelope.get("limitations") or []
    notes = envelope.get("research_notes") or []
    return "FIXTURE_NOT_MARKET_DATA" in limitations or "FIXTURE_NOT_MARKET_DATA" in notes


def _predict_key(pipeline, pipeline_version, as_of, trade_type, dataset_id, invocation, universe_label, symbols, portfolio):
    stub = {
        "as_of": as_of.isoformat(),
        "trade_type": trade_type,
        "dataset_id": dataset_id,
        "invocation": invocation,
        "scan": {"universe": universe_label},
        "methodology": {"pipeline_version": pipeline_version},
        "symbols": [{"symbol": symbol} for symbol in sorted(symbols)],
        "symbols_not_opened": [],
        "portfolio": {
            "trades_this_month": portfolio["trades_this_month"],
            "open_positions": portfolio["open_positions"],
        },
    }
    return pipeline.idempotency_key(stub)


def _read_portfolio(settings: Settings, pipeline, as_of) -> dict:
    empty = {"trades_this_month": None, "open_positions": None, "zones": None, "source": "not_supplied", "notes": []}
    if settings.research_db is None or not settings.research_db.is_file():
        return empty
    notes: list[str] = []
    try:
        connection = pipeline.store.open_readonly(str(settings.research_db))
        try:
            journal = pipeline.PortfolioState.from_journal(connection, as_of)
        finally:
            connection.close()
    except Exception:
        notes.append("JOURNAL_NOT_READABLE")
        empty["notes"] = notes
        return empty
    merged = pipeline.merge_portfolio(pipeline.PortfolioState(), journal, notes)
    zones = None if merged.zones_holding_allowance is None else [list(zone) for zone in merged.zones_holding_allowance]
    return {
        "trades_this_month": merged.trades_this_month,
        "open_positions": merged.open_positions,
        "zones": zones,
        "source": merged.source,
        "notes": notes,
    }


def _portfolio_from_stored(pipeline, snapshot: dict, as_of):
    zones = snapshot.get("zones")
    allowance = None if zones is None else tuple(tuple(zone) for zone in zones)
    return pipeline.PortfolioState(
        snapshot.get("trades_this_month"),
        snapshot.get("open_positions"),
        allowance,
        snapshot.get("source") or "not_supplied",
        as_of.isoformat(),
    )


def _risk_config(risk: dict | None):
    if not risk:
        return None
    from nse.research.risk import RiskConfig

    try:
        return RiskConfig(
            capital=float(risk["capital"]),
            rpt_amount=None if risk.get("rpt_amount") is None else float(risk["rpt_amount"]),
            rpt_pct=None if risk.get("rpt_pct") is None else float(risk["rpt_pct"]),
            stage=risk.get("stage"),
        )
    except (TypeError, ValueError) as exc:
        raise WorkError("REQUEST_INVALID", "risk inputs were refused") from exc


def _corporate_actions(settings: Settings, inputs_mod):
    if settings.corporate_actions_path is None:
        return None, None
    return inputs_mod.corporate_action_config(str(settings.corporate_actions_path))


def _calendar(settings: Settings):
    if settings.calendar_dir is None:
        return None
    try:
        return sources.load_calendar(settings)
    except Exception as exc:
        raise WorkError("DATA_INSUFFICIENT", "The NSE calendar could not be loaded") from exc


def _classify(calendar, day) -> str:
    if calendar is None:
        return "NO_CALENDAR"
    sources.ensure_repo_on_path()
    from nse.research.deps import calendar as calendar_mod

    try:
        return calendar.session_type(day)
    except calendar_mod.CalendarAmbiguityError:
        return "UNRESOLVED"
    except calendar_mod.CalendarCoverageError:
        return "UNCOVERED"


def _supported_symbols(settings: Settings, day) -> list[str]:
    if settings.universe_path is None or not settings.universe_path.is_file():
        raise ApiError(422, "DATA_INSUFFICIENT", "No universe file is configured")
    sources.ensure_repo_on_path()
    from nse.research import universe as universe_mod

    try:
        universe = universe_mod.load(str(settings.universe_path), name="SUPPORTED")
    except universe_mod.UniverseError as exc:
        raise ApiError(422, "DATA_INSUFFICIENT", "The universe file was refused") from exc
    return [row.symbol for row in universe.members(day)]


def _universe_request(value):
    if value == "SUPPORTED":
        return [], "SUPPORTED", "SUPPORTED"
    if isinstance(value, list) and value:
        symbols = []
        for item in value:
            if not isinstance(item, str):
                raise ApiError(400, "REQUEST_INVALID", "universe symbols must be strings")
            symbol = item.strip().upper()
            if not SYMBOL_RE.match(symbol):
                raise ApiError(400, "REQUEST_INVALID", "A universe symbol is not a usable ticker")
            symbols.append(symbol)
        unique = sorted(set(symbols))
        if len(unique) > 150:
            raise ApiError(400, "REQUEST_INVALID", "A symbol list is limited to 150 tickers")
        return unique, "LIST", "ADHOC"
    raise ApiError(400, "REQUEST_INVALID", "universe must be SUPPORTED or a symbol list")


def _risk_request(value):
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ApiError(400, "REQUEST_INVALID", "risk must be an object")
    allowed = {"capital", "rpt_pct", "rpt_amount", "stage"}
    if set(value) - allowed:
        raise ApiError(400, "REQUEST_INVALID", "risk contains an unknown field")
    if value.get("capital") in (None, ""):
        raise ApiError(400, "REQUEST_INVALID", "risk.capital is required when risk is set")
    has_amount = value.get("rpt_amount") not in (None, "")
    has_pct = value.get("rpt_pct") not in (None, "")
    if has_amount == has_pct:
        raise ApiError(400, "REQUEST_INVALID", "risk needs exactly one of rpt_amount or rpt_pct")
    stage = value.get("stage")
    if stage is not None and stage not in {"LEARNING", "INTERMEDIATE", "PROFESSIONAL"}:
        raise ApiError(400, "REQUEST_INVALID", "risk.stage is not a known stage")
    return {
        "capital": str(value["capital"]),
        "rpt_amount": None if not has_amount else str(value["rpt_amount"]),
        "rpt_pct": None if not has_pct else str(value["rpt_pct"]),
        "stage": stage,
    }


def _terminal(disposition, settings, mode, as_of, trade_type, universe_mode, universe_label, symbols, dataset_id, risk, code, message):
    stored = _stored(
        mode,
        as_of,
        as_of.isoformat() if hasattr(as_of, "isoformat") else as_of,
        trade_type,
        universe_mode,
        universe_label,
        symbols,
        dataset_id,
        risk,
        None,
        {"trades_this_month": None, "open_positions": None, "zones": None, "source": "not_supplied", "notes": []},
    )
    return Plan(
        disposition,
        stored,
        sources.fixture_source(settings),
        len(symbols) or None,
        error_code=code,
        error_message=message,
    )


def _stored(mode, as_of, as_of_text, trade_type, universe_mode, universe_label, symbols, dataset_id, risk, research_key, portfolio):
    return {
        "mode": mode,
        "invocation": MODES[mode],
        "as_of": as_of.isoformat(),
        "as_of_text": as_of_text if isinstance(as_of_text, str) else as_of.isoformat(),
        "trade_type": trade_type,
        "universe_mode": universe_mode,
        "universe_label": universe_label,
        "symbols": list(symbols),
        "dataset_id": dataset_id,
        "risk": risk,
        "research_key": research_key,
        "portfolio": portfolio,
        "notes": list(portfolio.get("notes") or []),
    }


def with_deciding_gates(symbol: dict) -> dict:
    """Attach the research helper's deciding gates. Status fields are copied, not recomputed."""
    sources.ensure_repo_on_path()
    from nse.research.explain import deciding_gates

    copy = dict(symbol)
    candidates = []
    for candidate in symbol.get("candidates") or []:
        item = dict(candidate)
        item["deciding_gates"] = [
            {"status": status, "gates": gates}
            for status, gates in deciding_gates(candidate)
        ]
        candidates.append(item)
    copy["candidates"] = candidates
    return copy


def saved_parameters_ok(parameters: dict) -> None:
    if not isinstance(parameters, dict):
        raise ApiError(400, "REQUEST_INVALID", "parameters must be an object")
    flat = {str(key).lower() for key in parameters}
    if flat & SECRET_KEYS:
        raise ApiError(422, "REQUEST_INVALID", "A saved scan config cannot store a secret")


def canonical_plan_body(body: dict) -> dict:
    """The idempotency body. Wall-clock fields are not part of it."""
    return {
        "mode": body.get("mode"),
        "as_of": body.get("as_of"),
        "trade_type": body.get("trade_type") or "MIT",
        "universe": body.get("universe"),
        "dataset_id": body.get("dataset_id"),
        "risk": body.get("risk"),
    }
