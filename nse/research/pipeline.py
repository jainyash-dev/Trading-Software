"""Research orchestration: one deterministic path from inputs to a scan, trade plans and a report.

This module coordinates. It does not detect zones, score freshness, evaluate G0-G8 or size
a position. Those stay in the scanner (the only qualification pathway), the engines it
calls, and risk.py. A candidate status is copied from the scan. A risk plan and a portfolio
check never replace it. Nothing here authorises an order, calls a broker, or reads a clock.

Outputs:
  research.json         this envelope, including the full scan (every symbol and blocked zone)
  trade_plans.json      the plan list; selected_quantity is always null
  research_report.md    ten sections, sorted by symbol, zone creation time and zone id
  plus the existing scan reports and run_manifest.json

ED-45. Standard library only.
"""

import argparse
import dataclasses
import datetime
import hashlib
import json
import os
from dataclasses import dataclass

from nse.research import models as m, narrative, reports, risk, run_manifest, scanner, store

SCHEMA = "research-pipeline/1"
RESEARCH_JSON = "research.json"
TRADE_PLANS_JSON = "trade_plans.json"
REPORT_MD = "research_report.md"
NOT_SUPPLIED = "NOT_SUPPLIED"
AUTHORISES_ORDER = False
HEADINGS = (
    "Scan summary",
    "Universe processed",
    "Data-quality limitations",
    "Eligible candidates",
    "Rejected candidates",
    "Manual-review candidates",
    "Blocked and data-insufficient candidates",
    "Detailed trade plans",
    "Risk and MTF explanations",
    "Reproducibility",
)
_PATH_PARAMS = run_manifest.PATH_PARAMS + ("instruments", "corporate_actions", "journal")
_ORDER_NOTE = ("Rows are ordered by symbol, zone creation time and zone id. "
               "That order is not a quality ranking. pre_entry_score is display only and is not used.")
_NO_ORDER = "This system does not submit orders. No quantity is selected."


def _check(code, outcome, reason, sources):
    return {"code": code, "outcome": outcome, "reason": reason, "sources": list(sources)}


def _day(value):
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    return datetime.date.fromisoformat(str(value)[:10])


def canonical(envelope):
    """Deterministic JSON. Caller-supplied generated_at is inside the embedded scan; no clock is added."""
    return json.dumps(envelope, sort_keys=True, separators=(",", ":"))


def digest(envelope):
    return hashlib.sha256(canonical(envelope).encode()).hexdigest()


def to_json(obj):
    return json.dumps(obj, sort_keys=True, indent=1) + "\n"


@dataclass(frozen=True)
class PortfolioState:
    """Counts already true at as_of. None means the count was not supplied, which is not a pass.

    zones_holding_allowance entries are (symbol, zone_id, trade_type, reason), matching the
    journal's one-order key. None means the allowance was not supplied.
    """

    trades_this_month: int = None
    open_positions: int = None
    zones_holding_allowance: tuple = None
    source: str = "not_supplied"
    as_of: str = None

    def __post_init__(self):
        for name in ("trades_this_month", "open_positions"):
            value = getattr(self, name)
            if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
                raise ValueError("%s must be a whole number >= 0 or None, got %r" % (name, value))
        zones = self.zones_holding_allowance
        if zones is not None:
            for zone in zones:
                if len(zone) != 4 or not all(isinstance(part, str) and part for part in zone[:3]):
                    raise ValueError("a zone allowance entry is (symbol, zone_id, trade_type, reason)")

    @staticmethod
    def from_journal(conn, at):
        raw = store.portfolio_at(conn, at)
        zones = tuple((z["symbol"], z["zone_id"], z["trade_type"], z["reason"])
                      for z in raw["zones_holding_allowance"])
        return PortfolioState(raw["trades_triggered_this_month"], raw["open_positions"], zones,
                              "journal", raw["as_of"])


def merge_portfolio(caller, journal, notes):
    """Combine a caller's counts with a journal snapshot. The larger count is used.

    A caller cannot clear a journal hold by omitting it. Missing on both sides stays missing.
    """
    if journal is None:
        return caller or PortfolioState()
    if caller is None:
        return journal

    def larger(left, right, label):
        if left is None:
            return right
        if right is None:
            return left
        if left != right:
            notes.append("PORTFOLIO_COUNT_DISAGREES: %s caller %s and journal %s; the larger count is used"
                         % (label, left, right))
        return max(left, right)

    zones, journal_zones = caller.zones_holding_allowance, journal.zones_holding_allowance
    if zones is None:
        merged = journal_zones
    elif journal_zones is None:
        merged = zones
    else:
        by = {(z[0], z[1], z[2]): z for z in list(journal_zones) + list(zones)}
        merged = tuple(by[key] for key in sorted(by))
    supplied = any(v is not None for v in (caller.trades_this_month, caller.open_positions,
                                           caller.zones_holding_allowance))
    return PortfolioState(
        larger(caller.trades_this_month, journal.trades_this_month, "trades_this_month"),
        larger(caller.open_positions, journal.open_positions, "open_positions"),
        merged, "caller+journal" if supplied else journal.source, journal.as_of or caller.as_of)


def _risk_config(risk_config, portfolio, notes):
    """Give the existing risk module the monthly count when this snapshot has one.

    Open positions and zone allowance are not risk-config fields. They stay separate checks.
    """
    if risk_config is None or portfolio is None or portfolio.trades_this_month is None:
        return risk_config
    current = risk_config.trades_this_month
    if current is None:
        return dataclasses.replace(risk_config, trades_this_month=portfolio.trades_this_month)
    if current != portfolio.trades_this_month:
        notes.append("PORTFOLIO_COUNT_DISAGREES: RiskConfig.trades_this_month %s and portfolio %s; "
                     "the risk plan uses the larger count" % (current, portfolio.trades_this_month))
        return dataclasses.replace(risk_config, trades_this_month=max(current, portfolio.trades_this_month))
    return risk_config


