"""Watchlists and alerts from two scan.json dicts (reports.to_json): local and deterministic.

An alert restates a change the scans already recorded; it never re-evaluates a gate or
changes a status, and BECAME_ACTIONABLE always says the manual checklist is pending and
no trade is approved (spec 8). Rules come from a fixed vocabulary:
  NEW_CANDIDATE      a candidate zone not in the previous scan (every candidate on a first run)
  STATUS_CHANGED     a candidate or symbol status differs from the previous scan
  BECAME_ACTIONABLE  a candidate is ACTIONABLE now and was not before (needs a previous scan)
  LEFT_ACTIONABLE    a candidate was ACTIONABLE and is not, or is no longer listed
  DATA_FAILURE       the symbol is DATA_INSUFFICIENT or has an ERROR finding
  ZONE_PROXIMITY     the price is within a user-supplied pct above a candidate's PL (no default)
  SCAN_COMPLETED     one event per scan with its counts
A first run (no previous scan) emits only SCAN_COMPLETED, NEW_CANDIDATE and DATA_FAILURE.
Alert ids hash rule + symbol + zone + as_of, so the same pair of scans never produces a
duplicate, and JsonlFileNotifier never appends an id the file already holds. Delivery is
stdout or a local file only (D31): email, webhook or push delivery is not implemented and
needs owner configuration and approval.
"""

import hashlib
import json
import math
import os
import sys

from nse.research import explain, models as m

NEW_CANDIDATE = "NEW_CANDIDATE"
STATUS_CHANGED = "STATUS_CHANGED"
BECAME_ACTIONABLE = "BECAME_ACTIONABLE"
LEFT_ACTIONABLE = "LEFT_ACTIONABLE"
DATA_FAILURE = "DATA_FAILURE"
ZONE_PROXIMITY = "ZONE_PROXIMITY"
SCAN_COMPLETED = "SCAN_COMPLETED"
RULES = (SCAN_COMPLETED, DATA_FAILURE, NEW_CANDIDATE, STATUS_CHANGED, BECAME_ACTIONABLE, LEFT_ACTIONABLE,
         ZONE_PROXIMITY)
FIRST_RUN_RULES = (SCAN_COMPLETED, NEW_CANDIDATE, DATA_FAILURE)

ACTIONABLE_WARNING = ("manual checks are pending and no trade is approved: every automated gate passed, "
                      "the checklist still needs a person")
DELIVERY_NOTE = ("external delivery (email, webhook, push) is not implemented; it needs owner configuration "
                 "and approval (D31)")


class WatchlistError(ValueError):
    pass


def parse_watchlist(data):
    """{"name", "symbols": [...], "rules": ["RULE" | {"rule": "ZONE_PROXIMITY", "pct": 2.0}]}
    -> {"name", "symbols", "rules": {rule: params}}. Unknown rules and a proximity rule
    without an explicit positive pct are errors: no threshold is assumed."""
    if not isinstance(data, dict):
        raise WatchlistError("a watchlist is a JSON object")
    name = data.get("name")
    symbols = data.get("symbols")
    rules = data.get("rules")
    if not isinstance(name, str) or not name:
        raise WatchlistError("watchlist needs a non-empty name")
    if not isinstance(symbols, list) or not all(isinstance(s, str) and s for s in symbols):
        raise WatchlistError("watchlist symbols must be a list of symbols ([] means every symbol)")
    if not isinstance(rules, list) or not rules:
        raise WatchlistError("watchlist needs at least one rule from %s" % ", ".join(RULES))
    out = {}
    for r in rules:
        spec = {"rule": r} if isinstance(r, str) else r
        if not isinstance(spec, dict) or spec.get("rule") not in RULES:
            raise WatchlistError("unknown rule %r (one of %s)" % (r, ", ".join(RULES)))
        params = {}
        if spec["rule"] == ZONE_PROXIMITY:
            pct = spec.get("pct")
            if isinstance(pct, bool) or not isinstance(pct, (int, float)) or not math.isfinite(pct) or pct <= 0:
                raise WatchlistError("ZONE_PROXIMITY needs an explicit pct > 0; there is no default")
            params["pct"] = float(pct)
        elif set(spec) - {"rule"}:
            raise WatchlistError("rule %s takes no parameters" % spec["rule"])
        if spec["rule"] in out:
            raise WatchlistError("rule %s listed twice" % spec["rule"])
        out[spec["rule"]] = params
    return {"name": name, "symbols": sorted(set(s.upper() for s in symbols)), "rules": out}


def load_watchlist(path):
    with open(path, encoding="utf-8") as fh:
        return parse_watchlist(json.load(fh))


def alert_id(rule, symbol, zone_id, as_of):
    return hashlib.sha256(("%s|%s|%s|%s" % (rule, symbol, zone_id, as_of)).encode("utf-8")).hexdigest()[:16]


def _candidates(scan):
    out = {}
    for s in scan["symbols"]:
        for c in s["candidates"]:
            out[(s["symbol"], "%s:%s" % (c["execution_tf"], c["zone"]["zone_id"]))] = (s, c)
    return out


