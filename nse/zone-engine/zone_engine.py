#!/usr/bin/env python3
"""NSE demand and supply Zone Engine (Phase 1, isolated). Standard library only.

Detects demand and supply zones on ONE timeframe of completed candles, scores the
7-point core, tracks freshness and distal-line invalidation, and says which demand
zones are eligible AT THE ZONE LEVEL. Location, trend, HTF conflict, R:R and every
other scanner gate are downstream and are not evaluated here.

It reads no market data, connects to no broker, needs no credentials and never
places an order. Callers pass candles in; nothing is fetched.

Sources (both read only, never modified):
  RB n  = line n of "Trading Rulebook 341a82c22ebf8056a235c9695e1c0d87.md"
  PS n  = line n of "Demand&Supply Indicator.pine"

Source precedence is DECISION_LOG D12 (rulebook-strict):
  1. Explicit rulebook rules win.
  2. Pine behaviour fills gaps only where the rulebook is silent and Pine does not
     conflict with it.
  3. Conflicts or ambiguities are exposed and the affected zone goes to manual review.
To expose conflicts the engine runs twice on the same candles: once with the
rulebook-strict profile (the result) and once with the Pine profile (comparison
only). Zones Pine would draw but the rulebook would not are reported, never
made eligible.

Rulebook-strict choices (D12 per-item table):
  - Strong / explosive candle = body > 50% of range (RB 402). Pine's extra path
    "close beyond the prior high/low" (PS 332-333, 1436-1437, 1587) is used only in
    the Pine comparison profile (PR1).
  - Max base candles = 5, a Pine input option (PS 10), because the rulebook scores
    4-5 bases (RB 786). A 6th base candle ends the cluster with no zone: the
    rulebook's "6+ = garbage area, reject" (RB 787, 800-806). A base candle that closes
    outside a full cluster is neither counted nor dismissed: BASE_CLOSED_OUTSIDE_CLUSTER,
    manual review, no zone (audit M3).
  - Leg-out count is per zone (RB 728). Pine counts only for the newest zone
    (PS 1764-1775); a difference that changes the score goes to manual review (PR5).
  - Transition candles (inside the cluster wicks, body <= 75%, PS 489) are not
    counted as bases, as in Pine; a count that includes them is also reported, and a
    score difference goes to manual review (RB 404, 739, 769; PR4).
  - A gap that lifts strength to 2 cannot be checked for "meaningful" (RB 941, 2974):
    manual review (PR6). No size threshold is invented.
  - Relative size and context of the leg-out (RB 740-741) are never automated: every
    demand zone carries the LEGOUT_RELATIVE_SIZE_CONTEXT check, with measured ranges
    as evidence (D8).
  - Pine-defined where the rulebook is silent: base threshold body <= 50% (PS 335),
    3-bar leg-in window (PS 1390), price-achievement test (PS 1434-1439, used as
    the objective minimum for RB 739), pending achievement window (PS 1546, 2097),
    Body-to-Wick PL/DL with exceptional DL (PS 1470-1490), 3-bar leg-out tracking
    with a cap of 5 (PS 1771), zero-base zones (PS 1717-1762).
  - Zero-base base score 2.0 is Pine's (PS 601); the rulebook table starts at one
    base (RB 785-787). Every zero-base score is tagged ZB-PINE-REF (D13).

Two Pine engine variants, reproduced as written:
  chart (D, 125m, 75m): PS 1386-1775. The pending block runs on the same bar that
        sets pending_left = 2 (PS 1546 then 1584), fails by construction and counts
        down, so ONE later bar can complete the achievement. New clusters may start
        while a zone is pending. Zero-base zones ignore pending.
  htf   (W, M, and the Q/HY/Y extension): PS 1777-2603. Pending is checked before
        the cluster logic (PS 1799 vs 2097), so TWO later bars can complete it; no
        cluster starts while pending (PS 1932); zero-base needs no pending (PS 2139).
  Q, HY and Y have no Pine zone engine at all (D11); results carry NO_PINE_REFERENCE.

Per bar, in Pine's order: strong-candle tracking, cluster/leg-out (and pending, in
the variant's order), zero-base, leg-out tracking, then invalidation and tests
(PS 2605-2656). A zone is invalidated permanently when a candle CLOSES beyond its
distal line (PS 2613; RB 1627, 1741). A later candle touching the proximal line by
wick or body is a test (RB 683-697; PS 2651); the creation bar is never a test.

Completed candles only: candles flagged complete=False at the end of the series
are ignored and listed; an incomplete candle followed by complete ones is an
error. as_of cuts the series before anything is computed, so later candles can
never change an earlier state.
"""

import math
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

ENGINE_VERSION = "1.0.0"

# --- timeframes (D11, D16, D23) -------------------------------------------------

