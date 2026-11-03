"""Rulebook risk management on top of a candidate result (C1, C2, Chapters 3 and 6).

A risk plan is separate from qualification: it never changes a gate outcome or a
candidate status, and it never approves a trade. Rules applied, all from the Rulebook:
  - Quantity = floor(RPT / (Entry - SL)) (RB 42, 2162); whole shares, so the loss at the
    SL is at most the RPT ("not more", RB 51, 2165) and the rounding shortfall is shown
    ("not less": RB 2204 accepts 333 x 3 = 999 for an RPT of 1000). Exact decimal
    arithmetic, so a binary-float error never adds or removes a share.
  - RPT % of capital against the declared development stage (RB 53-59, 2208-2214); the
    max monthly risk column is evidence only. Above every stage (2%) is a FAIL even with no
    stage declared.
  - Maximum 10 trades a month is a ceiling (RB 2392, 2408): 10 already taken -> FAIL.
  - R:R >= 2 (C2, RB 82), computed by levels.rr_range (one R:R implementation).
  - Size by risk, never by affordability (RB 68, 2227): capital short of the position
    value is MANUAL and the quantity is never reduced.
  - Cash equity only (D2; RB 67, 73): a derivative is a FAIL.
  - Never average down (RB 69, 2140, 2229): adding below the average is a FAIL.
max_position_value_pct is the user's own limit; None is NOT_CONFIGURED, never a default.
The entry and SL buffers are unresolved (B9), so a candidate plan is a RANGE over every
end of the printed entry and SL ranges; the person picks the buffer, then the quantity.
Every check: PASS, FAIL, MANUAL, NOT_APPLICABLE or NOT_CONFIGURED with reason and source.
Nothing here is externally validated (NOT_EXTERNALLY_VALIDATED).
"""

import json
import math
import os
from dataclasses import dataclass
from decimal import Decimal, ROUND_FLOOR
from typing import Optional

from nse.research import levels, models as m

RISK_VERSION = "1.0.0"
PASS, FAIL, MANUAL = m.PASS, m.FAIL, m.MANUAL
NOT_APPLICABLE = "NOT_APPLICABLE"
NOT_CONFIGURED = "NOT_CONFIGURED"
CHECK_OUTCOMES = (PASS, FAIL, MANUAL, NOT_APPLICABLE, NOT_CONFIGURED)
_WORST = (FAIL, MANUAL, NOT_CONFIGURED, PASS, NOT_APPLICABLE)       # most restrictive first

# plan statuses; none of them means "approved"
INVALID_LEVELS = "INVALID_LEVELS"
NOT_APPLICABLE_STATUS = "NOT_APPLICABLE_STATUS"
PLAN_FAIL = "RISK_RULE_FAILED"
PLAN_MANUAL = "MANUAL_REVIEW"
PLAN_WITHIN = "WITHIN_RISK_RULES_MANUAL_CHECKS_PENDING"

LEARNING, INTERMEDIATE, PROFESSIONAL = "LEARNING", "INTERMEDIATE", "PROFESSIONAL"
STAGES = (LEARNING, INTERMEDIATE, PROFESSIONAL)
# stage: (RPT % min, max, max monthly risk % min, max), as printed (RB 57-59, 2212-2214)
STAGE_BANDS = {
    LEARNING: (Decimal("0.5"), Decimal("1"), Decimal("5"), Decimal("10")),
    INTERMEDIATE: (Decimal("1"), Decimal("1.5"), Decimal("10"), Decimal("15")),
    PROFESSIONAL: (Decimal("1.5"), Decimal("2"), Decimal("15"), Decimal("20")),
}
MAX_RPT_PCT = Decimal("2")           # the top of every stage band (RB 59, 2214)
MAX_TRADES_PER_MONTH = 10            # RB 2392: a ceiling, not a target
NOTE = ("A risk plan never approves a trade. Manual checks are pending; the entry and SL buffers "
        "(B9) are chosen by the person. Nothing here is externally validated.")


