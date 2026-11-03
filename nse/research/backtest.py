"""Deterministic backtest infrastructure. It evaluates point-in-time scanner signals with an
execution model the USER supplies; it chooses no trading assumption itself.

Why every field of ExecutionModel is required (no defaults):
  - which price inside the printed entry and SL buffer ranges (B9; spec 6.2-6.3);
  - how a limit order fills when the bar opens through it, which of stop and target counts
    when one bar touches both, how long an unfilled order lives, costs and slippage (B12).
The rulebook does not settle these; a backtest that defaulted them would present an
invented rule as a result. Statuses to trade are also explicit: by default nothing is.

Point in time:
  - signals come from scanner.scan_history: each candidate's levels are those of the first
    scan (as_of = T) where its zone appears with an allowed status;
  - the simulation reads only candles that START after T; nothing at or before T;
  - a universe passed to run() is applied per scan date (scanner.scan); without one the
    result carries SURVIVORSHIP_UNCONTROLLED (B11);
  - a trade alive across a price-scale event (recorded corporate action or PREVCLOSE
    discontinuity) is excluded from the metrics and reported, because the unadjusted
    prices on either side are not comparable (B7).
Portfolio rules (optional ExecutionModel fields; None means NOT applied, and the result
then lists MONTHLY_TRADE_CAP_NOT_ENFORCED / PORTFOLIO_CONCURRENCY_NOT_MODELLED):
  - monthly_trade_cap: the rulebook's ceiling of 10 trades per month (RB 2392, 2408). A
    trade is counted in the calendar month of its FILL (the rulebook counts trades taken,
    and an order that never fills is not a trade). Fills are taken in the order (fill
    time, signal time, symbol, zone id): fill time first, so a later fill can never
    displace an earlier one (no lookahead); the rest break same-bar ties, whose intraday
    order is unknown. The rulebook picks "the best 10" (RB 2400, 2414): a human choice
    the engine does not make, so the result carries MONTHLY_CAP_SELECTION_BY_FILL_ORDER.
    Orders over the cap are NOT_TRADED_MONTHLY_CAP.
  - max_open_positions: a fill is NOT_TRADED_MAX_OPEN_POSITIONS when that many taken
    trades are open at its fill time. A trade exiting on the bar of the new fill counts
    as open (the intraday order is unknown: the conservative reading). Pending unfilled
    orders hold no slot.
Not modelled (each would need a user decision first): portfolio capital, price bands and
circuit limits, liquidity and position size versus traded volume, flat per-order charges
(costs are percentages only), and re-evaluating an order after its signal (an order lives
until it fills, expires or is cancelled by cancel_if_target_first).
Walk-forward and sensitivity: run_walk_forward evaluates user-given folds; run_sensitivity
runs user-given models side by side. The engine never selects, optimises or ranks a
parameter or a model, so the engine itself adds no test-period selection bias (a user who
picks a model after seeing these results does).
Outputs are records and arithmetic (R multiples, win rate, expectancy, drawdown,
distribution) of the simulated trades. They are not evidence of profitability: the result
says so, and lists every assumption it was given.
"""

import dataclasses
import datetime
import json
import math
import statistics
import sys
from dataclasses import dataclass
from typing import Optional, Tuple

from nse.research import corporate_actions, models as m, scanner

ENTRY_CHOICES = ("ENTRY_MIN", "ENTRY_MAX")
STOP_CHOICES = ("NORMAL_WIDE", "NORMAL_TIGHT", "EXCEPTIONAL_WIDE", "EXCEPTIONAL_TIGHT")
TARGET_CHOICES = ("STRUCTURAL",)
GAP_FILL = ("AT_OPEN", "AT_LEVEL")
SAME_BAR = ("STOP_FIRST", "TARGET_FIRST", "EXCLUDE")
SURVIVORSHIP_UNCONTROLLED = "SURVIVORSHIP_UNCONTROLLED"
NOT_PERFORMANCE_EVIDENCE = "NOT_PERFORMANCE_EVIDENCE"
MONTHLY_TRADE_CAP_NOT_ENFORCED = "MONTHLY_TRADE_CAP_NOT_ENFORCED"
MONTHLY_CAP_COUNTED_AT_FILL = "MONTHLY_CAP_COUNTED_AT_FILL"
MONTHLY_CAP_ABOVE_RULEBOOK = "MONTHLY_CAP_ABOVE_RULEBOOK"
RULEBOOK_MONTHLY_MAX = 10
MONTHLY_CAP_SELECTION_BY_FILL_ORDER = "MONTHLY_CAP_SELECTION_BY_FILL_ORDER"
PORTFOLIO_CONCURRENCY_NOT_MODELLED = "PORTFOLIO_CONCURRENCY_NOT_MODELLED"
NOT_TRADED_MONTHLY_CAP = "NOT_TRADED_MONTHLY_CAP"
NOT_TRADED_MAX_OPEN_POSITIONS = "NOT_TRADED_MAX_OPEN_POSITIONS"
SMALL_SAMPLE = "SMALL_SAMPLE"
# A reporting convention only, not a validation criterion: fewer closed trades than this
# and the metrics carry SMALL_SAMPLE. Thirty trades do not make a result significant either.
SMALL_SAMPLE_THRESHOLD = 30
# R-multiple buckets (label, upper bound inclusive); the last is everything above 3.
R_BUCKETS = (("<=-1", -1.0), ("(-1,0]", 0.0), ("(0,1]", 1.0), ("(1,2]", 2.0), ("(2,3]", 3.0), (">3", None))
# The execution assumptions with no default (B9, B12). The fields after them are optional
# portfolio rules whose default None means "not applied", recorded as a limitation.
ASSUMPTION_FIELDS = ("entry", "stop", "target", "statuses", "entry_expiry_sessions", "cancel_if_target_first",
                     "gap_fill", "same_bar", "cost_pct_per_side", "slippage_pct_per_side")
