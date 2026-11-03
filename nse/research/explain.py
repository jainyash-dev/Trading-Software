"""Deterministic answers about a finished scan (scan.json = reports.to_json(result)).

Every function reads the scan dict only. Nothing here re-evaluates a gate, re-derives
freshness, changes a status or calls a model or a network: the answers explain the
evidence the qualification pathway (qualification.evaluate_symbol, spec 8) already
recorded, and they cannot override eligibility. An item the scan does not contain is
reported as NOT_IN_SCAN, never guessed (unknown is never PASS). Tested and invalidated
zones are not zone results (D3), so their absence proves nothing about a zone.

Each answer is a dict: question, result, answer_lines, citations (gate ids, rule refs
taken from each gate's own `sources`, zone ids, data-quality finding codes), evidence
(the exact recorded fields used) and limitations. inconsistencies() is a self-check that
must find nothing on a scan the scanner wrote; it doubles as the report auditor.
"""

import argparse
import json
import os
import sys

from nse.research import models as m

OK = "OK"
NOT_IN_SCAN = "NOT_IN_SCAN"
SYMBOL_NOT_IN_SCAN = "SYMBOL_NOT_IN_SCAN"

AUTHORITY = ("explanation of recorded deterministic evidence only; it cannot change a status "
             "or eligibility, and no status approves a trade")

# status -> the gate outcomes that decide it, most restrictive first (models.derive_status)
PRECEDENCE = ((m.BLOCKED_STATUS, (m.BLOCKED,)), (m.REJECTED, (m.FAIL,)),
              (m.STATUS_DATA_INSUFFICIENT, (m.DATA_INSUFFICIENT,)),
              (m.MANUAL_REVIEW, (m.MANUAL, m.NOT_EVALUATED)))

# what each gate requires, transcribed from spec 8 (the gate's own reasons say why it did not pass)
REQUIREMENTS = {
    "G0": "completed candles only, adequate history and a complete execution series (spec 8 G0, spec 11)",
    "G1": "a fresh, unbreached execution-timeframe demand zone with test_count 0 per the MTF overlay (D2, D3)",
    "G2": "core 7/7 under the D12 definitions with no source disagreement (spec 5.1)",
    "G3": "a CMP location on the curve that permits a buy: not VHOC; HOC needs sector support (spec 7.2, R1)",
    "G4": "an execute row of the alignment matrix for the location and the trend-gate reading (spec 7.3, 7.6)",
    "G5": "no opposing M/Q/HY zone with its PL inside or within 5% above the zone, none within 10% "
          "needing review (spec 7.4)",
    "G6": "the execution demand not wholly below the HTF location zone's DL; Coinciding or known absence "
          "(spec 7.5, R3, R6)",
    "G7": "a structural target with R:R >= 2 for every buffer and SL choice (RB 82, RF8, spec 6)",
    "G8": "no red flag failing and no essential check open (RB 594-631)",
}


# --- loading and lookup ---------------------------------------------------------------

