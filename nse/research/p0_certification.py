"""Reproducible P0 certification build: one gate result per Nifty 100 member-date.

GTF P0 (gtf-p0-data-certification sections 12-14). Every gate value is derived from the
files on disk, with the existing loaders, and each symbol-date is classified by
`dataset_eligibility.classify_symbol_date`. Nothing here restates a methodology gate,
adjusts a price, fills a candle or joins two ISINs.

Gates and the values this build emits (anything outside dataset_eligibility's passing set
fails closed):

membership        VERIFIED when the period in nifty100_universe.csv cites a source whose
                  bytes hash to its recorded SHA-256 (membership.convert withholds the hash
                  until both review rows are ACCEPTED, D49/ED-48); otherwise UNVERIFIED.
identity          RESOLVED when instruments.resolve names one verified ISIN for the symbol on
                  the date, it equals the period's ISIN and, when an EQ row is held, the
                  bhavcopy ISIN. Otherwise UNKNOWN_INSTRUMENT, UNVERIFIED_RECORD,
                  PERIOD_ISIN_MISMATCH or BHAVCOPY_ISIN_MISMATCH (D51, ED-29).
corporate_action  The saved response for the symbol, classified by corporate_actions.
                  response_status (a body that is not a JSON list of event objects is
                  MALFORMED_RESPONSE). No saved response proves the API's completeness
                  (R-10; P0 master prompt Part 8), so a body with parsed price events is
                  EVENTS_VERIFIED_COMPLETENESS_NOT_PROVED and `[]` stays
                  EMPTY_RESPONSE_COMPLETENESS_UNKNOWN. The gate passes only with a window in
                  the completeness register (D62 + D66 / OD-CA-1): two independent
                  hash-verified non-API sources, a validated event reconciliation, and a
                  USER_APPROVED decision naming both source hashes and the reconciliation
                  hash. A single source never proves completeness. The register does not
                  exist today, so no value passes.
calendar          TRADING_DAY: only official equity sessions are enumerated.
eod               ACCEPTED when the archive for the session is held, manifest-matched, in
                  the format selected for the date (ED-20), and has an EQ row for the
                  symbol. Otherwise NO_ACCEPTED_FILE, NO_EQ_ROW, or NON_EQ_ONLY:<series>
                  (a BE/BZ row is never read as EQ, ED-30).
price_continuity  Per step from the previous equity session: CONTINUOUS only when no recorded
                  price-scale action has its ex-date in the step, the ISIN is unchanged,
                  this session's EQ PREVCLOSE equals the prior EQ close of the same
                  instrument (same symbol, or same ISIN under a symbol the instrument
                  records link), and the session range is not wholly outside a 15% band of
                  that close. NSE prints the unadjusted prior close on an ex-date, so the
                  PREVCLOSE chain alone cannot show a split or bonus (ED-50). Otherwise
                  NO_EQ_ROW, PRIOR_EQ_SESSION_MISSING, PRIOR_SESSION_NON_EQ:<series>,
                  PRICE_SCALE_EVENT_ON_STEP:<action>, ISIN_CHANGE_ON_STEP,
                  PREVCLOSE_BREAK_ACROSS_EXCLUDED_SESSION, UNEXPLAINED_PREVCLOSE_BREAK or
                  UNEXPLAINED_PRICE_SCALE_GAP. A break is classified, never smoothed. The
                  gate is per step: a study over a window needs every step in it to pass.
Only these six data gates are required (owner decision D63). GTF strategy qualification
is not a P0 data gate and is not run here; every output row says
gtf_trade_eligibility=NOT_EVALUATED_NOT_A_P0_GATE. A certified P0 symbol-date is data that
passed the data gates, never a GTF candidate. Candidates still come only from the canonical
pipeline (pipeline.run -> scanner.scan -> scan_symbol -> qualification.evaluate_symbol).

Corporate-action evidence tier (owner decision D62), reported beside the gate and never
passing it: CA_RESPONSE_PRESENT_NOT_COMPLETE when the response is hash-verified, non-empty,
has no unparsed price subject, and the symbol-date passed the EOD and price-continuity gates;
otherwise CORPORATE_ACTIONS_UNVERIFIED. Such a row is research_use
EXPLORATORY_ONLY_NOT_CERTIFIED when every other data gate passes. It keeps the
CORPORATE_ACTIONS_UNVERIFIED limitation and never enters the certified file.

Outputs: the membership reference history, the certified research universe (eligible rows
only), the exclusion register (one row per maximal run of identical gate results), a JSON
summary with input hashes and the source-to-output reconciliation, and optionally the full
per-symbol-date matrix. No output carries a timestamp, so a rebuild on the same inputs is
byte-identical. authorises_order is false on every row.

    python3 -m nse.research.p0_certification --out-dir docs/product-discovery/p0 \
        --matrix nse/output/p0/eligibility_matrix.csv
"""

import argparse
import csv
import datetime
import hashlib
import json
import os
import re
import sys

from nse.research import corporate_actions as ca, dataset_eligibility as de, instruments, membership
from nse.research import universe as univ
from nse.research.deps import CALENDAR_DIR, EOD_MANIFEST, EOD_RAW_DIR, ROOT, bhavcopy, calendar as cal_mod

BUILD_VERSION = "1.6.0"
WINDOW_START = datetime.date(2020, 12, 31)          # D59 provisional membership research window
WINDOW_END = datetime.date(2025, 12, 31)

UNIVERSE_DIR = os.path.join(ROOT, "nse", "data", "universe")
CA_DIR = os.path.join(ROOT, "nse", "data", "corporate_actions")