def portfolio_checks(state, symbol, zone_id, trade_type):
    """Three independent constraints. A supplied monthly count never clears the other two."""
    state = state or PortfolioState()
    out = []
    trades = state.trades_this_month
    if trades is None:
        out.append(_check("MONTHLY_TRADE_CAP", NOT_SUPPLIED,
                          "TRIGGERED trades this IST month were not supplied, so the cap is not passed",
                          ["D42", "D46", "RB 2392"]))
    elif trades >= m.OWNER_MONTHLY_TRADE_CAP:
        out.append(_check("MONTHLY_TRADE_CAP", m.FAIL,
                          "%d TRIGGERED trades already this IST month; the cap is %d and an exit does not free a slot"
                          % (trades, m.OWNER_MONTHLY_TRADE_CAP), ["D42", "D46", "RB 2392"]))
    else:
        out.append(_check("MONTHLY_TRADE_CAP", m.PASS,
                          "%d TRIGGERED trades already this IST month; the cap is %d"
                          % (trades, m.OWNER_MONTHLY_TRADE_CAP), ["D42", "D46", "RB 2392"]))
    opens = state.open_positions
    if opens is None:
        out.append(_check("SIMULTANEOUS_POSITIONS", NOT_SUPPLIED,
                          "open positions at as_of were not supplied, so the cap is not passed", ["D42"]))
    elif opens >= m.OWNER_MAX_OPEN_POSITIONS:
        out.append(_check("SIMULTANEOUS_POSITIONS", m.FAIL,
                          "%d positions are open; the cap is %d and it is independent of the monthly cap"
                          % (opens, m.OWNER_MAX_OPEN_POSITIONS), ["D42"]))
    else:
        out.append(_check("SIMULTANEOUS_POSITIONS", m.PASS,
                          "%d positions are open; the cap is %d" % (opens, m.OWNER_MAX_OPEN_POSITIONS), ["D42"]))
    zones = state.zones_holding_allowance
    if zones is None:
        out.append(_check("ONE_ORDER_PER_ZONE", NOT_SUPPLIED,
                          "the one-order allowance was not supplied, so this zone is not treated as clear", ["ED-3"]))
    else:
        held = [z for z in zones if z[0] == symbol and z[1] == zone_id and z[2] == trade_type]
        if held:
            out.append(_check("ONE_ORDER_PER_ZONE", m.FAIL, held[0][3], ["ED-3"]))
        else:
            out.append(_check("ONE_ORDER_PER_ZONE", m.PASS,
                              "no supplied allowance is held for this symbol, zone and trade type", ["ED-3"]))
    return out


def _covers(segment, day):
    start, end = segment.get("from"), segment.get("to")
    if start and day < datetime.date.fromisoformat(start):
        return False
    if end and day > datetime.date.fromisoformat(end):
        return False
    return True


def identity_view(symbol, day, membership):
    """Point-in-time identity from the input provenance and the universe row already resolved at day.

    A lineage segment that starts after day is ignored. Two covering segments are a conflict.
    The universe ISIN is recorded beside the instrument ISIN and is not a substitute for it.
    """
    provenance = (symbol.get("provenance") or {}).get("identity") or {}
    covering = [seg for seg in provenance.get("lineage") or [] if _covers(seg, day)]
    isins = sorted({seg.get("isin") for seg in covering if seg.get("isin")})
    if len(isins) == 1:
        isin, status = isins[0], "RECORDED" if provenance.get("records_verified") else "UNVERIFIED"
    elif len(isins) > 1:
        isin, status = None, "CONFLICT"
    elif provenance:
        isin, status = None, "UNAVAILABLE"
    else:
        isin, status = None, "NOT_ON_INPUT"
    universe_isin = None if not membership else membership.get("isin") or None
    conflict = bool(isin and universe_isin and isin != universe_isin)
    return {
        "symbol": symbol.get("symbol"), "isin": None if conflict else isin, "isin_status": "CONFLICT" if conflict else status,
        "records_supplied": provenance.get("records_supplied"), "records_verified": provenance.get("records_verified"),
        "lineage_segments_at_as_of": len(covering),
        "universe_isin": universe_isin,
        "universe_member": None if membership is None else membership.get("member", True),
        "reason": ("instrument ISIN %s and universe ISIN %s differ; neither is chosen" % (isin, universe_isin)
                   if conflict else "no point-in-time instrument ISIN on this input" if not isin else None),
    }


def mtf_view(symbol):
    """What the scan already recorded for Monthly, Weekly and Daily. No second overlay decision."""
    rows = {r.get("tf"): r for r in symbol.get("tda") or []}

    def one(tf, role):
        row = rows.get(tf)
        if row is None:
            return {"timeframe": tf, "role": role, "recorded": False,
                    "reason": "no top-down row on this symbol result"}
        series = row.get("series") or {}
        return {"timeframe": tf, "role": role, "recorded": True, "series_status": series.get("status"),
                "completed_candles": series.get("completed_candles"),
                "fresh_demand_below": row.get("fresh_demand_below"),
                "fresh_supply_above": row.get("fresh_supply_above"),
                "unknown_freshness_closer": row.get("unknown_freshness_closer") or [],
                "missing": row.get("missing") or []}

    return {
        "monthly": one("M", "curve and location; a tested Monthly demand is redrawn only when the next fresh demand is identified"),
        "weekly": one("W", "MIT trend gate and target-supply timeframe; an unresolved Weekly structure stays manual"),
        "daily": one("D", "execution opportunity; it does not override a Monthly or Weekly restriction"),
        "blocked_zones": list(symbol.get("blocked_zones") or []),
        "source": "scanner top-down rows and blocked zones; eligibility was decided by the overlay inside the scanner",
    }


def _gate_rows(candidate):
    rows = []
    for gate in candidate.get("gates") or []:
        rows.append({"gate": gate.get("gate"), "title": m.GATE_TITLES.get(gate.get("gate")),
                     "outcome": gate.get("outcome"), "reasons": list(gate.get("reasons") or []),
                     "manual_review": list(gate.get("manual_review") or []),
                     "sources": list(gate.get("sources") or [])})
    return rows


def _consistent(candidate):
    try:
        derived = m.derive_status([m.GateResult(g["gate"], g["outcome"]) for g in candidate.get("gates") or []])
    except (KeyError, TypeError, ValueError):
        return False
    return derived == candidate.get("status")


def _g7(candidate):
    for gate in candidate.get("gates") or []:
        if gate.get("gate") == "G7":
            return gate
    return {}


def _public_risk(plan):
    """The formula result, without per-buffer combinations and without a selected quantity."""
    if plan is None:
        return None
    kept = ("status", "reason", "checks", "entry_range", "sl_values", "quantity_range", "rr", "target",
            "target_source", "candidate_status", "manual_checks", "manual_checks_pending", "config_assessment",
            "note", "risk_version", "capital_required_range", "max_loss_if_stopped")
    out = {key: plan[key] for key in kept if key in plan}
    out["approved"] = False
    out["authorises_order"] = AUTHORISES_ORDER
    out["selected_quantity"] = None
    out["combinations_omitted"] = "buffer combinations are not a selected order; a person chooses a buffer, then risk.plan_trade"
    return out