def load_scan(path):
    """Read a scan.json. A file that is not a scan dict is an input error (ValueError)."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict) or not isinstance(data.get("symbols"), list) or "as_of" not in data:
        raise ValueError("%s is not a scan.json (needs as_of and a symbols list)" % path)
    return data


def symbol_record(scan, symbol):
    for s in scan["symbols"]:
        if s["symbol"] == symbol:
            return s
    return None


def _split_zone(zone_id):
    """'D:demand-1-2' -> ('D', 'demand-1-2'); a bare id matches every timeframe."""
    if ":" in zone_id:
        tf, zid = zone_id.split(":", 1)
        return tf, zid
    return None, zone_id


def find_candidates(scan, symbol, zone_id):
    s = symbol_record(scan, symbol)
    if s is None:
        return []
    tf, zid = _split_zone(zone_id)
    return [c for c in s["candidates"] if c["zone"]["zone_id"] == zid and (tf is None or c["execution_tf"] == tf)]


def gate_of(candidate, gate_id):
    for g in candidate["gates"]:
        if g["gate"] == gate_id:
            return g
    return None


def deciding_gates(candidate):
    """[(status, [gate dicts])] for every non-PASS outcome, in status-precedence order."""
    out = []
    for status, outcomes in PRECEDENCE:
        gs = [g for g in candidate["gates"] if g["outcome"] in outcomes]
        if gs:
            out.append((status, gs))
    return out


# --- answer building --------------------------------------------------------------------

class _Answer(object):
    def __init__(self, scan, question):
        self.scan = scan
        self.question = question
        self.result = OK
        self.lines = []
        self.gates, self.refs, self.zones, self.codes = set(), set(), set(), set()
        self.evidence = []
        self.limitations = set(scan.get("limitations") or [])

    def cite_gate(self, symbol, candidate, g, fields=("outcome", "reasons", "manual_review")):
        self.gates.add(g["gate"])
        self.refs.update(g.get("sources") or [])
        self.zones.add(candidate["zone"]["zone_id"])
        item = {"symbol": symbol, "zone_id": candidate["zone"]["zone_id"], "gate": g["gate"]}
        for f in fields:
            item[f] = g.get(f)
        self.evidence.append(item)

    def cite_findings(self, s):
        for f in s.get("findings") or []:
            self.codes.add(f["code"])

    def done(self):
        lim = sorted(self.limitations)
        return {"question": self.question, "result": self.result, "answer_lines": list(self.lines),
                "citations": {"gates": sorted(self.gates), "rule_refs": sorted(self.refs),
                              "zone_ids": sorted(self.zones), "finding_codes": sorted(self.codes)},
                "evidence": self.evidence, "limitations": lim + [AUTHORITY]}


def _missing_symbol(ans, symbol):
    ans.result = SYMBOL_NOT_IN_SCAN
    ans.lines.append("%s is not in this scan (as_of %s); nothing is known about it here." % (symbol, ans.scan["as_of"]))
    return ans.done()


def _missing_zone(ans, symbol, zone_id):
    ans.result = NOT_IN_SCAN
    ans.lines.append("%s %s is NOT_IN_SCAN: it is not a candidate of this scan (as_of %s)."
                     % (symbol, zone_id, ans.scan["as_of"]))
    return ans.done()


def why(scan, symbol):
    """Status of the symbol and of each candidate, with the deciding gates first."""
    ans = _Answer(scan, "why does %s have its status?" % symbol)
    s = symbol_record(scan, symbol)
    if s is None:
        return _missing_symbol(ans, symbol)
    ans.cite_findings(s)
    ans.limitations.update(s.get("limitations") or [])
    ans.lines.append("%s symbol status %s%s" % (symbol, s["status"],
                                                 ": " + "; ".join(s["reasons"]) if s["reasons"] else ""))
    errors = [f for f in s.get("findings") or [] if f["severity"] == "ERROR"]
    for f in errors:
        ans.lines.append("  data-quality ERROR %s: %s" % (f["code"], f["detail"]))
    ans.evidence.append({"symbol": symbol, "status": s["status"], "reasons": list(s["reasons"]),
                         "error_findings": [f["code"] for f in errors]})
    if not s["candidates"]:
        ans.lines.append("  no candidate was evaluated for %s." % symbol)
    for c in s["candidates"]:
        z = c["zone"]
        ans.zones.add(z["zone_id"])
        ans.limitations.update(c.get("limitations") or [])
        ans.lines.append("candidate %s:%s (PL %s, DL %s): %s" % (c["execution_tf"], z["zone_id"], z["proximal"],
                                                                  z["distal"], c["status"]))
        groups = deciding_gates(c)
        if not groups:
            ans.lines.append("  every automated gate G0-G8 passed; the manual checklist is pending: %s"
                             % ", ".join(x["code"] for x in c["manual_checks"]))
            for g in c["gates"]:
                ans.cite_gate(symbol, c, g, ("outcome",))
        for i, (status, gs) in enumerate(groups):
            label = "deciding" if i == 0 else "also"
            for g in gs:
                ans.cite_gate(symbol, c, g)
                ans.lines.append("  %s (%s) %s %s: %s" % (label, status, g["gate"], g["outcome"],
                                                          "; ".join(g["reasons"]) or "no reason recorded"))
                for x in g["manual_review"]:
                    ans.lines.append("    manual item: %s" % x)
    return ans.done()


def gate(scan, symbol, zone_id, gate_id):
    ans = _Answer(scan, "what did gate %s decide for %s %s?" % (gate_id, symbol, zone_id))
    if gate_id not in m.GATES:
        raise ValueError("unknown gate %r (one of %s)" % (gate_id, ", ".join(m.GATES)))
    if symbol_record(scan, symbol) is None:
        return _missing_symbol(ans, symbol)
    cands = find_candidates(scan, symbol, zone_id)
    if not cands:
        return _missing_zone(ans, symbol, zone_id)
    for c in cands:
        g = gate_of(c, gate_id)
        ans.cite_gate(symbol, c, g, ("outcome", "reasons", "manual_review", "evidence", "sources"))
        ans.lines.append("%s %s:%s %s (%s): %s" % (symbol, c["execution_tf"], c["zone"]["zone_id"], gate_id,
                                                   m.GATE_TITLES[gate_id], g["outcome"]))
        for r in g["reasons"]:
            ans.lines.append("  reason: %s" % r)
        for x in g["manual_review"]:
            ans.lines.append("  manual item (a person decides): %s" % x)
        ans.lines.append("  sources: %s" % (", ".join(g["sources"]) or "none recorded"))
    return ans.done()


def zone_freshness(scan, symbol, zone_id):
    """Answers only from candidate overlay_status, fresh_zones rows and blocked_zones records."""
    ans = _Answer(scan, "is %s %s fresh?" % (symbol, zone_id))
    s = symbol_record(scan, symbol)
    if s is None:
        return _missing_symbol(ans, symbol)
    tf, zid = _split_zone(zone_id)
    hit = False
    for c in find_candidates(scan, symbol, zone_id):
        z = c["zone"]
        hit = True
        ans.zones.add(zid)
        g1 = gate_of(c, "G1")
        ans.cite_gate(symbol, c, g1, ("outcome", "reasons", "evidence"))
        ans.evidence.append({"record": "candidate.zone", "tf": c["execution_tf"], "zone_id": zid,
                             "overlay_status": z["overlay_status"], "test_count": z["test_count"],
                             "overlay_base_touch_count": z["overlay_base_touch_count"], "dl_touched": z["dl_touched"]})
        ans.lines.append("%s %s:%s candidate zone: overlay_status %s, test_count %s, overlay touches %s, DL touched %s"
                         % (symbol, c["execution_tf"], zid, z["overlay_status"], z["test_count"],
                            z["overlay_base_touch_count"], z["dl_touched"]))
    for r in s.get("fresh_zones") or []:
        if r["zone_id"] == zid and (tf is None or r["tf"] == tf):
            hit = True
            ans.zones.add(zid)
            ans.evidence.append({"record": "fresh_zones", "tf": r["tf"], "zone_id": zid, "side": r["side"],
                                 "dl_touched": r["dl_touched"], "zone_level": r["zone_level"]})
            ans.lines.append("%s %s:%s is in the fresh-zone report (overlay-fresh, D3): %s %s, DL touched %s; %s"
                             % (symbol, r["tf"], zid, r["side"], r["pattern"], r["dl_touched"], r["zone_level"]))
    for b in s.get("blocked_zones") or []:
        if b["zone_id"] == zid and (tf is None or b["tf"] == tf):
            hit = True
            ans.zones.add(zid)
            ans.evidence.append({"record": "blocked_zones", "tf": b["tf"], "zone_id": zid,
                                 "overlay_status": b["overlay_status"], "disposition": b["disposition"],
                                 "reasons": list(b["reasons"])})
            ans.lines.append("%s %s:%s was removed by the MTF overlay: overlay_status %s, %s: %s"
                             % (symbol, b["tf"], zid, b["overlay_status"], b["disposition"],
                                "; ".join(b["reasons"]) or "no reason recorded"))
    if not hit:
        ans.result = NOT_IN_SCAN
        ans.lines.append("%s %s is NOT_IN_SCAN: no candidate, fresh-zone row or blocked-zone record has it "
                         "(as_of %s)." % (symbol, zone_id, scan["as_of"]))
        ans.lines.append("Tested and invalidated zones are not listed as zone results (D3), and the id may "
                         "not exist; its freshness is not determined by this scan.")
    return ans.done()


def confluence(scan, symbol, zone_id):
    """G6 class and the HTF zone it cites (spec 7.5; D15; R3, R6)."""
    ans = _Answer(scan, "does %s %s coincide with a higher-timeframe zone?" % (symbol, zone_id))
    if symbol_record(scan, symbol) is None:
        return _missing_symbol(ans, symbol)
    cands = find_candidates(scan, symbol, zone_id)
    if not cands:
        return _missing_zone(ans, symbol, zone_id)
    for c in cands:
        g6 = gate_of(c, "G6")
        ev = g6["evidence"]
        ans.cite_gate(symbol, c, g6, ("outcome", "reasons", "manual_review", "evidence"))
        head = "%s %s:%s G6 %s" % (symbol, c["execution_tf"], c["zone"]["zone_id"], g6["outcome"])
        if "class" not in ev:
            ans.lines.append("%s: no classification recorded (%s)" % (head, "; ".join(g6["reasons"]) or "none"))
            continue
        ans.lines.append("%s: class %s; execution range %s" % (head, ev["class"], ev.get("execution_range")))
        h = ev.get("htf_zone")
        if h:
            ans.zones.add(h["zone_id"])
            ans.lines.append("  HTF zone cited: %s:%s %s %s PL %s DL %s, freshness %s, DL untouched %s"
                             % (h["tf"], h["zone_id"], h["side"], h["pattern"], h["proximal"], h["distal"],
                                h["freshness"], ev.get("htf_zone_dl_untouched")))
        else:
            ans.lines.append("  no HTF location demand zone cited")
        for u in ev.get("zones_with_unknown_status") or []:
            ans.zones.add(u["zone_id"])
            ans.lines.append("  HTF zone with unknown status: %s:%s (%s)" % (u["tf"], u["zone_id"], u["freshness"]))
        for r in g6["reasons"]:
            ans.lines.append("  reason: %s" % r)
    return ans.done()


def _requirement(c, g):
    req = REQUIREMENTS[g["gate"]]
    if g["gate"] == "G4":
        t = (g.get("evidence") or {}).get("gate") or {}
        if t.get("tf"):
            req = ("the %s trend gate to give an execute row of the alignment matrix with the location %s "
                   "(it read %s; spec 7.3, 7.6)" % (t["tf"], ", ".join((g["evidence"].get("positions") or [])) or
                                                     "(undetermined)", ", ".join(t.get("readings") or []) or "nothing"))
    return req


def what_would_change(scan, symbol, zone_id):
    """For each non-PASS gate: the requirement it did not meet, as a condition. Not advice."""
    ans = _Answer(scan, "what would have to differ for %s %s to qualify?" % (symbol, zone_id))
    if symbol_record(scan, symbol) is None:
        return _missing_symbol(ans, symbol)
    cands = find_candidates(scan, symbol, zone_id)
    if not cands:
        return _missing_zone(ans, symbol, zone_id)
    for c in cands:
        ans.lines.append("%s %s:%s status %s" % (symbol, c["execution_tf"], c["zone"]["zone_id"], c["status"]))
        blocking = [g for g in c["gates"] if g["outcome"] != m.PASS]
        if not blocking:
            ans.lines.append("  every automated gate passed; nothing automated is open. The manual checklist "
                             "still needs a person: %s" % ", ".join(x["code"] for x in c["manual_checks"]))
        for g in blocking:
            ans.cite_gate(symbol, c, g)
            why_ = "; ".join(g["reasons"]) or "no reason recorded"
            o = g["outcome"]
            if o == m.FAIL:
                ans.lines.append("  %s FAIL: %s; qualification would need %s" % (g["gate"], why_, _requirement(c, g)))
            elif o == m.MANUAL:
                ans.lines.append("  %s MANUAL: %s; a person must resolve %s; the software cannot "
                                 "clear a manual item" % (g["gate"], why_, ", ".join(g["manual_review"]) or "it"))
            elif o == m.DATA_INSUFFICIENT:
                ans.lines.append("  %s DATA_INSUFFICIENT: %s; qualification would need the missing input, then "
                                 "%s" % (g["gate"], why_, _requirement(c, g)))
            elif o == m.BLOCKED:
                ans.lines.append("  %s BLOCKED: %s; the capability needs an owner decision before any output"
                                 % (g["gate"], why_))
            else:
                ans.lines.append("  %s NOT_EVALUATED: an earlier gate stopped the evaluation; it is decided only "
                                 "after that gate is resolved" % g["gate"])
        ans.lines.append("  even with every automated gate passing the best status is %s: no status approves "
                         "a trade" % m.ACTIONABLE)
    return ans.done()


def compare(scan, a, b):
    """Side-by-side gate table for every candidate of two symbols."""
    ans = _Answer(scan, "how do %s and %s compare?" % (a, b))
    columns, cols = [], []
    for sym in (a, b):
        s = symbol_record(scan, sym)
        if s is None:
            columns.append("%s (NOT_IN_SCAN)" % sym)
            cols.append(None)
            ans.result = SYMBOL_NOT_IN_SCAN
            continue
        ans.cite_findings(s)
        if not s["candidates"]:
            columns.append("%s (%s, no candidate)" % (sym, s["status"]))
            cols.append(None)
        for c in s["candidates"]:
            columns.append("%s %s:%s" % (sym, c["execution_tf"], c["zone"]["zone_id"]))
            cols.append((sym, c))
            for g in c["gates"]:
                ans.cite_gate(sym, c, g, ("outcome",))
    rows = [["status"] + [c["status"] if c else "-" for c in (x[1] if x else None for x in cols)]]
    for gid in m.GATES:
        rows.append([gid] + [gate_of(x[1], gid)["outcome"] if x else "-" for x in cols])
    table = {"columns": ["gate"] + columns, "rows": rows}
    ans.evidence.insert(0, {"table": table})
    widths = [max(len(str(r[i])) for r in [table["columns"]] + rows) for i in range(len(table["columns"]))]
    for r in [table["columns"]] + rows:
        ans.lines.append("  ".join(str(v).ljust(w) for v, w in zip(r, widths)).rstrip())
    return ans.done()


# --- self-checks (report auditor) --------------------------------------------------------

def _issue(code, symbol, zone_id, detail):
    return {"code": code, "symbol": symbol, "zone_id": zone_id, "detail": detail}


def _candidate_issues(scan, s, c):
    sym, zid = s["symbol"], c["zone"]["zone_id"]
    out = []
    try:
        gates = [m.GateResult(g["gate"], g["outcome"]) for g in c["gates"]]
        derived = m.derive_status(gates)
    except (KeyError, ValueError) as e:
        return [_issue("MALFORMED_GATES", sym, zid, str(e))]
    if c["status"] != derived:
        out.append(_issue("STATUS_NOT_DERIVED_FROM_GATES", sym, zid,
                          "status %s but the gate outcomes give %s" % (c["status"], derived)))
    if c["status"] == m.ACTIONABLE:
        codes = set(x.get("code") for x in c.get("manual_checks") or [])
        missing = [k for k, _, _ in m.CHECKLIST if k not in codes]
        if missing:
            out.append(_issue("ACTIONABLE_WITHOUT_CHECKLIST", sym, zid, "missing: %s" % ", ".join(missing)))
    if c["zone"].get("overlay_status") != "FRESH":
        out.append(_issue("CANDIDATE_ZONE_NOT_OVERLAY_FRESH", sym, zid,
                          "overlay_status %s" % c["zone"].get("overlay_status")))
    if c["zone"].get("side") != "demand":
        out.append(_issue("CANDIDATE_ZONE_NOT_DEMAND", sym, zid, "side %s" % c["zone"].get("side")))
    if c["symbol"] != sym or c["as_of"] != scan["as_of"] or c["trade_type"] != scan["trade_type"]:
        out.append(_issue("CANDIDATE_IDENTITY_MISMATCH", sym, zid, "symbol %s as_of %s trade_type %s"
                          % (c["symbol"], c["as_of"], c["trade_type"])))
    if c["trade_type"] != m.MIT and c["status"] != m.BLOCKED_STATUS:
        out.append(_issue("INTRADAY_NOT_BLOCKED", sym, zid, "%s status %s (M4b)" % (c["trade_type"], c["status"])))
    if any(b["zone_id"] == zid and b["tf"] == c["execution_tf"] for b in s.get("blocked_zones") or []):
        out.append(_issue("CANDIDATE_ZONE_ALSO_BLOCKED", sym, zid, "the overlay removed this zone"))
    if not any(r["zone_id"] == zid and r["tf"] == c["execution_tf"] for r in s.get("fresh_zones") or []):
        out.append(_issue("CANDIDATE_ZONE_NOT_IN_FRESH_REPORT", sym, zid, "no fresh-zone row on %s" % c["execution_tf"]))
    want_manual = ["%s:%s" % (g["gate"], x) for g in c["gates"] for x in g.get("manual_review") or []]
    if [x for x in want_manual if x not in c.get("manual_review") or []]:
        out.append(_issue("MANUAL_ITEM_DROPPED", sym, zid, "gate manual items missing from the candidate list"))
    for g in c["gates"]:
        if g["outcome"] not in (m.PASS, m.NOT_EVALUATED) and not any(
                r.startswith("%s %s" % (g["gate"], g["outcome"])) for r in c.get("status_reasons") or []):
            out.append(_issue("STATUS_REASON_DROPPED", sym, zid, "%s %s not in status_reasons" % (g["gate"], g["outcome"])))
    return out


def inconsistencies(scan, summary=None):
    """Self-checks; [] on a scan the scanner wrote. summary: summary.json dict, if available."""
    out = []
    if m.NOT_EXTERNALLY_VALIDATED not in (scan.get("limitations") or []):
        out.append(_issue("LIMITATION_DROPPED", "", "", "%s missing from the scan limitations" % m.NOT_EXTERNALLY_VALIDATED))
    for s in scan["symbols"]:
        if s["status"] == "EVALUATED" and not s["candidates"]:
            out.append(_issue("EVALUATED_WITHOUT_CANDIDATE", s["symbol"], "", "symbol EVALUATED but no candidate"))
        if s["status"] != "EVALUATED" and s["candidates"]:
            out.append(_issue("CANDIDATES_ON_UNEVALUATED_SYMBOL", s["symbol"], "", "symbol status %s" % s["status"]))
        for c in s["candidates"]:
            out.extend(_candidate_issues(scan, s, c))
    if summary is not None:
        sym, cand = {}, {}
        for s in scan["symbols"]:
            sym[s["status"]] = sym.get(s["status"], 0) + 1
            for c in s["candidates"]:
                cand[c["status"]] = cand.get(c["status"], 0) + 1
        checks = (("as_of", scan["as_of"]), ("symbols_processed", len(scan["symbols"])),
                  ("symbol_status_counts", dict(sorted(sym.items()))),
                  ("candidate_records", sum(cand.values())), ("candidate_status_counts", dict(sorted(cand.items()))),
                  ("fresh_zone_records", sum(len(s["fresh_zones"]) for s in scan["symbols"])),
                  ("blocked_zone_records", sum(len(s["blocked_zones"]) for s in scan["symbols"])),
                  ("data_quality_findings", sum(len(s["findings"]) for s in scan["symbols"])))
        for k, v in checks:
            if summary.get(k) != v:
                out.append(_issue("SUMMARY_COUNT_MISMATCH", "", "", "%s: summary %r, records %r" % (k, summary.get(k), v)))
    return sorted(out, key=lambda x: (x["symbol"], x["zone_id"], x["code"], x["detail"]))


def audit(scan, summary=None):
    issues = inconsistencies(scan, summary)
    ans = _Answer(scan, "is this scan internally consistent?")
    ans.result = OK if not issues else "INCONSISTENT"
    ans.lines.append("%d inconsistencies found" % len(issues))
    for i in issues:
        ans.zones.update([i["zone_id"]] if i["zone_id"] else [])
        ans.lines.append("  %s %s %s: %s" % (i["code"], i["symbol"] or "-", i["zone_id"] or "-", i["detail"]))
    if summary is None:
        ans.lines.append("summary counts: NOT_RECONCILED (no summary.json was supplied)")
    ans.evidence = issues
    return ans.done()


# --- CLI -----------------------------------------------------------------------------------

def render_text(ans):
    lines = ["Q: " + ans["question"], "result: " + ans["result"]] + ans["answer_lines"]
    cit = ans["citations"]
    lines.append("citations: gates %s; rules %s; zones %s; findings %s" % tuple(
        ", ".join(cit[k]) or "-" for k in ("gates", "rule_refs", "zone_ids", "finding_codes")))
    lines.append("limitations: " + "; ".join(ans["limitations"]))
    return "\n".join(lines) + "\n"


def cmd_explain(args):
    try:
        scan = load_scan(args.scan)
        summary = None
        spath = args.summary or os.path.join(os.path.dirname(os.path.abspath(args.scan)), "summary.json")
        if args.audit and (args.summary or os.path.exists(spath)):
            with open(spath, encoding="utf-8") as fh:
                summary = json.load(fh)
        if args.why:
            ans = why(scan, args.why)
        elif args.gate:
            ans = gate(scan, *args.gate)
        elif args.zone:
            ans = zone_freshness(scan, *args.zone)
        elif args.change:
            ans = what_would_change(scan, *args.change)
        elif args.compare:
            ans = compare(scan, *args.compare)
        else:
            ans = audit(scan, summary)
    except (OSError, ValueError) as e:
        print("error: %s" % e, file=sys.stderr)
        return 2
    if args.format == "json":
        sys.stdout.write(json.dumps(ans, sort_keys=True, indent=1) + "\n")
    else:
        sys.stdout.write(render_text(ans))
    return 1 if args.audit and ans["result"] != OK else 0


def add_commands(subparsers):
    p = subparsers.add_parser("explain", help="deterministic answers about a scan.json (evidence only)")
    p.add_argument("--scan", required=True, help="scan.json written by the scan command")
    q = p.add_mutually_exclusive_group(required=True)
    q.add_argument("--why", metavar="SYMBOL")
    q.add_argument("--gate", nargs=3, metavar=("SYMBOL", "ZONE", "GATE"))
    q.add_argument("--zone", nargs=2, metavar=("SYMBOL", "ZONE"), help="freshness from the overlay records")
    q.add_argument("--change", nargs=2, metavar=("SYMBOL", "ZONE"), help="conditions that are not met")
    q.add_argument("--compare", nargs=2, metavar=("A", "B"))
    q.add_argument("--audit", action="store_true", help="self-checks; exit 1 if inconsistencies are found")
    p.add_argument("--summary", help="summary.json for count reconciliation (default: next to --scan, if present)")
    p.add_argument("--format", default="text", choices=("text", "json"))
    p.set_defaults(func=cmd_explain)
    return p


def main(argv=None):
    p = argparse.ArgumentParser(prog="python3 -m nse.research.explain")
    sub = p.add_subparsers(dest="cmd", required=True)
    add_commands(sub)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