TIMEFRAME_VARIANT = {
    "Y": "htf", "HY": "htf", "Q": "htf", "M": "htf", "W": "htf",
    "D": "chart", "125m": "chart", "75m": "chart",
}
NO_PINE_ZONE_ENGINE = ("Y", "HY", "Q")
MIN_CANDLES = 3  # leg-in, base, leg-out; a zero-base zone also needs index > 2 (PS 1724)

# --- statuses and reason codes --------------------------------------------------

ELIGIBLE = "ZONE_ELIGIBLE"              # zone-level only; downstream gates still apply
MANUAL_REVIEW = "MANUAL_REVIEW"
INELIGIBLE = "INELIGIBLE"
CONTEXT_ONLY = "CONTEXT_ONLY"           # supply zones: resistance/target evidence (D2)

ZONE_TESTED = "ZONE_TESTED"                         # D3; RB 264, 683-697
ZONE_INVALIDATED = "ZONE_INVALIDATED"               # close beyond distal line, PS 2613
CORE_BELOW_7 = "CORE_BELOW_7"                       # RB 661, 829
SUPPLY_CONTEXT_ONLY = "SUPPLY_CONTEXT_ONLY"         # D2: no short candidates
INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"

GAP_MEANINGFULNESS_UNVERIFIED = "GAP_MEANINGFULNESS_UNVERIFIED"    # RB 941, 2974; PR6
BASE_COUNT_TRANSITION_AMBIGUITY = "BASE_COUNT_TRANSITION_AMBIGUITY"  # RB 404, 739, 769; PR4
LEGOUT_SEQUENCE_INTERRUPTED = "LEGOUT_SEQUENCE_INTERRUPTED"        # RB 728; PR5
PINE_SCORE_DIFFERS = "PINE_SCORE_DIFFERS"                          # D12; PR1, PR5
PINE_GEOMETRY_DIFFERS = "PINE_GEOMETRY_DIFFERS"                    # D12; PR1
PINE_NO_MATCHING_ZONE = "PINE_NO_MATCHING_ZONE"                    # D12; PR1
PENDING_WINDOW_PL_TOUCH = "PENDING_WINDOW_PL_TOUCH"                # RB 682 vs PS 2649; PR10
# A pending zone's first leg-out had body > 50% but failed the achievement test; the
# achievement candle came later. Pine starts the count at 1 on the achievement bar
# (PS 688, 1646). Whether the first leg-out is also one of the rulebook's "2+ explosive
# candles" (RB 728) is ambiguous, because RB 739 asks for price achievement as well.
PENDING_LEGOUT_COUNT_AMBIGUOUS = "PENDING_LEGOUT_COUNT_AMBIGUOUS"  # RB 728, 739 vs PS 688
PINE_ONLY_ZONE = "PINE_ONLY_ZONE"                                  # D12; PR1

LEGOUT_RELATIVE_SIZE_CONTEXT = "LEGOUT_RELATIVE_SIZE_CONTEXT"      # RB 740-741; D8

TAG_ZB = "ZB-PINE-REF"                    # D13
TAG_NO_PINE_REFERENCE = "NO_PINE_REFERENCE"  # D11: Q/HY/Y zones are a Python extension

EV_ZONE_CREATED = "ZONE_CREATED"
EV_PENDING_SET = "PENDING_SET"
EV_PENDING_REPLACED = "PENDING_REPLACED"
EV_ACHIEVEMENT_NOT_MET = "ACHIEVEMENT_NOT_MET"   # PR3: context-only pattern, manual (RB 1639)
EV_GARBAGE_AREA = "GARBAGE_AREA_6_PLUS_BASES"    # RB 787, 800-806
# A further base candle that CLOSES outside a full cluster: a 6th base (RB 787) or not an
# "overlapping" one (RB 802)? Unresolved by user decision M3: manual review, no zone.
EV_BASE_CLOSED_OUTSIDE = "BASE_CLOSED_OUTSIDE_CLUSTER"
EV_LEGOUT_INCREMENT = "LEGOUT_INCREMENT"
EV_TESTED = "ZONE_TESTED"
EV_DL_TOUCHED = "ZONE_DL_TOUCHED"                # D15 needs it; not an invalidation
EV_INVALIDATED = "ZONE_INVALIDATED"


# --- models ---------------------------------------------------------------------

@dataclass(frozen=True)
class Candle:
    """One candle. time is any increasing value (epoch seconds, ISO date string...)."""
    time: object
    open: float
    high: float
    low: float
    close: float
    complete: bool = True


