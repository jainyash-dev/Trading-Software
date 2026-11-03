"""Writes the SYNTHETIC candle CSVs of the scenario library (nse/scenarios/data/).

  python3 -m nse.scenarios.generate           # (re)write data/*.csv and data/MANIFEST.json
  python3 -m nse.scenarios.generate --check   # exit 1 if a committed file differs

Every price written here is INVENTED. The recipe is a copy of the long SYNTHETIC history
of tests/_research.py (long_mit_candles, extend; nse/ never imports tests/): five years of
weekday doji candles along waypoints chosen so that the Zone Engine itself finds a Monthly
supply curve top, a fresh Monthly demand curve bottom, a tested Monthly demand (the
coinciding zone, D15), a Weekly supply target and one Daily DBR demand zone
(PL 159.94, DL 157.92 at k = 1.68). Nothing about these prices is market data, and a
scenario built on them is never external validation (data_kind SYNTHETIC).

Output is deterministic: same code, byte-identical files (floats written with repr).
"""

import argparse
import datetime
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
MANIFEST = "MANIFEST.json"

# --- copy of tests/_research.py builder logic (SYNTHETIC) ---------------------------------
DBR = [(100.0, 101.0, 99.0, 100.0), (100.0, 100.5, 94.0, 95.0), (95.0, 96.0, 94.5, 95.2),
       (95.5, 102.0, 95.3, 101.5), (101.5, 105.0, 101.0, 104.5)]
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
LONG_K = 1.68


def weekdays(start, n):
    out, d = [], start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += datetime.timedelta(days=1)
    return out


def long_mit_rows(k=LONG_K, start=None, tail_step=1.002, tail_wick=.003, tail_days=12):
    """(date, open, high, low, close) rows; same values as tests/_research.long_mit_candles."""
    out = []
    for (d0, p0, w), (d1, p1, _) in zip(LONG_WAYPOINTS, LONG_WAYPOINTS[1:]):
        days = [d for d in (d0 + datetime.timedelta(i) for i in range((d1 - d0).days)) if d.weekday() < 5]
        for i, d in enumerate(days):
            p = round(p0 * (p1 / p0) ** (i / len(days)), 2)
            if start is None or d >= start:
                out.append((d, p, round(p * (1 + w), 2), round(p * (1 - w), 2), p))
    days = weekdays(out[-1][0] + datetime.timedelta(1), 5 + tail_days)
    for d, r in zip(days, DBR):
        out.append((d,) + tuple(round(x * k, 2) for x in r))
    p = DBR[-1][3] * k
    for d in days[5:]:
        p = round(p * tail_step, 2)
        out.append((d, p, round(p * (1 + tail_wick), 2), round(p * (1 - tail_wick), 2), p))
    return out


def extend(rows, more):
    """Append (o, h, l, c) rows on the following weekdays."""
    days = weekdays(rows[-1][0] + datetime.timedelta(1), len(more))
    return list(rows) + [(d,) + tuple(r) for d, r in zip(days, more)]


def _with_bad_high(rows, day):
    """One row whose high is below its close (OHLC_INCONSISTENT, a data-quality ERROR)."""
    out = []
    for r in rows:
        if r[0] == day:
            r = (r[0], r[1], round(r[4] * 0.98, 2), r[3], r[4])
        out.append(r)
    return out


