"""Owner-approved execution policy for backtests (B9, B12; DECISION_LOG section 1F).

The owner fixed these execution assumptions:
  - manual Kite / GTT execution only: nothing here talks to a broker;
  - pending orders expire after 10 verified NSE sessions (D42);
  - same-bar stop/target ambiguity: STOP_FIRST is the baseline, EXCLUDE the sensitivity;
  - a bar opening through a level fills AT_OPEN (a gap proxy, not an observed price);
  - slippage of 0.05%, 0.10% and 0.20% per side, all three run;
  - transaction costs from a separate, dated, instrument-specific Zerodha schedule;
  - B9: the Rulebook's buffer ranges are kept; which entry and stop inside them is tested
    is a set of scenarios the user declares BEFORE the run. Nothing picks one.

What stays a user input, because no approved decision fixes it: the entry/stop scenarios,
the statuses that place an order, cancel_if_target_first, and the cost schedule itself (no
Zerodha figures exist in this repository, so none are built in).

owner_grid returns every combination in a fixed order and labels each one; it never ranks
or selects a model (backtest.run_sensitivity reports them side by side).
"""

import datetime
import json
from dataclasses import dataclass
from typing import Dict, Tuple

from nse.research import backtest as bt, models as m

SLIPPAGE_PCT_PER_SIDE = (0.05, 0.10, 0.20)          # B12, percent per side
SAME_BAR_BASELINE = "STOP_FIRST"                     # B12
SAME_BAR_SENSITIVITY = ("EXCLUDE",)                  # B12
GAP_FILL = "AT_OPEN"                                 # B12 gap proxy
SOURCE = "B12, B9, D42, D45 (owner-approved; DECISION_LOG 1F)"


class CostScheduleError(ValueError):
    pass


@dataclass(frozen=True)
class CostPeriod:
    effective_from: datetime.date      # inclusive
    effective_to: datetime.date        # inclusive
    source: str                        # the official schedule this was copied from
    rates: Dict[str, float]            # instrument type -> percent per side


@dataclass(frozen=True)
class CostSchedule:
    """Dated, instrument-specific percentage costs. Every lookup must name the instrument type
    and a date range wholly inside one period; anything else is refused, never defaulted."""
    broker: str
    periods: Tuple[CostPeriod, ...]

    def __post_init__(self):
        if not self.broker or not self.periods:
            raise CostScheduleError("a cost schedule needs a broker and at least one dated period")
        spans = sorted((p.effective_from, p.effective_to) for p in self.periods)
        for (a0, a1), (b0, _) in zip(spans, spans[1:]):
            if b0 <= a1:
                raise CostScheduleError("cost periods overlap: %s-%s and one from %s" % (a0, a1, b0))
        for p in self.periods:
            if p.effective_to < p.effective_from:
                raise CostScheduleError("period %s-%s ends before it starts" % (p.effective_from, p.effective_to))
            if not p.source:
                raise CostScheduleError("period %s-%s has no source" % (p.effective_from, p.effective_to))
            for k, v in p.rates.items():
                if isinstance(v, bool) or not isinstance(v, (int, float)) or not 0 <= v < 100:
                    raise CostScheduleError("rate %s=%r is not a percentage" % (k, v))

    def rate_for(self, instrument_type, start, end):
        """(percent per side, period) for instrument_type over [start, end] (dates)."""
        for p in self.periods:
            if p.effective_from <= start and end <= p.effective_to:
                if instrument_type not in p.rates:
                    raise CostScheduleError("no %s rate in the %s-%s schedule (%s)"
                                            % (instrument_type, p.effective_from, p.effective_to, p.source))
                return float(p.rates[instrument_type]), p
        raise CostScheduleError("no single cost period covers %s to %s: split the window at the schedule change"
                                % (start, end))


def load_cost_schedule(path):
    """JSON: {"broker": "ZERODHA", "periods": [{"effective_from": "YYYY-MM-DD",
    "effective_to": "YYYY-MM-DD", "source": "...", "rates": {"EQ_DELIVERY": 0.1}}]}."""
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    try:
        periods = tuple(CostPeriod(datetime.date.fromisoformat(p["effective_from"]),
                                   datetime.date.fromisoformat(p["effective_to"]), p["source"], dict(p["rates"]))
                        for p in raw["periods"])
        return CostSchedule(raw["broker"], periods)
    except (KeyError, TypeError, ValueError) as e:
        if isinstance(e, CostScheduleError):
            raise
        raise CostScheduleError("%s: malformed cost schedule (%s)" % (path, e))


def owner_grid(entry_stop_scenarios, statuses, cancel_if_target_first, cost_schedule, instrument_type,
               start, end):
    """[(label, ExecutionModel)] for every predeclared (entry, stop) scenario x slippage x
    same-bar policy, in that fixed order. Every model has the owner limits (10 positions,
    10 trades per IST month, 10-session expiry) and the AT_OPEN gap proxy.
    start / end must span the whole backtest, from the first signal to the last date a fill
    or exit could fall on: the cost period is checked against them only, and they are
    recorded in the result as cost_window so the check can be audited."""
    if not entry_stop_scenarios:
        raise ValueError("declare at least one (entry, stop) scenario before the run (B9)")
    if len(set(entry_stop_scenarios)) != len(entry_stop_scenarios):
        raise ValueError("entry/stop scenarios repeat")
    cost, period = cost_schedule.rate_for(instrument_type, start, end)
    out = []
    for entry, stop in entry_stop_scenarios:
        for slip in SLIPPAGE_PCT_PER_SIDE:
            for same_bar in (SAME_BAR_BASELINE,) + SAME_BAR_SENSITIVITY:
                model = bt.ExecutionModel(
                    entry=entry, stop=stop, target="STRUCTURAL", statuses=tuple(statuses),
                    entry_expiry_sessions=m.OWNER_ENTRY_EXPIRY_SESSIONS,
                    cancel_if_target_first=cancel_if_target_first, gap_fill=GAP_FILL, same_bar=same_bar,
                    cost_pct_per_side=cost, slippage_pct_per_side=slip,
                    monthly_trade_cap=m.OWNER_MONTHLY_TRADE_CAP, max_open_positions=m.OWNER_MAX_OPEN_POSITIONS)
                label = "%s/%s/slip%.2f/%s" % (entry, stop, slip, same_bar)
                out.append((label, model))
    return out, {"cost_source": period.source, "cost_period": [period.effective_from.isoformat(),
                                                             period.effective_to.isoformat()],
                 "cost_window": [start.isoformat(), end.isoformat()],
                 "broker": cost_schedule.broker, "instrument_type": instrument_type, "policy_source": SOURCE,
                 "baseline_same_bar": SAME_BAR_BASELINE, "flat_charges_modelled": False}
