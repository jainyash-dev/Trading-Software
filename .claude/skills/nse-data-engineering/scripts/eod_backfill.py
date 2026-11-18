#!/usr/bin/env python3
"""Owner-approved scripted backfill of official NSE end-of-day bhavcopies (D47 and D55, 2026-11-09).

Scope of the approvals: the missing 2021-2025 (D47) and 2016-2020 (D55) sessions that
`acquire-plan` identifies, from the official URLs it prints. Nothing else. With
--include-excluded, the files of calendar-excluded sessions (Muhurat, the 2024 DR-switch
Saturdays), which NSE publishes, are fetched too, so the D33 check can see whether such a
session reached a zone (D52). With
--include-unresolved, the files of calendar-UNRESOLVED dates (D54: the 2016-2019 Dhanteras
days) are also fetched as evidence: they are held and validated, but the coverage report
never accepts them while the date is unresolved. This script is a tool of the nse-data-engineering
skill and deliberately lives outside nse/: the product code has no network code (D31).

  download  for every calendar trading day the plan marks MISSING, fetch the official archive
            into the inbox: allowed host only, URL equal to nse_bhavcopy.official_url(date),
            rate-limited, retried with backoff, resumable (a verified file already in the
            inbox is not fetched again), written to <name>.partial then renamed, never
            overwriting a file. Each attempt is appended to the download log (JSONL).
  ingest    pass every downloaded file through nse.research.acquisition.ingest one by one,
            with its own URL as source_page: strict parse, source selection (ED-20),
            duplicate / revision / malformed files quarantined, manifest rows and ledger.
  report    a JSON summary of the download log and the ledger.

Usage (from the repository root):
  python3 .claude/skills/nse-data-engineering/scripts/eod_backfill.py download --start 2021-01-01 --end 2025-12-31
  python3 .claude/skills/nse-data-engineering/scripts/eod_backfill.py ingest
  python3 .claude/skills/nse-data-engineering/scripts/eod_backfill.py report
"""

import argparse
import datetime
import http.client
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
import zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, ROOT)
from nse.research import acquisition as acq  # noqa: E402
from nse.research.deps import bhavcopy, calendar as cal_mod  # noqa: E402