# --- the files and their recipes ----------------------------------------------------------
def recipes():
    base = long_mit_rows()
    touch = [(176.0, 176.5, 159.5, 170.0), (170.0, 171.0, 169.0, 170.5)]
    return [
        ("long_mit.csv", base,
         "long_mit_rows(): the reference history; D DBR PL 159.94 DL 157.92 formed 2024-01-16, last day 2024-02-02"),
        ("long_mit_touched.csv", extend(base, touch),
         "long_mit.csv + 2024-02-05 low 159.5 (<= PL 159.94, > DL 157.92) + 2024-02-06 calm"),
        ("long_mit_wick_below_dl.csv", extend(base, [(176.0, 176.5, 157.0, 170.0), (170.0, 171.0, 169.0, 170.5)]),
         "long_mit.csv + 2024-02-05 low 157.0 (< DL 157.92) close 170.0 (> DL) + 2024-02-06 calm"),
        ("long_mit_invalidated.csv", extend(base, [(176.0, 176.0, 150.0, 151.0)] + [(151.0, 152.0, 150.0, 151.0)] * 10),
         "long_mit.csv + 2024-02-05 close 151.0 (< DL 157.92) + 10 calm days at 151"),
        ("long_mit_missing_session.csv", base[:-3] + base[-2:],
         "long_mit.csv without its third-last row (%s), a weekday after the zone formed" % base[-3][0]),
        ("long_mit_dq_error_2020.csv", _with_bad_high(base, datetime.date(2020, 3, 2)),
         "long_mit.csv with 2020-03-02 high set below its close (OHLC_INCONSISTENT)"),
        ("long_mit_dq_error_after.csv", _with_bad_high(extend(base, [(176.0, 177.0, 175.0, 176.5)]),
                                                       datetime.date(2024, 2, 5)),
         "long_mit.csv + 2024-02-05 with its high below its close (OHLC_INCONSISTENT after 2024-02-02)"),
        ("long_mit_k175.csv", long_mit_rows(k=1.75),
         "long_mit_rows(k=1.75): D DBR PL 166.6 lies wholly above the Monthly demand range"),
        ("long_mit_k179_flat.csv", long_mit_rows(k=1.79, tail_step=1.0, tail_wick=.002),
         "long_mit_rows(k=1.79, tail_step=1.0, tail_wick=.002): D DBR PL 170.41, close under the Weekly supply"),
        ("long_mit_from_2023_02.csv", long_mit_rows(start=datetime.date(2023, 2, 1)),
         "long_mit_rows(start=2023-02-01): history too short for Half-yearly and Yearly"),
        ("long_mit_hoc_uptrend.csv", long_mit_rows(tail_step=1.006, tail_days=120),
         "long_mit_rows(tail_step=1.006, tail_days=120): price climbs to 359.91 by the last day (2024-07-03)"),
    ]


def _csv_text(rows):
    lines = ["date,open,high,low,close"]
    for d, o, h, l, c in rows:
        lines.append("%s,%r,%r,%r,%r" % (d.isoformat(), float(o), float(h), float(l), float(c)))
    return "\n".join(lines) + "\n"


def render():
    """{file name: text}, including MANIFEST.json."""
    files, manifest = {}, {}
    for name, rows, recipe in recipes():
        text = _csv_text(rows)
        files[name] = text
        manifest[name] = {"data_kind": "SYNTHETIC", "rows": len(rows), "first_date": rows[0][0].isoformat(),
                          "last_date": rows[-1][0].isoformat(), "recipe": recipe,
                          "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}
    files[MANIFEST] = json.dumps({
        "data_kind": "SYNTHETIC",
        "note": "Invented prices written by nse/scenarios/generate.py; not market data, never external validation.",
        "generator": "python3 -m nse.scenarios.generate",
        "files": manifest}, sort_keys=True, indent=1) + "\n"
    return files


def main(argv=None):
    p = argparse.ArgumentParser(prog="python3 -m nse.scenarios.generate", description=__doc__.splitlines()[0])
    p.add_argument("--check", action="store_true", help="compare with the committed files; write nothing")
    p.add_argument("--out", default=DATA, help="folder to write (default nse/scenarios/data)")
    args = p.parse_args(argv)
    files = render()
    if args.check:
        bad = []
        for name, text in sorted(files.items()):
            path = os.path.join(args.out, name)
            if not os.path.exists(path):
                bad.append("%s: missing" % name)
                continue
            with open(path, encoding="utf-8", newline="") as fh:
                if fh.read() != text:
                    bad.append("%s: differs from the generator" % name)
        for b in bad:
            print(b)
        print("%d of %d files match the generator" % (len(files) - len(bad), len(files)))
        return 1 if bad else 0
    os.makedirs(args.out, exist_ok=True)
    for name, text in sorted(files.items()):
        with open(os.path.join(args.out, name), "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
    print("wrote %d files to %s (SYNTHETIC)" % (len(files), args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