OPTIONAL_RULES = (("monthly_trade_cap", MONTHLY_TRADE_CAP_NOT_ENFORCED),
                  ("max_open_positions", PORTFOLIO_CONCURRENCY_NOT_MODELLED))


@dataclass(frozen=True)
class ExecutionModel:
    entry: str                       # ENTRY_CHOICES: lower or upper end of the entry range (B9)
    stop: str                        # STOP_CHOICES: which DL, wide (largest buffer) or tight (B9)
    target: str                      # TARGET_CHOICES: the G7 structural target only
    statuses: Tuple[str, ...]        # candidate statuses that place an order
    entry_expiry_sessions: int       # sessions an unfilled limit order lives (B12)
    cancel_if_target_first: bool     # cancel the order if price reaches the target before filling (B12)
    gap_fill: str                    # GAP_FILL: a bar opening through a level fills at its open or the level (B12)
    same_bar: str                    # SAME_BAR: one bar touches the stop and the target (B12)
    cost_pct_per_side: float         # from an official schedule (B12)
    slippage_pct_per_side: float     # (B12)
    monthly_trade_cap: Optional[int] = None    # RB 2392; None: not enforced (a limitation, not a rule)
    max_open_positions: Optional[int] = None   # None: concurrency not modelled (a limitation)

    def __post_init__(self):
        for name, value, allowed in (("entry", self.entry, ENTRY_CHOICES), ("stop", self.stop, STOP_CHOICES),
                                     ("target", self.target, TARGET_CHOICES), ("gap_fill", self.gap_fill, GAP_FILL),
                                     ("same_bar", self.same_bar, SAME_BAR)):
            if value not in allowed:
                raise ValueError("%s must be one of %s" % (name, ", ".join(allowed)))
        if not self.statuses or any(s not in m.STATUS_ORDER for s in self.statuses):
            raise ValueError("statuses must be a non-empty subset of %s" % ", ".join(m.STATUS_ORDER))
        if m.BLOCKED_STATUS in self.statuses or m.REJECTED in self.statuses or m.STATUS_DATA_INSUFFICIENT in self.statuses:
            raise ValueError("BLOCKED, REJECTED and DATA_INSUFFICIENT results are never traded")
        if self.entry_expiry_sessions < 1:
            raise ValueError("entry_expiry_sessions must be at least 1")
        for v in (self.cost_pct_per_side, self.slippage_pct_per_side):
            if not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
                raise ValueError("costs and slippage must be finite and non-negative")
        for name, _ in OPTIONAL_RULES:
            v = getattr(self, name)
            if v is not None and (isinstance(v, bool) or not isinstance(v, int) or v < 1):
                raise ValueError("%s must be None (not applied) or an integer of at least 1" % name)

    def not_applied(self):
        """Limitation codes for the optional portfolio rules left at None."""
        return [code for name, code in OPTIONAL_RULES if getattr(self, name) is None]


def plan(candidate, model):
    """(entry, stop, target) from a CandidateResult's own G7 evidence, or (None, reason)."""
    lv = candidate.levels
    if not lv.get("valid", False):
        return None, "LEVELS_INVALID"
    g7 = candidate.gate("G7").evidence
    target = (g7.get("target") or {}).get("proximal")
    if target is None:
        return None, "NO_STRUCTURAL_TARGET"
    entry = lv["entry"][0] if model.entry == "ENTRY_MIN" else lv["entry"][1]
    kind, width = model.stop.split("_")
    lo, hi = lv["sl"][kind.lower()]
    stop = lo if width == "WIDE" else hi
    if not (stop < entry < target):
        return None, "LEVELS_NOT_ORDERED"
    return (entry, stop, target), None


