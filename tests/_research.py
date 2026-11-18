"""Test helpers for nse/research. Everything here is SYNTHETIC (not market data).

SnapBuilder assembles a real mtf_freshness.MtfSnapshot from the real dataclasses
(Zone, Assessment, EngineResult, HtfSeries, ZoneTouchState) with exact zone geometry and
overlay states, so each gate can be driven precisely. It is a unit-test fixture: it does
not run the replay, so results built on it are not integration evidence.

ideal_mit() is the reference scenario: every automated gate passes, so the status is
ACTIONABLE CANDIDATE: MANUAL CHECKS PENDING. Each test changes one thing.
  D  execution demand zone PL 890, DL 870 (normal 875), created on the 51st daily candle
  M  tested demand 850-900 (DL untouched: the coinciding zone), fresh demand 650-700
     (curve bottom), fresh supply 1500-1550 (curve top); price 950 -> LOC
  W  closes rise 1% a week for 60 weeks (12 o'clock, Strong Up); fresh supply 1200-1230
     is the target (R:R about 9 in the worst buffer case)
  Q, HY, Y available, no zones
"""

import datetime
import sys

from _load import ROOT

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from nse.research import models, qualification            # noqa: E402
from nse.research.deps import mtf, ze                      # noqa: E402

DT = datetime.datetime
AS_OF = DT(2025, 6, 30, 15, 30)


def rising(n, start=500.0, step=0.01):
    return [start * (1 + step) ** i for i in range(n)]


class SnapBuilder(object):
    def __init__(self, as_of=AS_OF):
        self.as_of = as_of
        self.series = {}
        self.zones = {}           # tf -> list of (assessment, state)
        self.calendar_validated = True
        self.unresolved = []
        self.limitations = []

    def add_series(self, tf, closes, truncated_at=None, insufficient=False):
        n = len(closes)
        cs = []
        for i, c in enumerate(closes):
            end = self.as_of - datetime.timedelta(days=(n - i))
            cs.append(mtf.HtfCandle(tf, "%s-%04d" % (tf, i), end - datetime.timedelta(hours=6), end, end,
                                    c, c * 1.01, c * 0.99, c, 1, 1, False))
        eng = None
        if n:
            eng = ze.EngineResult(ze.ENGINE_VERSION, tf, ze.TIMEFRAME_VARIANT.get(tf, "htf"), cs[-1].end, n, n, [],
                                  insufficient or n < ze.MIN_CANDLES, [], [], [], [], [])
        self.series[tf] = mtf.HtfSeries(tf, cs, eng, None, truncated_at, [] if truncated_at is None else
                                        [mtf.HTF_SERIES_TRUNCATED_AT_GAP])
        return self

    def add_zone(self, tf, side, pl, dl, status=mtf.FRESH, engine_status=None, normal_dl=None, created_index=None,
                 dl_touched=False, strong_closing=True, zero_base=False, engine_manual=(), core=7.0,
                 overlay_manual=(), engine_test_count=0, invalidated=False, zid=None):
        s = self.series[tf]
        n = len(s.candles)
        ci = n - 10 if created_index is None else created_index
        zid = zid or "%s-%d-%d-%s" % (side, ci - 1, ci, str(pl).replace(".", "_"))
        z = ze.Zone(id=zid, side=side, pattern="DBR" if side == "demand" else "RBD", reversal=True,
                    zero_base=zero_base, start_index=ci - 1, created_index=ci, start_time=s.candles[ci - 1].end,
                    created_time=s.candles[ci].end, proximal=pl, distal=dl,
                    normal_distal=dl if normal_dl is None else normal_dl, exceptional=normal_dl not in (None, dl),
                    base_count=0 if zero_base else 1, transition_count=0, legin_index=ci - 2, legin_high=pl * 1.02,
                    legin_low=dl, legout_index=ci, from_pending=False, has_gap=False, gap_size=0.0,
                    strong_closing=strong_closing, test_count=engine_test_count,
                    invalidated_index=(n - 1) if invalidated else None)
        if engine_status is None:
            engine_status = ze.ELIGIBLE if side == "demand" else ze.CONTEXT_ONLY
        score = ze.CoreScore(3.0 if engine_test_count == 0 else 1.5, 2.0, core - 5.0, core)
        a = ze.Assessment(z, score, engine_status, [], list(engine_manual) if engine_status == ze.MANUAL_REVIEW else [],
                          [ze.LEGOUT_RELATIVE_SIZE_CONTEXT] if side == "demand" else [],
                          [ze.TAG_ZB] if zero_base else [], [ze.ScoreReading("primary (rulebook-strict)", core, "D12")],
                          {"legout_count_pine": 1})
        st = mtf.ZoneTouchState(key="%s:%s" % (tf, zid), tf=tf, zone_id=zid, side=side, pattern=z.pattern,
                                proximal=pl, distal=dl, creation_period_end=z.created_time, known_at=z.created_time,
                                engine_status=engine_status, status=status,
                                manual_review=list(overlay_manual))
        if status in (mtf.TESTED,):
            st.base_touch_count = 1
            st.first_touch_at = self.as_of
        if status == mtf.INVALIDATED:
            st.invalidated_period_end = self.as_of
        if dl_touched:
            st.dl_touched_at = self.as_of
        s.engine.assessments.append(a)
        self.zones[st.key] = st
        return self

    def build(self):
        return mtf.MtfSnapshot(mtf.ENGINE_VERSION, self.as_of, "D", self.calendar_validated, list(self.limitations),
                               1000, [], [], [], list(self.unresolved), self.series, self.zones)