@dataclass(frozen=True)
class Rules:
    """Numeric parameters, each from a source. Not user-tunable trading rules."""
    strong_body_ratio: float = 0.5   # RB 402 (body > 50%); PS 12, strict ">" at PS 332
    base_body_ratio: float = 0.5     # PS 11, 335 ("<="); rulebook silent
    transition_factor: float = 1.5   # PS 489: transition body <= 1.5 x base threshold
    max_base_candles: int = 5        # RB 786 via the PS 10 option (D12, PR4)
    legin_window: int = 3            # PS 1390
    pending_bars: int = 2            # PS 1546, 2097
    legout_track_bars: int = 3       # PS 1771
    legout_cap: int = 5              # PS 1771


@dataclass
class Zone:
    id: str
    side: str                 # "demand" or "supply"
    pattern: str              # DBR, RBR, RBD, DBD
    reversal: bool
    zero_base: bool
    start_index: int
    created_index: int
    start_time: object
    created_time: object
    proximal: float
    distal: float             # the invalidation line (exceptional when it applies), PS 1473-1490
    normal_distal: float      # cluster wick extreme (RB 2118); equal to distal unless exceptional
    exceptional: bool
    base_count: int           # base candles only, as Pine counts (PS 1426-1427)
    transition_count: int
    legin_index: Optional[int]
    legin_high: Optional[float]
    legin_low: Optional[float]
    legout_index: int         # the first leg-out candle
    from_pending: bool
    has_gap: bool
    gap_size: float           # > 0 is a gap; the engine never judges "meaningful"
    strong_closing: bool      # leg-out close beyond the leg-in extreme (RB 451; PS 1515)
    legout_count: int = 1
    legout_count_consecutive: int = 1
    legout_increment_indices: List[int] = field(default_factory=list)
    test_count: int = 0
    test_indices: List[int] = field(default_factory=list)
    dl_touch_index: Optional[int] = None
    invalidated_index: Optional[int] = None
    pending_window_touch_indices: List[int] = field(default_factory=list)
    pending_first_legout_explosive: bool = False   # body > 50% on the failed first leg-out
    base_ranges: List[float] = field(default_factory=list)
    legin_range: Optional[float] = None
    legout_ranges: List[float] = field(default_factory=list)
    _consecutive_open: bool = True

    @property
    def is_demand(self):
        return self.side == "demand"

    @property
    def active(self):
        return self.invalidated_index is None

    @property
    def fresh(self):
        return self.test_count == 0

    @property
    def base_count_incl_transitions(self):
        return self.base_count + self.transition_count


@dataclass
class CoreScore:
    freshness: float
    strength: float
    base: float
    core: float
    core_max: float = 7.0
    base_basis: str = "RB 785-787"


@dataclass
class ScoreReading:
    name: str        # which reading of an ambiguous rule produced this core
    core: float
    source: str


@dataclass
class Assessment:
    zone: Zone
    score: CoreScore
    status: str
    reasons: List[str]
    manual_review: List[str]      # flags that put the zone in MANUAL_REVIEW
    manual_checks: List[str]      # human checks that never automate (D8)
    tags: List[str]
    readings: List[ScoreReading]
    evidence: Dict[str, object]


@dataclass
class EngineResult:
    engine_version: str
    timeframe: str
    variant: str
    as_of_time: object
    candles_received: int
    candles_processed: int
    ignored_incomplete: List[object]
    insufficient_history: bool
    reasons: List[str]
    assessments: List[Assessment]          # every zone: the audit view
    events: List[Dict[str, object]]
    pine_only_zones: List[Dict[str, object]]
    rejected_patterns: List[Dict[str, object]]

    @property
    def eligible(self):
        """Fresh, valid demand zones that pass every zone-level check, as of the close of
        the last processed candle. Not a candidate list on its own (audit M4): the engine
        sees no touch inside a candle still forming (a W/M zone touched on Tuesday stays
        here until the week closes) and has no data-gap or session checks. Candidates
        come from nse/mtf-freshness MtfSnapshot.eligible_after_overlay."""
        return [a for a in self.assessments if a.status == ELIGIBLE]

    @property
    def manual_review_zones(self):
        return [a for a in self.assessments if a.status == MANUAL_REVIEW]

    @property
    def context_supply(self):
        """Fresh, valid supply zones: resistance and target evidence only (D2)."""
        return [a for a in self.assessments
                if a.status == CONTEXT_ONLY and a.zone.active and a.zone.fresh]

    @property
    def fresh_zones(self):
        """Zone results for display: never a tested or invalidated zone (D3)."""
        return [a for a in self.assessments if a.zone.active and a.zone.fresh]

    def to_dict(self):
        out = asdict(self)
        for a in out["assessments"]:
            a["zone"].pop("_consecutive_open", None)
        # audit L4: the derived lists (zone ids) belong to a complete serialised result
        out["derived"] = {name: [a.zone.id for a in getattr(self, name)]
                          for name in ("eligible", "manual_review_zones", "context_supply", "fresh_zones")}
        return out


# --- candle helpers -------------------------------------------------------------