def _levels_block(candidate, plan):
    levels = candidate.get("levels") or {}
    evidence = (_g7(candidate).get("evidence") or {})
    target = evidence.get("target") if isinstance(evidence.get("target"), dict) else None
    entry = levels.get("entry") or [None, None]
    stops = (levels.get("sl") or {})
    block = {
        "entry_range": entry,
        "entry_buffer": "printed Rulebook tiers of the proximal and both distal lines; no buffer is chosen (B9)",
        "stop_normal_range": (stops.get("normal") or [None, None]),
        "stop_exceptional_range": (stops.get("exceptional") or [None, None]),
        "stop_structure": "normal distal and exceptional distal are both reported; an HTF stop is not selected",
        "levels_valid": levels.get("valid"),
        "level_problems": list(levels.get("problems") or []),
        "target_proximal": None if target is None else target.get("proximal"),
        "target_zone_id": None if target is None else target.get("zone_id"),
        "target_freshness": None if target is None else target.get("freshness"),
        "target_timeframe": evidence.get("target_tf"),
        "target_provenance": "G7 nearest fresh opposing supply" if target else "no structural target on the G7 evidence",
        "rr": evidence.get("rr"),
        "selected_entry": None,
        "selected_stop": None,
        "selected_quantity": None,
        "scan_risk_per_trade_quantity_range": evidence.get("quantity"),
    }
    if plan and plan.get("quantity_range"):
        block["risk_plan_quantity_range"] = plan.get("quantity_range")
    return block


_REFERENCE_FIELDS = ("symbol", "timeframe", "side", "start_time", "created_time")
_DEFINING_FIELDS = ("pattern", "proximal", "distal", "normal_distal", "zero_base")
SAME_ZONE = "SAME"
ZONE_IDENTITY_UNRESOLVED = "ZONE_IDENTITY_UNRESOLVED"
ZONE_IDENTITY_AMBIGUOUS = "ZONE_IDENTITY_AMBIGUOUS"
ZONE_NOT_IN_SERIES = "ZONE_NOT_IN_SERIES"
INVOCATIONS = ("manual", "scheduled", "historical", "replay")


def stable_reference(symbol, timeframe, zone):
    """Creation evidence. Not the engine index id, the dataset id, or the bar count.

    The engine id is ``side-startIndex-createdIndex`` and moves when candles are
    prepended. ``start_time`` and ``created_time`` are the candle close times stored
    by qualification. This function does not change ``zone_engine._zone_id``.
    """
    zone = zone or {}
    return {"symbol": symbol, "timeframe": timeframe, "side": zone.get("side"),
            "start_time": zone.get("start_time"), "created_time": zone.get("created_time")}


def defining_properties(zone):
    zone = zone or {}
    return {name: zone.get(name) for name in _DEFINING_FIELDS}


def compare_zone_identity(previous, current):
    """Link a stored plan to a later observation. Dataset id and engine id are ignored.

    Same reference and same defining properties: SAME, even if the engine id changed.
    Same reference and a different pattern or price: ZONE_IDENTITY_UNRESOLVED.
    A different reference: ZONE_NOT_IN_SERIES. The old plan is not moved onto that zone.
    """
    left, right = previous.get("reference") or {}, current.get("reference") or {}

    def complete(ref):
        return all(ref.get(name) not in (None, "") for name in _REFERENCE_FIELDS)

    if not complete(left) or not complete(right):
        return {"result": ZONE_IDENTITY_UNRESOLVED, "same_zone": False, "differences": [
            name for name in _REFERENCE_FIELDS if left.get(name) in (None, "") or right.get(name) in (None, "")]}
    if any(left.get(name) != right.get(name) for name in _REFERENCE_FIELDS):
        return {"result": ZONE_NOT_IN_SERIES, "same_zone": False, "differences": []}
    diffs = [name for name in _DEFINING_FIELDS
             if (previous.get("defining") or {}).get(name) != (current.get("defining") or {}).get(name)]
    if diffs:
        return {"result": ZONE_IDENTITY_UNRESOLVED, "same_zone": False, "differences": diffs}
    return {"result": SAME_ZONE, "same_zone": True, "differences": []}


def _withhold_plan(plan, code):
    """Keep the candidate status. Do not attach a usable plan or a quantity."""
    plan["identity_status"] = code
    plan["plan_usable"] = False
    blocking = set(plan.get("constraints_blocking") or [])
    blocking.add(code)
    plan["constraints_blocking"] = sorted(blocking)
    levels = plan.get("levels") or {}
    levels["risk_plan_quantity_range"] = None
    plan["levels"] = levels
    if plan.get("risk_plan"):
        plan["risk_plan"]["quantity_range"] = None
        plan["risk_plan"]["withheld"] = code


def _mark_identity(symbols):
    groups = {}
    for symbol in symbols:
        for candidate in symbol["candidates"]:
            zone = candidate.get("zone") or {}
            timeframe = candidate["trade_plan"].get("execution_tf") or zone.get("tf")
            reference = stable_reference(symbol["symbol"], timeframe, zone)
            plan = candidate["trade_plan"]
            plan["stable_zone_reference"] = reference
            plan["defining_properties"] = defining_properties(zone)
            plan["engine_zone_id"] = plan.get("zone_id")
            key = tuple(reference[name] for name in _REFERENCE_FIELDS)
            groups.setdefault(key, []).append(plan)
    for key, plans in groups.items():
        if len(plans) > 1:
            status = ZONE_IDENTITY_AMBIGUOUS
        elif not all(part not in (None, "") for part in key):
            status = ZONE_IDENTITY_UNRESOLVED
        else:
            status = "STABLE"
        for plan in plans:
            if status == "STABLE":
                plan["identity_status"] = status
                plan["plan_usable"] = True
            else:
                _withhold_plan(plan, status)


def _fixture_scan(scan):
    for symbol in scan.get("symbols") or []:
        source = (symbol.get("provenance") or {}).get("source")
        text = source if isinstance(source, str) else " ".join(str(x) for x in (source or []))
        if "SYNTHETIC" in text or "FIXTURE" in text:
            return True
    return False


