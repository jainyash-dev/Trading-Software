"""Step 2 of the identity build (after identity_collect_obs.py). Rebuild nse/data/universe/instrument_records.csv for 2016-2025 (D51, D56, ED-37).

Base: the LISTING / SYMBOL_CHANGE rows from NSE EQUITY_L.csv and symbolchange.csv (as built by
build_universe.py). Then, from the held official bhavcopies 2016-2025 (member_obs_full.json,
isin_changes_full.json written by collect_obs.py) and the official corporate-action records:

* an instrument whose ISIN changed inside the held data gets a LISTING on its EARLIEST observed
  ISIN from its first held session (source: that bhavcopy archive), and one ISIN_CHANGE per
  evidenced change (source: the saved NSE corporate-action response). Evidence (ED-37): an
  official SPLIT / BONUS / CONSOLIDATION / UNPARSED_PRICE_EVENT record of the instrument
  (any symbol in its official rename chain) with
    ex-date or record date equal to the first session under the new ISIN.
  An unevidenced change gets no record: the identity check then reports
  ISIN_CHANGED_WITHOUT_RECORD (DATA_INSUFFICIENT across it). Names are never matched.
* a member ISIN absent from EQUITY_L.csv (delisted / merged) gets a LISTING from its first held
  session (source: that bhavcopy); its end is not recorded without official evidence.
Writes instrument_records.csv and identity_report.json (universe folder).
"""
import csv
import datetime as dt
import hashlib
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, ROOT)
from nse.research import instruments  # noqa: E402
from nse.research.deps import calendar as cal_mod  # noqa: E402

HERE = os.path.join(ROOT, "nse/output/identity_build")     # written by identity_collect_obs.py
U = os.path.join(ROOT, "nse/data/universe")
CA = os.path.join(ROOT, "nse/data/corporate_actions")
REC = "2026-11-09"
SCALE = ("SPLIT", "BONUS", "CONSOLIDATION", "UNPARSED_PRICE_EVENT")