MEMBERSHIP_UNVERIFIED = "UNVERIFIED"
ID_UNKNOWN = "UNKNOWN_INSTRUMENT"
ID_UNVERIFIED_RECORD = "UNVERIFIED_RECORD"
ID_PERIOD_ISIN_MISMATCH = "PERIOD_ISIN_MISMATCH"
ID_BHAVCOPY_ISIN_MISMATCH = "BHAVCOPY_ISIN_MISMATCH"
CA_EVENTS_COMPLETENESS_NOT_PROVED = "EVENTS_VERIFIED_COMPLETENESS_NOT_PROVED"
CA_HASH_MISMATCH = "SOURCE_HASH_MISMATCH"
CA_OUTSIDE_WINDOW = "OUTSIDE_RESPONSE_WINDOW"
EOD_NO_FILE = "NO_ACCEPTED_FILE"
EOD_NO_EQ_ROW = "NO_EQ_ROW"
EOD_NON_EQ_ONLY = "NON_EQ_ONLY"
PX_NO_EQ_ROW = "NO_EQ_ROW"
PX_PRIOR_MISSING = "PRIOR_EQ_SESSION_MISSING"
PX_PRIOR_NON_EQ = "PRIOR_SESSION_NON_EQ"
PX_EXCLUDED_SESSION = "PREVCLOSE_BREAK_ACROSS_EXCLUDED_SESSION"
PX_PRICE_EVENT = "PRICE_SCALE_EVENT_ON_STEP"
PX_ISIN_CHANGE = "ISIN_CHANGE_ON_STEP"
PX_UNEXPLAINED = "UNEXPLAINED_PREVCLOSE_BREAK"
PX_SCALE_GAP = "UNEXPLAINED_PRICE_SCALE_GAP"
PX_CALENDAR_UNRESOLVED = "CALENDAR_UNRESOLVED_ON_STEP"
PX_ACROSS_EXCLUDED = "STEP_ACROSS_EXCLUDED_SESSION"
CA_CONFLICTING = "CONFLICTING_RESPONSES"
CA_EMPTY_RENAMED = "EMPTY_RESPONSE_RENAMED_TICKER"
CA_OLD_TICKER = "RESPONSE_OF_RENAMED_AWAY_TICKER"
PX_AMBIGUOUS_RENAME = "AMBIGUOUS_RENAME_HISTORY"
RENAME_NONE, RENAME_CURRENT, RENAME_OLD, RENAME_AMBIGUOUS = "NONE", "CURRENT", "OLD", "AMBIGUOUS"


def rename_state(records, symbol):
    """How the SYMBOL_CHANGE records (verified or not) touch a ticker (review N-1, R-1):
    NONE, CURRENT (only renamed into), OLD (renamed away from), AMBIGUOUS (records under two ISINs)."""
    touching = [r for r in records if r.record_type == instruments.SYMBOL_CHANGE
                and symbol in (r.symbol, r.new_symbol)]
    if not touching:
        return RENAME_NONE
    if len(set(r.isin for r in touching)) > 1:
        return RENAME_AMBIGUOUS
    if any(r.symbol == symbol for r in touching):
        return RENAME_OLD
    return RENAME_CURRENT
CAL_UNRESOLVED = "UNRESOLVED"
SCALE_GAP_BAND = ca.SCALE_GAP_BAND
GTF_NOT_EVALUATED = "NOT_EVALUATED_NOT_A_P0_GATE"
SCOPE = "P0_DATA"                     # D63: data certification, not GTF trade eligibility
USE_CERTIFIED = "CERTIFIED_P0_DATA"
USE_EXPLORATORY = "EXPLORATORY_ONLY_NOT_CERTIFIED"   # D62: CA_RESPONSE_PRESENT_NOT_COMPLETE
USE_EXCLUDED = "EXCLUDED"

GATE_ORDER = de.DATA_GATES
DATA_GATES = GATE_ORDER

CERTIFIED_COLUMNS = ("symbol", "trade_date", "isin", "certification_scope", "membership_gate", "identity_gate",
                     "corporate_action_gate", "calendar_gate", "eod_gate", "price_continuity_gate",
                     "corporate_action_evidence_tier", "limitations", "gtf_trade_eligibility", "final_eligibility",
                     "authorises_order")
MATRIX_COLUMNS = ("trade_date", "symbol", "isin") + tuple(g + "_gate" for g in GATE_ORDER) + (
    "corporate_action_evidence_tier", "research_use", "limitations", "gtf_trade_eligibility",
    "final_eligibility", "blocking_gate", "failed_gates", "evidence")
REGISTER_COLUMNS = ("symbol", "isin", "membership_period_from", "from_date", "to_date", "sessions",
                    "final_eligibility", "blocking_gate", "failed_gates", "corporate_action_evidence_tier",
                    "research_use", "limitations", "reason", "evidence")
HISTORY_COLUMNS = ("symbol", "series", "isin", "effective_from", "effective_to", "membership_status",
                   "identity_at_start", "source", "source_file", "source_sha256", "notes")

_CA_FILE = re.compile(r"^ca_(.+?)_(\d{4})_(\d{4})(?:\.retry\d+)?\.json$")   # retries are read too


def ca_gate_value(body_status):
    """The certification gate value for one saved corporate-action response status.

    A parsed price event is verified as an event present in the body. It does not prove the
    API listed every event, so it does not pass the gate (R-10, ED-50). No status maps to
    COVERED_NO_EVENTS_PROVED: that needs a source that proves both window and absence."""
    if body_status == ca.COVERED_WITH_VERIFIED_EVENTS:
        return CA_EVENTS_COMPLETENESS_NOT_PROVED
    return body_status or ca.MISSING_COVERAGE