def body_ratio(c):
    rng = c.high - c.low
    return abs(c.close - c.open) / rng if rng > 0 else 0.0


def _validate(candles):
    prev = None
    for i, c in enumerate(candles):
        for v in (c.open, c.high, c.low, c.close):
            if not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v):
                raise ValueError("candle %d has a non-numeric price" % i)
        if c.low > min(c.open, c.close) or c.high < max(c.open, c.close) or c.high < c.low:
            raise ValueError("candle %d has inconsistent OHLC" % i)
        if prev is not None and not c.time > prev:
            raise ValueError("candle times must strictly increase (index %d)" % i)
        prev = c.time


def _completed(candles):
    """Split into completed candles and ignored trailing incomplete ones."""
    n = len(candles)
    k = n
    while k > 0 and not candles[k - 1].complete:
        k -= 1
    for i in range(k):
        if not candles[i].complete:
            raise ValueError("incomplete candle at index %d is followed by completed candles" % i)
    return list(candles[:k]), [c.time for c in candles[k:]]


# --- detection ------------------------------------------------------------------

class _Pending(object):
    pass


class _Detector(object):
    """One pass over completed candles. profile is "rulebook" or "pine"."""

    def __init__(self, candles, rules, variant, profile):
        self.c = candles
        self.r = rules
        self.variant = variant
        self.pine = profile == "pine"
        self.zones = []           # creation order, invalidated zones included
        self.events = []
        self.rejected = []
        self.last_strong = None   # (index, dir, high, low)
        self.in_cluster = False
        self.cl = None
        self.pending = None
        self.pending_left = 0
        self.ratios = [body_ratio(x) for x in candles]

    # candle classes
    def bull(self, i):
        return self.c[i].close > self.c[i].open

    def bear(self, i):
        return self.c[i].close < self.c[i].open

    def is_base(self, i):
        return self.ratios[i] <= self.r.base_body_ratio

    def strong_bull(self, i):
        if not self.bull(i):
            return False
        if self.ratios[i] > self.r.strong_body_ratio:
            return True
        return self.pine and i > 0 and self.c[i].close > self.c[i - 1].high   # PS 332

    def strong_bear(self, i):
        if not self.bear(i):
            return False
        if self.ratios[i] > self.r.strong_body_ratio:
            return True
        return self.pine and i > 0 and self.c[i].close < self.c[i - 1].low    # PS 333

    def event(self, kind, i, **kw):
        e = {"event": kind, "index": i, "time": self.c[i].time}
        e.update(kw)
        self.events.append(e)

    # main loop
    def run(self):
        for i in range(len(self.c)):
            if self.strong_bull(i) or self.strong_bear(i):
                c = self.c[i]
                self.last_strong = (i, "bull" if self.strong_bull(i) else "bear", c.high, c.low)
            if self.variant == "chart":
                self.cluster_step(i)       # PS 1386-1583
                self.pending_step(i)       # PS 1584-1715 (same bar)
            else:
                self.pending_step(i)       # PS 1799-1930
                if self.pending_left == 0:
                    self.cluster_step(i)   # PS 1932-2133
            self.zero_base_step(i)         # PS 1717-1762 / 2135-2176
            self.legout_step(i)            # PS 1764-1775 / 2178-2189
            self.state_step(i)             # PS 2605-2656
        return self

    def cluster_step(self, i):
        c = self.c[i]
        r = self.ratios[i]
        if not self.in_cluster:
            if self.is_base(i) and self.last_strong is not None \
                    and i - self.last_strong[0] <= self.r.legin_window:
                li, ldir, lh, ll = self.last_strong
                self.in_cluster = True
                self.cl = {
                    "start": i, "count": 1, "transitions": 0,
                    "wh": c.high, "wl": c.low,
                    "bh": max(c.open, c.close), "bl": min(c.open, c.close),
                    "legin": (li, ldir, lh, ll),
                    "base_ranges": [c.high - c.low],
                }
            return
        cl = self.cl
        inside = c.high <= cl["wh"] and c.low >= cl["wl"]
        transition = inside and r <= self.r.base_body_ratio * self.r.transition_factor
        breaks = c.close > cl["wh"] or c.close < cl["wl"]
        can_continue = (self.is_base(i) and not breaks) or transition
        if can_continue and cl["count"] < self.r.max_base_candles:
            cl["wh"] = max(cl["wh"], c.high)
            cl["wl"] = min(cl["wl"], c.low)
            cl["bh"] = max(cl["bh"], max(c.open, c.close))
            cl["bl"] = min(cl["bl"], min(c.open, c.close))
            if self.is_base(i):
                cl["count"] += 1
                cl["base_ranges"].append(c.high - c.low)
            else:
                cl["transitions"] += 1
            return
        if can_continue and self.is_base(i):
            self.event(EV_GARBAGE_AREA, i, cluster_start=cl["start"], base_count=cl["count"] + 1)
            self.rejected.append({"reason": EV_GARBAGE_AREA, "cluster_start": cl["start"],
                                  "index": i, "source": "RB 787, 800-806"})
        elif self.is_base(i) and breaks and cl["count"] >= self.r.max_base_candles:
            self.event(EV_BASE_CLOSED_OUTSIDE, i, cluster_start=cl["start"], base_count=cl["count"])
            self.rejected.append({
                "reason": EV_BASE_CLOSED_OUTSIDE, "disposition": MANUAL_REVIEW,
                "cluster_start": cl["start"], "index": i, "base_count": cl["count"],
                "cluster_high": cl["wh"], "cluster_low": cl["wl"], "close": c.close,
                "note": "6th base (RB 787) or not overlapping (RB 802)? Unresolved (audit M3)",
                "source": "RB 787, 800-806, 814",
            })
        self.legout_eval(i)
        self.in_cluster = False
        self.cl = None

    def legout_eval(self, i):
        c = self.c[i]
        cl = self.cl
        li, ldir, lh, ll = cl["legin"]
        combined_high = max(lh, cl["wh"])
        combined_low = min(ll, cl["wl"])
        bull = self.bull(i) and (self.ratios[i] > self.r.strong_body_ratio
                                 or (self.pine and c.close > cl["wh"]))   # PS 1436
        bear = self.bear(i) and (self.ratios[i] > self.r.strong_body_ratio
                                 or (self.pine and c.close < cl["wl"]))   # PS 1437
        if bull:
            demand = True
        elif bear:
            demand = False
        else:
            return
        reversal = (ldir == "bear") == demand
        achieved = c.close > combined_high if demand else c.close < combined_low
        if achieved:
            gap = (c.low - cl["wh"]) if demand else (cl["wl"] - c.high)
            self.create(i, demand, reversal, cl, legout_index=i, lo_high=c.high, lo_low=c.low,
                        gap=gap, from_pending=False, legout_ranges=[c.high - c.low])
            return
        if self.pending_left > 0:
            self.event(EV_PENDING_REPLACED, i, cluster_start=self.pending.cl["start"])
        p = _Pending()
        p.cl = cl
        p.demand = demand
        p.reversal = reversal
        p.combined_high = combined_high
        p.combined_low = combined_low
        p.legout_index = i
        p.lo_high = c.high
        p.lo_low = c.low
        p.window = []
        p.legout_ranges = [c.high - c.low]
        self.pending = p
        self.pending_left = self.r.pending_bars
        self.event(EV_PENDING_SET, i, cluster_start=cl["start"], side="demand" if demand else "supply")

    def pending_step(self, i):
        if self.pending_left <= 0:
            return
        p = self.pending
        c = self.c[i]
        if p.demand:
            cont = self.bull(i) and (self.ratios[i] > self.r.strong_body_ratio
                                     or (self.pine and c.close > p.cl["wh"]))   # PS 1587
            achieved = cont and c.close > p.combined_high
        else:
            cont = self.bear(i) and (self.ratios[i] > self.r.strong_body_ratio
                                     or (self.pine and c.close < p.cl["wl"]))   # PS 1590
            achieved = cont and c.close < p.combined_low
        if achieved:
            gap = (p.lo_low - p.cl["wh"]) if p.demand else (p.cl["wl"] - p.lo_high)  # PS 1651-1653
            z = self.create(i, p.demand, p.reversal, p.cl, legout_index=p.legout_index,
                            lo_high=max(c.high, p.lo_high), lo_low=min(c.low, p.lo_low),
                            gap=gap, from_pending=True,
                            legout_ranges=p.legout_ranges + [c.high - c.low])
            z.pending_first_legout_explosive = self.ratios[p.legout_index] > self.r.strong_body_ratio
            for j in p.window + [i]:
                cj = self.c[j]
                touched = cj.low <= z.proximal if z.is_demand else cj.high >= z.proximal
                if touched:
                    z.pending_window_touch_indices.append(j)
            self.pending_left = 0
            self.pending = None
            return
        p.lo_high = max(p.lo_high, c.high)
        p.lo_low = min(p.lo_low, c.low)
        if i != p.legout_index:
            p.window.append(i)
        self.pending_left -= 1
        if self.pending_left <= 0:
            self.event(EV_ACHIEVEMENT_NOT_MET, i, cluster_start=p.cl["start"],
                       side="demand" if p.demand else "supply")
            self.rejected.append({
                "reason": EV_ACHIEVEMENT_NOT_MET, "cluster_start": p.cl["start"],
                "legout_index": p.legout_index, "index": i,
                "side": "demand" if p.demand else "supply",
                "note": "not an execution zone; usable only as HTF context after manual review",
                "source": "PS 1434-1439, 1584-1715; RB 730, 739, 1639",
            })
            self.pending = None

    def zero_base_step(self, i):
        if i <= 2 or self.in_cluster:                     # PS 1721-1724
            return
        if self.variant == "htf" and self.pending_left != 0:   # PS 2139, 2158
            return
        c, p = self.c[i], self.c[i - 1]
        if self.strong_bear(i - 1) and self.strong_bull(i):
            prox = max(min(p.open, p.close), min(c.open, c.close))   # PS 1729
            dist = min(p.low, c.low)
            self.create_zero_base(i, True, prox, dist, gap=c.low - p.high,
                                  strong_closing=c.close > p.high)
        if self.strong_bull(i - 1) and self.strong_bear(i):
            prox = min(max(p.open, p.close), max(c.open, c.close))   # PS 1748
            dist = max(p.high, c.high)
            self.create_zero_base(i, False, prox, dist, gap=p.low - c.high,
                                  strong_closing=c.close < p.low)

    def _zone_id(self, side, start, created):
        return "%s-%s-%s" % (side, start, created)

    def create(self, i, demand, reversal, cl, legout_index, lo_high, lo_low, gap,
               from_pending, legout_ranges):
        li, ldir, lh, ll = cl["legin"]
        if demand:
            prox = cl["bh"]
            normal = cl["wl"]
            dist = min(ll, cl["wl"], lo_low) if reversal else min(cl["wl"], lo_low)  # PS 1475-1477
            exceptional = dist < cl["wl"]
            pattern = "DBR" if reversal else "RBR"
            strong_closing = self.c[i].close > lh
        else:
            prox = cl["bl"]
            normal = cl["wh"]
            dist = max(lh, cl["wh"], lo_high) if reversal else max(cl["wh"], lo_high)  # PS 1485-1487
            exceptional = dist > cl["wh"]
            pattern = "RBD" if reversal else "DBD"
            strong_closing = self.c[i].close < ll
        side = "demand" if demand else "supply"
        z = Zone(
            id=self._zone_id(side, cl["start"], i), side=side, pattern=pattern,
            reversal=reversal, zero_base=False,
            start_index=cl["start"], created_index=i,
            start_time=self.c[cl["start"]].time, created_time=self.c[i].time,
            proximal=prox, distal=dist, normal_distal=normal, exceptional=exceptional,
            base_count=cl["count"], transition_count=cl["transitions"],
            legin_index=li, legin_high=lh, legin_low=ll, legout_index=legout_index,
            from_pending=from_pending, has_gap=gap > 0, gap_size=gap,
            strong_closing=strong_closing, base_ranges=list(cl["base_ranges"]),
            legin_range=lh - ll, legout_ranges=legout_ranges,
        )
        self.zones.append(z)
        self.event(EV_ZONE_CREATED, i, zone=z.id, pattern=pattern, from_pending=from_pending)
        return z

    def create_zero_base(self, i, demand, prox, dist, gap, strong_closing):
        p = self.c[i - 1]
        c = self.c[i]
        side = "demand" if demand else "supply"
        z = Zone(
            id=self._zone_id(side, i - 1, i), side=side, pattern="DBR" if demand else "RBD",
            reversal=True, zero_base=True, start_index=i - 1, created_index=i,
            start_time=p.time, created_time=c.time,
            proximal=prox, distal=dist, normal_distal=dist, exceptional=False,  # PS 1736, 1755
            base_count=0, transition_count=0,
            legin_index=i - 1, legin_high=p.high, legin_low=p.low, legout_index=i,
            from_pending=False, has_gap=gap > 0, gap_size=gap,
            strong_closing=strong_closing,
            legin_range=p.high - p.low, legout_ranges=[c.high - c.low],
        )
        self.zones.append(z)
        self.event(EV_ZONE_CREATED, i, zone=z.id, pattern=z.pattern, zero_base=True)

    def legout_step(self, i):
        if self.pine:
            active = [z for z in self.zones if z.active]
            targets = active[-1:]             # PS 1766: the newest zone only
        else:
            targets = [z for z in self.zones if z.active]   # per zone (RB 728)
        for z in targets:
            since = i - z.created_index
            if since < 1 or since > self.r.legout_track_bars:
                continue
            ok = self.strong_bull(i) if z.is_demand else self.strong_bear(i)
            if ok and z.legout_count < self.r.legout_cap:
                z.legout_count += 1
                z.legout_increment_indices.append(i)
                self.event(EV_LEGOUT_INCREMENT, i, zone=z.id, legout_count=z.legout_count)
            if z._consecutive_open:
                if ok and z.legout_count_consecutive < self.r.legout_cap:
                    z.legout_count_consecutive += 1
                elif not ok:
                    z._consecutive_open = False

    def state_step(self, i):
        c = self.c[i]
        for z in self.zones:
            if not z.active:
                continue
            bottom, top = min(z.proximal, z.distal), max(z.proximal, z.distal)
            if (z.is_demand and c.close < bottom) or (not z.is_demand and c.close > top):
                z.invalidated_index = i                      # PS 2613: permanent
                self.event(EV_INVALIDATED, i, zone=z.id)
                continue
            if i > z.created_index:
                tested = c.low <= z.proximal if z.is_demand else c.high >= z.proximal
                if tested:
                    z.test_count += 1
                    z.test_indices.append(i)
                    self.event(EV_TESTED, i, zone=z.id, test_count=z.test_count)
                dl = c.low <= z.distal if z.is_demand else c.high >= z.distal
                if dl and z.dl_touch_index is None:
                    z.dl_touch_index = i
                    self.event(EV_DL_TOUCHED, i, zone=z.id)