def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def read(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


obs = json.load(open(os.path.join(HERE, "member_obs_full.json")))
changes = json.load(open(os.path.join(HERE, "isin_changes_full.json")))
base = read(os.path.join(U, "build", "instrument_records_base.csv"))   # LISTING / SYMBOL_CHANGE from EQUITY_L and symbolchange (ED-32)
ca_rows = read(os.path.join(CA, "actions.csv"))
manifest = {r["file_name"]: r for r in read(os.path.join(ROOT, "nse/data/eod/manifest.csv")) if r["kind"] == "ARCHIVE"}
by_date = {r["trade_date"]: r["file_name"] for r in manifest.values()}
cal = cal_mod.NseCalendar.load(os.path.join(ROOT, "nse/data/calendar"))
report = {"isin_changes_evidenced": [], "isin_changes_unevidenced": [], "listings_from_bhavcopy": [],
          "listing_replaced": []}

# a rename before the held data keeps its record only when its ISIN is the one the new symbol
# traded on its first held session; otherwise the ISIN at the rename is unknown (the base build
# used today's EQUITY_L ISIN, which made two ISINs active under one symbol, e.g. TISCO ->
# TATASTEEL 2005 with INE081A01020): the record is dropped and reported, never guessed
FIRST_HELD = "2016-01-01"
kept = []
for r in base:
    if r["record_type"] == "SYMBOL_CHANGE" and r["effective_from"] < FIRST_HELD:
        first = sorted(x for x in obs.get(r["new_symbol"], []) if x[1] in ("EQ", "BE", "BZ"))[:1]
        if first and first[0][2] != r["isin"]:
            report.setdefault("pre_history_renames_dropped", []).append(
                {"old": r["symbol"], "new": r["new_symbol"], "date": r["effective_from"], "record_isin": r["isin"],
                 "isin_on_first_held_session": first[0][2]})
            continue
    kept.append(r)
base = kept

# rename chains from the official SYMBOL_CHANGE rows: symbol -> every symbol of its chain
chain = {}
for r in base:
    if r["record_type"] == "SYMBOL_CHANGE":
        group = chain.get(r["symbol"], {r["symbol"]}) | chain.get(r["new_symbol"], {r["new_symbol"]})
        for s in group:
            chain[s] = group


def chain_of(s):
    return chain.get(s, {s})


def rec_date(r):
    t = r["notes"].split("record date ")[-1].strip()
    try:
        return dt.datetime.strptime(t, "%d-%b-%Y").date().isoformat()
    except ValueError:
        return ""


def next_trading_day(d):
    x = dt.date.fromisoformat(d) + dt.timedelta(days=1)
    while not cal.is_trading_day(x):
        x += dt.timedelta(days=1)
    return x.isoformat()


def evidence(symbol, d0, d1):
    out = []
    for r in ca_rows:
        if r["symbol"] not in chain_of(symbol) or r["action"] not in SCALE:
            continue
        if r["ex_date"] == d1 or rec_date(r) == d1:
            out.append((r, "ex-date or record date is the first session under the new ISIN"))
        # QA 2026-11-09: an "ex-date = last old session" convention is an inference, not
        # evidence (D56: ambiguous evidence stays DATA_INSUFFICIENT); it is not used
    return out


def bhav_source(day):
    name = by_date[day]
    return "../eod/raw/" + name, manifest[name]["sha256"]


def first_obs(symbols, isin=None):
    rows = sorted(r[:3] + [s] for s in symbols for r in obs.get(s, []) if isin is None or r[2] == isin)
    return rows[0] if rows else None


# a SYMBOL_CHANGE takes the ISIN traded on both sides of the rename in the bhavcopies (the base
# build used the CURRENT ISIN from EQUITY_L, wrong when the ISIN changed after the rename)
for r in base:
    if r["record_type"] != "SYMBOL_CHANGE":
        continue
    before = [x for x in obs.get(r["symbol"], []) if x[0] < r["effective_from"] and x[1] in ("EQ", "BE", "BZ")]
    after = [x for x in obs.get(r["new_symbol"], []) if x[0] >= r["effective_from"] and x[1] in ("EQ", "BE", "BZ")]
    if not before or not after:
        continue                                      # outside the held data: unchanged
    i_old, i_new = max(before)[2], min(after)[2]
    if i_old == i_new and i_old != r["isin"]:
        report.setdefault("symbol_change_isin_corrected", []).append(
            {"old": r["symbol"], "new": r["new_symbol"], "date": r["effective_from"], "was": r["isin"], "now": i_old})
        r["isin"] = i_old
        r["notes"] = "ISIN traded under both symbols in the bhavcopies of %s and %s (official)" % (max(before)[0], min(after)[0])

changed = {}
for s, d0, i0, d1, i1, _ in changes:
    changed.setdefault(frozenset(chain_of(s)), []).append((s, d0, i0, d1, i1))

recs = [r for r in base]
for group, chs in sorted(changed.items(), key=lambda kv: sorted(kv[0])):
    chs.sort(key=lambda c: c[3])
    first_isin = chs[0][2]
    final_isin = chs[-1][4]
    # the EQUITY_L LISTING of this instrument (on its current ISIN) is replaced
    listing = [r for r in recs if r["record_type"] == "LISTING" and r["isin"] == final_isin]
    for r in listing:
        recs.remove(r)
        report["listing_replaced"].append({k: r[k] for k in ("symbol", "isin", "effective_from")})
    d, _, isin, sym = first_obs(group, first_isin)
    src, ssha = bhav_source(d)
    recs.append({"record_type": "LISTING", "symbol": sym, "new_symbol": "", "isin": isin, "series": "EQ",
                 "effective_from": d, "effective_to": "", "source": "NSE CM bhavcopy (official)", "source_file": src,
                 "source_sha256": ssha, "recorded_on": REC,
                 "notes": "first held session with this ISIN (held EOD files start 2016-01-01); earlier history not held; "
                          "listing date per EQUITY_L: %s" % (listing[0]["effective_from"] if listing else "not listed")})
    for s, d0, i0, d1, i1 in chs:
        ev = evidence(s, d0, d1)
        if not ev:
            report["isin_changes_unevidenced"].append({"symbol": s, "last_old": d0, "old": i0, "first_new": d1, "new": i1})
            continue
        r, why = ev[0]
        f = os.path.join(CA, r["source_file"])
        recs.append({"record_type": "ISIN_CHANGE", "symbol": s, "new_symbol": "", "isin": i1, "series": "EQ",
                     "effective_from": d1, "effective_to": "", "source": "NSE corporate actions (saved API response)",
                     "source_file": os.path.relpath(f, U), "source_sha256": sha(f), "recorded_on": REC,
                     "notes": "ISIN %s -> %s: last session on the old ISIN %s, first on the new %s (official bhavcopies); "
                              "evidence: %s %s %s (record date %s; %s) (ED-37)"
                              % (i0, i1, d0, d1, r["symbol"], r["action"], r["ex_date"], rec_date(r) or "not printed", why)})
        report["isin_changes_evidenced"].append({"symbol": s, "first_new": d1, "old": i0, "new": i1,
                                                 "evidence": [r["symbol"], r["action"], r["ex_date"], rec_date(r)], "rule": why})

# member ISINs with no listing record at all: from the first held session
listed = set(r["isin"] for r in recs if r["record_type"] in ("LISTING", "ISIN_CHANGE"))
univ = read(os.path.join(U, "nifty100_baseline.csv")) + read(os.path.join(U, "nifty100_changes.csv"))
for isin, sym in sorted(set((r["isin"], r["symbol"]) for r in univ)):
    if isin in listed or sym.startswith("DUMMY"):
        continue
    hit = first_obs(chain_of(sym), isin)
    if hit is None:
        report.setdefault("member_isin_without_observation", []).append({"symbol": sym, "isin": isin})
        continue
    d, _, _, s = hit
    last = max(r[0] for x in chain_of(sym) for r in obs.get(x, []) if r[2] == isin)
    src, ssha = bhav_source(d)
    recs.append({"record_type": "LISTING", "symbol": s, "new_symbol": "", "isin": isin, "series": "EQ",
                 "effective_from": d, "effective_to": "", "source": "NSE CM bhavcopy (official)", "source_file": src,
                 "source_sha256": ssha, "recorded_on": REC,
                 "notes": "not in NSE EQUITY_L.csv; first held session with this ISIN (held EOD files start 2016-01-01); "
                          "last held session %s; the end of the listing has no official record here" % last})
    listed.add(isin)
    report["listings_from_bhavcopy"].append({"symbol": s, "isin": isin, "from": d, "last_held": last})

order = {"LISTING": 0, "ISIN_CHANGE": 1, "SYMBOL_CHANGE": 2, "MERGER": 3, "DELISTING": 4}
recs.sort(key=lambda r: (r["isin"][:9], r["effective_from"], order[r["record_type"]], r["symbol"]))
out = os.path.join(U, "instrument_records.csv")
with open(out, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(instruments.COLUMNS), lineterminator="\n")
    w.writeheader()
    w.writerows(recs)
loaded = instruments.load(out)
report["counts"] = {"records": len(recs), "verified": sum(1 for r in loaded if r.verified),
                    "by_type": {t: sum(1 for r in recs if r["record_type"] == t) for t in order}}
with open(os.path.join(U, "identity_report.json"), "w") as fh:
    json.dump(report, fh, indent=1, sort_keys=True)
print(json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in report.items()}, indent=1))
for x in report["isin_changes_unevidenced"]:
    print("UNEVIDENCED", x)