def _event(rule, symbol, zone, scan, text, status=None, previous=None, extra=None):
    ev = {"id": alert_id(rule, symbol, zone, scan["as_of"]), "rule": rule, "symbol": symbol, "zone": zone,
          "as_of": scan["as_of"], "status": status, "previous_status": previous, "text": text}
    if extra:
        ev.update(extra)
    return ev


def evaluate(prev_scan, curr_scan, watchlist):
    """Sorted, de-duplicated alert events. watchlist: parse_watchlist() output (or its JSON)."""
    _require_consistent(curr_scan, "current")
    if prev_scan is not None:
        _require_consistent(prev_scan, "previous")
    if "rules" in watchlist and not isinstance(watchlist["rules"], dict):
        watchlist = parse_watchlist(watchlist)
    rules = watchlist["rules"]
    first = prev_scan is None
    if not first:
        if prev_scan["as_of"] > curr_scan["as_of"]:
            raise ValueError("previous scan (as_of %s) is later than the current scan (%s)"
                             % (prev_scan["as_of"], curr_scan["as_of"]))
        if prev_scan.get("trade_type") != curr_scan.get("trade_type"):
            raise ValueError("scans of different trade types cannot be compared")
    active = [r for r in rules if not first or r in FIRST_RUN_RULES]
    wanted = set(watchlist["symbols"])

    def watched(sym):
        return not wanted or sym in wanted

    events = []
    if SCAN_COMPLETED in active:
        cands = [c for s in curr_scan["symbols"] for c in s["candidates"] if watched(s["symbol"])]
        counts = {}
        for c in cands:
            counts[c["status"]] = counts.get(c["status"], 0) + 1
        text = "scan %s completed: %d symbols, %d candidates (%s)" % (
            curr_scan["as_of"], len([s for s in curr_scan["symbols"] if watched(s["symbol"])]), len(cands),
            ", ".join("%s %d" % kv for kv in sorted(counts.items())) or "none")
        events.append(_event(SCAN_COMPLETED, "", "", curr_scan, text, extra={"watchlist": watchlist["name"]}))
    curr = _candidates(curr_scan)
    prev = {} if first else _candidates(prev_scan)
    prev_sym = {} if first else {s["symbol"]: s for s in prev_scan["symbols"]}
    for s in curr_scan["symbols"]:
        sym = s["symbol"]
        if not watched(sym):
            continue
        if DATA_FAILURE in active:
            errors = sorted(set(f["code"] for f in s.get("findings") or [] if f["severity"] == "ERROR"))
            if s["status"] == "DATA_INSUFFICIENT" or errors:
                events.append(_event(DATA_FAILURE, sym, "", curr_scan,
                                     "%s data failure: status %s; %s; no candidate can be relied on until the "
                                     "input is fixed" % (sym, s["status"], "; ".join(s["reasons"]) or
                                                         "ERROR findings: " + ", ".join(errors)),
                                     status=s["status"], extra={"finding_codes": errors}))
        if STATUS_CHANGED in active and sym in prev_sym and prev_sym[sym]["status"] != s["status"]:
            events.append(_event(STATUS_CHANGED, sym, "", curr_scan, "%s symbol status %s -> %s"
                                 % (sym, prev_sym[sym]["status"], s["status"]),
                                 status=s["status"], previous=prev_sym[sym]["status"]))
    for key in sorted(set(curr) | set(prev)):
        sym, zone = key
        if not watched(sym):
            continue
        c = curr.get(key, (None, None))[1]
        p = prev.get(key, (None, None))[1]
        now = c["status"] if c else None
        before = p["status"] if p else None
        if c and not p and NEW_CANDIDATE in active:
            text = "%s %s new candidate, status %s" % (sym, zone, now)
            if now == m.ACTIONABLE:
                text += "; " + ACTIONABLE_WARNING
            events.append(_event(NEW_CANDIDATE, sym, zone, curr_scan, text, now))
        if c and p and now != before and STATUS_CHANGED in active:
            events.append(_event(STATUS_CHANGED, sym, zone, curr_scan, "%s %s status %s -> %s"
                                 % (sym, zone, before, now), now, before))
        if now == m.ACTIONABLE and before != m.ACTIONABLE and BECAME_ACTIONABLE in active:
            events.append(_event(BECAME_ACTIONABLE, sym, zone, curr_scan, "%s %s became %s; %s"
                                 % (sym, zone, m.ACTIONABLE, ACTIONABLE_WARNING), now, before))
        if before == m.ACTIONABLE and now != m.ACTIONABLE and LEFT_ACTIONABLE in active:
            why = ("status now %s" % now if c else
                   "no longer a candidate in this scan (see the scan records; tested and invalidated zones are "
                   "not listed, D3)")
            events.append(_event(LEFT_ACTIONABLE, sym, zone, curr_scan, "%s %s left %s: %s"
                                 % (sym, zone, m.ACTIONABLE, why), now, before))
        if c and ZONE_PROXIMITY in active:
            s = curr[key][0]
            pct = rules[ZONE_PROXIMITY]["pct"]
            pl = c["zone"]["proximal"]
            if s.get("price") is not None and pl:
                dist = (s["price"] - pl) / pl * 100.0
                if 0 <= dist <= pct:                  # within pct ABOVE the PL
                    events.append(_event(ZONE_PROXIMITY, sym, zone, curr_scan,
                                         "%s %s price %s is %.2f%% from PL %s (threshold %g%%, user-supplied); "
                                         "status %s; proximity is not an entry signal"
                                         % (sym, zone, s["price"], dist, pl, pct, now), now,
                                         extra={"distance_pct": round(dist, 4), "pct": pct}))
    seen, out = set(), []
    for e in events:
        if e["id"] not in seen:
            seen.add(e["id"])
            out.append(e)
    return sorted((_annotate(e, curr_scan) for e in out),
                  key=lambda e: (e["as_of"], RULES.index(e["rule"]), e["symbol"], e["zone"], e["id"]))