# --- scoring (separate from detection and from eligibility) ----------------------

def freshness_points(test_count):
    return 3.0 if test_count == 0 else (1.5 if test_count == 1 else 0.0)   # RB 675-677; PS 595


def strength_points(legout_count, has_gap):
    if legout_count >= 2 or (legout_count >= 1 and has_gap):                # RB 728-730; PS 596-600
        return 2.0
    return 1.0 if legout_count >= 1 else 0.0


def base_points(base_count):
    """Returns (points, basis). Zero bases: Pine's value, not defined by the rulebook (D13)."""
    if base_count == 0:
        return 2.0, TAG_ZB                                                   # PS 601
    if base_count <= 3:
        return 2.0, "RB 785"
    if base_count <= 5:
        return 1.0, "RB 786"
    return 0.0, "RB 787"


def core_score(test_count, legout_count, has_gap, base_count):
    f = freshness_points(test_count)
    s = strength_points(legout_count, has_gap)
    b, basis = base_points(base_count)
    return CoreScore(freshness=f, strength=s, base=b, core=f + s + b, base_basis=basis)


# --- eligibility (separate from scoring) -----------------------------------------

def _match_key(z):
    return (z.side, z.start_index, z.created_index, z.pattern)


def _assess(z, pine_zone, timeframe, rules):
    primary = core_score(z.test_count, z.legout_count, z.has_gap, z.base_count)
    readings = [ScoreReading("primary (rulebook-strict)", primary.core, "D12")]
    flags = []

    def alt(name, flag, source, legout_count=None, has_gap=None, base_count=None):
        s = core_score(z.test_count,
                       z.legout_count if legout_count is None else legout_count,
                       z.has_gap if has_gap is None else has_gap,
                       z.base_count if base_count is None else base_count)
        readings.append(ScoreReading(name, s.core, source))
        if s.core != primary.core:
            flags.append(flag)

    if z.transition_count:
        alt("base count incl. transition candles", BASE_COUNT_TRANSITION_AMBIGUITY,
            "RB 404, 739, 769 vs PS 1426", base_count=z.base_count_incl_transitions)
    if z.legout_count_consecutive != z.legout_count:
        alt("consecutive leg-out candles only", LEGOUT_SEQUENCE_INTERRUPTED,
            "RB 728", legout_count=z.legout_count_consecutive)
    if z.has_gap:
        alt("gap not meaningful", GAP_MEANINGFULNESS_UNVERIFIED,
            "RB 941, 2974", has_gap=False)
    if z.from_pending and z.pending_first_legout_explosive:
        alt("first leg-out of a pending zone also counted", PENDING_LEGOUT_COUNT_AMBIGUOUS,
            "RB 728, 739 vs PS 688",
            legout_count=min(z.legout_count + 1, rules.legout_cap))
    if pine_zone is None:
        flags.append(PINE_NO_MATCHING_ZONE)
    else:
        ps = core_score(pine_zone.test_count, pine_zone.legout_count, pine_zone.has_gap,
                        pine_zone.base_count)
        readings.append(ScoreReading("Pine profile", ps.core, "PS 332-333, 1764-1775"))
        if ps.core != primary.core:
            flags.append(PINE_SCORE_DIFFERS)
        if (pine_zone.proximal, pine_zone.distal) != (z.proximal, z.distal):
            flags.append(PINE_GEOMETRY_DIFFERS)
    if z.pending_window_touch_indices:
        flags.append(PENDING_WINDOW_PL_TOUCH)

    tags = []
    if z.zero_base:
        tags.append(TAG_ZB)
    if timeframe in NO_PINE_ZONE_ENGINE:
        tags.append(TAG_NO_PINE_REFERENCE)
        flags = [f for f in flags if f not in (PINE_NO_MATCHING_ZONE, PINE_SCORE_DIFFERS,
                                               PINE_GEOMETRY_DIFFERS)]

    evidence = {
        "legout_ranges": z.legout_ranges,
        "base_ranges": z.base_ranges,
        "legin_range": z.legin_range,
        "gap_size": z.gap_size,
        "base_count": z.base_count,
        "base_count_incl_transitions": z.base_count_incl_transitions,
        "legout_count": z.legout_count,
        "legout_count_consecutive": z.legout_count_consecutive,
        "legout_count_pine": None if pine_zone is None else pine_zone.legout_count,
        "test_indices": z.test_indices,
        "dl_touch_index": z.dl_touch_index,
        "pending_window_touch_indices": z.pending_window_touch_indices,
        "pending_first_legout_explosive": z.pending_first_legout_explosive,
    }

    reasons = []
    manual_checks = []
    if not z.is_demand:
        status = CONTEXT_ONLY
        reasons.append(SUPPLY_CONTEXT_ONLY)
        if not z.active:
            reasons.append(ZONE_INVALIDATED)
        elif not z.fresh:
            reasons.append(ZONE_TESTED)
    elif not z.active:
        status = INELIGIBLE
        reasons.append(ZONE_INVALIDATED)
    elif not z.fresh:
        status = INELIGIBLE
        reasons.append(ZONE_TESTED)
    else:
        any_seven = any(r.core == 7.0 for r in readings)
        if primary.core == 7.0 and not flags:
            status = ELIGIBLE
        elif any_seven and flags:    # some reading reaches 7/7 and the sources disagree
            status = MANUAL_REVIEW
        else:
            status = INELIGIBLE
            reasons.append(CORE_BELOW_7)
        if status in (ELIGIBLE, MANUAL_REVIEW):
            manual_checks.append(LEGOUT_RELATIVE_SIZE_CONTEXT)
    manual_review = sorted(set(flags)) if status == MANUAL_REVIEW else []
    return Assessment(zone=z, score=primary, status=status, reasons=reasons,
                      manual_review=manual_review, manual_checks=manual_checks,
                      tags=tags, readings=readings, evidence=evidence)


