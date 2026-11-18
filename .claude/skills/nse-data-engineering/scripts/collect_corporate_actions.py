#!/usr/bin/env python3
"""Owner-approved collection of official NSE corporate-action records (D56, 2026-11-09).

Scope: the historical NIFTY 100 members in nse/data/universe/ (every symbol in the baseline
and changes files, and the earlier symbols of renamed members), window 2016-01-01 to
2025-12-31, from NSE's corporate-actions page data
(https://www.nseindia.com/api/corporates-corporateActions). Outside nse/ by design (D31).

For each symbol: one GET with a browser session (cookies from the NSE home page), a pause
between requests, retries with backoff; the raw response is saved unchanged as
nse/data/corporate_actions/raw/ca_<SYMBOL>_2016_2025.json (an existing file is never
overwritten), and a row is appended to collection_log.jsonl (URL, HTTP status, SHA-256,
size, rows, retrieved_at). coverage.csv lists, per symbol, the window collected and the file
that holds it; a symbol is covered only if its response was a non-empty JSON list (an empty
response is logged but never counted as coverage: it cannot be told from "no events").

The API's output is not byte-stable and its completeness is not documented by NSE; the
completeness check against bhavcopy PREVCLOSE discontinuities is a separate step.
"""

import argparse
import csv
import datetime
import hashlib
import http.cookiejar
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
CA = os.path.join(ROOT, "nse", "data", "corporate_actions")
RAW = os.path.join(CA, "raw")
LOG = os.path.join(CA, "collection_log.jsonl")
COVERAGE = os.path.join(CA, "coverage.csv")
U = os.path.join(ROOT, "nse", "data", "universe")
HOME = "https://www.nseindia.com/"
API = "https://www.nseindia.com/api/corporates-corporateActions"
WINDOW = ("01-01-2016", "31-12-2025")
COVERAGE_COLUMNS = ("symbol", "from_date", "to_date", "source_file", "source_sha256", "rows", "retrieved_on", "notes")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"