def _completeness(scan, requested):
    present = {s.get("symbol") for s in scan.get("symbols") or []}
    missing = sorted(set(requested or []) - present)
    if not present:
        return "FAILED", missing
    if missing:
        return "PARTIAL", missing
    return "COMPLETE", []


def idempotency_key(envelope):
    """Identity of a finished research decision. A retry with the same inputs matches it.

    The wall clock and the completeness result are not included. The requested symbol
    set is the symbols that have a result plus the symbols that were never opened.
    """
    present = [s.get("symbol") for s in envelope.get("symbols") or []]
    requested = sorted(set(present) | set(envelope.get("symbols_not_opened") or []))
    portfolio = envelope.get("portfolio") or {}
    body = {"as_of": envelope.get("as_of"), "trade_type": envelope.get("trade_type"),
            "dataset_id": envelope.get("dataset_id"), "invocation": envelope.get("invocation"),
            "universe": (envelope.get("scan") or {}).get("universe"),
            "pipeline_version": (envelope.get("methodology") or {}).get("pipeline_version"),
            "requested_symbols": requested,
            "trades_this_month": portfolio.get("trades_this_month"),
            "open_positions": portfolio.get("open_positions")}
    return "scan-" + hashlib.sha256(canonical(body).encode()).hexdigest()[:16]


def _trade_plan(candidate, risk_plan, checks):
    status = candidate.get("status")
    blocking = [c["code"] for c in checks if c["outcome"] == m.FAIL]
    unknown = [c["code"] for c in checks if c["outcome"] == NOT_SUPPLIED]
    risk_status = None if risk_plan is None else risk_plan.get("status")
    if risk_status in (risk.PLAN_FAIL, risk.INVALID_LEVELS):
        blocking.append("RISK_PLAN")
    if risk_plan is None:
        unknown.append("RISK_CONFIG")
    elif risk_status == risk.PLAN_MANUAL:
        unknown.append("RISK_PLAN")
    return {
        "symbol": candidate.get("symbol"), "trade_type": candidate.get("trade_type"),
        "as_of": candidate.get("as_of"), "zone_id": (candidate.get("zone") or {}).get("zone_id"),
        "execution_tf": candidate.get("execution_tf"),
        "created_time": (candidate.get("zone") or {}).get("created_time"),
        "candidate_status": status, "status_consistent_with_gates": _consistent(candidate),
        "authorises_order": AUTHORISES_ORDER, "selected_quantity": None,
        "constraints_blocking": blocking, "constraints_unknown": unknown,
        "manual_checks": list(candidate.get("manual_checks") or []),
        "levels": _levels_block(candidate, risk_plan),
        "gates": _gate_rows(candidate),
        "overlay_status": (candidate.get("zone") or {}).get("overlay_status"),
        "portfolio_checks": checks, "risk_plan": _public_risk(risk_plan),
        "note": _NO_ORDER,
    }


def _candidate_view(candidate, risk_plan, portfolio):
    zone = candidate.get("zone") or {}
    checks = portfolio_checks(portfolio, candidate.get("symbol"), zone.get("zone_id"), candidate.get("trade_type"))
    plan = _trade_plan(candidate, risk_plan, checks)
    return {"candidate_status": candidate.get("status"), "status_consistent_with_gates": plan["status_consistent_with_gates"],
            "zone_id": zone.get("zone_id"), "created_time": zone.get("created_time"),
            "zone": {"zone_id": zone.get("zone_id"), "side": zone.get("side"), "pattern": zone.get("pattern"),
                     "proximal": zone.get("proximal"), "distal": zone.get("distal"),
                     "normal_distal": zone.get("normal_distal"), "zero_base": zone.get("zero_base"),
                     "overlay_status": zone.get("overlay_status"), "start_time": zone.get("start_time"),
                     "created_time": zone.get("created_time"), "tf": candidate.get("execution_tf"),
                     "test_count": zone.get("test_count")},
            "gates": plan["gates"], "trade_plan": plan}


def _symbol_view(symbol, day, membership, risk_by_key, portfolio):
    candidates = []
    for candidate in symbol.get("candidates") or []:
        zone = candidate.get("zone") or {}
        key = (candidate.get("symbol"), zone.get("zone_id"), zone.get("created_time"))
        candidates.append(_candidate_view(candidate, risk_by_key.get(key), portfolio))
    candidates.sort(key=lambda c: (str(c.get("created_time") or ""), str(c.get("zone_id") or "")))
    return {"symbol": symbol.get("symbol"), "symbol_status": symbol.get("status"),
            "reasons": list(symbol.get("reasons") or []),
            "identity": identity_view(symbol, day, membership),
            "mtf": mtf_view(symbol), "findings": list(symbol.get("findings") or []),
            "limitations": list(symbol.get("limitations") or []),
            "blocked_zones": list(symbol.get("blocked_zones") or []), "candidates": candidates}


def _risk_index(scan, risk_config):
    if risk_config is None:
        return {}
    packed = risk.plans_for_scan(scan, risk_config)
    return {(p.get("symbol"), p.get("zone_id"), p.get("created_time")): p for p in packed["plans"]}


def _counts(symbols):
    by_symbol, by_candidate = {}, {}
    for symbol in symbols:
        by_symbol[symbol["symbol_status"]] = by_symbol.get(symbol["symbol_status"], 0) + 1
        for candidate in symbol["candidates"]:
            status = candidate["candidate_status"]
            by_candidate[status] = by_candidate.get(status, 0) + 1
    return {"symbols": len(symbols), "symbol_status": dict(sorted(by_symbol.items())),
            "candidates": sum(by_candidate.values()), "candidate_status": dict(sorted(by_candidate.items())),
            "blocked_zones": sum(len(s["blocked_zones"]) for s in symbols)}


