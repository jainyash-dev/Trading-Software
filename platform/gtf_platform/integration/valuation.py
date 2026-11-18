"""EOD portfolio marks from accepted local closes (PR-007 / FR-6.3).

Uses the same local CSV or bhavcopy inputs as the chart path. Never invents a
quote, never uses a future session, never claims P0 certification. A missing
close stays UNAVAILABLE. Sector and live drawdown are out of scope here.
"""

from __future__ import annotations

import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from gtf_platform.config import Settings
from gtf_platform.integration import sources

UNAVAILABLE = "UNAVAILABLE"
AVAILABLE = "AVAILABLE"
STALE = "STALE"


def close_on_or_before(settings: Settings, symbol: str, valuation_at) -> dict[str, Any]:
    """Last accepted daily close on or before the valuation date.

    Returns price fields plus an explicit state. Future closes are excluded by
    cutting the series at the valuation instant. Invalid loads and empty history
    are UNAVAILABLE.
    """
    if not isinstance(symbol, str) or not symbol.strip():
        return _unavailable("symbol is required")
    symbol = symbol.strip().upper()
    day = _as_date(valuation_at)
    if day is None:
        return _unavailable("valuation date is invalid")
    if settings.csv_dir is None and settings.bhavcopy_dir is None:
        return _unavailable("No accepted local market data is configured")
    sources.ensure_repo_on_path()
    from nse.research import inputs as inputs_mod

    as_of = datetime.datetime.combine(day, datetime.time(23, 59, 59))
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
        return _unavailable(str(exc)[:400])
    if not loaded:
        return _unavailable("No series was loaded for %s" % symbol)
    daily = loaded[0]
    blocked_from = _earliest_blocking_error_date(daily, day)
    chosen = None
    for candle in daily.candles:
        candle_day = _candle_day(candle)
        # FR-6.3 is date-based: include the session close when its trade date is on or
        # before the valuation date. Never use a later session. An ERROR finding dated
        # on day D blocks that session and later ones, but an earlier accepted close
        # remains usable as STALE.
        if candle_day is None or candle_day > day:
            continue
        if blocked_from is not None and candle_day >= blocked_from:
            continue
        chosen = candle
    if chosen is None:
        if blocked_from is not None:
            return _unavailable(
                "No accepted close on or before %s for %s after data-quality findings from %s"
                % (day.isoformat(), symbol, blocked_from.isoformat())
            )
        return _unavailable("No accepted close on or before %s for %s" % (day.isoformat(), symbol))
    close = _price(getattr(chosen, "close", None))
    if close is None:
        return _unavailable("Close price is missing or invalid for %s" % symbol)
    price_date = _candle_day(chosen)
    state = AVAILABLE if price_date == day else STALE
    return {
        "state": state,
        "close": close,
        "price_date": price_date.isoformat() if price_date else None,
        "valuation_date": day.isoformat(),
        "research_use": _research_use(settings),
        "reason": None if state == AVAILABLE else (
            "Latest accepted close is %s; valuation date is %s" % (price_date.isoformat(), day.isoformat())
        ),
    }


def position_remaining_risk(position: dict) -> dict[str, Any]:
    """Monetary risk on remaining open quantity vs the locked/planned stop (FR-6.4).

    Uses executed remaining quantity and average entry when available. Missing or
    invalid stop geometry is UNAVAILABLE. Never uses planned quantity when an
    executed open quantity exists.
    """
    if not bool(position.get("counts_as_open")):
        return {"position_risk": None, "position_risk_state": UNAVAILABLE, "position_risk_reason": "Position is not open"}
    open_qty = position.get("open_quantity")
    if not isinstance(open_qty, int) or open_qty <= 0:
        return {"position_risk": None, "position_risk_state": UNAVAILABLE, "position_risk_reason": "No remaining open quantity"}
    avg = position.get("average_entry_price")
    if avg is None:
        return {"position_risk": None, "position_risk_state": UNAVAILABLE, "position_risk_reason": "Average entry is unavailable"}
    stop = position.get("locked_stop")
    if stop is None:
        stop = position.get("planned_stop")
    if stop is None:
        return {"position_risk": None, "position_risk_state": UNAVAILABLE, "position_risk_reason": "Stop-loss is missing"}
    try:
        entry = Decimal(str(avg))
        stop_d = Decimal(str(stop))
    except (InvalidOperation, ValueError):
        return {"position_risk": None, "position_risk_state": UNAVAILABLE, "position_risk_reason": "Entry or stop is not numeric"}
    if entry <= 0 or stop_d <= 0:
        return {"position_risk": None, "position_risk_state": UNAVAILABLE, "position_risk_reason": "Entry or stop must be positive"}
    if stop_d >= entry:
        return {
            "position_risk": None,
            "position_risk_state": UNAVAILABLE,
            "position_risk_reason": "Invalid stop geometry for a long: stop must be below average entry",
        }
    risk = ((entry - stop_d) * Decimal(open_qty)).quantize(Decimal("0.01"))
    return {
        "position_risk": float(risk),
        "position_risk_state": AVAILABLE,
        "position_risk_reason": None,
        "risk_per_share": float(entry - stop_d),
        "risk_quantity": open_qty,
    }