def ideal_mit_builder():
    b = SnapBuilder()
    b.add_series("D", [940.0] * 60)
    b.add_zone("D", "demand", 890.0, 870.0, normal_dl=875.0, created_index=50)
    b.add_series("W", rising(60))
    b.add_zone("W", "supply", 1200.0, 1230.0)
    b.add_series("M", [800.0 + i for i in range(60)])
    b.add_zone("M", "demand", 900.0, 850.0, status=mtf.TESTED, zid="m-coinciding")
    b.add_zone("M", "demand", 700.0, 650.0, zid="m-bottom")
    b.add_zone("M", "supply", 1500.0, 1550.0, zid="m-top")
    for tf in ("Q", "HY", "Y"):
        b.add_series(tf, [800.0, 820.0, 840.0, 860.0])
    return b


def verified_ca(*symbols):
    """A hash-verified collection window wide enough for the synthetic fixtures.

    This is not market evidence. It is the covered case of P01-H1: an empty event list
    counts only inside a window the caller states was checked. Pass coverage=None for
    the unknown-file case.
    """
    span = (datetime.date(1990, 1, 1), datetime.date(2100, 1, 1))
    return {s: [span] for s in (symbols or ("SYN",))}


def evaluate(builder, trade_type=models.MIT, price=950.0, risk=1000.0, data_errors=(), coverage="VERIFIED"):
    if coverage == "VERIFIED":
        coverage = verified_ca("SYN")
    ctx = qualification.SymbolContext("SYN", trade_type, builder.build(), price,
                                      risk_per_trade=risk, data_errors=list(data_errors),
                                      corporate_action_coverage=coverage)
    return qualification.evaluate_symbol(ctx)


def only(result):
    assert len(result["candidates"]) == 1, [c.zone["zone_id"] for c in result["candidates"]]
    return result["candidates"][0]


# --- synthetic daily candles for the REAL replay (integration tests) -----------------------

class WeekdayCalendar(object):
    """Test fixture: every weekday trades. Not an NSE calendar."""
    def __init__(self, closed=()):
        self.closed = set(closed)

    def is_trading_day(self, d):
        return d.weekday() < 5 and d not in self.closed


def weekdays(start, n):
    out, d = [], start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += datetime.timedelta(days=1)
    return out


def candle(d, o, h, l, c):
    return mtf.TimedCandle(DT.combine(d, mtf.SESSION_OPEN), DT.combine(d, mtf.SESSION_CLOSE), o, h, l, c)


CALM_LOW = (100.0, 100.5, 99.5, 100.0)
DBR = [(100.0, 101.0, 99.0, 100.0), (100.0, 100.5, 94.0, 95.0), (95.0, 96.0, 94.5, 95.2),
       (95.5, 102.0, 95.3, 101.5), (101.5, 105.0, 101.0, 104.5)]
CALM_HIGH = (104.0, 104.5, 103.5, 104.0)
DBR_PL = 95.2


def dbr_days(before=40, after=15, start=datetime.date(2025, 1, 6)):
    """Calm doji days, then the DBR (PL 95.2, DL 94.0), then calm days above it."""
    days = weekdays(start, before + len(DBR) + after)
    rows = [CALM_LOW] * before + DBR + [CALM_HIGH] * after
    return days, rows