def assemble_scan(scan, risk_config=None, portfolio=None, dataset_id=None, membership=None, notes=None,
                  requested_symbols=None, invocation="manual"):
    """Build the envelope from a scan dict. Does not recompute a gate or rewrite a status."""
    if invocation not in INVOCATIONS:
        raise ValueError("invocation must be one of %s" % ", ".join(INVOCATIONS))
    notes = list(notes or [])
    if _fixture_scan(scan):
        notes.append("FIXTURE_NOT_MARKET_DATA")
    portfolio = portfolio or PortfolioState()
    day = _day(scan["as_of"])
    used = _risk_config(risk_config, portfolio, notes)
    if scan.get("generated_at") is None:
        notes.append("GENERATED_AT_NOT_SUPPLIED: the caller did not label the run; no clock was read")
    risk_by_key = _risk_index(scan, used)
    def _member(symbol):
        if membership is None:
            return None
        return membership.get(symbol.get("symbol")) or {"member": False, "isin": None, "verified": False, "source": None}

    symbols = [_symbol_view(s, day, _member(s), risk_by_key, portfolio) for s in scan.get("symbols") or []]
    for symbol, raw in zip(symbols, scan.get("symbols") or []):
        if symbol["symbol_status"] != raw.get("status"):
            raise RuntimeError("research view changed a symbol status")
        raw_status = [c.get("status") for c in raw.get("candidates") or []]
        view_status = [c["candidate_status"] for c in symbol["candidates"]]
        if sorted(view_status) != sorted(raw_status):
            raise RuntimeError("research view changed a candidate status")
    _mark_identity(symbols)
    plans = [c["trade_plan"] for s in symbols for c in s["candidates"]]
    plans.sort(key=lambda p: (str(p.get("symbol")), str(p.get("created_time") or ""), str(p.get("zone_id") or "")))
    limitations = sorted(set(scan.get("limitations") or []) | set(notes))
    completeness, missing_symbols = _completeness(scan, requested_symbols)
    full_universe = (completeness == "COMPLETE" and m.UNIVERSE_UNVERIFIED not in limitations
                     and scan.get("universe") not in (None, "", "ADHOC"))
    return {
        "schema": SCHEMA, "as_of": scan.get("as_of"), "trade_type": scan.get("trade_type"),
        "invocation": invocation, "dataset_id": dataset_id,
        "completeness": completeness, "symbols_not_opened": missing_symbols,
        "full_universe_scan": full_universe,
        "methodology": {"pipeline_version": scan.get("pipeline_version"),
                        "engine_versions": scan.get("engine_versions") or {},
                        "qualification": "scanner.scan only", "risk_version": risk.RISK_VERSION,
                        "schema": SCHEMA},
        "ranking": _ORDER_NOTE, "authorises_order": AUTHORISES_ORDER,
        "order_note": _NO_ORDER, "research_notes": sorted(set(notes)), "limitations": limitations,
        "portfolio": {"source": portfolio.source, "as_of": portfolio.as_of,
                      "trades_this_month": portfolio.trades_this_month,
                      "open_positions": portfolio.open_positions,
                      "monthly_cap": m.OWNER_MONTHLY_TRADE_CAP,
                      "open_position_cap": m.OWNER_MAX_OPEN_POSITIONS,
                      "zones_holding_allowance": None if portfolio.zones_holding_allowance is None else
                      [list(z) for z in portfolio.zones_holding_allowance]},
        "counts": _counts(symbols), "symbols": symbols, "trade_plans": plans,
        "blocked_zones": [{"symbol": s.get("symbol"), **b} for s in scan.get("symbols") or []
                          for b in s.get("blocked_zones") or []],
        "scan": scan,
    }


def _membership(universe, day):
    if universe is None:
        return None
    out = {}
    for row in universe.members(day):
        out[row.symbol] = {"member": True, "isin": row.isin or None, "series": row.series,
                           "verified": row.verified, "source": row.source,
                           "effective_from": row.effective_from.isoformat(),
                           "effective_to": None if row.effective_to is None else row.effective_to.isoformat()}
    return out


@dataclass(frozen=True)
class ResearchRun:
    result: object
    envelope: dict


def run(inputs, config, universe=None, risk_config=None, portfolio=None, dataset_id=None, notes=None,
        invocation="manual", requested_symbols=None):
    """Scan, then attach plans. inputs and config are not modified.

    invocation is manual, scheduled, historical, or replay. This function does not wait
    for a clock and does not start a scheduler. A scheduled caller passes invocation
    ``scheduled`` and the same inputs it would pass for a manual run.
    """
    result = scanner.scan(inputs, config, universe)
    scan = reports.to_dict(result)
    membership = _membership(universe, _day(result.as_of))
    if requested_symbols is None:
        requested_symbols = sorted({i.symbol for i in inputs} | set(membership or {}))
    envelope = assemble_scan(scan, risk_config, portfolio, dataset_id, membership, notes,
                             requested_symbols, invocation)
    envelope["idempotency_key"] = idempotency_key(envelope)
    return ResearchRun(result, envelope)


def run_history(inputs, as_of_times, config, universe=None, risk_config=None, portfolio=None,
                dataset_id=None, notes=None, invocation="historical"):
    """One independent run per as_of. Later candles are not visible to earlier runs.

    portfolio is None, or a function (as_of datetime) -> PortfolioState. One snapshot cannot
    be reused: a later cancellation would make an earlier date look clear.
    """
    if portfolio is not None and not callable(portfolio):
        raise ValueError("run_history portfolio must be None or a function of as_of; "
                         "one snapshot would be applied to every date")
    runs = []
    for moment in sorted(as_of_times):
        state = None if portfolio is None else portfolio(moment)
        runs.append(run(inputs, dataclasses.replace(config, as_of=moment), universe, risk_config,
                        state, dataset_id, notes, invocation))
    return runs


def _md(value):
    if value is None:
        return "-"
    if isinstance(value, (list, tuple)):
        value = ", ".join(str(x) for x in value) or "-"
    return str(value).replace("|", "\\|").replace("\n", " ")


def _table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(_md(cell) for cell in row) + " |" for row in rows]
    return out


def _candidates(envelope):
    rows = [(s, c) for s in envelope["symbols"] for c in s["candidates"]]
    rows.sort(key=lambda sc: (str(sc[0]["symbol"]), str(sc[1].get("created_time") or ""), str(sc[1].get("zone_id") or "")))
    return rows