def simulate(levels, candles, signal_end, model, zone=None):
    """One limit buy. candles: the symbol's candles; only those starting after signal_end
    are read. Returns a dict trade record (no metrics). When zone is supplied, its
    completed-candle DL invalidation is recorded separately from trade stop events.
    assumption_events lists each bar where a B12 policy decided the result: a bar that
    opened through a level (GAP_THROUGH_*, gap_fill) or one whose intrabar order is
    unknown (SAME_BAR_AMBIGUOUS, same_bar), so the user sees how much they matter."""
    entry, stop, target = levels
    future = [c for c in candles if c.start > signal_end and c.complete]
    rec = {"entry_level": entry, "stop_level": stop, "target_level": target, "fill_time": None, "fill_price": None,
           "exit_time": None, "exit_price": None, "exit_reason": None,
           "trade_events": [], "zone_events": [], "assumption_events": []}
    i = 0
    filled = None
    while i < len(future) and i < model.entry_expiry_sessions:
        c = future[i]
        if c.low <= entry:
            filled = i
            rec["fill_time"] = c.end.isoformat()
            if c.open < entry:
                rec["assumption_events"].append({"type": "GAP_THROUGH_ENTRY", "time": c.end.isoformat(),
                                                 "policy": "gap_fill=" + model.gap_fill})
            rec["fill_price"] = c.open if (c.open < entry and model.gap_fill == "AT_OPEN") else entry
            break
        if model.cancel_if_target_first and c.high >= target:
            rec["exit_reason"] = "CANCELLED_TARGET_FIRST"
            return rec
        i += 1
    if filled is None:
        rec["exit_reason"] = "EXPIRED" if i >= model.entry_expiry_sessions else "OPEN_ORDER_AT_END_OF_DATA"
        return rec
    invalidation_recorded = False
    for j in range(filled, len(future)):
        c = future[j]
        fill_bar = j == filled
        if zone and not invalidation_recorded and c.complete:
            distal = zone.get("distal")
            side = zone.get("side", "demand")
            breached = (c.close < distal) if side == "demand" else (c.close > distal)
            if breached:
                rec["zone_events"].append({"type": "ZONE_INVALIDATED", "zone_id": zone.get("zone_id"),
                                           "timeframe": zone.get("timeframe"), "time": c.end.isoformat(),
                                           "close": c.close, "distal": distal,
                                           "rule": "completed candle close beyond DL"})
                invalidation_recorded = True
        hit_stop = c.low <= stop
        # on the fill bar the order of the fill and a target touch is unknown: the same-bar
        # policy decides it (STOP_FIRST ignores it, TARGET_FIRST takes it, EXCLUDE drops the trade)
        hit_target = c.high >= target
        ambiguous = (hit_stop and hit_target) or (fill_bar and hit_target)
        if ambiguous:
            rec["assumption_events"].append({"type": "SAME_BAR_AMBIGUOUS", "time": c.end.isoformat(),
                                             "kind": "STOP_AND_TARGET" if hit_stop else "FILL_AND_TARGET",
                                             "policy": "same_bar=" + model.same_bar})
            if model.same_bar == "EXCLUDE":
                rec.update(exit_reason="EXCLUDED_SAME_BAR", exit_time=c.end.isoformat())
                return rec
            if model.same_bar == "TARGET_FIRST":
                hit_stop = False
            else:
                hit_target = False
        if hit_stop:
            if fill_bar and rec["fill_price"] <= stop:
                price = rec["fill_price"]                    # filled below the stop: out at once
            elif not fill_bar and c.open < stop and model.gap_fill == "AT_OPEN":
                price = c.open
            else:
                price = stop
            if not fill_bar and c.open < stop:
                rec["assumption_events"].append({"type": "GAP_THROUGH_STOP", "time": c.end.isoformat(),
                                                 "policy": "gap_fill=" + model.gap_fill})
            rec["trade_events"].append({"type": "STOP_LOSS_HIT", "time": c.end.isoformat(),
                                        "price": price, "stop_level": stop})
            rec.update(exit_time=c.end.isoformat(), exit_price=price, exit_reason="STOP")
            return rec
        if hit_target:
            if not fill_bar and c.open > target:
                rec["assumption_events"].append({"type": "GAP_THROUGH_TARGET", "time": c.end.isoformat(),
                                                 "policy": "gap_fill=" + model.gap_fill})
            price = c.open if (not fill_bar and c.open > target and model.gap_fill == "AT_OPEN") else target
            rec.update(exit_time=c.end.isoformat(), exit_price=price, exit_reason="TARGET")
            return rec
    rec["exit_reason"] = "OPEN_AT_END_OF_DATA"
    return rec


