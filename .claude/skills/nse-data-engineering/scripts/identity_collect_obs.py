"""Step 1 of the identity build (ED-37; run identity_build_records.py next).

Member-symbol observations 2016-2025 from the held official bhavcopies (strict loader).
Output: member_obs_full.json {symbol: [[date, series, isin, prevclose, close], ...]} and
isin_changes_full.json [[symbol, last_old_date, old_isin, first_new_date, new_isin, series], ...]."""
import csv, json, os, sys
from multiprocessing import Pool
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, ROOT)
from nse.research.deps import bhavcopy as bc  # noqa: E402
OUT = os.path.join(ROOT, "nse/output/identity_build")      # intermediate, regenerable
U = os.path.join(ROOT, "nse/data/universe")


def members():
    out = set()
    for n in ("nifty100_baseline.csv", "nifty100_changes.csv", "instrument_records.csv"):
        for r in csv.DictReader(open(os.path.join(U, n), newline="", encoding="utf-8")):
            out.add(r["symbol"].strip())
            if r.get("new_symbol", "").strip():
                out.add(r["new_symbol"].strip())
    return sorted(s for s in out if s and not s.startswith("DUMMY"))


MEM = set(members())


def one(path):
    f = bc.load(path)
    return [(r.symbol, f.trade_date.isoformat(), r.series, r.isin, str(r.prev_close), str(r.close))
            for r in f.rows if r.symbol in MEM]


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    paths = bc.archive_paths(os.path.join(ROOT, "nse/data/eod/raw"))
    with Pool(4) as p:
        res = p.map(one, paths, chunksize=20)
    obs = {}
    for rows in res:
        for s, d, ser, isin, pc, c in rows:
            obs.setdefault(s, []).append([d, ser, isin, pc, c])
    for v in obs.values():
        v.sort()
    json.dump(obs, open(os.path.join(OUT, "member_obs_full.json"), "w"))
    changes = []
    for s, rows in sorted(obs.items()):
        eq = [r for r in rows if r[1] in ("EQ", "BE", "BZ")]
        for a, b in zip(eq, eq[1:]):
            if a[2] != b[2]:
                changes.append([s, a[0], a[2], b[0], b[2], b[1]])
    json.dump(changes, open(os.path.join(OUT, "isin_changes_full.json"), "w"), indent=0)
    print(len(paths), "files;", len(obs), "symbols;", len(changes), "ISIN changes")
    for c in changes:
        print(c)