def research_report(envelope):
    """Human report. It restates the envelope and does not re-decide a gate."""
    lines = ["# Research report %s" % envelope.get("as_of"), "", narrative.BANNER, "",
             "Running this report to completion is not a trade result. %s" % _NO_ORDER, "",
            "- schema: %s" % envelope.get("schema"),
            "- invocation: %s" % envelope.get("invocation"),
            "- completeness: %s" % envelope.get("completeness"),
            "- full-universe scan: %s" % ("yes" if envelope.get("full_universe_scan") else
                                          "no. This is not a certified full-universe scan; read the limitations"),
            "- trade type: %s" % envelope.get("trade_type"),
             "- dataset id: %s" % (envelope.get("dataset_id") or "not supplied"),
             "- %s" % envelope.get("ranking"), ""]
    counts = envelope["counts"]
    lines += ["## %s" % HEADINGS[0], ""]
    lines += _table(["item", "value"], [["symbols", counts["symbols"]], ["candidates", counts["candidates"]],
                                        ["blocked zones", counts["blocked_zones"]],
                                        ["symbol statuses", counts["symbol_status"]],
                                        ["candidate statuses", counts["candidate_status"]]])
    lines += ["", "Symbol status EVALUATED means at least one candidate was recorded. Read each candidate status.", ""]
    lines += ["## %s" % HEADINGS[1], ""]
    uni_rows = [[s["symbol"], s["symbol_status"], (s["identity"] or {}).get("isin_status"),
                 (s["identity"] or {}).get("isin"), (s["identity"] or {}).get("universe_isin"),
                 "; ".join(s["reasons"]) or "-"] for s in envelope["symbols"]]
    lines += _table(["symbol", "symbol status", "ISIN status", "instrument ISIN", "universe ISIN", "reasons"], uni_rows)
    lines += ["", "## %s" % HEADINGS[2], ""]
    findings = [[s["symbol"], f.get("severity"), f.get("code"), f.get("date"), f.get("detail")]
                for s in envelope["symbols"] for f in s.get("findings") or []]
    findings.sort(key=lambda r: (str(r[0]), str(r[2]), str(r[3]), str(r[4])))
    lines += (_table(["symbol", "severity", "code", "date", "detail"], findings) if findings else ["No findings were recorded."])
    lines += ["", "Limitations:"]
    lines += ["- %s" % item for item in envelope.get("limitations") or ["none"]]
    lines += [""]

    def section(title, rows, columns):
        lines.append("## %s" % title)
        lines.append("")
        if not rows:
            lines.append("none")
        else:
            lines.extend(_table(columns, rows))
        lines.append("")

    eligible, rejected, manual, blocked = [], [], [], []
    for symbol, candidate in _candidates(envelope):
        plan = candidate["trade_plan"]
        base = [symbol["symbol"], candidate["zone_id"], candidate["candidate_status"],
                plan["constraints_blocking"] or "-", plan["constraints_unknown"] or "-"]
        status = candidate["candidate_status"]
        if status == m.ACTIONABLE:
            eligible.append(base + ["manual checks pending"])
        elif status == m.REJECTED:
            rejected.append(base)
        elif status == m.MANUAL_REVIEW:
            manual.append(base)
        else:
            blocked.append(base)
    no_candidate = []
    for symbol in envelope["symbols"]:
        if symbol["candidates"]:
            continue
        kind = symbol["symbol_status"]
        row = [symbol["symbol"], "-", kind, "; ".join(symbol["reasons"]) or "-"]
        if kind == scanner.SYMBOL_NO_EXECUTION_ZONE:
            rejected.append([symbol["symbol"], "-", kind, "-", "-"])
        elif kind in (scanner.SYMBOL_BLOCKED, scanner.SYMBOL_DATA_INSUFFICIENT, scanner.SYMBOL_NOT_IN_UNIVERSE):
            no_candidate.append(row)
        else:
            no_candidate.append(row)
    section(HEADINGS[3], eligible, ["symbol", "zone", "status", "blocking", "unknown", "still required"])
    lines += ["An eligible row means every automated gate passed. The manual checklist is still pending. "
              "It is not an order.", ""]
    section(HEADINGS[4], rejected, ["symbol", "zone", "status", "blocking", "unknown"])
    section(HEADINGS[5], manual, ["symbol", "zone", "status", "blocking", "unknown"])
    blocked_zones = [[b.get("symbol"), b.get("tf"), b.get("zone_id"), b.get("overlay_status"), b.get("disposition")]
                     for b in envelope.get("blocked_zones") or []]
    blocked_zones.sort(key=lambda r: (str(r[0]), str(r[1]), str(r[2])))
    lines += ["## %s" % HEADINGS[6], ""]
    lines += (_table(["symbol", "status", "reasons"], [[r[0], r[2], r[3]] for r in no_candidate])
              if no_candidate else ["No symbol-level blocked or data-insufficient row."])
    lines += [""]
    lines += (_table(["symbol", "tf", "zone", "overlay", "disposition"], blocked_zones)
              if blocked_zones else ["No zone was removed by the overlay."])
    lines += ["", "Candidate rows in this class:"]
    lines += (_table(["symbol", "zone", "status", "blocking", "unknown"], blocked) if blocked else ["none"])
    lines += ["", "## %s" % HEADINGS[7], ""]
    if not envelope["trade_plans"]:
        lines += ["none", ""]
    for plan in envelope["trade_plans"]:
        levels = plan["levels"]
        lines += ["### %s %s" % (plan["symbol"], plan["zone_id"]), "",
                  "- candidate status: %s" % plan["candidate_status"],
                  "- authorises an order: no",
                  "- selected entry, stop and quantity: none",
                  "- entry range: %s" % levels["entry_range"],
                  "- stop, normal distal: %s" % levels["stop_normal_range"],
                  "- stop, exceptional distal: %s" % levels["stop_exceptional_range"],
                  "- %s" % levels["stop_structure"],
                  "- target proximal: %s (%s, freshness %s)" % (levels["target_proximal"], levels["target_provenance"],
                                                                levels["target_freshness"]),
                  "- R:R recorded by G7: %s" % (levels["rr"] or "not computed"),
                  "- quantity range from the risk plan: %s" % (levels.get("risk_plan_quantity_range") or "not calculated"),
                  "- blocking constraints: %s" % (plan["constraints_blocking"] or "none"),
                  "- unknown constraints: %s" % (plan["constraints_unknown"] or "none"),
                  "- %s" % ("a blocking or unknown constraint means this quantity range is not a size to place"
                            if plan["constraints_blocking"] or plan["constraints_unknown"] else
                            "the quantity range is still not a selected size"),
                  "- %s" % levels["entry_buffer"], ""]
        lines += _table(["gate", "outcome", "reasons"],
                        [[g["gate"], g["outcome"], "; ".join(g["reasons"][:2])] for g in plan["gates"]])
        lines.append("")
    lines += ["## %s" % HEADINGS[8], ""]
    port = envelope["portfolio"]
    lines += ["Portfolio source: %s. Monthly cap %s, open-position cap %s. The caps are independent."
              % (port["source"], port["monthly_cap"], port["open_position_cap"]),
              "Trades this month: %s. Open positions: %s."
              % (port["trades_this_month"] if port["trades_this_month"] is not None else "not supplied",
                 port["open_positions"] if port["open_positions"] is not None else "not supplied"),
              "A missing count is not a pass. A risk-plan quantity is a range over unchosen buffers.", ""]
    for symbol in envelope["symbols"]:
        mtf = symbol["mtf"]
        lines.append("### %s" % symbol["symbol"])
        for name in ("monthly", "weekly", "daily"):
            row = mtf[name]
            lines.append("- %s: series %s; missing %s" % (name, row.get("series_status") or row.get("reason"),
                                                          row.get("missing") or "-"))
        if symbol["blocked_zones"]:
            lines.append("- overlay removed %d execution-timeframe zone(s)" % len(symbol["blocked_zones"]))
        lines.append("")
    lines += ["## %s" % HEADINGS[9], "",
              "- methodology: %s" % envelope["methodology"],
              "- dataset id: %s" % (envelope.get("dataset_id") or "not supplied"),
              "- code revision and the wall clock are in run_manifest.json, so this report stays a function of the inputs",
              "- identical inputs, configuration and as_of produce an identical research.json digest",
              "- %s" % _ORDER_NOTE, ""]
    return "\n".join(lines).rstrip() + "\n"


