"""Scenario laboratory: data-driven expectations run through the REAL scanner.

A scenario (nse/scenarios/*.json) names candle data, an as-of time, a trade type, a
calendar and the outcome the rules require, with rule references and an explanation of
why. run_scenario loads the data (marketdata.from_csv or from_bhavcopy), calls
scanner.scan, and compares. Nothing here decides a gate, a freshness or an eligibility:
every actual value is read from the ScanResult. overlay_zone_states additionally reads
the zone states of mtf_freshness.replay called exactly as the scanner calls it (an
observation of the same overlay, needed to tell TESTED from INVALIDATED for zones the
engine already dropped).

Data kinds (README.md):
  SYNTHETIC        invented candles in nse/scenarios/data/, each listed with its sha256 in
                   data/MANIFEST.json (written by nse/scenarios/generate.py); software
                   regression evidence only, never external validation
  HISTORICAL_REAL  local legacy bhavcopies named by repository path and sha256; absent or
                   different files make the scenario UNAVAILABLE, never PASS (D31: nothing
                   is downloaded)
  OWNER_CHART      a CSV the product owner transcribed from a chart (templates/); none is
                   shipped, none is invented
Calendars: WEEKDAYS_SYNTHETIC (every weekday trades; only for SYNTHETIC data), NSE
(nse/data/calendar; UNAVAILABLE if it does not load), NONE (CALENDAR_UNVALIDATED, D28).

Results: PASS (every assertion held), FAIL (an assertion did not), UNAVAILABLE (inputs
absent; reported, not a pass), INVALID (schema or provenance error). The report is a pure
function of the library and the caller's generated_at: no clock is read.
"""

import csv
import datetime
import hashlib
import io
import json
import os
import re
from dataclasses import asdict, dataclass, field
from typing import List, Optional

from nse.research import marketdata, models as m, scanner
from nse.research.deps import CALENDAR_DIR, ROOT, bhavcopy, calendar as cal_mod, mtf

DEFAULT_LIBRARY = os.path.join(ROOT, "nse", "scenarios")
DEFAULT_OUT = os.path.join(ROOT, "nse", "output", "scenarios")
DATA_MANIFEST = os.path.join("data", "MANIFEST.json")

PASS, FAIL, UNAVAILABLE, INVALID = "PASS", "FAIL", "UNAVAILABLE", "INVALID"
RESULTS = (PASS, FAIL, UNAVAILABLE, INVALID)
SYNTHETIC, HISTORICAL_REAL, OWNER_CHART = "SYNTHETIC", "HISTORICAL_REAL", "OWNER_CHART"
DATA_KINDS = (SYNTHETIC, HISTORICAL_REAL, OWNER_CHART)
CAL_WEEKDAYS, CAL_NSE, CAL_NONE = "WEEKDAYS_SYNTHETIC", "NSE", "NONE"
CALENDARS = (CAL_WEEKDAYS, CAL_NSE, CAL_NONE)

REQUIRED = ("id", "title", "description", "rule_refs", "data_kind", "data", "as_of", "trade_type", "calendar",
            "risk_per_trade", "expected", "explanation")
OPTIONAL = ("source_note",)                 # required for HISTORICAL_REAL and OWNER_CHART
EXPECTED_KEYS = ("symbol", "symbol_status", "symbol_reason_contains", "candidate_count", "candidates",
                 "fresh_zone_count", "fresh_zone_ids_absent", "fresh_zones_absent", "fresh_zones_present",
                 "blocked_zone_overlay_status", "overlay_zone_states", "same_decisions_as")
CANDIDATE_KEYS = ("match", "status", "gates", "manual_review_contains")
CANDIDATE_MATCH = ("zone_id", "created_time", "proximal", "distal", "pattern")
FRESH_MATCH = ("tf", "zone_id", "side", "pattern", "proximal", "distal", "created_time")
BLOCKED_MATCH = ("tf", "zone_id")
OVERLAY_MATCH = ("tf", "zone_id", "side", "pattern", "proximal", "distal")
BHAV_KEYS = ("bhavcopy", "series", "manifest")
SYMBOL_STATUSES = (scanner.SYMBOL_EVALUATED, scanner.SYMBOL_NO_EXECUTION_ZONE, scanner.SYMBOL_DATA_INSUFFICIENT,
                   scanner.SYMBOL_BLOCKED, scanner.SYMBOL_NOT_IN_UNIVERSE)