# --- entry point ----------------------------------------------------------------

def run_engine(candles, timeframe, as_of=None, rules=None):
    """Detect, score and assess zones on one timeframe.

    candles   sequence of Candle, oldest first, one timeframe only. The engine has no
              clock (audit M2): time must be the candle's CLOSE time, so as_of drops a
              candle that has not closed yet, and complete must be False for any candle
              still forming. A vendor bar stamped with its OPEN time and marked complete
              would be used early. The orchestrator builds candles that satisfy this.
    timeframe one of Y, HY, Q, M, W, D, 125m, 75m (60m/120m are refused, D16)
    as_of     optional time; candles after it are dropped before anything runs
    """
    if timeframe not in TIMEFRAME_VARIANT:
        raise ValueError("unsupported timeframe %r; allowed: %s"
                         % (timeframe, ", ".join(TIMEFRAME_VARIANT)))
    rules = rules or Rules()
    variant = TIMEFRAME_VARIANT[timeframe]
    candles = list(candles)
    if as_of is not None:
        candles = [c for c in candles if c.time <= as_of]
    _validate(candles)
    done, ignored = _completed(candles)
    received = len(candles)
    base = dict(engine_version=ENGINE_VERSION, timeframe=timeframe, variant=variant,
                as_of_time=done[-1].time if done else None, candles_received=received,
                candles_processed=len(done), ignored_incomplete=ignored)
    if len(done) < MIN_CANDLES:
        return EngineResult(insufficient_history=True, reasons=[INSUFFICIENT_HISTORY],
                            assessments=[], events=[], pine_only_zones=[],
                            rejected_patterns=[], **base)

    rb = _Detector(done, rules, variant, "rulebook").run()
    pine = _Detector(done, rules, variant, "pine").run()
    pine_by_key = {_match_key(z): z for z in pine.zones}
    rb_keys = set(_match_key(z) for z in rb.zones)

    assessments = [_assess(z, pine_by_key.get(_match_key(z)), timeframe, rules) for z in rb.zones]
    pine_only = []
    if timeframe not in NO_PINE_ZONE_ENGINE:
        for z in pine.zones:
            if _match_key(z) not in rb_keys:
                pine_only.append({
                    "reason": PINE_ONLY_ZONE, "side": z.side, "pattern": z.pattern,
                    "start_index": z.start_index, "created_index": z.created_index,
                    "proximal": z.proximal, "distal": z.distal, "zero_base": z.zero_base,
                    "note": "Pine would draw this zone; the rulebook-strict profile does not "
                            "(e.g. a candle strong only by closing beyond the prior extreme). "
                            "Never eligible; manual review.",
                    "source": "D12; PS 332-333, 1436-1437; RB 402",
                })
    return EngineResult(insufficient_history=False, reasons=[], assessments=assessments,
                        events=rb.events, pine_only_zones=pine_only,
                        rejected_patterns=rb.rejected, **base)