def r_multiple(rec, model):
    """Net R of a closed trade: (net exit - net entry) / planned risk per share."""
    if rec["exit_reason"] not in ("STOP", "TARGET"):
        return None
    side = (model.cost_pct_per_side + model.slippage_pct_per_side) / 100.0
    entry_cost = rec["fill_price"] * (1 + side)
    exit_net = rec["exit_price"] * (1 - side)
    risk = rec["entry_level"] - rec["stop_level"]
    return round((exit_net - entry_cost) / risk, 6)


def metrics(trades):
    """Arithmetic over closed trades in exit order. Max drawdown is on cumulative R."""
    closed = sorted([t for t in trades if t.get("r") is not None], key=lambda t: (t["exit_time"], t["symbol"], t["zone_id"]))
    rs = [t["r"] for t in closed]
    peak = cum = dd = 0.0
    for r in rs:
        cum += r
        peak = max(peak, cum)
        dd = min(dd, cum - peak)
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r <= 0]
    return {"closed_trades": len(rs), "wins": len(wins), "losses": len(losses),
            "win_rate": round(len(wins) / len(rs), 6) if rs else None,
            "expectancy_r": round(sum(rs) / len(rs), 6) if rs else None,
            "total_r": round(sum(rs), 6), "max_drawdown_r": round(dd, 6),
            "not_closed": sum(1 for t in trades if t.get("r") is None and not t.get("excluded_reason")),
            "excluded": sum(1 for t in trades if t.get("excluded_reason"))}


def r_bucket(r):
    """Label of the R_BUCKETS bucket holding r (upper bounds inclusive)."""
    for label, upper in R_BUCKETS:
        if upper is None or r <= upper:
            return label


def extended_metrics(trades):
    """metrics() plus the distribution of the closed trades (same win/loss convention:
    r <= 0 is a loss). profit_factor is None when there is no loss to divide by, never
    infinity. sample_size_warning is SMALL_SAMPLE below SMALL_SAMPLE_THRESHOLD closed
    trades (a reporting convention). The assumption counts show how many trades a gap or
    same-bar policy decided."""
    out = metrics(trades)
    closed = sorted([t for t in trades if t.get("r") is not None], key=lambda t: (t["exit_time"], t["symbol"], t["zone_id"]))
    rs = [t["r"] for t in closed]
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r <= 0]
    run_ = longest = 0
    for r in rs:
        run_ = run_ + 1 if r <= 0 else 0
        longest = max(longest, run_)
    buckets = dict((label, 0) for label, _ in R_BUCKETS)
    for r in rs:
        buckets[r_bucket(r)] += 1
    reasons = {}
    events = {}
    for t in trades:
        key = t.get("exit_reason") or "NONE"
        reasons[key] = reasons.get(key, 0) + 1
        for e in t.get("assumption_events") or []:
            events[e["type"]] = events.get(e["type"], 0) + 1
    out.update({
        "avg_win_r": round(sum(wins) / len(wins), 6) if wins else None,
        "avg_loss_r": round(sum(losses) / len(losses), 6) if losses else None,
        "profit_factor": round(sum(wins) / abs(sum(losses)), 6) if losses and sum(losses) != 0 else None,
        "max_consecutive_losses": longest,
        "median_r": round(statistics.median(rs), 6) if rs else None,
        "r_distribution": [{"bucket": label, "count": buckets[label]} for label, _ in R_BUCKETS],
        "exit_reasons": reasons,
        "sample_size_warning": SMALL_SAMPLE if len(rs) < SMALL_SAMPLE_THRESHOLD else None,
        "small_sample_threshold": SMALL_SAMPLE_THRESHOLD,
        "same_bar_ambiguous_trades": sum(1 for t in trades if any(
            e["type"] == "SAME_BAR_AMBIGUOUS" for e in t.get("assumption_events") or [])),
        "gap_fill_trades": sum(1 for t in trades if any(
            e["type"].startswith("GAP_THROUGH_") for e in t.get("assumption_events") or [])),
        "assumption_event_counts": events})
    return out