def _annotate(ev, scan):
    """Every event carries the scan's, the symbol's and the candidate's limitations and the
    candidate's manual-review items, so a restriction never disappears into an alert."""
    lims = set(scan.get("limitations") or [])
    manual = []
    for s in scan.get("symbols") or []:
        if s.get("symbol") != ev["symbol"]:
            continue
        lims |= set(s.get("limitations") or [])
        for c in s.get("candidates") or []:
            if ev.get("zone") == "%s:%s" % (c.get("execution_tf"), (c.get("zone") or {}).get("zone_id")):
                lims |= set(c.get("limitations") or [])
                manual = sorted(c.get("manual_review") or [])
                ev["manual_checks_pending"] = sorted(x.get("code") for x in c.get("manual_checks") or [])
    ev["limitations"] = sorted(lims)
    ev["manual_review"] = manual
    return ev


def _require_consistent(scan, which):
    # an edited or mixed scan.json (a status that its own gates do not give) is refused (review 2026-11-02)
    from nse.research import explain
    bad = [i for i in explain.inconsistencies(scan) if i["code"] == "STATUS_NOT_DERIVED_FROM_GATES"]
    if bad:
        raise ValueError("%s scan fails the self-audit (%s): no alerts from it" % (which, "; ".join(
            "%s %s %s" % (i["code"], i["symbol"], i["zone_id"]) for i in bad[:3])))


# --- notifiers --------------------------------------------------------------------------

class Notifier(object):
    """Delivers events; returns the events actually delivered."""
    def notify(self, events):
        raise NotImplementedError


class StdoutNotifier(Notifier):
    def __init__(self, stream=None):
        self.stream = stream

    def notify(self, events):
        out = self.stream or sys.stdout
        for e in events:
            out.write("[%s] %s %s\n" % (e["id"], e["rule"], e["text"]))
        return list(events)


class JsonlFileNotifier(Notifier):
    """Append-only JSON lines; an id already in the file is never appended again."""
    def __init__(self, path):
        self.path = path

    def known_ids(self):
        ids = set()
        if not os.path.exists(self.path):
            return ids
        with open(self.path, encoding="utf-8") as fh:
            for n, line in enumerate(fh, 1):
                if not line.strip():
                    continue
                try:
                    ids.add(json.loads(line)["id"])
                except (ValueError, KeyError, TypeError) as e:
                    raise ValueError("%s line %d is not an alert record: %s" % (self.path, n, e))
        return ids

    def notify(self, events):
        known = self.known_ids()
        new = [e for e in events if e["id"] not in known]
        if new:
            folder = os.path.dirname(os.path.abspath(self.path))
            os.makedirs(folder, exist_ok=True)
            with open(self.path, "a", encoding="utf-8", newline="") as fh:
                for e in new:
                    fh.write(json.dumps(e, sort_keys=True) + "\n")
        return new


# --- CLI ----------------------------------------------------------------------------------

def cmd_alerts(args):
    try:
        wl = load_watchlist(args.watchlist)
        curr = explain.load_scan(args.scan)
        prev = explain.load_scan(args.previous) if args.previous else None
        events = evaluate(prev, curr, wl)
        StdoutNotifier().notify(events)
        if args.jsonl:
            added = JsonlFileNotifier(args.jsonl).notify(events)
            print("appended %d of %d alerts to %s" % (len(added), len(events), args.jsonl))
    except (OSError, ValueError) as e:
        print("error: %s" % e, file=sys.stderr)
        return 2
    print("note: " + DELIVERY_NOTE)
    return 0


def add_commands(subparsers):
    p = subparsers.add_parser("alerts", help="watchlist alerts from two scan.json files (local delivery only)")
    p.add_argument("--watchlist", required=True, help='JSON {"name", "symbols", "rules"}')
    p.add_argument("--scan", required=True, help="current scan.json")
    p.add_argument("--previous", help="previous scan.json; omitted -> first-run rules only")
    p.add_argument("--jsonl", help="append new alerts to this JSON-lines file (idempotent by alert id)")
    p.set_defaults(func=cmd_alerts)
    return p