EOD = os.path.join(ROOT, "nse", "data", "eod")
INBOX = os.path.join(EOD, "inbox")
QUARANTINE = os.path.join(EOD, "quarantine")
DOWNLOAD_LOG = os.path.join(EOD, "download_log.jsonl")
LEDGER = os.path.join(EOD, "acquisition_ledger.jsonl")
CALENDAR = os.path.join(ROOT, "nse", "data", "calendar")
ALLOWED_PREFIX = "https://nsearchives.nseindia.com/content/"
APPROVED_WINDOW = (datetime.date(2016, 1, 1), datetime.date(2025, 12, 31))     # D47 (2021-2025) + D55 (2016-2020)
PROVENANCE = "SCRIPT_DOWNLOADED_USER_APPROVED"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) research-backfill"


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def log(entry, path=DOWNLOAD_LOG):
    with open(path, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")


def read_jsonl(path):
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def check_archive(path, name):
    """None when the archive has the official layout and its own format parses strictly,
    else the reason. Selection and provenance are checked again at ingest."""
    try:
        with zipfile.ZipFile(path) as z:
            members = [i.filename for i in z.infolist()]
            if not bhavcopy.archive_layout_ok(name, members):
                return "archive members %s, expected [%s]" % (members, name[:-len(".zip")])
            bad = z.testzip()
            if bad:
                return "corrupt member %s" % bad
    except zipfile.BadZipFile as e:
        return "not a zip archive (%s)" % e
    try:
        bhavcopy.load(path)
    except bhavcopy.BhavcopyError as e:
        return "%s: %s" % (type(e).__name__, e)
    return None


def fetch(url, dest, timeout):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(dest, "wb") as fh:
        status = resp.status
        if not resp.geturl().startswith(ALLOWED_PREFIX):          # a redirect must stay on the official host
            raise urllib.error.URLError("redirected off the official host to %s" % resp.geturl())
        while True:
            chunk = resp.read(1 << 16)
            if not chunk:
                break
            fh.write(chunk)
    return status


def cmd_download(a):
    start, end = datetime.date.fromisoformat(a.start), datetime.date.fromisoformat(a.end)
    if a.retries < 1:
        sys.exit("--retries must be at least 1")
    if start < APPROVED_WINDOW[0] or end > APPROVED_WINDOW[1]:
        sys.exit("refused: the approvals (D47, D55) cover 2016-01-01..2025-12-31 only")
    os.makedirs(INBOX, exist_ok=True)
    cal = cal_mod.NseCalendar.load(CALENDAR)
    rows = acq.plan(cal, start, end, os.path.join(EOD, "manifest.csv"), os.path.join(EOD, "raw"))
    wanted = (acq.EXPECTED,) + ((acq.CALENDAR_AMBIGUOUS,) if a.include_unresolved else ()) \
        + ((acq.EXCLUDED_SESSION,) if a.include_excluded else ())
    todo = [r for r in rows if r["status"] == acq.MISSING and r["calendar_status"] in wanted]
    done = {e["file_name"]: e for e in read_jsonl(DOWNLOAD_LOG) if e.get("outcome") == "DOWNLOADED"}
    print("missing calendar trading days in window: %d" % len(todo))
    fetched = 0
    attempts_made = 0
    for r in todo:
        if a.max_files and attempts_made >= a.max_files:
            break
        d = datetime.date.fromisoformat(r["session_date"])
        name, url = r["file_name"], r["url"]
        if url != bhavcopy.official_url(d) or not url.startswith(ALLOWED_PREFIX) or name != bhavcopy.official_name(d):
            log({"session_date": r["session_date"], "file_name": name, "url": url, "outcome": "REFUSED_URL",
                 "recorded_at": now()})
            continue
        dest = os.path.join(INBOX, name)
        if os.path.exists(dest):
            prior = done.get(name)
            if prior and prior.get("sha256") == sha256(dest):
                continue                                       # resume: already downloaded and verified
            log({"session_date": r["session_date"], "file_name": name, "url": url, "recorded_at": now(),
                 "outcome": "EXISTING_FILE_NOT_OVERWRITTEN", "sha256": sha256(dest)})
            continue
        staging = os.path.join(INBOX, ".partial")
        os.makedirs(staging, exist_ok=True)
        part = os.path.join(staging, name)                    # official name, so the strict check applies
        outcome, detail, status = None, "", None
        attempts_made += 1
        for attempt in range(1, a.retries + 1):
            time.sleep(a.rate)
            try:
                status = fetch(url, part, a.timeout)
                outcome = "DOWNLOADED"
                break
            except urllib.error.HTTPError as e:
                status, detail = e.code, str(e)
                if e.code == 404:
                    outcome = "NOT_SERVED"
                    break
            except (urllib.error.URLError, http.client.HTTPException, OSError, TimeoutError) as e:
                detail = "%s: %s" % (type(e).__name__, e)
            time.sleep(a.rate * (2 ** attempt))                # backoff before the next attempt
        entry = {"session_date": r["session_date"], "file_name": name, "url": url, "http_status": status,
                 "attempts": attempt, "recorded_at": now(), "downloaded_on": datetime.date.today().isoformat()}
        if outcome != "DOWNLOADED":
            if os.path.exists(part):
                os.remove(part)
            entry.update(outcome=outcome or "FAILED", detail=detail)
            log(entry)
            print("%s %s %s" % (r["session_date"], entry["outcome"], detail))
            continue
        problem = check_archive(part, name)
        entry.update(size_bytes=os.path.getsize(part), sha256=sha256(part))
        if problem:
            entry.update(outcome="FAILED_VERIFICATION", detail=problem)
            os.makedirs(QUARANTINE, exist_ok=True)
            os.replace(part, os.path.join(QUARANTINE, "%s_%s.download" % (entry["sha256"], name)))
            log(entry)
            print("%s FAILED_VERIFICATION %s" % (r["session_date"], problem))
            continue
        os.replace(part, dest)
        entry["outcome"] = "DOWNLOADED"
        log(entry)
        fetched += 1
        if fetched % 50 == 0:
            print("downloaded %d" % fetched, flush=True)
    print("downloaded this run: %d" % fetched)


def cmd_ingest(a):
    entries = [e for e in read_jsonl(DOWNLOAD_LOG) if e.get("outcome") == "DOWNLOADED"]
    ingested = set(e["file_name"] for e in read_jsonl(LEDGER) if e.get("outcome") in (acq.INGESTED, acq.DUPLICATE))
    counts = {}
    for e in sorted(entries, key=lambda x: x["session_date"]):
        path = os.path.join(INBOX, e["file_name"])
        if e["file_name"] in ingested or not os.path.isfile(path):
            continue
        if sha256(path) != e["sha256"]:
            counts["INBOX_FILE_CHANGED"] = counts.get("INBOX_FILE_CHANGED", 0) + 1
            continue
        [res] = acq.ingest([path], os.path.join(EOD, "raw"), os.path.join(EOD, "manifest.csv"), QUARANTINE, LEDGER,
                           source_page=e["url"], downloaded_on=e["downloaded_on"],
                           provenance_status=PROVENANCE, recorded_at=now())
        counts[res["outcome"]] = counts.get(res["outcome"], 0) + 1
    print(json.dumps(counts, sort_keys=True))


def cmd_report(a):
    dl = read_jsonl(DOWNLOAD_LOG)
    last = {}
    for e in dl:
        last[e["file_name"]] = e
    out = {"download_attempt_records": len(dl),
           "files_by_last_outcome": _count(e["outcome"] for e in last.values()),
           "not_served": sorted(e["session_date"] for e in last.values() if e["outcome"] == "NOT_SERVED"),
           "failed": sorted((e["session_date"], e["outcome"], e.get("detail", "")) for e in last.values()
                            if e["outcome"] not in ("DOWNLOADED", "NOT_SERVED")),
           "ledger_outcomes": _count(e.get("outcome") for e in read_jsonl(LEDGER) if e.get("event") == "INGEST"),
           "quarantine_reasons": _count(e.get("reason") for e in read_jsonl(LEDGER)
                                        if e.get("outcome") in (acq.QUARANTINED, acq.REVISED_FILE_QUARANTINED))}
    text = json.dumps(out, indent=1, sort_keys=True)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    print(text)


def _count(items):
    c = {}
    for x in items:
        c[x] = c.get(x, 0) + 1
    return dict(sorted(c.items(), key=lambda kv: str(kv[0])))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("download")
    d.add_argument("--start", required=True)
    d.add_argument("--end", required=True)
    d.add_argument("--rate", type=float, default=1.0, help="seconds to wait before each request")
    d.add_argument("--retries", type=int, default=3)
    d.add_argument("--timeout", type=float, default=30.0)
    d.add_argument("--max-files", type=int, default=0, help="stop after this many downloads (0: no limit)")
    d.add_argument("--include-excluded", action="store_true",
                   help="also fetch files of calendar-excluded sessions (Muhurat, shortened): official EOD "
                        "files held for the D33 touch check, never used for candles (D52)")
    d.add_argument("--include-unresolved", action="store_true",
                   help="also fetch files for calendar-UNRESOLVED dates, as evidence (D54); never accepted")
    d.set_defaults(func=cmd_download)
    sub.add_parser("ingest").set_defaults(func=cmd_ingest)
    r = sub.add_parser("report")
    r.add_argument("--out")
    r.set_defaults(func=cmd_report)
    a = p.parse_args(argv)
    return a.func(a)


if __name__ == "__main__":
    main()
