"""Point-in-time candles from accepted local files.

Weekly and monthly bars come from the research replay. Missing sessions are
reported and are not filled. Prices are not adjusted here.

Volume is traded quantity when the source provides it (CSV ``volume`` or
bhavcopy ``TOTTRDQTY`` / ``traded_qty``). Missing volume stays null; it is
never coerced to zero. Zero is only returned when the source states zero.

Weekly and monthly volume is the sum of the constituent daily sessions that
built the HTF candle. It is null (with ``HTF_VOLUME_INCOMPLETE`` or
``HTF_VOLUME_SESSION_MISMATCH``) when any constituent session lacks a stated
volume. A duplicated source session has no stated volume.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from gtf_platform.config import Settings
from gtf_platform.errors import ApiError
from gtf_platform.integration import sources

TIMEFRAMES = ("M", "W", "D")
_CACHE: dict[tuple, dict] = {}

# Chart path never runs the P0 certification matrix. Successful retrieval is not
# CERTIFIED_P0_DATA. Fixtures and non-fixtures are labelled explicitly.
RESEARCH_USE_FIXTURE = "FIXTURE_NOT_MARKET_DATA"
RESEARCH_USE_EXPLORATORY = "EXPLORATORY_ONLY_NOT_CERTIFIED"
VOLUME_UNIT = "TRADED_QUANTITY"


def read_candles(settings: Settings, *, symbol: str, timeframe: str, as_of_text: str, dataset_id: str) -> dict:
    sources.assert_fixture_isolation(settings)
    if timeframe not in TIMEFRAMES:
        raise ApiError(400, "REQUEST_INVALID", "timeframe must be M, W, or D")
    if not isinstance(symbol, str) or not symbol.strip():
        raise ApiError(400, "REQUEST_INVALID", "symbol is required")
    symbol = symbol.strip().upper()
    from gtf_platform.integration.research import SYMBOL_RE

    if not SYMBOL_RE.match(symbol):
        raise ApiError(400, "REQUEST_INVALID", "symbol is not a usable ticker")
    if not as_of_text:
        raise ApiError(400, "REQUEST_INVALID", "as_of is required")
    identity = sources.dataset_identity(settings)
    if identity is None:
        raise ApiError(422, "DATA_INSUFFICIENT", "No accepted local market data is configured")
    if dataset_id != identity["dataset_id"]:
        raise ApiError(409, "CONFLICT", "dataset_id does not match the local files")
    sources.ensure_repo_on_path()
    from nse.research import inputs as inputs_mod

    try:
        as_of = inputs_mod.parse_as_of(as_of_text)
    except ValueError as exc:
        raise ApiError(400, "REQUEST_INVALID", "as_of is not a date or timestamp") from exc
    cache_key = (identity["dataset_id"], symbol, timeframe, as_of.isoformat(), sources.fixture_source(settings))
    cached = _CACHE.get(cache_key)
    if cached is not None:
        return dict(cached)
    try:
        loaded = inputs_mod.load(
            [symbol],
            csv_dir=str(settings.csv_dir) if settings.csv_dir else None,
            bhavcopy_dir=str(settings.bhavcopy_dir) if settings.bhavcopy_dir else None,
            manifest=str(settings.eod_manifest) if settings.eod_manifest else None,
            series=settings.series,
            source_label=settings.source_label,
            price_adjustment=settings.price_adjustment,
            instrument_records=str(settings.instruments_path) if settings.instruments_path else None,
        )
    except inputs_mod.InputSourceError as exc:
        raise ApiError(422, "DATA_INSUFFICIENT", str(exc)[:400]) from exc
    daily = loaded[0]
    calendar = None
    if settings.calendar_dir is not None:
        try:
            calendar = sources.load_calendar(settings)
        except Exception as exc:
            raise ApiError(422, "DATA_INSUFFICIENT", "The NSE calendar could not be loaded") from exc
    visible = [candle for candle in daily.candles if candle.end <= as_of]
    volume_table = _volume_table(settings, symbol)
    payload = _series(
        settings,
        symbol,
        timeframe,
        as_of,
        dataset_id,
        daily,
        visible,
        calendar,
        volume_table,
        identity,
    )
    if len(_CACHE) > 8:
        _CACHE.clear()
    _CACHE[cache_key] = payload
    return dict(payload)


def _series(settings, symbol, timeframe, as_of, dataset_id, daily, visible, calendar, volume_table, identity) -> dict:
    from nse.research.deps import mtf

    limitations = list(daily.limitations)
    findings = [item.to_dict() for item in daily.findings_at(as_of.date())]
    missing = []
    excluded = []
    candles = []
    invalid = []
    if visible:
        try:
            snapshot = mtf.replay(visible, "D", htf=("D", "W", "M"), as_of=as_of, calendar=calendar)
        except ValueError as exc:
            raise ApiError(422, "DATA_INSUFFICIENT", str(exc)[:400]) from None
        limitations = sorted(set(limitations) | set(snapshot.limitations))
        series = snapshot.series.get(timeframe)
        if series is not None:
            excluded_days = {item.date for item in snapshot.excluded_candles}
            base_days = [c.end.date() for c in visible if c.end.date() not in excluded_days]
            htf_volume_codes: set[str] = set()
            for candle in series.candles:
                if timeframe == "D":
                    row = _htf_candle(candle, volume_table)
                else:
                    row = _htf_candle(candle, None)
                    volume, sessions, code = _aggregate_volume(candle, timeframe, base_days, volume_table)
                    row["volume"] = volume
                    row["volume_sessions"] = sessions
                    if code:
                        htf_volume_codes.add(code)
                issues = _validate_candle_row(row)
                if issues:
                    invalid.append({"session_date": row["session_date"], "codes": issues})
                    continue
                candles.append(row)
            limitations.extend(sorted(htf_volume_codes))
            if series.truncated_at:
                limitations.append("SERIES_TRUNCATED")
        missing = [gap.date.isoformat() for gap in snapshot.data_gaps]
        excluded = [
            {"date": item.date.isoformat(), "classification": item.classification}
            for item in snapshot.excluded_candles
        ]
    elif not daily.candles:
        limitations.append("NO_BARS")
    else:
        limitations.append("NO_CANDLES_AT_OR_BEFORE_AS_OF")
    if invalid:
        limitations.append("INVALID_SOURCE_CANDLES_EXCLUDED")
    provenance = _provenance(daily)
    volume_meta = _volume_state(candles, volume_table)
    quality = _data_quality(settings, identity, daily, findings, volume_meta)
    available_from = candles[0]["session_date"] if candles else None
    available_to = candles[-1]["session_date"] if candles else None
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "dataset_id": dataset_id,
        "requested_as_of": as_of.isoformat(),
        "available_from": available_from,
        "available_to": available_to,
        "source": provenance,
        "limitations": limitations,
        "findings": findings,
        "missing_sessions": missing,
        "excluded_sessions": excluded,
        "invalid_candles": invalid,
        "candles": candles,
        "volume_state": volume_meta["volume_state"],
        "volume_unit": VOLUME_UNIT if volume_meta["volume_state"] != "UNSUPPORTED" else None,
        "volume_source": volume_meta["volume_source"],
        "adjusted": False,
        "data_quality": quality,
    }


def _htf_candle(candle, volume_table: dict | None) -> dict:
    session = candle.end.date().isoformat()
    volume = None
    if volume_table and volume_table.get("supported"):
        # Missing key or explicit None => unavailable. "0" stays "0".
        if session in volume_table["by_session"]:
            volume = volume_table["by_session"][session]
    return {
        "time": candle.end.isoformat(),
        "session_date": session,
        "open": _price(candle.open),
        "high": _price(candle.high),
        "low": _price(candle.low),
        "close": _price(candle.close),
        "volume": volume,
    }


def _aggregate_volume(candle, timeframe: str, base_days: list, volume_table: dict) -> tuple[str | None, int | None, str | None]:
    """Weekly/monthly traded quantity = sum of the constituent daily sessions.

    Constituent sessions are the visible, non-excluded daily sessions inside the
    HTF candle's period, i.e. exactly the sessions whose OHLC built the candle.
    The sum is returned only when every constituent session has a stated
    volume (a literal "0" counts as stated). Otherwise the volume is null and a
    limitation code says why. Nothing is filled or estimated.
    """
    if not volume_table.get("supported"):
        return None, None, None
    from nse.research.deps import mtf

    first, last = candle.start.date(), candle.end.date()
    days = [d for d in base_days if first <= d <= last and mtf.period_key(timeframe, d) == candle.period_key]
    if len(days) != candle.sessions_present:
        return None, len(days), "HTF_VOLUME_SESSION_MISMATCH"
    by_session = volume_table.get("by_session") or {}
    total = 0
    for day in days:
        value = by_session.get(day.isoformat())
        if value is None or not _non_negative_int_text(str(value)):
            return None, len(days), "HTF_VOLUME_INCOMPLETE"
        total += int(value)
    return str(total), len(days), None


def _volume_table(settings: Settings, symbol: str) -> dict:
    csv_table = _csv_volumes(settings, symbol)
    if csv_table["supported"]:
        return csv_table
    bhav_table = _bhav_volumes(settings, symbol)
    if bhav_table["supported"]:
        return bhav_table
    return {"supported": False, "volume_source": None, "by_session": {}}


def _csv_volumes(settings: Settings, symbol: str) -> dict:
    if settings.csv_dir is None:
        return {"supported": False, "volume_source": None, "by_session": {}}
    path = settings.csv_dir / ("%s.csv" % symbol)
    if not path.is_file():
        return {"supported": False, "volume_source": None, "by_session": {}}
    import csv

    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or "volume" not in reader.fieldnames:
            return {"supported": False, "volume_source": None, "by_session": {}}
        found: dict[str, str | None] = {}
        duplicates: set[str] = set()
        for row in reader:
            day = (row.get("date") or "").strip()
            if not day:
                continue
            if day in found or day in duplicates:
                # A duplicated source session has no single stated volume.
                duplicates.add(day)
                found[day] = None
                continue
            raw = row.get("volume")
            if raw is None:
                found[day] = None
                continue
            text = str(raw).strip()
            if text == "":
                found[day] = None
                continue
            if not _non_negative_int_text(text):
                found[day] = None
                continue
            found[day] = str(int(text))
        return {"supported": True, "volume_source": "CSV_VOLUME", "by_session": found}


def _bhav_volumes(settings: Settings, symbol: str) -> dict:
    """Map session dates to bhavcopy traded_qty (NSE TOTTRDQTY / UDiFF equivalent)."""
    if settings.bhavcopy_dir is None or settings.csv_dir is not None:
        return {"supported": False, "volume_source": None, "by_session": {}}
    sources.ensure_repo_on_path()
    from nse.research.deps import bhavcopy, replay_mod

    try:
        paths = bhavcopy.archive_paths(str(settings.bhavcopy_dir))
        if settings.eod_manifest is not None and settings.eod_manifest.is_file():
            files = bhavcopy.load_many(paths, manifest=str(settings.eod_manifest))
        else:
            files = bhavcopy.load_many(paths)
        daily = replay_mod.daily_series(files, symbol, settings.series or "EQ")
    except Exception:
        return {"supported": False, "volume_source": None, "by_session": {}}
    if not daily.bars:
        return {"supported": False, "volume_source": None, "by_session": {}}
    found = {}
    for bar in daily.bars:
        qty = bar.traded_qty
        if qty is None:
            found[bar.trade_date.isoformat()] = None
        else:
            found[bar.trade_date.isoformat()] = str(int(qty))
    return {"supported": True, "volume_source": "BHAVCOPY_TOTTRDQTY", "by_session": found}


def _volume_state(candles: list[dict], volume_table: dict) -> dict:
    if not volume_table.get("supported"):
        return {"volume_state": "UNSUPPORTED", "volume_source": None}
    if not candles:
        return {"volume_state": "UNAVAILABLE", "volume_source": volume_table.get("volume_source")}
    present = sum(1 for row in candles if row.get("volume") is not None)
    if present == 0:
        state = "UNAVAILABLE"
    elif present == len(candles):
        state = "PRESENT"
    else:
        state = "PARTIAL"
    return {"volume_state": state, "volume_source": volume_table.get("volume_source")}


def _data_quality(settings, identity, daily, findings, volume_meta) -> dict:
    fixture = bool(identity.get("fixture") or sources.fixture_source(settings))
    research_use = RESEARCH_USE_FIXTURE if fixture else RESEARCH_USE_EXPLORATORY
    identity_status = "UNKNOWN"
    for item in findings:
        code = (item.get("code") or "") if isinstance(item, dict) else ""
        if code in {"UNKNOWN_INSTRUMENT", "IDENTITY_UNRESOLVED", "ISIN_CHANGE"}:
            identity_status = "UNSUPPORTED_OR_UNRESOLVED"
            break
        if code:
            identity_status = "SEE_FINDINGS"
    provenance = daily.provenance or {}
    return {
        "research_use": research_use,
        "certified": False,
        "certification_note": (
            "Chart responses do not run the P0 certification matrix. "
            "Successful candle retrieval is never CERTIFIED_P0_DATA."
        ),
        "fixture": fixture,
        "identity_status": identity_status,
        "price_adjustment": provenance.get("price_adjustment") or settings.price_adjustment or "UNKNOWN",
        "volume_state": volume_meta["volume_state"],
        "volume_source": volume_meta.get("volume_source"),
        "adjusted": False,
        "data_ready": False,
    }


def _validate_candle_row(row: dict) -> list[str]:
    issues = []
    try:
        open_ = Decimal(str(row["open"]))
        high = Decimal(str(row["high"]))
        low = Decimal(str(row["low"]))
        close = Decimal(str(row["close"]))
    except (InvalidOperation, KeyError, TypeError):
        return ["INVALID_OHLC"]
    for value in (open_, high, low, close):
        if not value.is_finite():
            return ["NON_FINITE_OHLC"]
    if high < low:
        issues.append("HIGH_BELOW_LOW")
    if open_ > high or open_ < low or close > high or close < low:
        issues.append("OPEN_CLOSE_OUTSIDE_RANGE")
    volume = row.get("volume")
    if volume is not None and not _non_negative_int_text(str(volume)):
        issues.append("INVALID_VOLUME")
    return issues


def _non_negative_int_text(text: str) -> bool:
    try:
        value = int(text)
    except (TypeError, ValueError):
        return False
    return value >= 0


def _price(value) -> str:
    if isinstance(value, Decimal):
        text = format(value, "f")
    else:
        text = format(Decimal(str(value)), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _provenance(daily) -> dict:
    raw = dict(daily.provenance or {})
    if "file" in raw:
        raw["file"] = str(raw["file"]).rsplit("/", 1)[-1]
    return raw