def write_run(run, folder, input_paths=(), parameters=None, assumptions=None):
    """Write the scan reports, the research envelope, the plan list, the markdown and the manifest."""
    os.makedirs(folder, exist_ok=True)
    written = reports.write_all(run.result, folder)
    report = research_report(run.envelope)
    files = {RESEARCH_JSON: to_json(run.envelope), TRADE_PLANS_JSON: to_json(run.envelope["trade_plans"]),
             REPORT_MD: report}
    for name, text in files.items():
        with open(os.path.join(folder, name), "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
    written = sorted(set(written) | set(files))
    manifest = run_manifest.build("research", run.envelope["as_of"], parameters or {}, input_paths,
                                  limitations=run.envelope["limitations"], assumptions=assumptions or {})
    run_manifest.write(manifest, folder, written)
    return written, manifest


def _parse_zones(text, trade_type):
    if not text:
        return None
    out = []
    for part in text.split(","):
        bits = [x.strip() for x in part.split(":")]
        if len(bits) == 2:
            symbol, zone_id, used = bits[0], bits[1], trade_type
        elif len(bits) == 3:
            symbol, zone_id, used = bits
        else:
            raise ValueError("--ordered-zones entries are SYMBOL:ZONE or SYMBOL:ZONE:TRADE_TYPE, got %r" % part)
        out.append((symbol.upper(), zone_id, used, "caller"))
    return tuple(out)


def _portfolio_from_args(args, as_of):
    notes = []
    caller = PortfolioState(args.trades_this_month, args.open_positions, _parse_zones(args.ordered_zones, args.trade_type),
                            "caller" if any(v is not None for v in (args.trades_this_month, args.open_positions, args.ordered_zones))
                            else "not_supplied", as_of.isoformat())
    journal = None
    if args.journal:
        if not os.path.isfile(args.journal):
            raise ValueError("journal database does not exist: %s" % args.journal)
        conn = store.open_readonly(args.journal)
        try:
            journal = PortfolioState.from_journal(conn, as_of)
        finally:
            conn.close()
    return merge_portfolio(caller, journal, notes), notes


def _risk_from_args(args):
    if args.capital is None and args.rpt_pct is None and args.rpt_amount is None and args.stage is None:
        return None
    return risk.RiskConfig(capital=args.capital, rpt_amount=args.rpt_amount, rpt_pct=args.rpt_pct, stage=args.stage,
                           trades_this_month=args.trades_this_month)


def _scan_config(args, as_of, calendar):
    from nse.research import inputs as inputs_
    acts, cov = inputs_.corporate_action_config(getattr(args, "corporate_actions", None))
    return scanner.ScanConfig(as_of=as_of, trade_type=args.trade_type, calendar=calendar,
                              calendar_label=args.calendar or "NONE", risk_per_trade=args.risk_per_trade,
                              generated_at=args.generated_at,
                              universe_label="ADHOC" if not args.universe else args.universe,
                              corporate_actions=acts, corporate_action_coverage=cov)


def _load(args, as_of):
    from nse.research import inputs as inputs_, marketdata, universe as uni
    from nse.research.deps import calendar as cal_mod
    if args.trade_type == m.MIT and not args.csv_dir and not args.bhavcopy_dir:
        raise ValueError("a MIT research run needs --csv-dir or --bhavcopy-dir")
    universe = None
    symbols = None
    if args.universe:
        universe = uni.load(args.universe)
        symbols = [r.symbol for r in universe.members(as_of.date())]
    elif args.symbols:
        universe = uni.adhoc(args.symbols.split(","))
        symbols = [r.symbol for r in universe.rows]
    calendar = cal_mod.NseCalendar.load(args.calendar) if args.calendar else None
    if args.trade_type == m.MIT:
        loaded = inputs_.from_args(args, symbols)
    else:
        loaded = [marketdata.DailyInput(s, [], {}, [], []) for s in (symbols or [])]
    return universe, loaded, calendar


def _input_paths(args, symbols, loads_data):
    paths = list(run_manifest.scan_input_paths(args, symbols, loads_data=loads_data))
    for name in ("journal",):
        value = getattr(args, name, None)
        if value:
            paths.append(value)
    return paths


def _parameters(args):
    keys = ("as_of", "as_of_list", "invocation", "trade_type", "symbols", "universe", "calendar", "risk_per_trade",
            "generated_at", "series", "source_label", "price_adjustment", "csv_dir", "bhavcopy_dir", "manifest",
            "corporate_actions", "instruments", "journal", "capital", "rpt_pct", "rpt_amount", "stage",
            "trades_this_month", "open_positions", "ordered_zones")
    params = {key: getattr(args, key, None) for key in keys}
    return run_manifest.relative_paths(params, _PATH_PARAMS)


def _execute_one(args, as_of, folder):
    universe, loaded, calendar = _load(args, as_of)
    config = _scan_config(args, as_of, calendar)
    portfolio, notes = _portfolio_from_args(args, as_of)
    if args.as_of_list and any(getattr(args, name, None) is not None
                              for name in ("trades_this_month", "open_positions", "ordered_zones")):
        notes.append("CALLER_PORTFOLIO_REUSED: the same caller counts are applied at every as-of in this list")
    paths = _input_paths(args, [i.symbol for i in loaded], loads_data=args.trade_type == m.MIT)
    dataset = run_manifest.dataset_sha256(run_manifest.fingerprints(paths))
    invocation = getattr(args, "invocation", None) or "manual"
    if args.as_of_list and invocation == "manual":
        invocation = "historical"
    done = run(loaded, config, universe, _risk_from_args(args), portfolio, dataset, notes, invocation)
    params = _parameters(args)
    params["as_of"] = as_of.isoformat()
    params["as_of_list"] = None
    params["replay_of"] = None
    written, manifest = write_run(done, folder, paths, params)
    return done, written, manifest


def _print_result(folder, written, manifest, envelope):
    print(json.dumps({"as_of": envelope["as_of"], "counts": envelope["counts"],
                      "authorises_order": AUTHORISES_ORDER, "digest": digest(envelope)}, sort_keys=True, indent=1))
    print("wrote %s: %s, %s (%s)" % (folder, ", ".join(written), run_manifest.MANIFEST_NAME, manifest["run_id"]))


def cmd_research(args):
    """One as-of, a list of as-of times, or a replay of a previous research manifest."""
    if args.replay_of:
        return _replay(args)
    if bool(args.as_of) == bool(args.as_of_list):
        raise ValueError("give exactly one of --as-of and --as-of-list")
    from nse.research import inputs as inputs_
    if args.as_of_list:
        moments = [inputs_.parse_as_of(x.strip()) for x in args.as_of_list.split(",") if x.strip()]
        if not moments:
            raise ValueError("--as-of-list needs at least one date")
        index = []
        for moment in sorted(moments):
            folder = os.path.join(args.out, moment.date().isoformat())
            done, written, manifest = _execute_one(args, moment, folder)
            index.append({"as_of": done.envelope["as_of"], "digest": digest(done.envelope), "folder": folder,
                          "run_id": manifest["run_id"]})
        os.makedirs(args.out, exist_ok=True)
        with open(os.path.join(args.out, "history_index.json"), "w", encoding="utf-8", newline="") as fh:
            fh.write(to_json(index))
        print(to_json(index))
        return 0
    done, written, manifest = _execute_one(args, inputs_.parse_as_of(args.as_of), args.out)
    _print_result(args.out, written, manifest, done.envelope)
    return 0


def _replay(args):
    path = os.path.join(args.replay_of, run_manifest.MANIFEST_NAME)
    if not os.path.isfile(path):
        raise ValueError("no %s in %s" % (run_manifest.MANIFEST_NAME, args.replay_of))
    with open(path, encoding="utf-8") as fh:
        manifest = json.load(fh)
    if manifest.get("kind") != "research":
        raise ValueError("manifest kind is %s; research replay needs a research manifest" % manifest.get("kind"))
    params = dict(manifest.get("parameters") or {})
    params["out"] = args.out
    params["replay_of"] = None
    params["as_of_list"] = None
    replay_args = argparse.Namespace(**params)
    for name, value in (("trade_type", m.MIT), ("series", "EQ"), ("source_label", "USER_CSV"),
                        ("price_adjustment", "UNKNOWN")):
        if getattr(replay_args, name, None) is None:
            setattr(replay_args, name, value)
    from nse.research import inputs as inputs_
    done, written, new_manifest = _execute_one(replay_args, inputs_.parse_as_of(replay_args.as_of), args.out)
    previous = os.path.join(args.replay_of, RESEARCH_JSON)
    if not os.path.isfile(previous):
        print(json.dumps({"replay": "NO_PREVIOUS_RESEARCH_JSON", "digest": digest(done.envelope)}))
        return 0
    with open(previous, encoding="utf-8") as fh:
        old = json.load(fh)
    same = digest(old) == digest(done.envelope)
    print(json.dumps({"replay": "MATCH" if same else "DIFFER", "previous": digest(old),
                      "current": digest(done.envelope), "run_id": new_manifest["run_id"]}, sort_keys=True))
    return 0 if same else 1


def add_commands(subparsers):
    p = subparsers.add_parser("research", help="scan, trade plans and a research report at one or more as-of times")
    p.add_argument("--as-of", help="date or ISO datetime; the close of that date when a date is given")
    p.add_argument("--as-of-list", help="comma-separated as-of values; one folder per date under --out")
    p.add_argument("--replay-of", help="folder with a research run_manifest.json to run again")
    p.add_argument("--invocation", default="manual", choices=INVOCATIONS,
                   help="manual, scheduled, historical, or replay. A list of dates is recorded as historical")
    p.add_argument("--trade-type", default=m.MIT, choices=m.TRADE_TYPES)
    g = p.add_mutually_exclusive_group()
    g.add_argument("--symbols", help="comma-separated ad-hoc universe (UNIVERSE_UNVERIFIED)")
    g.add_argument("--universe", help="universe CSV (nse/research/universe.py format)")
    src = p.add_mutually_exclusive_group()
    src.add_argument("--bhavcopy-dir")
    src.add_argument("--csv-dir")
    p.add_argument("--manifest")
    p.add_argument("--corporate-actions")
    p.add_argument("--instruments")
    p.add_argument("--series", default="EQ")
    p.add_argument("--source-label", default="USER_CSV")
    p.add_argument("--price-adjustment", default="UNKNOWN", choices=("UNKNOWN", "NONE", "ADJUSTED"))
    p.add_argument("--calendar")
    p.add_argument("--risk-per-trade", type=float, help="rupee RPT recorded for the scan's G8 quantity range")
    p.add_argument("--generated-at", help="label stored in the scan; omit it and no clock is read")
    p.add_argument("--capital", type=float, help="capital for the risk plan; omitted means no sizing config")
    p.add_argument("--rpt-pct", type=float, help="risk per trade as a percent of capital")
    p.add_argument("--rpt-amount", type=float, help="risk per trade in rupees; give this or --rpt-pct")
    p.add_argument("--stage", choices=risk.STAGES)
    p.add_argument("--trades-this-month", type=int, help="TRIGGERED trades already taken this IST month")
    p.add_argument("--open-positions", type=int, help="positions already open at as_of")
    p.add_argument("--ordered-zones", help="SYMBOL:ZONE or SYMBOL:ZONE:TRADE_TYPE pairs that already hold the one-order allowance")
    p.add_argument("--journal", help="existing research store; read-only portfolio counts at as_of")
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_research)
    return p