def setup_attributes(candidate):
    """Setup attributes from the candidate's own gate evidence at its signal scan, so no
    later data can enter: G3 location (spec 7.2), G4 trend gate reading (spec 7.3), G6
    coinciding class (spec 7.5), zone pattern and core score, status and gate outcomes.
    A value the evidence does not hold is UNKNOWN, never guessed."""
    def ev(name):
        try:
            return candidate.gate(name).evidence or {}
        except KeyError:
            return {}
    pos = ev("G3").get("position_at_price") or []
    gate = ev("G4").get("gate") or {}
    return {"location": "+".join(sorted(pos)) if pos else "UNKNOWN",
            "trend_gate_label": gate.get("rulebook_label") or "UNKNOWN",
            "trend_gate_readings": "+".join(gate.get("readings") or []) or "UNKNOWN",
            "coinciding_class": ev("G6").get("class") or "UNKNOWN",
            "pattern": candidate.zone.get("pattern") or "UNKNOWN",
            "core": candidate.zone.get("core") or "UNKNOWN",
            "status": candidate.status,
            "gate_outcomes": dict((g.gate, g.outcome) for g in candidate.gates)}


BREAKDOWN_ATTRIBUTES = ("location", "trend_gate_label", "trend_gate_readings", "coinciding_class", "pattern",
                        "core", "status")


def breakdowns(trades):
    """metrics() per exit year and exit month (closed trades) and per signal-time setup
    attribute (every trade record). Groups are reported, never ranked."""
    out = {"exit_year": {}, "exit_month": {}}
    closed = [t for t in trades if t.get("r") is not None]
    for dim, width in (("exit_year", 4), ("exit_month", 7)):
        keys = sorted(set(t["exit_time"][:width] for t in closed))
        out[dim] = dict((k, metrics([t for t in closed if t["exit_time"][:width] == k])) for k in keys)
    for attr in BREAKDOWN_ATTRIBUTES:
        vals = sorted(set((t.get("setup") or {}).get(attr, "UNKNOWN") for t in trades))
        out[attr] = dict((v, metrics([t for t in trades if (t.get("setup") or {}).get(attr, "UNKNOWN") == v]))
                         for v in vals)
    return out


def apply_portfolio_rules(trades, model):
    """Monthly cap (RB 2392, 2408) and concurrency, when the model sets them. Filled
    trades are taken in (fill time, signal time, symbol, zone id) order; a refused one
    keeps what it would have done under not_traded and is not counted anywhere else.
    Mutates and returns trades."""
    if model.monthly_trade_cap is None and model.max_open_positions is None:
        return trades
    ts = datetime.datetime.fromisoformat
    filled = sorted([t for t in trades if t.get("fill_time")],
                    key=lambda t: (ts(t["fill_time"]), t["signal_as_of"], t["symbol"], t["zone_id"]))
    taken, per_month = [], {}
    for t in filled:
        fill = ts(t["fill_time"])
        reason = None
        if model.max_open_positions is not None:
            open_now = sum(1 for a in taken if a.get("exit_time") is None or ts(a["exit_time"]) >= fill)
            if open_now >= model.max_open_positions:
                reason = NOT_TRADED_MAX_OPEN_POSITIONS
        month = t["fill_time"][:7]
        if reason is None and model.monthly_trade_cap is not None and per_month.get(month, 0) >= model.monthly_trade_cap:
            reason = NOT_TRADED_MONTHLY_CAP
        if reason is None:
            taken.append(t)
            per_month[month] = per_month.get(month, 0) + 1
            continue
        t["not_traded"] = {"reason": reason, "fill_month": month,
                           "would_have": dict((k, t.get(k)) for k in ("fill_time", "fill_price", "exit_time",
                                                                      "exit_price", "exit_reason", "r",
                                                                      "excluded_reason", "trade_events",
                                                                      "assumption_events"))}
        t.pop("excluded_reason", None)
        t.update(fill_time=None, fill_price=None, exit_time=None, exit_price=None, exit_reason=reason, r=None,
                 trade_events=[], assumption_events=[])
    return trades


def _price_scale_events(inputs, scan_config):
    # price-scale events per symbol: recorded corporate actions and PREVCLOSE discontinuities.
    # A trade alive across one would mix two price scales (prices are unadjusted, B7).
    events = {}
    for i in inputs:
        dates = [f.date for f in i.findings if f.code == "PREVCLOSE_DISCONTINUITY" and f.date]
        dates += [a.ex_date for a in (scan_config.corporate_actions or [])
                  if a.symbol == i.symbol and a.action in corporate_actions.PRICE_ACTIONS]
        events[i.symbol] = sorted(set(dates))
    return events


def _limitations(model, universe):
    limitations = [NOT_PERFORMANCE_EVIDENCE, m.NOT_EXTERNALLY_VALIDATED] + model.not_applied()
    if universe is None or universe.adhoc:
        limitations.append(SURVIVORSHIP_UNCONTROLLED)
    if model.monthly_trade_cap is not None:
        limitations.append(MONTHLY_CAP_SELECTION_BY_FILL_ORDER)
        limitations.append(MONTHLY_CAP_COUNTED_AT_FILL)            # engineering reading of "trade" (B12)
        if model.monthly_trade_cap > RULEBOOK_MONTHLY_MAX:
            limitations.append(MONTHLY_CAP_ABOVE_RULEBOOK)         # RB 2392: a MAXIMUM of 10
    return sorted(set(limitations))