def mark_positions(settings: Settings, positions: list[dict], valuation_at) -> dict[str, Any]:
    """Attach per-position marks, remaining risk, and a portfolio valuation summary.

    Closed positions are not marked. Missing closes leave that position and the
    portfolio aggregate UNAVAILABLE. Unrealised P&L uses average entry × remaining
    quantity when both exist; otherwise UNAVAILABLE. Sector exposure stays UNAVAILABLE.
    """
    marked = []
    market_value = Decimal("0")
    unrealised = Decimal("0")
    open_risk = Decimal("0")
    any_open = False
    all_priced = True
    all_risked = True
    any_stale = False
    stale_reasons: list[str] = []
    for position in positions:
        row = dict(position)
        risk = position_remaining_risk(row)
        row.update(risk)
        open_qty = row.get("open_quantity")
        counts_open = bool(row.get("counts_as_open"))
        if not counts_open or not isinstance(open_qty, int) or open_qty <= 0:
            row["valuation"] = None
            row["valuation_state"] = UNAVAILABLE
            row["price_date"] = None
            row["unrealised_pnl"] = UNAVAILABLE if row.get("unrealised") == UNAVAILABLE else row.get("unrealised")
            row["market_value"] = None
            marked.append(row)
            continue
        any_open = True
        if risk["position_risk_state"] != AVAILABLE:
            all_risked = False
        else:
            open_risk += Decimal(str(risk["position_risk"]))
        quote = close_on_or_before(settings, str(row.get("symbol") or ""), valuation_at)
        row["valuation_state"] = quote["state"] if quote["state"] in (AVAILABLE, STALE) else UNAVAILABLE
        row["valuation"] = quote.get("close") if row["valuation_state"] != UNAVAILABLE else None
        row["price_date"] = quote.get("price_date")
        row["valuation_date"] = quote.get("valuation_date")
        row["valuation_reason"] = quote.get("reason")
        row["research_use"] = quote.get("research_use")
        if row["valuation_state"] == STALE:
            any_stale = True
            if quote.get("reason"):
                stale_reasons.append("%s: %s" % (row.get("symbol"), quote["reason"]))
        if row["valuation"] is None:
            all_priced = False
            row["market_value"] = None
            row["unrealised_pnl"] = UNAVAILABLE
        else:
            close = Decimal(str(row["valuation"]))
            qty = Decimal(open_qty)
            value = (close * qty).quantize(Decimal("0.01"))
            row["market_value"] = float(value)
            market_value += value
            avg = row.get("average_entry_price")
            if avg is None:
                row["unrealised_pnl"] = UNAVAILABLE
                all_priced = False
            else:
                pnl = ((close - Decimal(str(avg))) * qty).quantize(Decimal("0.01"))
                row["unrealised_pnl"] = float(pnl)
                unrealised += pnl
        marked.append(row)
    if not any_open:
        portfolio_state = UNAVAILABLE
        reason = "No open position to value"
        total = None
        total_unrealised = UNAVAILABLE
        exposure_state = UNAVAILABLE
        exposure = None
        portfolio_risk_state = UNAVAILABLE
        portfolio_risk = None
    elif not all_priced:
        portfolio_state = UNAVAILABLE
        reason = "One or more open positions have no accepted close on or before the valuation date"
        total = None
        total_unrealised = UNAVAILABLE
        exposure_state = UNAVAILABLE
        exposure = None
        portfolio_risk_state = AVAILABLE if all_risked else UNAVAILABLE
        portfolio_risk = float(open_risk) if all_risked else None
    else:
        # STALE marks remain usable with an explicit price_date (P5 EOD policy),
        # but the portfolio valuation_state must stay STALE so freshness is visible.
        portfolio_state = STALE if any_stale else AVAILABLE
        reason = "; ".join(stale_reasons) if any_stale else None
        total = float(market_value)
        total_unrealised = float(unrealised)
        exposure_state = STALE if any_stale else AVAILABLE
        exposure = total
        portfolio_risk_state = AVAILABLE if all_risked else UNAVAILABLE
        portfolio_risk = float(open_risk) if all_risked else None
    return {
        "positions": marked,
        "valuation": total,
        "valuation_state": portfolio_state,
        "unrealised_pnl": total_unrealised,
        "valuation_reason": reason,
        "exposure": exposure,
        "exposure_state": exposure_state,
        "sector": None,
        "sector_state": UNAVAILABLE,
        "sector_reason": "Sector concentration stays UNAVAILABLE until a sector source exists (D6, FR-6.7)",
        "portfolio_risk": portfolio_risk,
        "portfolio_risk_state": portfolio_risk_state,
        "research_use": _research_use(settings),
    }