def members():
    out = set()
    for name in ("nifty100_baseline.csv", "nifty100_changes.csv"):
        with open(os.path.join(U, name), newline="", encoding="utf-8") as fh:
            out.update(r["symbol"].strip() for r in csv.DictReader(fh))
    with open(os.path.join(U, "instrument_records.csv"), newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            out.add(r["symbol"].strip())
            if r["new_symbol"].strip():
                out.add(r["new_symbol"].strip())
    return sorted(s for s in out if s and not s.startswith("DUMMY"))


def opener():
    jar = http.cookiejar.CookieJar()
    o = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    o.addheaders = [("User-Agent", UA), ("Accept", "application/json,text/html,*/*"),
                    ("Accept-Language", "en-US,en;q=0.9"), ("Referer", HOME)]
    try:
        o.open(HOME, timeout=30).read()
    except urllib.error.URLError:
        pass                                      # the API may still answer; the outcome is logged
    return o


def _rows_in(path):
    try:
        with open(path, "rb") as fh:
            rows = json.loads(fh.read().decode("utf-8"))
        return len(rows) if isinstance(rows, list) else None
    except (OSError, ValueError):
        return None


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--rate", type=float, default=2.0)
    p.add_argument("--retries", type=int, default=3)
    p.add_argument("--symbols", help="comma-separated subset (default: all members)")
    p.add_argument("--retry-empty", action="store_true",
                   help="re-request symbols whose latest saved response was empty; saved as a new numbered file")
    a = p.parse_args(argv)
    os.makedirs(RAW, exist_ok=True)
    syms = a.symbols.split(",") if a.symbols else members()
    o = opener()
    for s in syms:
        dest = os.path.join(RAW, "ca_%s_2016_2025.json" % s.replace("/", "_"))
        if os.path.exists(dest):
            if not a.retry_empty or _rows_in(dest) != 0:
                continue                                          # never overwrite; resume
            n = 1
            while os.path.exists(dest[:-5] + ".retry%d.json" % n):
                if _rows_in(dest[:-5] + ".retry%d.json" % n) != 0:
                    break
                n += 1
            else:
                dest = dest[:-5] + ".retry%d.json" % n                # a new file; the empty one is kept
            if not dest.endswith(".retry%d.json" % n):
                continue
        url = API + "?" + urllib.parse.urlencode({"index": "equities", "symbol": s,
                                                   "from_date": WINDOW[0], "to_date": WINDOW[1]})
        entry = {"symbol": s, "url": url, "retrieved_at": datetime.datetime.now(datetime.timezone.utc)
                 .strftime("%Y-%m-%dT%H:%M:%SZ")}
        data, status = None, None
        for attempt in range(1, a.retries + 1):
            time.sleep(a.rate)
            try:
                with o.open(url, timeout=30) as resp:
                    status, data = resp.status, resp.read()
                break
            except urllib.error.HTTPError as e:
                status = e.code
                if e.code in (401, 403):
                    o = opener()                                  # refresh the session cookies
            except (urllib.error.URLError, OSError) as e:
                entry["detail"] = "%s: %s" % (type(e).__name__, e)
            time.sleep(a.rate * (2 ** attempt))
        entry.update(http_status=status, attempts=attempt)
        try:
            rows = json.loads(data.decode("utf-8")) if data else None
        except ValueError:
            rows = None
        if not isinstance(rows, list):
            entry["outcome"] = "NOT_COLLECTED"
            with open(LOG, "a") as fh:
                fh.write(json.dumps(entry, sort_keys=True) + "\n")
            print(s, "NOT_COLLECTED", status)
            continue
        with open(dest, "wb") as fh:
            fh.write(data)
        entry.update(outcome="COLLECTED", sha256=sha(data), size_bytes=len(data), rows=len(rows),
                     file="raw/" + os.path.basename(dest))
        with open(LOG, "a") as fh:
            fh.write(json.dumps(entry, sort_keys=True) + "\n")
    write_coverage()


def write_coverage():
    """coverage.csv from the collection log: one row per symbol with a collected file whose
    bytes still match the logged SHA-256 (the INFY / RELIANCE files collected earlier are
    added from their own hashes, recorded on 2026-11-09)."""
    rows = {}
    if os.path.isfile(LOG):
        with open(LOG) as fh:
            for line in fh:
                e = json.loads(line)
                if e.get("outcome") == "COLLECTED":
                    rows[e["symbol"]] = e
    for s in ("INFY", "RELIANCE"):
        f = os.path.join(RAW, "ca_%s_2016_2025.json" % s)
        if s not in rows and os.path.isfile(f):
            data = open(f, "rb").read()
            rows[s] = {"symbol": s, "file": "raw/" + os.path.basename(f), "sha256": sha(data),
                       "rows": len(json.loads(data)), "retrieved_at": "2026-11-09", "url": "(earlier MP1 retrieval)"}
    out = []
    for s, e in sorted(rows.items()):
        path = os.path.join(CA, e["file"])
        if not os.path.isfile(path) or sha(open(path, "rb").read()) != e["sha256"]:
            continue
        if not e["rows"]:
            # an empty response cannot be told from "no events" (NSE files events under the
            # current symbol; former tickers return []): never coverage (D52 safeguard)
            continue
        out.append({"symbol": s, "from_date": "2016-01-01", "to_date": "2025-12-31", "source_file": e["file"],
                    "source_sha256": e["sha256"], "rows": e["rows"], "retrieved_on": e["retrieved_at"][:10],
                    "notes": "NSE corporate actions API response, window %s..%s; %s" % (WINDOW[0], WINDOW[1], e["url"])})
    with open(COVERAGE, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(COVERAGE_COLUMNS), lineterminator="\n")
        w.writeheader()
        w.writerows(out)
    print("coverage rows:", len(out))


if __name__ == "__main__":
    sys.exit(main())