def _portfolio_rules(model):
    return {"monthly_trade_cap": model.monthly_trade_cap, "monthly_cap_counts": "FILL_MONTH",
            "max_open_positions": model.max_open_positions,
            "order": "fill time, signal time, symbol, zone id",
            "exit_on_fill_bar_counts_as_open": True, "pending_orders_hold_a_slot": False,
            "sources": {"monthly_trade_cap": ["RB 2392", "RB 2400", "RB 2408", "RB 2414-2415"],
                        "max_open_positions": ["user parameter (not a Rulebook rule)"]}}


def _from_history(history, inputs, scan_config, model, split=None, universe=None):
    """Trades and metrics from scans already made (one model). Shared by run and
    run_sensitivity so every model reads the same signals."""
    by_symbol = {i.symbol: i for i in inputs}
    events = _price_scale_events(inputs, scan_config)
    seen = set()
    trades = []
    for scan in history:
        for s in scan.symbols:
            for c in s.candidates:
                key = (c.symbol, c.zone["zone_id"])
                if key in seen or c.status not in model.statuses:
                    continue
                seen.add(key)
                t = datetime.datetime.fromisoformat(scan.as_of)
                levels, why = plan(c, model)
                rec = {"symbol": c.symbol, "zone_id": c.zone["zone_id"], "signal_as_of": scan.as_of,
                       "status": c.status, "manual_checks_pending": [x["code"] for x in c.manual_checks],
                       "segment": None if split is None else ("IN_SAMPLE" if t <= split else "OUT_OF_SAMPLE"),
                       "setup": setup_attributes(c)}
                if levels is None:
                    rec.update(exit_reason="NOT_TRADED_" + why, r=None)
                else:
                    rec.update(simulate(levels, by_symbol[c.symbol].candles, t, model,
                                        zone={"zone_id": c.zone["zone_id"], "timeframe": c.execution_tf,
                                              "side": c.zone["side"], "distal": c.zone["distal"]}))
                    rec["r"] = r_multiple(rec, model)
                    end = (datetime.date.fromisoformat(rec["exit_time"][:10]) if rec.get("exit_time")
                           else datetime.date.max)
                    spanned = [d for d in events.get(c.symbol, []) if t.date() < d <= end]
                    if spanned:
                        rec.update(r=None, excluded_reason="PRICE_SCALE_EVENT_DURING_TRADE %s (B7)"
                                   % ", ".join(d.isoformat() for d in spanned))
                trades.append(rec)
    trades.sort(key=lambda r: (r["signal_as_of"], r["symbol"], r["zone_id"]))
    apply_portfolio_rules(trades, model)
    out = {"model": dataclasses.asdict(model), "scans": len(history), "signals": len(trades), "trades": trades,
           "metrics": {"ALL": extended_metrics(trades)}, "breakdowns": breakdowns(trades),
           "portfolio_rules": _portfolio_rules(model), "limitations": _limitations(model, universe),
           "note": "Simulated with the user-supplied execution model above. Manual checks were not performed; "
                   "this is arithmetic on research signals, not a performance claim."}
    if split is not None:
        out["split"] = split.isoformat()
        for seg in ("IN_SAMPLE", "OUT_OF_SAMPLE"):
            out["metrics"][seg] = extended_metrics([t for t in trades if t["segment"] == seg])
    return out


def run(inputs, as_of_times, scan_config, model, split=None, universe=None):
    """Signals from point-in-time scans, then simulation. split: a datetime; signals at or
    before it are IN_SAMPLE, later ones OUT_OF_SAMPLE (reported separately, never pooled
    silently)."""
    history = scanner.scan_history(inputs, as_of_times, scan_config, universe=universe)
    return _from_history(history, inputs, scan_config, model, split=split, universe=universe)


# --- walk-forward and sensitivity: evaluation only, never selection ---------------------

NO_SELECTION_NOTE = ("The engine selects, optimises and ranks nothing: every model and fold is the user's. "
                     "It therefore adds no test-period selection bias itself; choosing a model after reading "
                     "these results would.")


def _truncate(inputs, end):
    """Inputs holding only candles that end at or before end, and findings dated on or
    before it: a segment cannot read anything after its window."""
    out = []
    for i in inputs:
        out.append(dataclasses.replace(i, candles=[c for c in i.candles if c.end <= end],
                                       findings=[f for f in i.findings if f.known_at(end.date())]))
    return out


def _windows(inputs, start, end):
    return sorted(set(c.end for i in inputs for c in i.candles if start <= c.end <= end))