OVERLAY_STATUSES = (mtf.FRESH, mtf.TESTED, mtf.BASE_CLOSE_BEYOND_DL_PENDING, mtf.INVALIDATED,
                    mtf.UNKNOWN_DATA_GAP, mtf.UNVERIFIED_SESSION, mtf.MANUAL_REVIEW)
ID_RE = re.compile(r"^[a-z0-9][a-z0-9_]*$")
SYMBOL_RE = re.compile(r"^[A-Z0-9][A-Z0-9&_-]*$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
# Rulebook / Pine lines, approved R1-R6, DECISION_LOG IDs, D41 readings, spec sections, audit items
RULE_REF_RE = re.compile(r"^(?:(?:RB|PS) \d+(?:-\d+)?|R[1-6]|D\d+|P-[A-Z0-9]+-\d+|spec \d+(?:\.\d+)*(?: G\d)?"
                         r"|audit [A-Z]\d+[a-z]?)$")
NOTE = ("A SYNTHETIC scenario is software regression evidence on invented prices: it is not market data, "
        "not TradingView parity and not external validation. UNAVAILABLE is never a pass. No status approves a trade.")


class WeekdayCalendar(object):
    """WEEKDAYS_SYNTHETIC: every weekday trades. For invented data only; not an NSE calendar."""

    def is_trading_day(self, d):
        return d.weekday() < 5


class Unavailable(Exception):
    """Inputs the scenario needs are not present (never a pass)."""


class Invalid(Exception):
    """The scenario or its data provenance is malformed."""


@dataclass
class Entry:
    path: str
    scenario: Optional[dict]
    errors: List[str] = field(default_factory=list)


# --- loading and validation -------------------------------------------------------------

def _no_duplicates(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError("duplicate key %r" % k)
        out[k] = v
    return out


def load_file(path):
    try:
        with open(path, encoding="utf-8") as fh:
            s = json.load(fh, object_pairs_hook=_no_duplicates)
    except (OSError, ValueError) as e:
        return Entry(path, None, ["cannot read %s: %s" % (os.path.basename(path), e)])
    errors = validate(s)
    stem = os.path.splitext(os.path.basename(path))[0]
    if isinstance(s, dict) and s.get("id") != stem:
        errors.append("id %r must equal the file name %r" % (s.get("id"), stem))
    return Entry(path, s, errors)


def load_library(folder):
    """Every *.json directly in folder (templates/ and data/ are not scenarios), sorted."""
    if not os.path.isdir(folder):
        raise OSError("scenario library %s is not a folder" % folder)
    entries = [load_file(os.path.join(folder, n)) for n in sorted(os.listdir(folder)) if n.endswith(".json")]
    seen = {}
    for e in entries:
        sid = e.scenario.get("id") if isinstance(e.scenario, dict) else None
        if sid in seen:
            e.errors.append("duplicate id %r (also %s)" % (sid, os.path.basename(seen[sid])))
        seen.setdefault(sid, e.path)
    return entries


def _keys(obj, allowed, where, required=()):
    errs = []
    if not isinstance(obj, dict):
        return ["%s must be an object" % where]
    for k in sorted(obj):
        if k not in allowed:
            errs.append("%s: unknown key %r" % (where, k))
    for k in required:
        if k not in obj:
            errs.append("%s: missing key %r" % (where, k))
    return errs


def _text(v):
    return isinstance(v, str) and v.strip() != ""


def _number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _rel_path(p):
    return _text(p) and not os.path.isabs(p) and ".." not in p.replace("\\", "/").split("/")


def _match_errors(match, allowed, where):
    errs = _keys(match, allowed, where)
    if not errs and not match:
        errs.append("%s: needs at least one criterion" % where)
    if isinstance(match, dict):
        for k in ("proximal", "distal"):
            if k in match and not _number(match[k]):
                errs.append("%s.%s must be a number" % (where, k))
        for k in ("tf", "zone_id", "created_time", "pattern", "side"):
            if k in match and not _text(match[k]):
                errs.append("%s.%s must be text" % (where, k))
    return errs


def _list_of(v, where, check):
    if not isinstance(v, list):
        return ["%s must be a list" % where]
    errs = []
    for i, x in enumerate(v):
        errs += check(x, "%s[%d]" % (where, i))
    return errs


def parse_as_of(text):
    """A date (the 15:30 close of that day) or an ISO datetime, as the scan CLI reads it."""
    if "T" in text or " " in text:
        return datetime.datetime.fromisoformat(text)
    return datetime.datetime.combine(datetime.date.fromisoformat(text), mtf.SESSION_CLOSE)


def _expected_errors(e, symbols):
    errs = _keys(e, EXPECTED_KEYS, "expected", required=("symbol_status",))
    if not isinstance(e, dict):
        return errs
    if "symbol" in e and e["symbol"] not in symbols:
        errs.append("expected.symbol %r is not in data" % e["symbol"])
    if "symbol" not in e and len(symbols) != 1:
        errs.append("expected.symbol is required when data has more than one symbol")
    if "symbol_status" in e and e["symbol_status"] not in SYMBOL_STATUSES:
        errs.append("expected.symbol_status must be one of %s" % ", ".join(SYMBOL_STATUSES))
    for k in ("candidate_count", "fresh_zone_count"):
        if k in e and (not isinstance(e[k], int) or isinstance(e[k], bool) or e[k] < 0):
            errs.append("expected.%s must be a whole number >= 0" % k)
    for k in ("symbol_reason_contains", "fresh_zone_ids_absent"):
        if k in e:
            errs += _list_of(e[k], "expected." + k, lambda x, w: [] if _text(x) else ["%s must be text" % w])

    def cand(c, w):
        out = _keys(c, CANDIDATE_KEYS, w, required=("match",))
        if not isinstance(c, dict):
            return out
        if "match" in c:
            out += _match_errors(c["match"], CANDIDATE_MATCH, w + ".match")
        if "status" in c and c["status"] not in m.STATUS_ORDER:
            out.append("%s.status must be one of %s" % (w, ", ".join(m.STATUS_ORDER)))
        if "gates" in c:
            g = c["gates"]
            if not isinstance(g, dict) or not g:
                out.append("%s.gates must be a non-empty object" % w)
            else:
                for k in sorted(g):
                    if k not in m.GATES:
                        out.append("%s.gates: unknown gate %r" % (w, k))
                    elif g[k] not in m.OUTCOMES:
                        out.append("%s.gates.%s must be one of %s" % (w, k, ", ".join(m.OUTCOMES)))
        if "manual_review_contains" in c:
            out += _list_of(c["manual_review_contains"], w + ".manual_review_contains",
                            lambda x, ww: [] if _text(x) else ["%s must be text" % ww])
        if "status" not in c and "gates" not in c and "manual_review_contains" not in c:
            out.append("%s: needs status, gates or manual_review_contains" % w)
        return out

    if "candidates" in e:
        errs += _list_of(e["candidates"], "expected.candidates", cand)

    def fresh_absent(x, w):
        return _match_errors(x, FRESH_MATCH, w)

    def fresh_present(x, w):
        out = _keys(x, ("match", "zone_level_contains"), w, required=("match",))
        if isinstance(x, dict):
            if "match" in x:
                out += _match_errors(x["match"], FRESH_MATCH, w + ".match")
            if "zone_level_contains" in x and not _text(x["zone_level_contains"]):
                out.append("%s.zone_level_contains must be text" % w)
        return out

    def state(allowed, extra):
        def check(x, w):
            out = _keys(x, ("match", "overlay_status") + extra, w, required=("match", "overlay_status"))
            if isinstance(x, dict):
                if "match" in x:
                    out += _match_errors(x["match"], allowed, w + ".match")
                if "overlay_status" in x and x["overlay_status"] not in OVERLAY_STATUSES:
                    out.append("%s.overlay_status must be one of %s" % (w, ", ".join(OVERLAY_STATUSES)))
                for k in extra:
                    if k in x and not _text(x[k]):
                        out.append("%s.%s must be text" % (w, k))
            return out
        return check

    if "fresh_zones_absent" in e:
        errs += _list_of(e["fresh_zones_absent"], "expected.fresh_zones_absent", fresh_absent)
    if "fresh_zones_present" in e:
        errs += _list_of(e["fresh_zones_present"], "expected.fresh_zones_present", fresh_present)
    if "blocked_zone_overlay_status" in e:
        errs += _list_of(e["blocked_zone_overlay_status"], "expected.blocked_zone_overlay_status",
                         state(BLOCKED_MATCH, ("disposition",)))
    if "overlay_zone_states" in e:
        errs += _list_of(e["overlay_zone_states"], "expected.overlay_zone_states", state(OVERLAY_MATCH, ()))
    if "same_decisions_as" in e and not (_text(e["same_decisions_as"]) and ID_RE.match(e["same_decisions_as"])):
        errs.append("expected.same_decisions_as must be a scenario id")
    return errs


def validate(s):
    """Schema errors of one scenario (empty list: valid). Unknown keys are rejected."""
    errs = _keys(s, REQUIRED + OPTIONAL, "scenario", required=REQUIRED)
    if not isinstance(s, dict):
        return errs
    if "id" in s and not (isinstance(s["id"], str) and ID_RE.match(s["id"])):
        errs.append("id must match %s" % ID_RE.pattern)
    for k in ("title", "description", "explanation"):
        if k in s and not _text(s[k]):
            errs.append("%s must be non-empty text" % k)
    if "rule_refs" in s:
        refs = s["rule_refs"]
        if not isinstance(refs, list) or not refs:
            errs.append("rule_refs must be a non-empty list")
        else:
            for r in refs:
                if not isinstance(r, str) or not RULE_REF_RE.match(r):
                    errs.append("rule_refs: %r is not a reference like 'RB 1896', 'R5', 'D3', 'spec 8 G0'" % (r,))
    kind = s.get("data_kind")
    if "data_kind" in s and kind not in DATA_KINDS:
        errs.append("data_kind must be one of %s" % ", ".join(DATA_KINDS))
    if kind in (HISTORICAL_REAL, OWNER_CHART) and not _text(s.get("source_note")):
        errs.append("source_note is required for %s (where the data came from)" % kind)
    if "source_note" in s and not _text(s["source_note"]):
        errs.append("source_note must be non-empty text")
    symbols = []
    if "data" in s:
        d = s["data"]
        if not isinstance(d, dict) or not d:
            errs.append("data must be a non-empty object: symbol -> source")
        else:
            symbols = sorted(d)
            for sym in symbols:
                if not SYMBOL_RE.match(sym):
                    errs.append("data: symbol %r must be upper case" % sym)
                v = d[sym]
                if kind in (SYNTHETIC, OWNER_CHART):
                    if not (_rel_path(v) and v.endswith(".csv")):
                        errs.append("data.%s must be a .csv path relative to the library folder" % sym)
                elif kind == HISTORICAL_REAL:
                    w = "data.%s" % sym
                    errs += _keys(v, BHAV_KEYS, w, required=("bhavcopy",))
                    if isinstance(v, dict):
                        if not isinstance(v.get("bhavcopy"), list) or not v.get("bhavcopy"):
                            errs.append("%s.bhavcopy must be a non-empty list" % w)
                        else:
                            for i, f in enumerate(v["bhavcopy"]):
                                ww = "%s.bhavcopy[%d]" % (w, i)
                                errs += _keys(f, ("path", "sha256"), ww, required=("path", "sha256"))
                                if isinstance(f, dict):
                                    if "path" in f and not _rel_path(f["path"]):
                                        errs.append("%s.path must be relative to the repository root" % ww)
                                    if "sha256" in f and not (isinstance(f["sha256"], str) and SHA_RE.match(f["sha256"])):
                                        errs.append("%s.sha256 must be 64 lower-case hex digits" % ww)
                        if "series" in v and not _text(v["series"]):
                            errs.append("%s.series must be text" % w)
                        if "manifest" in v and v["manifest"] is not None and not _rel_path(v["manifest"]):
                            errs.append("%s.manifest must be a repository path or null" % w)
    if "as_of" in s:
        try:
            if not isinstance(s["as_of"], str):
                raise ValueError("not text")
            parse_as_of(s["as_of"])
        except ValueError as e:
            errs.append("as_of %r: %s" % (s["as_of"], e))
    if "trade_type" in s and s["trade_type"] not in m.TRADE_TYPES:
        errs.append("trade_type must be one of %s" % ", ".join(m.TRADE_TYPES))
    if "calendar" in s:
        if s["calendar"] not in CALENDARS:
            errs.append("calendar must be one of %s" % ", ".join(CALENDARS))
        elif s["calendar"] == CAL_WEEKDAYS and kind != SYNTHETIC:
            errs.append("calendar WEEKDAYS_SYNTHETIC is for SYNTHETIC data only (D28: no weekday fallback)")
    if "risk_per_trade" in s and s["risk_per_trade"] is not None and not (
            _number(s["risk_per_trade"]) and s["risk_per_trade"] > 0):
        errs.append("risk_per_trade must be a positive number or null")
    if "expected" in s:
        errs += _expected_errors(s["expected"], symbols)
    return errs


# --- inputs -------------------------------------------------------------------------------

def _sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _synthetic_manifest(base):
    path = os.path.join(base, DATA_MANIFEST)
    if not os.path.exists(path):
        raise Invalid("SYNTHETIC data needs %s (the generator's file list)" % DATA_MANIFEST)
    with open(path, encoding="utf-8") as fh:
        man = json.load(fh)
    if man.get("data_kind") != SYNTHETIC or not isinstance(man.get("files"), dict):
        raise Invalid("%s must declare data_kind SYNTHETIC and a files table" % DATA_MANIFEST)
    return man["files"]


def _csv_file(base, rel):
    path = os.path.join(base, rel)
    if not os.path.isfile(path):
        raise Invalid("data file %s does not exist" % rel)
    return path


def check_data(s, base):
    """Provenance of the scenario's files, without running it. Raises Invalid or Unavailable."""
    kind = s["data_kind"]
    if kind in (SYNTHETIC, OWNER_CHART):
        listed = _synthetic_manifest(base) if kind == SYNTHETIC else (
            _synthetic_manifest(base) if os.path.exists(os.path.join(base, DATA_MANIFEST)) else {})
        for sym, rel in sorted(s["data"].items()):
            path = _csv_file(base, rel)
            name = os.path.relpath(path, os.path.join(base, "data")).replace(os.sep, "/")
            if kind == SYNTHETIC:
                rec = listed.get(name)
                if rec is None or rec.get("data_kind") != SYNTHETIC:
                    raise Invalid("%s is not listed as SYNTHETIC in %s" % (rel, DATA_MANIFEST))
                if rec.get("sha256") != _sha(path):
                    raise Invalid("%s differs from its %s sha256 (re-run python3 -m nse.scenarios.generate)"
                                  % (rel, DATA_MANIFEST))
            elif name in listed:
                raise Invalid("%s is SYNTHETIC (listed in %s); it cannot be an OWNER_CHART" % (rel, DATA_MANIFEST))
    else:
        for sym, spec in sorted(s["data"].items()):
            for f in spec["bhavcopy"]:
                path = os.path.join(ROOT, f["path"])
                if not os.path.isfile(path):
                    raise Unavailable("%s: local file %s is absent (git-ignored raw data, D31)" % (sym, f["path"]))
                if _sha(path) != f["sha256"]:
                    raise Unavailable("%s: %s is not the referenced file (sha256 differs)" % (sym, f["path"]))
            if spec.get("manifest") and not os.path.isfile(os.path.join(ROOT, spec["manifest"])):
                raise Unavailable("%s: manifest %s is absent" % (sym, spec["manifest"]))


def _inputs(s, base):
    check_data(s, base)
    out = []
    for sym, v in sorted(s["data"].items()):
        if s["data_kind"] == HISTORICAL_REAL:
            man = bhavcopy.read_manifest(os.path.join(ROOT, v["manifest"])) if v.get("manifest") else None
            files = bhavcopy.load_many([os.path.join(ROOT, f["path"]) for f in v["bhavcopy"]], man)
            out.append(marketdata.from_bhavcopy(files, sym, v.get("series", "EQ")))
        else:
            # invented prices have no corporate actions (NONE); an owner's chart transcription is UNKNOWN
            out.append(marketdata.from_csv(os.path.join(base, v), sym,
                                           "SCENARIO_" + s["data_kind"],
                                           "NONE" if s["data_kind"] == SYNTHETIC else "UNKNOWN"))
    return out


def _calendar(name):
    if name == CAL_WEEKDAYS:
        return WeekdayCalendar()
    if name == CAL_NSE:
        try:
            return cal_mod.NseCalendar.load(CALENDAR_DIR)
        except (OSError, cal_mod.CalendarError) as e:
            raise Unavailable("NSE calendar did not load from nse/data/calendar: %s" % e)
    return None


def scan_scenario(s, base):
    """(inputs, ScanConfig, ScanResult) through the real scanner."""
    inputs = _inputs(s, base)
    cfg = scanner.ScanConfig(as_of=parse_as_of(s["as_of"]), trade_type=s["trade_type"],
                             calendar=_calendar(s["calendar"]), calendar_label=s["calendar"],
                             risk_per_trade=s["risk_per_trade"], universe_label="SCENARIO:" + s["id"])
    return inputs, cfg, scanner.scan(inputs, cfg)


# --- assertions ---------------------------------------------------------------------------

def _matches(rec, match):
    return all(rec.get(k) == v for k, v in match.items())


def _fmt(match):
    return "{%s}" % ", ".join("%s: %s" % (k, match[k]) for k in sorted(match))


def decisions(sym):
    """Every decision field of a SymbolResult (provenance and findings text excluded: they name files)."""
    keep = ("status", "reasons", "price", "candidates", "blocked_zones", "fresh_zones", "tda", "series",
            "limitations")
    d = json.loads(json.dumps(asdict(sym), default=_iso, sort_keys=True))
    return {k: d[k] for k in keep}


def _iso(v):
    if isinstance(v, (datetime.date, datetime.datetime)):
        return v.isoformat()
    raise TypeError("not JSON-serialisable: %s" % type(v).__name__)


def _overlay_states(inp, cfg):
    snap = mtf.replay(inp.candles, "D", htf=scanner.HTF, as_of=cfg.as_of, calendar=cfg.calendar)
    return [{"tf": st.tf, "zone_id": st.zone_id, "side": st.side, "pattern": st.pattern, "proximal": st.proximal,
             "distal": st.distal, "overlay_status": st.status} for _, st in sorted(snap.zones.items())]


class _Checks(object):
    def __init__(self):
        self.items = []

    def add(self, check, expected, actual, passed=None):
        ok = (expected == actual) if passed is None else passed
        self.items.append({"check": check, "expected": expected, "actual": actual, "passed": bool(ok)})


def _assert(s, sym, inp, cfg, ref_decisions):
    e = s["expected"]
    c = _Checks()
    c.add("symbol_status", e["symbol_status"], sym.status)
    for text in e.get("symbol_reason_contains", []):
        c.add("symbol reasons contain %r" % text, True, any(text in r for r in sym.reasons))
    if "candidate_count" in e:
        c.add("candidate_count", e["candidate_count"], len(sym.candidates))
    cands = [x.to_dict() for x in sym.candidates]
    for want in e.get("candidates", []):
        name = "candidate %s" % _fmt(want["match"])
        hit = [x for x in cands if _matches(x["zone"], want["match"])]
        if len(hit) != 1:
            c.add(name + " matches exactly one candidate", 1, len(hit))
            continue
        got = hit[0]
        if "status" in want:
            c.add(name + " status", want["status"], got["status"])
        outcomes = {g["gate"]: g["outcome"] for g in got["gates"]}
        for gate in sorted(want.get("gates", {})):
            c.add("%s %s" % (name, gate), want["gates"][gate], outcomes.get(gate))
        for text in want.get("manual_review_contains", []):
            c.add("%s manual_review contains %r" % (name, text), True, text in got["manual_review"])
    if "fresh_zone_count" in e:
        c.add("fresh_zone_count", e["fresh_zone_count"], len(sym.fresh_zones))
    ids = sorted(set(z["zone_id"] for z in sym.fresh_zones))
    for zid in e.get("fresh_zone_ids_absent", []):
        c.add("fresh zone %s absent" % zid, False, zid in ids)
    for match in e.get("fresh_zones_absent", []):
        c.add("fresh zone %s absent" % _fmt(match), 0, len([z for z in sym.fresh_zones if _matches(z, match)]))
    for want in e.get("fresh_zones_present", []):
        hit = [z for z in sym.fresh_zones if _matches(z, want["match"])]
        name = "fresh zone %s" % _fmt(want["match"])
        c.add(name + " present exactly once", 1, len(hit))
        if len(hit) == 1 and "zone_level_contains" in want:
            c.add(name + " zone_level contains %r" % want["zone_level_contains"], True,
                  want["zone_level_contains"] in hit[0]["zone_level"], None)
    for want in e.get("blocked_zone_overlay_status", []):
        hit = [b for b in sym.blocked_zones if _matches(b, want["match"])]
        name = "blocked zone %s" % _fmt(want["match"])
        if len(hit) != 1:
            c.add(name + " matches exactly one blocked zone", 1, len(hit))
            continue
        c.add(name + " overlay_status", want["overlay_status"], hit[0]["overlay_status"])
        if "disposition" in want:
            c.add(name + " disposition", want["disposition"], hit[0]["disposition"])
    if e.get("overlay_zone_states"):
        states = _overlay_states(inp, cfg)
        for want in e["overlay_zone_states"]:
            hit = [x for x in states if _matches(x, want["match"])]
            name = "overlay zone %s" % _fmt(want["match"])
            if len(hit) != 1:
                c.add(name + " matches exactly one overlay zone", 1, len(hit))
            else:
                c.add(name + " status", want["overlay_status"], hit[0]["overlay_status"])
    if ref_decisions is not None:
        mine = decisions(sym)
        diff = sorted(k for k in mine if mine[k] != ref_decisions[k])
        c.add("same decisions as %s" % e["same_decisions_as"], [], diff)
    return c.items


def _actual(sym):
    return {"symbol": sym.symbol, "status": sym.status, "reasons": list(sym.reasons),
            "candidates": [{"zone_id": x.zone["zone_id"], "proximal": x.zone["proximal"], "distal": x.zone["distal"],
                            "created_time": x.zone["created_time"], "status": x.status,
                            "gates": {g.gate: g.outcome for g in x.gates}} for x in sym.candidates],
            "fresh_zone_count": len(sym.fresh_zones),
            "blocked_zones": [{"zone_id": b["zone_id"], "tf": b["tf"], "overlay_status": b["overlay_status"],
                               "disposition": b["disposition"]} for b in sym.blocked_zones]}


def _record(s, path, result, assertions=(), actual=None, reason=None):
    sid = s.get("id") if isinstance(s, dict) else None
    get = (lambda k, d=None: s.get(k, d)) if isinstance(s, dict) else (lambda k, d=None: d)
    failures = ["%s: expected %s, actual %s" % (a["check"], json.dumps(a["expected"], sort_keys=True),
                                               json.dumps(a["actual"], sort_keys=True))
                for a in assertions if not a["passed"]]
    return {"id": sid or os.path.splitext(os.path.basename(path or "unknown"))[0],
            "file": os.path.basename(path) if path else None,
            "title": get("title"), "data_kind": get("data_kind"), "rule_refs": get("rule_refs", []),
            "trade_type": get("trade_type"), "as_of": get("as_of"), "calendar": get("calendar"),
            "result": result, "reason": reason, "expected": get("expected"), "actual": actual,
            "assertions": list(assertions), "failures": failures, "explanation": get("explanation")}


def run_scenario(s, base, library=None, path=None, _scans=None):
    """One record. base: the folder data paths are relative to. library: {id: (scenario, base)}
    for same_decisions_as. Never raises for a scenario problem: it becomes the result."""
    errors = validate(s)
    if errors:
        return _record(s, path, INVALID, reason="; ".join(errors))
    scans = {} if _scans is None else _scans
    e = s["expected"]
    ref = None
    try:
        sid = s["id"]
        if sid not in scans:
            scans[sid] = scan_scenario(s, base)
        inputs, cfg, res = scans[sid]
        symbol = e.get("symbol") or sorted(s["data"])[0]
        [sym] = [x for x in res.symbols if x.symbol == symbol]
        [inp] = [x for x in inputs if x.symbol == symbol]
        if "same_decisions_as" in e:
            other = (library or {}).get(e["same_decisions_as"])
            if other is None or other[0].get("id") == sid:
                raise Invalid("same_decisions_as %r is not another scenario in the library" % e["same_decisions_as"])
            if validate(other[0]):
                raise Invalid("same_decisions_as %r is itself invalid" % e["same_decisions_as"])
            oid = other[0]["id"]
            if oid not in scans:
                scans[oid] = scan_scenario(other[0], other[1])
            osyms = [x for x in scans[oid][2].symbols if x.symbol == symbol]
            if len(osyms) != 1:
                raise Invalid("same_decisions_as %r has no symbol %s" % (oid, symbol))
            ref = decisions(osyms[0])
    except Unavailable as x:
        return _record(s, path, UNAVAILABLE, reason=str(x))
    except (Invalid, bhavcopy.BhavcopyError, ValueError, OSError) as x:
        return _record(s, path, INVALID, reason="%s: %s" % (type(x).__name__, x))
    items = _assert(s, sym, inp, cfg, ref)
    return _record(s, path, PASS if all(a["passed"] for a in items) else FAIL, items, _actual(sym))


def _display(path):
    p = os.path.abspath(path)
    return os.path.relpath(p, ROOT).replace(os.sep, "/") if p.startswith(ROOT + os.sep) else p


def run_library(folder=DEFAULT_LIBRARY, only=None, generated_at=None):
    """Deterministic report: records sorted by id, summary counts, no clock."""
    entries = load_library(folder)
    library = {e.scenario["id"]: (e.scenario, folder) for e in entries
               if not e.errors and isinstance(e.scenario, dict)}
    known = set(library) | set(e.scenario.get("id") for e in entries if isinstance(e.scenario, dict))
    if only:
        missing = sorted(set(only) - known)
        if missing:
            raise ValueError("unknown scenario id(s): %s" % ", ".join(missing))
    scans = {}
    records = []
    for e in entries:
        sid = e.scenario.get("id") if isinstance(e.scenario, dict) else None
        if only and sid not in only:
            continue
        if e.errors:
            records.append(_record(e.scenario, e.path, INVALID, reason="; ".join(e.errors)))
        else:
            records.append(run_scenario(e.scenario, folder, library, e.path, scans))
    records.sort(key=lambda r: (r["id"], r["file"] or ""))
    counts = {k: 0 for k in RESULTS}
    by_kind = {}
    for r in records:
        counts[r["result"]] += 1
        k = by_kind.setdefault(str(r["data_kind"]), {x: 0 for x in RESULTS})
        k[r["result"]] += 1
    verdict = ("FAILED" if counts[FAIL] or counts[INVALID] else
               "PASSED_WITH_UNAVAILABLE" if counts[UNAVAILABLE] else "PASSED") if records else "NO_SCENARIOS"
    return {"library": _display(folder), "generated_at": generated_at, "pipeline_version": m.PIPELINE_VERSION,
            "engine_versions": {"zone_engine": mtf.ze.ENGINE_VERSION, "mtf_freshness": mtf.ENGINE_VERSION},
            "only": sorted(only) if only else None,
            "summary": dict(counts, total=len(records)), "by_data_kind": by_kind, "verdict": verdict,
            "note": NOTE, "scenarios": records}


CSV_COLUMNS = ("id", "data_kind", "trade_type", "as_of", "result", "assertions_passed", "assertions_total",
               "failures", "reason", "rule_refs")


def report_csv(report):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(CSV_COLUMNS), lineterminator="\n")
    w.writeheader()
    for r in report["scenarios"]:
        w.writerow({"id": r["id"], "data_kind": r["data_kind"] or "", "trade_type": r["trade_type"] or "",
                    "as_of": r["as_of"] or "", "result": r["result"],
                    "assertions_passed": sum(1 for a in r["assertions"] if a["passed"]),
                    "assertions_total": len(r["assertions"]), "failures": " | ".join(r["failures"]),
                    "reason": r["reason"] or "", "rule_refs": " | ".join(r["rule_refs"] or [])})
    return buf.getvalue()


def report_json(report):
    return json.dumps(report, sort_keys=True, indent=1) + "\n"


def write_report(report, folder):
    os.makedirs(folder, exist_ok=True)
    files = {"scenarios_report.json": report_json(report), "scenarios_report.csv": report_csv(report)}
    for name, text in sorted(files.items()):
        with open(os.path.join(folder, name), "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
    return sorted(files)


# --- CLI ----------------------------------------------------------------------------------

def cmd_run(args):
    try:
        rep = run_library(args.library, args.only, args.generated_at)
    except (OSError, ValueError) as e:
        print("error: %s" % e)
        return 2
    written = write_report(rep, args.out)
    for r in rep["scenarios"]:
        print("%-12s %s%s" % (r["result"], r["id"], (": " + (r["reason"] or "; ".join(r["failures"])))
                              if r["result"] != PASS else ""))
    print(json.dumps({"summary": rep["summary"], "verdict": rep["verdict"]}, sort_keys=True))
    print("wrote %s: %s" % (args.out, ", ".join(written)))
    return 1 if rep["summary"][FAIL] or rep["summary"][INVALID] else 0


def cmd_validate(args):
    try:
        entries = load_library(args.library)
    except OSError as e:
        print("error: %s" % e)
        return 2
    bad = 0
    for e in entries:
        problems = list(e.errors)
        note = ""
        if not problems:
            try:
                check_data(e.scenario, args.library)
            except Invalid as x:
                problems.append(str(x))
            except Unavailable as x:
                note = " (data UNAVAILABLE: %s)" % x
        bad += bool(problems)
        print("%-8s %s%s%s" % ("INVALID" if problems else "VALID", os.path.basename(e.path),
                               ": " + "; ".join(problems) if problems else "", note))
    print("%d scenario file(s), %d invalid" % (len(entries), bad))
    return 1 if bad else 0


def add_commands(subparsers):
    r = subparsers.add_parser("scenarios-run", help="run the scenario library through the real scanner")
    r.add_argument("--library", default=DEFAULT_LIBRARY, help="scenario folder (default nse/scenarios)")
    r.add_argument("--only", nargs="+", metavar="ID", help="run only these scenario ids")
    r.add_argument("--out", default=DEFAULT_OUT, help="report folder (default nse/output/scenarios, git-ignored)")
    r.add_argument("--generated-at", help="label recorded in the report; no clock is read")
    r.set_defaults(func=cmd_run)
    v = subparsers.add_parser("scenarios-validate", help="check scenario schema and data provenance without running")
    v.add_argument("--library", default=DEFAULT_LIBRARY)
    v.set_defaults(func=cmd_validate)