def dbr_candles(touch_on=None, skip=(), **kw):
    days, rows = dbr_days(**kw)
    out = []
    for i, (d, r) in enumerate(zip(days, rows)):
        if i in skip:
            continue
        if touch_on is not None and i == touch_on:
            r = (104.0, 104.2, 95.0, 103.0)          # low 95.0 <= PL 95.2: a test (RB 683-697)
        out.append(candle(d, *r))
    return days, out


def random_walk(seed, n, start=datetime.date(2023, 1, 2), price=500.0):
    import random
    rnd = random.Random(seed)
    out = []
    for d in weekdays(start, n):
        o = price
        c = max(1.0, o * (1 + rnd.gauss(0.0005, 0.02)))
        h = max(o, c) * (1 + abs(rnd.gauss(0, 0.006)))
        l = min(o, c) * (1 - abs(rnd.gauss(0, 0.006)))
        out.append(candle(d, round(o, 2), round(h, 2), round(l, 2), round(c, 2)))
        price = c
    return out


def daily_input(symbol, candles):
    from nse.research import marketdata
    return marketdata.DailyInput(symbol, list(candles), {"source": "SYNTHETIC_TEST_FIXTURE"}, [], [])


# --- a long SYNTHETIC history that reaches ACTIONABLE through the REAL replay -------------
# Five years of weekday doji candles (open = close, so no daily zone forms except the one
# placed on purpose) following waypoints that make the Zone Engine itself produce:
#   M  RBD supply ~384-405 (T1-T3, 2020): the curve top
#   M  DBR demand ~96.5-90.4 (B1-B3, 2021): the curve bottom, fresh
#   M  RBR demand ~161-150.5 (R1-R3, Oct-Dec 2023): tested by the January dip, DL untouched,
#      so it is the coinciding zone (D15)
#   W  RBD supply ~188.6 (start of January 2024): the target
#   D  the DBR of dbr_candles scaled by k, inside the M RBR zone
# Q, HY and Y supply zones sit far above. Nothing about these prices is market data.
LONG_WAYPOINTS = [
    (datetime.date(2019, 4, 1), 200, .012), (datetime.date(2020, 7, 1), 330, .012),
    (datetime.date(2020, 8, 1), 385, .012),
    (datetime.date(2020, 8, 14), 400, .012), (datetime.date(2020, 9, 1), 383, .012),
    (datetime.date(2020, 10, 1), 310, .012),
    (datetime.date(2021, 10, 1), 115, .012),
    (datetime.date(2021, 11, 1), 95, .012),
    (datetime.date(2021, 11, 15), 91.5, .012), (datetime.date(2021, 12, 1), 97, .012),
    (datetime.date(2022, 1, 1), 125, .003),
    (datetime.date(2023, 10, 1), 155, .003),
    (datetime.date(2023, 11, 1), 160, .003),
    (datetime.date(2023, 11, 15), 151, .003), (datetime.date(2023, 12, 1), 162, .003),
    (datetime.date(2024, 1, 1), 190, .003),
    (datetime.date(2024, 1, 11), 168, .003),
]
LONG_K = 1.68                    # D zone: PL 159.94, DL 157.92
LONG_PL, LONG_DL = 159.94, 157.92


def long_mit_candles(k=LONG_K, start=None, tail_step=1.002, tail_wick=.003, tail_days=12):
    out = []
    for (d0, p0, w), (d1, p1, _) in zip(LONG_WAYPOINTS, LONG_WAYPOINTS[1:]):
        days = [d for d in (d0 + datetime.timedelta(i) for i in range((d1 - d0).days)) if d.weekday() < 5]
        for i, d in enumerate(days):
            p = round(p0 * (p1 / p0) ** (i / len(days)), 2)
            if start is None or d >= start:
                out.append(candle(d, p, round(p * (1 + w), 2), round(p * (1 - w), 2), p))
    days = weekdays(out[-1].start.date() + datetime.timedelta(1), 5 + tail_days)
    for d, r in zip(days, DBR):
        out.append(candle(d, *[round(x * k, 2) for x in r]))
    p = DBR[-1][3] * k
    for d in days[5:]:
        p = round(p * tail_step, 2)
        out.append(candle(d, p, round(p * (1 + tail_wick), 2), round(p * (1 - tail_wick), 2), p))
    return out


def extend(candles, rows):
    """Append rows (o, h, l, c) on the following weekdays."""
    days = weekdays(candles[-1].start.date() + datetime.timedelta(1), len(rows))
    return list(candles) + [candle(d, *r) for d, r in zip(days, rows)]