def check_folds(folds):
    """folds: (in_start, in_end, out_start, out_end) datetimes. Each fold must be ordered
    with IN before OUT, and OUT windows may not overlap (pooled OUT would count twice)."""
    if not folds:
        raise ValueError("at least one fold is required")
    outs = []
    for n, f in enumerate(folds):
        if len(f) != 4 or not all(isinstance(x, datetime.datetime) for x in f):
            raise ValueError("fold %d: need (in_start, in_end, out_start, out_end) datetimes" % n)
        a, b, c, d = f
        if not (a <= b < c <= d):
            raise ValueError("fold %d: need in_start <= in_end < out_start <= out_end" % n)
        outs.append((c, d, n))
    outs.sort()
    for (c0, d0, n0), (c1, d1, n1) in zip(outs, outs[1:]):
        if c1 <= d0:
            raise ValueError("OUT windows of folds %d and %d overlap" % (n0, n1))
    return [tuple(f) for f in folds]


def _segment(inputs, start, end, scan_config, model, universe):
    seg_inputs = _truncate(inputs, end)
    res = run(seg_inputs, _windows(seg_inputs, start, end), dataclasses.replace(scan_config, as_of=end), model,
              universe=universe)
    res["window"] = [start.isoformat(), end.isoformat()]
    return res


def run_walk_forward(inputs, folds, scan_config, model, universe=None):
    """Each fold: an IN and an OUT segment, each scanned at every candle end inside its
    own window and simulated on candles that end by the window's end (a trade still open
    then is OPEN_AT_END_OF_DATA). Candles before the window are history, as in any scan.
    pooled_out joins the OUT trades of every fold, one record per (symbol, zone id): the
    earliest signal is kept (a zone signals once, P-BT-1)."""
    folds = check_folds(folds)
    out_folds, pooled, seen, dropped = [], [], set(), 0
    for n, (a, b, c, d) in enumerate(folds):
        seg_in = _segment(inputs, a, b, scan_config, model, universe)
        seg_out = _segment(inputs, c, d, scan_config, model, universe)
        out_folds.append({"fold": n, "IN": seg_in, "OUT": seg_out})
    for t in sorted([t for f in out_folds for t in f["OUT"]["trades"]],
                    key=lambda t: (t["signal_as_of"], t["symbol"], t["zone_id"])):
        key = (t["symbol"], t["zone_id"])
        if key in seen:
            dropped += 1
            continue
        seen.add(key)
        pooled.append(t)
    return {"model": dataclasses.asdict(model), "folds": out_folds,
            "pooled_out": {"metrics": extended_metrics(pooled), "signals": len(pooled),
                           "duplicate_zone_signals_dropped": dropped},
            "limitations": _limitations(model, universe), "no_selection": NO_SELECTION_NOTE,
            "note": "Per-fold IN and OUT arithmetic with one user model. Not a performance claim."}


def run_sensitivity(inputs, as_of_times, scan_config, models, split=None, universe=None):
    """The same point-in-time signals simulated under each user model, reported side by
    side in the order given. Nothing is ranked or picked: there is no 'best' model."""
    if not models:
        raise ValueError("at least one model is required")
    history = scanner.scan_history(inputs, as_of_times, scan_config, universe=universe)
    runs = []
    for n, mod in enumerate(models):
        res = _from_history(history, inputs, scan_config, mod, split=split, universe=universe)
        runs.append({"index": n, "model": res["model"], "signals": res["signals"], "metrics": res["metrics"],
                     "limitations": res["limitations"], "portfolio_rules": res["portfolio_rules"]})
    return {"scans": len(history), "runs": runs, "no_selection": NO_SELECTION_NOTE,
            "limitations": sorted(set(x for r in runs for x in r["limitations"])),
            "note": "Side-by-side arithmetic under each user model, in input order. Not ranked; "
                    "not a performance claim."}


def to_json(result):
    return json.dumps(result, sort_keys=True, indent=1)


# --- command line (registered on nse.research.cli by add_commands) ----------------------

def load_model(path):
    """ExecutionModel from a JSON file. Every assumption field is required; the optional
    portfolio rules may be absent (then not applied, and listed as limitations)."""
    with open(path, encoding="utf-8") as fh:
        spec = json.load(fh)
    if not isinstance(spec, dict):
        raise ValueError("%s: a model is a JSON object" % path)
    spec["statuses"] = tuple(spec.get("statuses", ()))
    return ExecutionModel(**spec)