def _dec(v):
    return Decimal(repr(float(v)))


def _num(v):
    return float(v.quantize(Decimal("0.0001")))


def _finite(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _check(code, outcome, reason, sources):
    if outcome not in CHECK_OUTCOMES:
        raise ValueError("unknown check outcome %r" % outcome)
    return {"code": code, "outcome": outcome, "reason": reason, "sources": list(sources)}


@dataclass(frozen=True)
class RiskConfig:
    capital: float
    rpt_amount: Optional[float] = None
    rpt_pct: Optional[float] = None              # percent of capital, e.g. 1.0 = 1%
    stage: Optional[str] = None
    trades_this_month: Optional[int] = None      # trades already taken this month
    open_risk_amount: Optional[float] = None     # risk already open this month (evidence only)
    max_position_value_pct: Optional[float] = None   # the user's own limit; None = NOT_CONFIGURED

    def __post_init__(self):
        if not _finite(self.capital) or self.capital <= 0:
            raise ValueError("capital must be a finite number > 0, got %r" % (self.capital,))
        if (self.rpt_amount is None) == (self.rpt_pct is None):
            raise ValueError("give exactly one of rpt_amount and rpt_pct")
        for name in ("rpt_amount", "rpt_pct"):
            v = getattr(self, name)
            if v is not None and (not _finite(v) or v <= 0):
                raise ValueError("%s must be a finite number > 0, got %r" % (name, v))
        if self.stage is not None and self.stage not in STAGES:
            raise ValueError("stage must be one of %s or None, got %r" % (", ".join(STAGES), self.stage))
        t = self.trades_this_month
        if t is not None and (not isinstance(t, int) or isinstance(t, bool) or t < 0):
            raise ValueError("trades_this_month must be a whole number >= 0 or None, got %r" % (t,))
        if self.open_risk_amount is not None and (not _finite(self.open_risk_amount) or self.open_risk_amount < 0):
            raise ValueError("open_risk_amount must be a finite number >= 0 or None")
        q = self.max_position_value_pct
        if q is not None and (not _finite(q) or q <= 0 or q > 100):
            raise ValueError("max_position_value_pct must be in (0, 100] or None, got %r" % (q,))

    @property
    def rpt(self):
        """RPT in rupees, exact (Decimal)."""
        if self.rpt_amount is not None:
            return _dec(self.rpt_amount)
        return _dec(self.capital) * _dec(self.rpt_pct) / 100

    @property
    def rpt_percent(self):
        if self.rpt_pct is not None:
            return _dec(self.rpt_pct)
        return _dec(self.rpt_amount) * 100 / _dec(self.capital)

    def to_dict(self):
        return {"capital": self.capital, "rpt_amount_input": self.rpt_amount, "rpt_pct_input": self.rpt_pct,
                "rpt_amount": _num(self.rpt), "rpt_pct": _num(self.rpt_percent), "stage": self.stage,
                "trades_this_month": self.trades_this_month, "open_risk_amount": self.open_risk_amount,
                "max_position_value_pct": self.max_position_value_pct}


def assess_config(config):
    """Checks of the configuration itself: RPT against the stage band, the monthly ceiling."""
    pct = config.rpt_percent
    if config.stage is None:
        if pct > MAX_RPT_PCT:
            stage = _check("RPT_STAGE_BAND", FAIL, "RPT %s%% is above 2%%, the top of every stage band; C1: RPT "
                           "must never exceed your defined percentage" % _num(pct), ["RB 53-59, 2208-2220, 1029", "P-RISK-1 (reading, owner decision)"])
        else:
            stage = _check("RPT_STAGE_BAND", MANUAL, "development stage not declared, so the RPT %s%% cannot be "
                           "checked against its band" % _num(pct), ["RB 53-59, 2208-2214"])
    else:
        lo, hi = STAGE_BANDS[config.stage][:2]
        if pct > hi:
            stage = _check("RPT_STAGE_BAND", FAIL, "RPT %s%% is above the %s maximum %s%%; C1: RPT must never "
                           "exceed your defined percentage" % (_num(pct), config.stage, hi), ["RB 53-59, 2208-2220, 1029", "P-RISK-1 (reading, owner decision)"])
        elif pct < lo:
            stage = _check("RPT_STAGE_BAND", MANUAL, "RPT %s%% is below the printed %s band %s-%s%%; the Rulebook "
                           "does not say whether that is allowed" % (_num(pct), config.stage, lo, hi),
                           ["RB 53-59, 2208-2214"])
        else:
            stage = _check("RPT_STAGE_BAND", PASS, "RPT %s%% is within the %s band %s-%s%%"
                           % (_num(pct), config.stage, lo, hi), ["RB 53-59, 2208-2214"])
    t = config.trades_this_month
    if t is None:
        month = _check("MONTHLY_TRADE_LIMIT", MANUAL, "trades taken this month not given; the 10-trade ceiling "
                       "cannot be checked", ["RB 2392, 2408"])
    elif t >= MAX_TRADES_PER_MONTH:
        month = _check("MONTHLY_TRADE_LIMIT", FAIL, "%d trades already taken this month; 10 is the maximum, stop "
                       "trading until next month" % t, ["RB 2392, 2408"])
    else:
        month = _check("MONTHLY_TRADE_LIMIT", PASS, "%d trades taken this month; this would be trade %d of at "
                       "most 10" % (t, t + 1), ["RB 2392, 2408"])
    evidence = {"rpt_amount": _num(config.rpt), "rpt_pct": _num(pct)}
    if config.stage is not None:
        lo, hi, mlo, mhi = STAGE_BANDS[config.stage]
        evidence["stage_rpt_band_pct"] = [float(lo), float(hi)]
        evidence["stage_max_monthly_risk_pct"] = [float(mlo), float(mhi)]
    if config.open_risk_amount is not None:
        evidence["open_risk_pct"] = _num(_dec(config.open_risk_amount) * 100 / _dec(config.capital))
        evidence["open_risk_pct_with_this_trade"] = _num((_dec(config.open_risk_amount) + config.rpt) * 100
                                                         / _dec(config.capital))
    evidence["note"] = "max monthly risk (RB 2212-2214) is shown as evidence only; it is not a gate"
    return {"checks": [stage, month], "evidence": evidence, "outcome": _worst([stage, month])}


def _worst(checks):
    outs = [c["outcome"] for c in checks]
    for o in _WORST:
        if o in outs:
            return o
    return NOT_APPLICABLE


def _status(checks):
    w = _worst(checks)
    return PLAN_FAIL if w == FAIL else PLAN_MANUAL if w == MANUAL else PLAN_WITHIN


def _invalid(entry, stop, target, config, reason, cfg_checks):
    checks = cfg_checks + [_check("LEVELS", FAIL, reason, ["RB 42, 2162"])]
    return {"status": INVALID_LEVELS, "entry": entry, "stop": stop, "target": target, "quantity": None,
            "checks": checks, "config": config.to_dict(), "approved": False, "manual_checks_pending": True,
            "limitations": [m.NOT_EXTERNALLY_VALIDATED], "note": NOTE, "risk_version": RISK_VERSION}


def plan_trade(entry, stop, target, config, derivative=False):
    """Position size and risk checks for one long trade at entry, stop and target (target may
    be None: R:R is then MANUAL). derivative=True is a FAIL (D2). Never raises on bad levels:
    the plan is INVALID_LEVELS with the reason."""
    cfg = assess_config(config)["checks"]
    for name, v in (("entry", entry), ("stop", stop)):
        if not _finite(v) or v <= 0:
            return _invalid(entry, stop, target, config, "INVALID_LEVELS: %s must be a finite price > 0, got %r"
                            % (name, v), cfg)
    if target is not None and not _finite(target):
        return _invalid(entry, stop, target, config, "INVALID_LEVELS: target must be finite, got %r" % (target,), cfg)
    dist = _dec(entry) - _dec(stop)
    if dist <= 0:
        return _invalid(entry, stop, target, config, "INVALID_LEVELS: risk distance entry - stop = %s is not "
                        "positive (a long SL is below the entry)" % _num(dist), cfg)
    checks = list(cfg)
    if derivative:
        checks.append(_check("INSTRUMENT_CASH_EQUITY", FAIL, "derivative: F&O lot sizes are fixed and can force "
                             "risk beyond the RPT; cash equity only", ["D2", "RB 67, 73, 2260-2261"]))
    else:
        checks.append(_check("INSTRUMENT_CASH_EQUITY", PASS, "cash equity (D2 scope)", ["D2", "RB 67, 73, 2260-2261"]))
    rpt = config.rpt
    qty = int((rpt / dist).to_integral_value(rounding=ROUND_FLOOR))
    loss = dist * qty
    out = {"entry": entry, "stop": stop, "target": target, "risk_per_share": _num(dist), "quantity": qty,
           "rpt_amount": _num(rpt), "loss_if_stopped": _num(loss), "rpt_shortfall": _num(rpt - loss)}
    if qty == 0:
        checks.append(_check("QUANTITY", FAIL, "RPT %s is smaller than the risk of one share %s: no position "
                             "fits the formula" % (_num(rpt), _num(dist)), ["RB 42, 2162"]))
    else:
        checks.append(_check("QUANTITY", PASS, "floor(%s / %s) = %d shares" % (_num(rpt), _num(dist), qty),
                             ["RB 42, 2162"]))
        checks.append(_check("RPT_NOT_EXCEEDED", PASS if loss <= rpt else FAIL,
                             "loss if stopped %s vs RPT %s; shortfall %s from whole shares (RB 2204 accepts 999 "
                             "for 1000)" % (_num(loss), _num(rpt), _num(rpt - loss)), ["RB 51, 2165, 2204"]))
    cap_req = _dec(entry) * qty
    out["capital_required"] = _num(cap_req)
    out["position_value_pct"] = _num(cap_req * 100 / _dec(config.capital))
    if qty and cap_req > _dec(config.capital):
        checks.append(_check("CAPITAL_SUFFICIENT", MANUAL, "CAPITAL_INSUFFICIENT: %d shares need %s, capital is %s. "
                             "The size is not reduced: size by risk, never by affordability; skip or review"
                             % (qty, _num(cap_req), config.capital), ["RB 68, 75, 2227"]))
    elif qty:
        checks.append(_check("CAPITAL_SUFFICIENT", PASS, "position value %s is within capital %s"
                             % (_num(cap_req), config.capital), ["RB 68, 2227"]))
    q = config.max_position_value_pct
    if q is None:
        checks.append(_check("POSITION_VALUE_LIMIT", NOT_CONFIGURED, "no user position-value limit configured; "
                             "the Rulebook prints none", ["RB 68"]))
    elif qty and cap_req * 100 / _dec(config.capital) > _dec(q):
        checks.append(_check("POSITION_VALUE_LIMIT", MANUAL, "position value %s%% of capital is above your limit "
                             "%s%%; the size is not reduced (RB 68): skip or review"
                             % (out["position_value_pct"], q), ["user limit", "RB 68"]))
    elif qty:
        checks.append(_check("POSITION_VALUE_LIMIT", PASS, "position value %s%% of capital is within your limit %s%%"
                             % (out["position_value_pct"], q), ["user limit"]))
    if target is None:
        out["rr"] = None
        checks.append(_check("RR_MIN_2", MANUAL, "no target given: R:R cannot be computed", ["RB 82", "C2"]))
    else:
        point = {"entry": [entry, entry], "sl": {"normal": [stop, stop], "exceptional": [stop, stop]}}
        rr_out = levels.rr_range(point, target)
        rr = rr_out["rr"][0]
        out["rr"] = rr
        out["profit_at_target"] = _num((_dec(target) - _dec(entry)) * qty)
        ok = rr_out["status"] == levels.PASS_ALL
        checks.append(_check("RR_MIN_2", PASS if ok else FAIL, "R:R %s %s 2" % (rr, ">=" if ok else "<"),
                             ["RB 82, 90", "C2", "RF8"]))
    if config.open_risk_amount is not None:
        out["open_risk_pct_with_this_trade"] = _num((_dec(config.open_risk_amount) + loss) * 100
                                                    / _dec(config.capital))
    out.update({"status": _status(checks), "checks": checks, "config": config.to_dict(), "approved": False,
                "manual_checks_pending": True, "limitations": [m.NOT_EXTERNALLY_VALIDATED],
                "rules": ["SL is a hard order and locked once triggered (RB 2138-2139)",
                          "never average down (RB 69, 2140)", "exit on touch, not on close (RB 2141)"],
                "note": NOTE, "risk_version": RISK_VERSION})
    return out


def plan_add_to_position(existing_position, new_price):
    """Adding to an open position. existing_position: {"quantity": int > 0, "average_price": > 0}.
    Below the average is averaging down: FAIL (RB 69, 2140, 2229). At or above it is MANUAL:
    adding is not a Rulebook entry type, and its risk is not covered by the RPT formula."""
    qty = existing_position.get("quantity")
    avg = existing_position.get("average_price")
    if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
        raise ValueError("existing_position quantity must be a whole number > 0, got %r" % (qty,))
    for name, v in (("average_price", avg), ("new_price", new_price)):
        if not _finite(v) or v <= 0:
            raise ValueError("%s must be a finite price > 0, got %r" % (name, v))
    if _dec(new_price) < _dec(avg):
        c = _check("AVERAGING_DOWN", FAIL, "new price %s is below the average %s: NEVER add to a losing trade"
                   % (new_price, avg), ["RB 69, 2140, 2229"])
    else:
        c = _check("AVERAGING_DOWN", MANUAL, "adding at %s (average %s) is not a Rulebook entry type; a new "
                   "position needs its own zone, SL and RPT" % (new_price, avg), ["RB 42, 2162", "RB 69"])
    return {"status": PLAN_FAIL if c["outcome"] == FAIL else PLAN_MANUAL, "checks": [c], "approved": False,
            "existing_position": {"quantity": qty, "average_price": avg}, "new_price": new_price,
            "limitations": [m.NOT_EXTERNALLY_VALIDATED], "risk_version": RISK_VERSION}


def _merge(plans):
    """One check per code, the most restrictive outcome over every combination."""
    by = {}
    order = []
    for p in plans:
        for c in p["checks"]:
            if c["code"] not in by:
                by[c["code"]] = []
                order.append(c["code"])
            by[c["code"]].append(c)
    out = []
    for code in order:
        cs = by[code]
        w = _worst(cs)
        reasons = sorted(set(c["reason"] for c in cs if c["outcome"] == w))
        reason = reasons[0] if len(reasons) == 1 else "%d combinations: %s" % (len(reasons), " | ".join(reasons))
        if w == FAIL and any(c["outcome"] == PASS for c in cs):
            # fails for some buffer / SL choices only: the choice is the trader's (spec 6.3: DEPENDS -> MANUAL; B9)
            w, reason = MANUAL, "DEPENDS_ON_BUFFER (B9): fails for %d of %d entry/SL combinations: %s" % (
                sum(1 for c in cs if c["outcome"] == FAIL), len(cs), reason)
        out.append({"code": code, "outcome": w, "reason": reason,
                    "sources": sorted(set(s for c in cs for s in c["sources"]))})
    return out


def _span(vals):
    vals = [v for v in vals if v is not None]
    return [min(vals), max(vals)] if vals else [None, None]


def risk_plan_for_candidate(candidate, config, derivative=False):
    """Risk plan for one candidate record of scan.json (reports.to_dict(result)["symbols"][i]
    ["candidates"][j]). Only ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING gets sizing; any other
    status is NOT_APPLICABLE_STATUS with the reasons. Sizing is a range over every end of the
    printed entry range and both SL ranges (B9), with the G7 target."""
    zone = candidate.get("zone") or {}
    head = {"symbol": candidate.get("symbol"), "trade_type": candidate.get("trade_type"),
            "execution_tf": candidate.get("execution_tf"), "as_of": candidate.get("as_of"),
            "zone_id": zone.get("zone_id"), "created_time": zone.get("created_time"),
            "candidate_status": candidate.get("status"), "approved": False, "manual_checks_pending": True,
            "candidate_manual_checks": sorted(x.get("code") for x in candidate.get("manual_checks") or []),
            "config": config.to_dict(), "config_assessment": assess_config(config),
            "limitations": sorted(set(list(candidate.get("limitations") or []) + [m.NOT_EXTERNALLY_VALIDATED])),
            "note": NOTE, "risk_version": RISK_VERSION}
    gates = candidate.get("gates") or []
    try:
        derived = m.derive_status([m.GateResult(g["gate"], g["outcome"]) for g in gates])
    except (KeyError, TypeError, ValueError) as e:
        derived = "UNDERIVABLE (%s)" % e
    if derived != candidate.get("status"):
        # a status its own gates do not give (an edited or mixed scan.json): never sized (review 2026-11-02)
        head.update({"status": NOT_APPLICABLE_STATUS,
                     "reason": "STATUS_INCONSISTENT_WITH_GATES: recorded %s, gates give %s; no sizing"
                     % (candidate.get("status"), derived),
                     "status_reasons": list(candidate.get("status_reasons") or []),
                     "manual_review": list(candidate.get("manual_review") or [])})
        return head
    if candidate.get("status") != m.ACTIONABLE:
        head.update({"status": NOT_APPLICABLE_STATUS, "reason": "no sizing for a %s result; sizing is offered only "
                     "for %s" % (candidate.get("status"), m.ACTIONABLE),
                     "status_reasons": list(candidate.get("status_reasons") or []),
                     "manual_review": list(candidate.get("manual_review") or [])})
        return head
    lv = candidate.get("levels") or {}
    g7 = [g for g in candidate.get("gates") or [] if g.get("gate") == "G7"]
    target = ((g7[0].get("evidence") or {}).get("target") or {}).get("proximal") if g7 else None
    head["target"] = target
    head["target_source"] = "G7 evidence: nearest fresh opposing supply PL (RB 551-558)" if target is not None \
        else "no G7 target in the candidate record"
    entries = sorted(set(v for v in (lv.get("entry") or []) if v is not None))
    sls = sorted(set(v for pair in (lv.get("sl") or {}).values() for v in pair if v is not None))
    if not lv.get("valid") or not entries or not sls:
        head.update({"status": INVALID_LEVELS, "reason": "candidate levels are not valid: %s"
                     % "; ".join(lv.get("problems") or ["missing entry or SL range"])})
        return head
    combos = [plan_trade(e, s, target, config, derivative) for e in entries for s in sls]
    checks = _merge(combos)
    manual = [{"code": "BUFFER_SELECTION", "reason": "entry and SL buffers are unresolved (B9): the quantity "
               "depends on the buffer the person chooses within the printed tiers; recompute with plan_trade",
               "sources": ["D7", "B9"]}]
    if any(p["status"] == INVALID_LEVELS for p in combos):
        status = INVALID_LEVELS
    else:
        status = _status(checks)
    head.update({
        "status": status, "checks": checks, "manual_checks": manual,
        "entry_range": [entries[0], entries[-1]], "sl_values": sls,
        "quantity_range": _span(p["quantity"] for p in combos),
        "max_loss_if_stopped": max(p.get("loss_if_stopped") or 0 for p in combos),
        "capital_required_range": _span(p.get("capital_required") for p in combos),
        "rr": levels.rr_range(lv, target) if target is not None and status != INVALID_LEVELS else None,
        "combinations": [{k: p.get(k) for k in ("entry", "stop", "quantity", "risk_per_share", "loss_if_stopped",
                                                 "rpt_shortfall", "capital_required", "rr", "status")}
                         for p in combos],
    })
    return head


def plans_for_scan(scan, config, derivative=False):
    """Every candidate of a scan.json dict, in (symbol, created_time, zone_id) order."""
    scan_lims = list(scan.get("limitations") or [])
    plans = []
    for s in scan.get("symbols") or []:
        for c in s.get("candidates") or []:
            p = risk_plan_for_candidate(c, config, derivative)
            p["limitations"] = sorted(set(p["limitations"]) | set(scan_lims) | set(s.get("limitations") or []))
            plans.append(p)
    plans.sort(key=lambda p: (str(p["symbol"]), str(p["created_time"]), str(p["zone_id"])))
    counts = {}
    for p in plans:
        counts[p["status"]] = counts.get(p["status"], 0) + 1
    return {"as_of": scan.get("as_of"), "trade_type": scan.get("trade_type"), "config": config.to_dict(),
            "config_assessment": assess_config(config), "plans": plans,
            "plan_status_counts": dict(sorted(counts.items())), "approved": False,
            "limitations": sorted(set(scan_lims) | {m.NOT_EXTERNALLY_VALIDATED}), "note": NOTE, "risk_version": RISK_VERSION}


def to_json(obj):
    return json.dumps(obj, sort_keys=True, indent=1)


def cmd_risk_plan(args):
    try:
        with open(args.scan, encoding="utf-8") as fh:
            scan = json.load(fh)
        config = RiskConfig(capital=args.capital, rpt_amount=args.rpt_amount, rpt_pct=args.rpt_pct,
                            stage=args.stage, trades_this_month=args.trades_this_month,
                            max_position_value_pct=args.max_position_pct, open_risk_amount=args.open_risk)
    except (OSError, ValueError) as e:
        print("risk-plan: %s" % e)
        return 2
    out = plans_for_scan(scan, config)
    text = to_json(out)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    print(text)
    failed = out["config_assessment"]["outcome"] == FAIL or any(
        p["status"] in (PLAN_FAIL, INVALID_LEVELS) for p in out["plans"])
    return 1 if failed else 0


def add_commands(subparsers):
    r = subparsers.add_parser("risk-plan", help="Rulebook position size and risk checks for a scan's candidates "
                              "(never approves a trade)")
    r.add_argument("--scan", required=True, help="scan.json written by the scan command")
    r.add_argument("--capital", required=True, type=float)
    g = r.add_mutually_exclusive_group(required=True)
    g.add_argument("--rpt-amount", type=float, help="risk per trade in rupees")
    g.add_argument("--rpt-pct", type=float, help="risk per trade in percent of capital (1 = 1%%)")
    r.add_argument("--stage", choices=STAGES, help="development stage (RB 53-59); omitted -> MANUAL")
    r.add_argument("--trades-this-month", type=int, help="trades already taken this month; omitted -> MANUAL")
    r.add_argument("--open-risk", type=float, help="risk already open this month, rupees (evidence only)")
    r.add_argument("--max-position-pct", type=float, help="your own position-value limit, %% of capital")
    r.add_argument("--out", help="also write the JSON here")
    r.set_defaults(func=cmd_risk_plan)