def _unavailable(reason: str) -> dict[str, Any]:
    return {
        "state": UNAVAILABLE,
        "close": None,
        "price_date": None,
        "valuation_date": None,
        "research_use": None,
        "reason": reason,
    }


def _research_use(settings: Settings) -> str:
    if getattr(settings, "fixture_mode", False) or (settings.source_label or "").upper() == "FIXTURE":
        return "FIXTURE_NOT_MARKET_DATA"
    return "EXPLORATORY_ONLY_NOT_CERTIFIED"


def _earliest_blocking_error_date(daily, day: datetime.date) -> datetime.date | None:
    """Earliest ERROR finding date that is known by the valuation day.

    Undated ERROR findings block every session (fail closed). Dated ERROR findings
    block that session and later ones only, so a prior accepted close can still mark.
    """
    findings = getattr(daily, "findings", None) or []
    earliest = None
    undated_block = False
    for finding in findings:
        severity = getattr(finding, "severity", None) or getattr(finding, "level", None)
        if str(severity).upper() not in {"ERROR", "ERR"}:
            continue
        known = getattr(finding, "known_at", None)
        if callable(known):
            try:
                if not known(day):
                    continue
            except TypeError:
                pass
        finding_day = getattr(finding, "date", None)
        if finding_day is None:
            undated_block = True
            continue
        if finding_day > day:
            continue
        if earliest is None or finding_day < earliest:
            earliest = finding_day
    if undated_block:
        return datetime.date.min
    return earliest


def _candle_day(candle) -> datetime.date | None:
    end = getattr(candle, "end", None)
    if isinstance(end, datetime.datetime):
        return end.date()
    if isinstance(end, datetime.date):
        return end
    start = getattr(candle, "start", None)
    if isinstance(start, datetime.datetime):
        return start.date()
    if isinstance(start, datetime.date):
        return start
    return None


def _as_date(value) -> datetime.date | None:
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str) and value.strip():
        text = value.strip().replace("Z", "+00:00")
        try:
            return datetime.datetime.fromisoformat(text).date()
        except ValueError:
            try:
                return datetime.date.fromisoformat(text[:10])
            except ValueError:
                return None
    return None


def _as_datetime(value) -> datetime.datetime | None:
    if isinstance(value, datetime.datetime):
        return value.replace(tzinfo=None) if value.tzinfo is not None else value
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return datetime.datetime.combine(value, datetime.time(23, 59, 59))
    if isinstance(value, str) and value.strip():
        text = value.strip().replace("Z", "+00:00")
        try:
            parsed = datetime.datetime.fromisoformat(text)
        except ValueError:
            return None
        return parsed.replace(tzinfo=None) if parsed.tzinfo is not None else parsed
    return None


def _price(value) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        text = str(value).strip().lower()
        if text in {"nan", "inf", "+inf", "-inf", "infinity", "+infinity", "-infinity"}:
            return None
        number = Decimal(text)
    except (InvalidOperation, ValueError):
        return None
    if not number.is_finite() or number <= 0:
        return None
    return float(number)