def load_folds(path, as_of):
    """Folds JSON: a list of [in_start, in_end, out_start, out_end] or of objects with
    those keys; dates are parsed like --start (the 15:30 close of the day)."""
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    if not isinstance(raw, list):
        raise ValueError("%s: folds are a JSON list" % path)
    keys = ("in_start", "in_end", "out_start", "out_end")
    folds = []
    for n, f in enumerate(raw):
        if isinstance(f, dict):
            missing = [k for k in keys if k not in f]
            if missing:
                raise ValueError("fold %d: missing %s" % (n, ", ".join(missing)))
            f = [f[k] for k in keys]
        if not isinstance(f, list) or len(f) != 4:
            raise ValueError("fold %d: need four dates" % n)
        folds.append(tuple(as_of(str(x)) for x in f))
    return check_folds(folds)


def _common(p):
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--symbols")
    g.add_argument("--universe")
    s = p.add_mutually_exclusive_group(required=True)
    s.add_argument("--bhavcopy-dir")
    s.add_argument("--csv-dir")
    p.add_argument("--manifest")
    p.add_argument("--series", default="EQ")
    p.add_argument("--source-label", default="USER_CSV")
    p.add_argument("--price-adjustment", default="UNKNOWN", choices=("UNKNOWN", "NONE", "ADJUSTED"))
    p.add_argument("--calendar")
    p.add_argument("--risk-per-trade", type=float)
    p.add_argument("--out", required=True)


def _setup(args, end):
    from nse.research import cli, universe as uni
    from nse.research.deps import calendar as cal_mod
    universe = uni.load(args.universe) if args.universe else uni.adhoc(args.symbols.split(","))
    inputs = cli._inputs(args, sorted(set(r.symbol for r in universe.rows)))
    calendar = cal_mod.NseCalendar.load(args.calendar) if args.calendar else None
    cfg = scanner.ScanConfig(as_of=end, calendar=calendar, calendar_label=args.calendar or "NONE",
                             risk_per_trade=args.risk_per_trade, universe_label=universe.name)
    return inputs, cfg, None if universe.adhoc else universe


def _write(path, res, summary):
    import os
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(to_json(res) + "\n")
    print(json.dumps(summary, sort_keys=True, indent=1))


def _guarded(fn):
    def handler(args):
        from nse.research import universe as uni
        from nse.research.deps import bhavcopy, calendar as cal_mod
        try:
            return fn(args)
        except (ValueError, TypeError, OSError, uni.UniverseError, cal_mod.CalendarError, bhavcopy.BhavcopyError) as e:
            print("error: %s" % e, file=sys.stderr)
            return 2
    return handler


def cmd_walk_forward(args):
    from nse.research import cli
    model = load_model(args.model)
    folds = load_folds(args.folds, cli._as_of)
    inputs, cfg, universe = _setup(args, max(f[3] for f in folds))
    res = run_walk_forward(inputs, folds, cfg, model, universe=universe)
    _write(args.out, res, {"folds": [{"fold": f["fold"], "IN": f["IN"]["metrics"]["ALL"],
                                      "OUT": f["OUT"]["metrics"]["ALL"]} for f in res["folds"]],
                           "pooled_out": res["pooled_out"], "limitations": res["limitations"]})
    return 0


def cmd_sensitivity(args):
    from nse.research import cli
    models = [load_model(p) for p in args.models]
    start, end = cli._as_of(args.start), cli._as_of(args.end)
    inputs, cfg, universe = _setup(args, end)
    dates = _windows(inputs, start, end)
    res = run_sensitivity(inputs, dates, cfg, models, split=cli._as_of(args.split) if args.split else None,
                          universe=universe)
    _write(args.out, res, {"runs": [{"index": r["index"], "model_file": args.models[r["index"]],
                                     "metrics": r["metrics"]["ALL"]} for r in res["runs"]],
                           "limitations": res["limitations"]})
    return 0


def add_commands(subparsers):
    """Register backtest-walk-forward and backtest-sensitivity (input options as backtest)."""
    w = subparsers.add_parser("backtest-walk-forward",
                              help="per-fold IN/OUT simulation of point-in-time signals with one user model")
    w.add_argument("--model", required=True, help="JSON with every backtest.ExecutionModel assumption field")
    w.add_argument("--folds", required=True, help="JSON list of [in_start, in_end, out_start, out_end]")
    _common(w)
    w.set_defaults(func=_guarded(cmd_walk_forward))
    s = subparsers.add_parser("backtest-sensitivity",
                              help="the same signals under several user models, side by side, unranked")
    s.add_argument("--models", required=True, nargs="+", help="model JSON files, reported in this order")
    s.add_argument("--start", required=True, help="first signal date")
    s.add_argument("--end", required=True, help="last signal date")
    s.add_argument("--split", help="in-sample up to this date, out-of-sample after")
    _common(s)
    s.set_defaults(func=_guarded(cmd_sensitivity))
    return subparsers
