"""SMA-50 clock trend reading (spec 7.3; D14, D21, D22).

Method: SMA-50 clock on completed candles of one timeframe (RB 1672-1711, 1748). The
rulebook gives no numeric angle, so Pine's clock is the numeric reference (D14, rulebook
silent, no conflict): pct = (SMA50 - SMA50[5]) / SMA50 * 100 with thresholds
+-0.1 / 0.4 / 1.0 / 2.0 (PS 252-291), strict ">" as Pine writes it.

Each Pine position maps to the SET of rulebook readings it can mean (D14 table). A set
with more than one reading is an ambiguity; the alignment matrix decides whether it
changes the outcome (spec 7.3: manual only where it matters).

Fewer than 55 completed candles (SMA50 now and 5 candles earlier, D23) is
INSUFFICIENT_HISTORY, never "sideways". A series that a data gap or an unresolved
calendar date has ended is TRUNCATED: its last candle is not the latest one.
"""

from nse.research import structure

PERIOD = 50
LOOKBACK = 5                       # PS 205 default i_clock_lookback
MIN_CANDLES = PERIOD + LOOKBACK

STRONG_UP = "STRONG_UP"
MODERATE_UP = "MODERATE_UP"
MILD_UP = "MILD_UP"
SIDEWAYS = "SIDEWAYS"
DOWN = "DOWN"
UPS = (STRONG_UP, MODERATE_UP, MILD_UP)

OK = "OK"
INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
TRUNCATED = "TRUNCATED"
UNAVAILABLE = "UNAVAILABLE"

# Pine position -> rulebook readings (D14 table, RB 1686-1695, 1708)
# 12 o'clock is "Extreme Uptrend" (RB 1688); approved R2 maps it to STRONG_UP for matrix
# evaluation while preserving the original label in evidence and reports.
READINGS = {
    "12 o'clock": (STRONG_UP,),
    "1 o'clock": (STRONG_UP, MODERATE_UP),
    "2 o'clock": (MODERATE_UP, MILD_UP),
    "2-3 o'clock": (MILD_UP, SIDEWAYS),
    "3 o'clock": (SIDEWAYS,),
    "3-4 o'clock": (DOWN, SIDEWAYS),
    "4 o'clock": (DOWN,),
    "5 o'clock": (DOWN,),
    "6 o'clock": (DOWN,),
}

RULEBOOK_LABELS = {"12 o'clock": "Extreme Uptrend"}


def clock_position(pct):
    if pct > 2.0:
        return "12 o'clock"
    if pct > 1.0:
        return "1 o'clock"
    if pct > 0.4:
        return "2 o'clock"
    if pct > 0.1:
        return "2-3 o'clock"
    if pct > -0.1:
        return "3 o'clock"
    if pct > -0.4:
        return "3-4 o'clock"
    if pct > -1.0:
        return "4 o'clock"
    if pct > -2.0:
        return "5 o'clock"
    return "6 o'clock"


def sma(values, n):
    return sum(values[-n:]) / float(n)


def reading_from_closes(closes):
    """Trend reading from completed closes, oldest first."""
    if len(closes) < MIN_CANDLES:
        return {"status": INSUFFICIENT_HISTORY, "candles": len(closes), "needed": MIN_CANDLES,
                "readings": [], "pct": None, "position": None}
    now = sma(closes, PERIOD)
    before = sma(closes[:-LOOKBACK], PERIOD)
    pct = (now - before) / now * 100.0 if now != 0 else 0.0
    pos = clock_position(pct)
    prev = sma(closes[:-1], PERIOD)
    return {"status": OK, "candles": len(closes), "needed": MIN_CANDLES, "pct": round(pct, 6),
            "position": pos, "rulebook_label": RULEBOOK_LABELS.get(pos), "readings": list(READINGS[pos]),
            "sma50": round(now, 6), "sma50_5_back": round(before, 6),
            "pine_dashboard_state": "UPTREND" if now > prev else ("DOWNTREND" if now < prev else "RANGING")}


def trend_for(snapshot, tf):
    """Trend reading on a snapshot timeframe; never reads a series past a gap as current."""
    st = structure.series_status(snapshot, tf)
    if st["status"] == structure.NOT_REQUESTED:
        return {"tf": tf, "status": UNAVAILABLE, "readings": [], "series": st}
    if st["status"] == structure.TRUNCATED:
        return {"tf": tf, "status": TRUNCATED, "readings": [], "series": st}
    closes = [c.close for c in snapshot.series[tf].candles]
    out = reading_from_closes(closes)
    out["tf"] = tf
    out["series"] = st
    return out