def _collection_hashes(collection_log):
    """{"raw/<file>": sha256} from the collector's log (ED-39); {} when there is no log."""
    out = {}
    if not collection_log or not os.path.isfile(collection_log):
        return out
    with open(collection_log, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rec = json.loads(line)
                if rec.get("file") and rec.get("sha256"):
                    out[rec["file"]] = rec["sha256"].strip().lower()
    return out


def corporate_action_bodies(coverage_csv, actions_csv, raw_dir, collection_log=None):
    """{symbol: {"status", "from", "to", "file", "parsed", "unparsed", "hash_verified"}} for every
    saved response.

    A coverage row counts only when its file hashes to the recorded SHA-256. A `[]` body is
    not in coverage.csv (ED-39). It is read from raw/ and is hash-verified only against the
    collector's log (review M-2). When a symbol's raw-only files disagree (an empty first
    response and a non-empty retry), the status is CONFLICTING_RESPONSES and nothing passes."""
    counts = {}
    with open(actions_csv, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["action"] not in ca.PRICE_ACTIONS:
                continue
            c = counts.setdefault(os.path.basename(r["source_file"]), [0, 0])
            c[1 if r["action"] == "UNPARSED_PRICE_EVENT" else 0] += 1
    out = {}
    with open(coverage_csv, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            sym = r["symbol"].strip().upper()
            if sym in out:
                # review F2: a second row would overwrite the first (and could hide an unparsed
                # subject); refuse rather than pick one
                raise ValueError("%s: %s has more than one coverage row; one response per symbol is expected"
                                 % (coverage_csv, sym))
            name = os.path.basename(r["source_file"])
            entry = {"from": r["from_date"], "to": r["to_date"], "file": "corporate_actions/" + r["source_file"],
                     "parsed": counts.get(name, [0, 0])[0], "unparsed": counts.get(name, [0, 0])[1],
                     "hash_verified": True}
            if not ca.m.source_verified(coverage_csv, "NSE corporate actions", r["source_file"], r["source_sha256"]):
                entry["status"] = CA_HASH_MISMATCH
                entry["hash_verified"] = False
            else:
                with open(os.path.join(os.path.dirname(os.path.abspath(coverage_csv)), r["source_file"]),
                          encoding="utf-8") as body:
                    text = body.read()
                # review N-3: a price-type entry the parser skipped (unreadable ex-date, non-EQ) is unparsed
                entry["unparsed"] += ca.unreadable_price_entries(text)
                entry["status"] = ca.response_status(text, entry["parsed"], entry["unparsed"])
            out[sym] = entry
    logged = _collection_hashes(collection_log)
    raw_only = {}
    for name in sorted(os.listdir(raw_dir)):
        hit = _CA_FILE.match(name)
        if not hit or hit.group(1).upper() in out:
            continue
        with open(os.path.join(raw_dir, name), encoding="utf-8") as body:
            text = body.read()
        status = (ca.EMPTY_RESPONSE if ca.empty_api_body(text)
                  else ca.MALFORMED_RESPONSE if ca.response_status(text) == ca.MALFORMED_RESPONSE
                  else ca.MISSING_COVERAGE)
        verified = logged.get("raw/" + name) == _sha(os.path.join(raw_dir, name))
        raw_only.setdefault(hit.group(1).upper(), []).append(
            {"status": status, "from": "%s-01-01" % hit.group(2), "to": "%s-12-31" % hit.group(3),
             "file": "corporate_actions/raw/" + name, "parsed": 0, "unparsed": 0, "hash_verified": verified})
    for sym, entries in raw_only.items():
        first = dict(entries[0])
        if len(set(e["status"] for e in entries)) > 1:
            first["status"] = CA_CONFLICTING
        first["hash_verified"] = all(e["hash_verified"] for e in entries)
        first["file"] = "; ".join(e["file"] for e in entries)
        out[sym] = first
    return out


def _ca_value(bodies, symbol, day, completeness=None, renamed=RENAME_NONE):
    """(gate value, response status, evidence, completeness proved).

    The gate passes only when the completeness register (corporate_actions.load_completeness)
    holds a window for the symbol-date AND the saved response is hash-verified with no
    unparsed price subject. With a proved window an empty response is COVERED_NO_EVENTS_PROVED
    and a parsed one is CA_COMPLETENESS_VERIFIED. Without one, nothing passes (D62).

    Never passes (review M-2, M-3): a response whose hash is not verified (coverage.csv or the
    collector's log); and an empty response of a ticker joined to another by a verified
    rename, because NSE files events under the current ticker (ED-39), so the old ticker's
    `[]` says nothing about its events."""
    body = bodies.get(symbol)
    if body is None:
        return (ca.MISSING_COVERAGE, ca.MISSING_COVERAGE,
                "no saved corporate-action response for %s" % symbol, False)
    if not (body["from"] <= day.isoformat() <= body["to"]):
        return (CA_OUTSIDE_WINDOW, CA_OUTSIDE_WINDOW,
                "%s window %s..%s" % (body["file"], body["from"], body["to"]), False)
    status = body["status"]
    if status == ca.EMPTY_RESPONSE and renamed != RENAME_NONE:
        return (CA_EMPTY_RENAMED, CA_EMPTY_RENAMED, "%s; empty response of a renamed ticker (ED-39)" % body["file"],
                False)
    if renamed in (RENAME_OLD, RENAME_AMBIGUOUS) and status in (
            ca.COVERED_WITH_VERIFIED_EVENTS, ca.RESPONSE_PRESENT_COMPLETENESS_NOT_PROVED):
        # review R-1, N-1: events are filed under the current ticker; an old or ambiguous
        # ticker's response never proves anything about its events
        # review O-2: it proves nothing, so it does not earn the exploratory tier either
        return (CA_OLD_TICKER, CA_OLD_TICKER, "%s; response of a renamed-away or ambiguous ticker (ED-39)"
                % body["file"], False)
    if body.get("hash_verified") and ca.completeness_proved(completeness, symbol, day):
        where = "%s; completeness register window" % body["file"]
        if status == ca.EMPTY_RESPONSE:
            return de.CA_COVERED_NONE, status, where, True
        if status in (ca.COVERED_WITH_VERIFIED_EVENTS, ca.RESPONSE_PRESENT_COMPLETENESS_NOT_PROVED):
            return de.CA_COMPLETE, status, where, True
    return ca_gate_value(status), status, body["file"], False


def research_use(row, tier):
    """CERTIFIED_P0_DATA only when every data gate passes. EXPLORATORY_ONLY when every data
    gate except corporate_action passes and the tier is CA_RESPONSE_PRESENT_NOT_COMPLETE (D62).
    Neither is GTF trade eligibility."""
    if row["final_eligibility"] == de.ELIGIBLE:
        return USE_CERTIFIED
    failed = set(part.split("=")[0] for part in row["failed_gates"].split(", ") if part)
    if failed == {"corporate_action"} and tier == ca.CA_RESPONSE_PRESENT_NOT_COMPLETE:
        return USE_EXPLORATORY
    return USE_EXCLUDED


def _excluded_between(cal, a, b):
    """Calendar-excluded sessions strictly between a and b."""
    out = []
    d = a + datetime.timedelta(days=1)
    while d < b:
        try:
            if cal.is_excluded_session(d):
                out.append(d)
        except cal_mod.CalendarError:
            out.append(d)                            # an unclassifiable day is not a clean gap
        d += datetime.timedelta(days=1)
    return out


def price_step(symbol, day, prior_day, rows_today, rows_prior, linked_symbols, price_actions, cal):
    """(value, detail) for the step from prior_day into day. rows_*: {symbol: {series: BhavRow}}.

    The prior EQ row is the same symbol's, or the same ISIN's under one of linked_symbols.
    The builder passes there only the previous ticker of a VERIFIED rename whose effective
    date falls inside this step (instruments.verified_rename_into; D51, REV-1). Nothing else
    is joined."""
    today = (rows_today.get(symbol) or {}).get("EQ")
    if today is None:
        return PX_NO_EQ_ROW, "no EQ row on %s" % day
    prior = (rows_prior.get(symbol) or {}).get("EQ")
    if prior is None:
        for other in linked_symbols:
            cand = (rows_prior.get(other) or {}).get("EQ")
            if other != symbol and cand is not None and cand.isin == today.isin:
                prior = cand
                break
    if prior is None:
        series = sorted((rows_prior.get(symbol) or {}).keys())
        if series:
            return "%s:%s" % (PX_PRIOR_NON_EQ, "+".join(series)), "%s on %s has %s rows only" % (
                symbol, prior_day, "+".join(series))
        return PX_PRIOR_MISSING, "no EQ row for %s on the previous session %s" % (symbol, prior_day)
    detail = "PREVCLOSE %s on %s vs close %s on %s; range %s..%s" % (
        today.prev_close, day, prior.close, prior_day, today.low, today.high)
    # review F3 / D54: a history never runs across a date the calendar cannot classify
    unresolved = _unresolved_between(cal, prior_day, day)
    if unresolved:
        return PX_CALENDAR_UNRESOLVED, "%s; unclassified date %s" % (
            detail, ", ".join(d.isoformat() for d in unresolved))
    # A recorded price-scale event on the step is a discontinuity whatever PREVCLOSE says:
    # NSE prints the unadjusted prior close on the ex-date (55 of 55 recorded 2021-2025
    # events, legacy and UDiFF; ED-50), so an intact chain does not show continuity.
    events = sorted(set(a.action for a in price_actions if prior_day < a.ex_date <= day))
    if events:
        return "%s:%s" % (PX_PRICE_EVENT, "+".join(events)), detail
    if prior.isin != today.isin:
        return PX_ISIN_CHANGE, "%s; ISIN %s -> %s" % (detail, prior.isin, today.isin)
    # review M-5: a step across an excluded session (Muhurat, shortened) fails whether or not
    # PREVCLOSE happens to equal the prior regular close; the session traded and is not a
    # research candle, and no approved rule joins across it (D52 covers unheld sessions only)
    excluded = _excluded_between(cal, prior_day, day)
    if excluded:
        names = ", ".join(d.isoformat() for d in excluded)
        if today.prev_close != prior.close:
            return PX_EXCLUDED_SESSION, "%s; excluded session %s" % (detail, names)
        return PX_ACROSS_EXCLUDED, "%s; excluded session %s inside the step" % (detail, names)
    if today.prev_close != prior.close:
        return PX_UNEXPLAINED, detail
    if scale_gap(prior.close, today.low, today.high):
        return PX_SCALE_GAP, detail
    return de.PRICE_CONTINUOUS, ""


def scale_gap(prior_close, low, high):
    """The one screen definition, corporate_actions.price_scale_gap (review F8, ED-52).

    A screen, not a classifier: it never names an event or a ratio, and a flagged step is
    excluded pending investigation, not called an error. It cannot see a smaller event
    (a rights issue moves the price a few percent); that residual stays with the
    corporate-action gate (ED-50)."""
    return ca.price_scale_gap(prior_close, low, high, SCALE_GAP_BAND)


def _unresolved_between(cal, a, b):
    """Dates strictly between a and b the calendar cannot classify (review F3, D54)."""
    out = []
    d = a + datetime.timedelta(days=1)
    while d < b:
        try:
            cal.is_trading_day(d)
        except cal_mod.CalendarError:
            out.append(d)
        d += datetime.timedelta(days=1)
    return out


def identity_value(records, symbol, day, period_isin, eq_row):
    res = instruments.resolve(records, symbol, day)
    if res["status"] != instruments.RESOLVED:
        return ID_UNKNOWN, res.get("reason") or ""
    if not res.get("verified"):
        return ID_UNVERIFIED_RECORD, "instrument record for %s is not hash-verified" % res["isin"]
    if period_isin and res["isin"] != period_isin:
        return ID_PERIOD_ISIN_MISMATCH, "records %s, membership period %s" % (res["isin"], period_isin)
    if eq_row is not None and eq_row.isin != res["isin"]:
        return ID_BHAVCOPY_ISIN_MISMATCH, "records %s, bhavcopy %s" % (res["isin"], eq_row.isin)
    return de.IDENTITY_RESOLVED, ""


def _sessions(cal, start, end):
    """(official equity sessions start..end, dates the calendar cannot classify)."""
    out, unresolved = [], []
    d = start
    while d <= end:
        try:
            if cal.is_trading_day(d):
                out.append(d)
        except cal_mod.CalendarError:
            unresolved.append(d)
        d += datetime.timedelta(days=1)
    return out, unresolved


def _previous_session(cal, day):
    d = day - datetime.timedelta(days=1)
    for _ in range(30):
        try:
            if cal.is_trading_day(d):
                return d
        except cal_mod.CalendarError:
            return None                              # an unresolved day before the window: no join
        d -= datetime.timedelta(days=1)
    return None


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _rel(path):
    return os.path.relpath(os.path.abspath(path), ROOT)


def _universe_matches_ledger(universe_csv, records_csv):
    """Review L-4: True when the universe file's periods (symbol, ISIN, dates, hash released)
    equal a fresh membership.convert of the review ledger beside it; NOT_CHECKED when the
    ledger inputs are not there (synthetic fixtures)."""
    folder = os.path.dirname(os.path.abspath(universe_csv))
    names = ("nifty100_baseline.csv", "nifty100_changes.csv", "nifty100_count_exceptions.csv",
             "nifty100_review.csv")
    if not all(os.path.isfile(os.path.join(folder, n)) for n in names):
        return "NOT_CHECKED"
    conv = membership.convert(os.path.join(folder, names[0]), os.path.join(folder, names[1]),
                              count_exceptions_path=os.path.join(folder, names[2]),
                              review_path=os.path.join(folder, names[3]),
                              instrument_records=instruments.load(records_csv))
    fresh = {(r["symbol"], r["isin"], r["effective_from"], r["effective_to"], bool(r["source_sha256"]))
             for r in conv.rows}
    with open(universe_csv, newline="", encoding="utf-8") as fh:
        held = {(r["symbol"], r["isin"], r["effective_from"], r["effective_to"], bool(r["source_sha256"]))
                for r in csv.DictReader(fh)}
    return fresh == held


def build(start=WINDOW_START, end=WINDOW_END, universe_csv=None, records_csv=None, coverage_csv=None,
          actions_csv=None, calendar_dir=CALENDAR_DIR, raw_dir=EOD_RAW_DIR, manifest=EOD_MANIFEST,
          completeness_csv=None, decision_log=None):
    """Classify every member-date start..end. Returns {"rows", "history", "summary"}.

    completeness_csv: the corporate-action completeness register; default
    <coverage folder>/completeness.csv. It does not exist today (OD-CA-1)."""
    universe_csv = universe_csv or os.path.join(UNIVERSE_DIR, "nifty100_universe.csv")
    # review N-2, R2-C: the real universe is always checked, however its path was passed
    default_universe = (os.path.realpath(universe_csv)       # realpath: a symlink is still the real file
                        == os.path.realpath(os.path.join(UNIVERSE_DIR, "nifty100_universe.csv")))
    records_csv = records_csv or os.path.join(UNIVERSE_DIR, "instrument_records.csv")
    coverage_csv = coverage_csv or os.path.join(CA_DIR, "coverage.csv")
    actions_csv = actions_csv or os.path.join(CA_DIR, "actions.csv")
    completeness_csv = completeness_csv or os.path.join(os.path.dirname(coverage_csv), "completeness.csv")
    decision_log = decision_log or os.path.join(ROOT, "nse", "docs", "DECISION_LOG.md")
    raw_ca_dir = os.path.join(os.path.dirname(coverage_csv), "raw")
    api_hashes = frozenset(_sha(os.path.join(raw_ca_dir, n)) for n in sorted(os.listdir(raw_ca_dir)))
    completeness = ca.load_completeness(completeness_csv, ca.completeness_decisions(decision_log), api_hashes)
    cal = cal_mod.NseCalendar.load(calendar_dir)
    ledger_check = _universe_matches_ledger(universe_csv, records_csv)
    if default_universe and ledger_check != True:      # review N-2: the real build never skips it
        raise ValueError("the review ledger beside %s is incomplete; the universe cannot be checked" % universe_csv)
    if ledger_check is False:
        raise ValueError("%s does not match a fresh conversion of the review ledger; re-run membership.convert"
                         % universe_csv)
    u = univ.load(universe_csv)
    records = instruments.load(records_csv)
    collection_log = os.path.join(os.path.dirname(coverage_csv), "collection_log.jsonl")
    bodies = corporate_action_bodies(coverage_csv, actions_csv, os.path.join(os.path.dirname(coverage_csv), "raw"),
                                     collection_log)
    actions_by_symbol = {}
    for a in ca.load(actions_csv):
        if a.action in ca.PRICE_ACTIONS:
            actions_by_symbol.setdefault(a.symbol, []).append(a)

    sessions, unresolved = _sessions(cal, start, end)
    first_prior = _previous_session(cal, sessions[0]) if sessions else None
    load_from = first_prior or start
    symbols = set(r.symbol for r in u.rows)
    # REV-1: tickers are linked only through VERIFIED, dated SYMBOL_CHANGE records
    linked = {s: set(instruments.verified_rename_names(records, s)) for s in symbols}
    renames = {s: rename_state(records, s) for s in symbols}
    wanted = set().union(*linked.values()) if linked else set()

    paths = []
    for p in bhavcopy.archive_paths(raw_dir):
        d, _ = bhavcopy.name_info(os.path.basename(p))
        if load_from <= d <= end:
            paths.append(p)
    files = bhavcopy.load_many(paths, manifest, keep=lambda r: r.symbol in wanted)
    by_date = {}
    for f in files:
        rows = {}
        for r in f.rows:
            rows.setdefault(r.symbol, {})[r.series] = r
        by_date[f.trade_date] = {"rows": rows, "file": f.source.file_name}
    session_set = set(sessions) | ({first_prior} if first_prior else set())
    held_off_session = sorted(d.isoformat() for d in by_date if d not in session_set)

    out = []
    prior_day = first_prior
    unresolved_set = set(unresolved)
    expected_member_dates = 0
    # review F3: a member-date on a date the calendar cannot classify gets a row (calendar
    # UNRESOLVED) rather than vanishing; it never becomes the prior session of a later step
    for day in sorted(set(sessions) | unresolved_set):
        held = by_date.get(day)
        prior = by_date.get(prior_day) if prior_day else None
        expected_member_dates += len(u.members(day))
        for mem in u.members(day):
            sym = mem.symbol
            rows_today = held["rows"] if held else {}
            eq = (rows_today.get(sym) or {}).get("EQ")
            gates, ev = {}, []
            gates["membership"] = de.MEMBERSHIP_VERIFIED if mem.verified else MEMBERSHIP_UNVERIFIED
            if not mem.verified:
                ev.append("membership: period from %s in nifty100_universe.csv has no verified source hash"
                          % mem.effective_from)
            gates["identity"], why = identity_value(records, sym, day, mem.isin, eq)
            if why:
                ev.append("identity: " + why)
            state = renames.get(sym, RENAME_NONE)
            gates["corporate_action"], body_status, where, proved = _ca_value(bodies, sym, day, completeness, state)
            ev.append("corporate_action: " + where)
            gates["calendar"] = CAL_UNRESOLVED if day in unresolved_set else de.CALENDAR_TRADING_DAY
            if held is None:
                gates["eod"] = EOD_NO_FILE
            elif eq is not None:
                gates["eod"] = de.EOD_ACCEPTED
            elif rows_today.get(sym):
                gates["eod"] = "%s:%s" % (EOD_NON_EQ_ONLY, "+".join(sorted(rows_today[sym])))
            else:
                gates["eod"] = EOD_NO_EQ_ROW
            if held is not None and gates["eod"] != de.EOD_ACCEPTED:
                ev.append("eod: %s" % held["file"])
            if state == RENAME_AMBIGUOUS:
                gates["price_continuity"], why = PX_AMBIGUOUS_RENAME, "rename records under two ISINs (N-1)"
            elif prior is None:
                gates["price_continuity"], why = PX_PRIOR_MISSING, "previous session %s not held" % prior_day
            else:
                # NSE files an event under the instrument's current symbol (ED-39), so the
                # events of every ticker joined by a verified rename are read. The prior row
                # may sit under another ticker only on the step of that verified rename.
                names = sorted(linked.get(sym, {sym}))
                rename = instruments.verified_rename_into(records, sym, prior_day, day)
                if rename is not None and rename.isin != mem.isin:
                    rename = None                    # review L-1: the record's ISIN must be the period's
                gates["price_continuity"], why = price_step(
                    sym, day, prior_day, rows_today, prior["rows"], [rename.symbol] if rename else [],
                    [a for n in names for a in actions_by_symbol.get(n, ())], cal)
            if why:
                ev.append("price_continuity: " + why)
            row = de.classify_symbol_date(sym, day.isoformat(), mem.isin, gates, "; ".join(ev),
                                          required_gates=de.DATA_GATES)
            integrity = gates["eod"] == de.EOD_ACCEPTED and gates["price_continuity"] == de.PRICE_CONTINUOUS
            row["ca_tier"] = ca.evidence_tier(body_status, integrity, proved)
            row["research_use"] = research_use(row, row["ca_tier"])
            # the B7 limitation stays unless the completeness register proved the window (D62)
            row["limitations"] = ca.CA_UNVERIFIED if row["ca_tier"] != ca.CA_COMPLETENESS_VERIFIED else ""
            row["period_from"] = mem.effective_from.isoformat()      # review F1: the period id
            out.append(row)
        if day not in unresolved_set:
            prior_day = day

    history = _history(universe_csv, u, records)
    inputs = {_rel(p): _sha(p) for p in (universe_csv,
                                          os.path.join(os.path.dirname(universe_csv), "nifty100_review.csv"),
                                          records_csv, coverage_csv, actions_csv, completeness_csv,
                                          collection_log, decision_log, manifest,
                                          os.path.join(calendar_dir, "events.csv"),
                                          os.path.join(calendar_dir, "sources.csv"))
              if os.path.isfile(p)}
    # review F7: every saved response (in coverage.csv or not) and this builder's own code
    raw_ca = os.path.join(os.path.dirname(coverage_csv), "raw")
    digest = hashlib.sha256()
    for name in sorted(os.listdir(raw_ca)):
        digest.update(("%s %s\n" % (name, _sha(os.path.join(raw_ca, name)))).encode())
    inputs[_rel(raw_ca) + "/* (name+sha256 list)"] = digest.hexdigest()
    # review L-3: the code that decides the outputs is part of the fingerprint
    for mod in (__file__, ca.__file__, instruments.__file__, de.__file__, univ.__file__, membership.__file__,
                bhavcopy.__file__, cal_mod.__file__):
        inputs[_rel(os.path.abspath(mod))] = _sha(os.path.abspath(mod))
    summary = _summary(out, sessions, unresolved, held_off_session, history, bodies, inputs, start, end,
                       expected_member_dates)
    # the auditable rename policy: every SYMBOL_CHANGE record touching a universe ticker
    summary["rename_links"] = [x for x in instruments.rename_links(records)
                               if x["previous_symbol"] in wanted or x["new_symbol"] in wanted]
    summary["universe_matches_ledger_conversion"] = ledger_check
    summary["completeness_register"] = {
        "path": _rel(completeness_csv), "present": os.path.isfile(completeness_csv),
        "proved_windows": sum(len(v) for v in completeness.values()),
        "note": ("a window needs two hash-verified independent official sources that are not saved API "
                 "responses, event-by-event reconciliation, and a USER_APPROVED decision whose entry has a "
                 "'Completeness window accepted' line naming both source hashes and the reconciliation "
                 "hash (D66 / OD-CA-1)")}
    return {"rows": out, "history": history, "summary": summary}


def _history(universe_csv, u, records):
    with open(universe_csv, newline="", encoding="utf-8") as fh:
        raw = list(csv.DictReader(fh))
    out = []
    for r, mem in zip(raw, u.rows):
        res = instruments.resolve(records, mem.symbol, mem.effective_from)
        ident = res["status"] if res["status"] != instruments.RESOLVED else (
            de.IDENTITY_RESOLVED if res.get("verified") and res["isin"] == mem.isin else ID_PERIOD_ISIN_MISMATCH)
        out.append({"symbol": r["symbol"], "series": r["series"], "isin": r["isin"],
                    "effective_from": r["effective_from"], "effective_to": r["effective_to"],
                    "membership_status": de.MEMBERSHIP_VERIFIED if mem.verified else MEMBERSHIP_UNVERIFIED,
                    "identity_at_start": ident, "source": r["source"], "source_file": r["source_file"],
                    "source_sha256": r["source_sha256"], "notes": r["notes"]})
    return out


def _run_key(r):
    # review F1/F7: the membership period, the evidence tier and the research use are part of
    # the key, so each register row cites one period and its columns hold for every date in it
    return (r["isin"], r.get("period_from", ""), r["final_eligibility"], r["failed_gates"],
            r.get("ca_tier", ""), r.get("research_use", ""))


def register(rows):
    """One row per maximal run of a symbol's excluded member-dates on consecutive sessions
    of the whole window (not of the symbol's own member-dates: review F1) with identical
    gates, period, tier and research use."""
    by_symbol = {}
    for r in rows:
        if r["final_eligibility"] != de.ELIGIBLE:
            by_symbol.setdefault(r["symbol"], []).append(r)
    index = {d: i for i, d in enumerate(sorted(set(r["trade_date"] for r in rows)))}
    out = []
    for sym in sorted(by_symbol):
        run = None
        for r in by_symbol[sym]:
            key = _run_key(r)
            if run and run["key"] == key and index[r["trade_date"]] == run["last"] + 1:
                run["to"], run["last"], run["n"] = r["trade_date"], index[r["trade_date"]], run["n"] + 1
                if r["gate_results"]["price_continuity"] != de.PRICE_CONTINUOUS and len(run["ev"]) < 3:
                    run["ev"].append(r["evidence"])
                continue
            if run:
                out.append(_register_row(sym, run))
            run = {"key": key, "from": r["trade_date"], "to": r["trade_date"], "last": index[r["trade_date"]],
                   "n": 1, "row": r, "ev": [r["evidence"]]}
        if run:
            out.append(_register_row(sym, run))
    return out


def _register_row(sym, run):
    r = run["row"]
    blocking = r["blocking_gate"]
    return {"symbol": sym, "isin": r["isin"], "membership_period_from": r.get("period_from", ""),
            "from_date": run["from"], "to_date": run["to"], "sessions": run["n"],
            "final_eligibility": r["final_eligibility"], "blocking_gate": blocking, "failed_gates": r["failed_gates"],
            "corporate_action_evidence_tier": r.get("ca_tier", ""), "research_use": r.get("research_use", ""),
            "limitations": r.get("limitations", ""),
            "reason": "blocked at %s (%s)" % (blocking, r["gate_results"][blocking]),
            "evidence": " | ".join(run["ev"]) + (" | ..." if run["n"] > len(run["ev"]) else "")}


def register_covers_exactly_once(rows, reg):
    """Review F5: every excluded symbol-date lies in exactly one register row, and every
    register row's dates are excluded dates of that symbol with the row's key."""
    days = sorted(set(r["trade_date"] for r in rows))
    pos = {d: i for i, d in enumerate(days)}
    excluded = {(r["symbol"], r["trade_date"]): _run_key(r) for r in rows if r["final_eligibility"] != de.ELIGIBLE}
    seen = set()
    for x in reg:
        span = days[pos[x["from_date"]]:pos[x["to_date"]] + 1]
        if len(span) != x["sessions"]:
            return False
        for d in span:
            k = (x["symbol"], d)
            if k not in excluded or k in seen:
                return False
            seen.add(k)
    return seen == set(excluded)


def _summary(rows, sessions, unresolved, held_off_session, history, bodies, inputs, start, end,
             expected_member_dates=None):
    final, any_fail, only_fail, values = {}, {}, {}, {}
    data_pass = 0
    labels = {}
    by_date = {}
    for r in rows:
        final[r["final_eligibility"]] = final.get(r["final_eligibility"], 0) + 1
        named = set(part.split("=")[0] for part in r["failed_gates"].split(", ") if part)
        failed = [g for g in GATE_ORDER if g in named]
        for g in failed:
            any_fail[g] = any_fail.get(g, 0) + 1
        if len(failed) == 1:
            only_fail[failed[0]] = only_fail.get(failed[0], 0) + 1
        if not [g for g in failed if g in DATA_GATES]:
            data_pass += 1
        for g in GATE_ORDER:
            v = values.setdefault(g, {})
            key = r["gate_results"][g].split(":")[0]
            v[key] = v.get(key, 0) + 1
        by_date.setdefault(r["trade_date"], []).append(r)
    full_dates = 0
    for day, rs in by_date.items():
        res = de.certify_members([{"symbol": x["symbol"], "trade_date": x["trade_date"], "isin": x["isin"],
                                   "gates": x["gate_results"]} for x in rs], index_evidence_resolved=False,
                                 required_gates=de.DATA_GATES)
        labels[res["label"]] = labels.get(res["label"], 0) + 1
        full_dates += 1 if res["full_index_certified"] else 0
    reg = register(rows)
    eligible = final.get(de.ELIGIBLE, 0)
    non_eq = {}
    for r in rows:
        v = r["gate_results"]["eod"]
        if v.startswith(EOD_NON_EQ_ONLY):
            non_eq.setdefault(r["symbol"], {}).setdefault(v.split(":")[1], []).append(r["trade_date"])
    tiers, uses = {}, {}
    for r in rows:
        tiers[r["ca_tier"]] = tiers.get(r["ca_tier"], 0) + 1
        uses[r["research_use"]] = uses.get(r["research_use"], 0) + 1
    return {
        "build_version": BUILD_VERSION,
        "certification_scope": SCOPE,
        "data_gates": list(DATA_GATES),
        "gtf_trade_eligibility": GTF_NOT_EVALUATED,
        "note": ("P0 data certification only (D63). A certified symbol-date is not GTF trade eligibility. "
                 "EXPLORATORY_ONLY_NOT_CERTIFIED rows are outside the certified universe and keep "
                 "CORPORATE_ACTIONS_UNVERIFIED (D62)."),
        "corporate_action_evidence_tier": dict(sorted(tiers.items())),
        "research_use": dict(sorted(uses.items())),
        "window": [start.isoformat(), end.isoformat()],
        "inputs_sha256": dict(sorted(inputs.items())),
        "sessions": len(sessions),
        "calendar_unresolved_dates_in_window": [d.isoformat() for d in unresolved],
        "archives_held_on_non_sessions": held_off_session,
        "member_dates": len(rows),
        "certified_symbol_dates": eligible,
        "excluded_symbol_dates": len(rows) - eligible,
        "symbols": len(set(r["symbol"] for r in rows)),
        "by_final_eligibility": dict(sorted(final.items())),
        "rows_failing_gate": dict(sorted(any_fail.items())),
        "rows_failing_only_this_gate": dict(sorted(only_fail.items())),
        "rows_passing_every_data_gate": data_pass,
        "gate_values": {g: dict(sorted(v.items())) for g, v in sorted(values.items())},
        "label_by_date": dict(sorted(labels.items())),
        "full_index_certified_dates": full_dates,
        "membership_periods": len(history),
        "membership_periods_verified": sum(1 for h in history if h["membership_status"] == de.MEMBERSHIP_VERIFIED),
        "corporate_action_responses": {k: sum(1 for b in bodies.values() if b["status"] == k)
                                       for k in sorted(set(b["status"] for b in bodies.values()))},
        "non_eq_member_stretches": {s: {series: {"sessions": len(ds), "first": ds[0], "last": ds[-1]}
                                        for series, ds in sorted(v.items())} for s, v in sorted(non_eq.items())},
        "register_rows": len(reg),
        "reconciliation": {
            # review F5: counted independently from Universe.members on every evaluated day
            "member_dates_equal_universe_member_count": expected_member_dates == len(rows),
            "certified_plus_excluded_equal_rows": sum(final.values()) == len(rows)
                                                   and sum(uses.values()) == len(rows),
            "register_sessions_equal_excluded": sum(x["sessions"] for x in reg) == len(rows) - eligible,
            "register_covers_each_excluded_date_once": register_covers_exactly_once(rows, reg),
            "one_row_per_symbol_date": len(set((r["symbol"], r["trade_date"]) for r in rows)) == len(rows),
            "no_order_authorised": not any(r["authorises_order"] for r in rows),
        },
        "authorises_order": False,
    }


def _write(path, columns, rows):
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(columns), lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return path


def write_outputs(result, out_dir, matrix_path=None):
    rows = result["rows"]

    def common(r):
        return dict({g + "_gate": r["gate_results"][g] for g in GATE_ORDER}, symbol=r["symbol"],
                    trade_date=r["trade_date"], isin=r["isin"], final_eligibility=r["final_eligibility"],
                    corporate_action_evidence_tier=r["ca_tier"], limitations=r["limitations"],
                    gtf_trade_eligibility=GTF_NOT_EVALUATED)
    eligible = [dict(common(r), certification_scope=SCOPE, authorises_order="false")
                for r in rows if r["final_eligibility"] == de.ELIGIBLE]
    paths = {
        "certified": _write(os.path.join(out_dir, "P0_CERTIFIED_RESEARCH_UNIVERSE.csv"), CERTIFIED_COLUMNS, eligible),
        "register": _write(os.path.join(out_dir, "P0_RESEARCH_EXCLUSION_REGISTER.csv"), REGISTER_COLUMNS,
                           register(rows)),
        "history": _write(os.path.join(out_dir, "P0_MEMBERSHIP_REFERENCE_HISTORY.csv"), HISTORY_COLUMNS,
                          result["history"]),
    }
    summary_path = os.path.join(out_dir, "P0_CERTIFICATION_SUMMARY.json")
    with open(summary_path, "w", encoding="utf-8") as fh:
        json.dump(result["summary"], fh, indent=1, sort_keys=True)
        fh.write("\n")
    paths["summary"] = summary_path
    if matrix_path:
        paths["matrix"] = _write(matrix_path, MATRIX_COLUMNS, [
            dict(common(r), research_use=r["research_use"], blocking_gate=r["blocking_gate"],
                 failed_gates=r["failed_gates"], evidence=r["evidence"])
            for r in rows])
    return paths


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python3 -m nse.research.p0_certification", description=__doc__.split("\n")[0])
    ap.add_argument("--start", default=WINDOW_START.isoformat())
    ap.add_argument("--end", default=WINDOW_END.isoformat())
    ap.add_argument("--out-dir", required=True, help="folder for the certified file, register, history and summary")
    ap.add_argument("--matrix", help="also write the per-symbol-date matrix here (large; keep out of git)")
    a = ap.parse_args(argv)
    result = build(datetime.date.fromisoformat(a.start), datetime.date.fromisoformat(a.end))
    paths = write_outputs(result, a.out_dir, a.matrix)
    s = result["summary"]
    print(json.dumps({"member_dates": s["member_dates"], "certified_symbol_dates": s["certified_symbol_dates"],
                      "excluded_symbol_dates": s["excluded_symbol_dates"], "label_by_date": s["label_by_date"],
                      "reconciliation": s["reconciliation"], "written": {k: _rel(v) for k, v in paths.items()}},
                     indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
