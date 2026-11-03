"""Markdown narrative reports from a scan.json dict (reports.to_json). Deterministic, no clock.

The text restates recorded evidence: it never re-evaluates a gate or changes a status,
and nothing is hidden: rejected, blocked, data-insufficient and manual-review results are
listed with their deciding gate. Every report opens with a banner saying no status
approves a trade and nothing is externally validated (spec 8). generated_at is shown
only as recorded by the scan's caller.
"""

import os
import sys

from nse.research import explain, models as m

BANNER = ("> **Research output only.** No status approves a trade. %s means every automated gate passed "
          "and the manual checklist is still pending. Nothing here is externally validated; the "
          "limitations listed at the end apply." % m.ACTIONABLE)


def _md(v):
    if v is None:
        return "-"
    if isinstance(v, (list, tuple)):
        v = ", ".join(str(x) for x in v) or "-"
    return str(v).replace("|", "\\|").replace("\n", " ")


def _table(header, rows):
    out = ["| " + " | ".join(_md(h) for h in header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(_md(c) for c in r) + " |" for r in rows]
    return out


def _head(scan, title):
    return ["# " + title, "", BANNER, "",
            "- as_of: %s" % scan["as_of"],
            "- generated_at: %s" % (scan.get("generated_at") or "not recorded"),
            "- trade type: %s; calendar: %s; universe: %s" % (scan.get("trade_type"), scan.get("calendar"),
                                                               scan.get("universe")),
            "- pipeline %s; engines %s" % (scan.get("pipeline_version"), ", ".join(
                "%s %s" % kv for kv in sorted((scan.get("engine_versions") or {}).items()))), ""]


def _deciding(c):
    groups = explain.deciding_gates(c)
    if not groups:
        return "-", "every automated gate passed"
    g = groups[0][1][0]
    return "%s %s" % (g["gate"], g["outcome"]), (g["reasons"] or ["no reason recorded"])[0]


def _cands(scan):
    return [(s, c) for s in scan["symbols"] for c in s["candidates"]]


def _zone(c):
    return "%s:%s" % (c["execution_tf"], c["zone"]["zone_id"])


def daily_report(scan):
    lines = _head(scan, "Daily scan report %s" % scan["as_of"])
    sym_counts, cand_counts = {}, {}
    for s in scan["symbols"]:
        sym_counts[s["status"]] = sym_counts.get(s["status"], 0) + 1
    for _, c in _cands(scan):
        cand_counts[c["status"]] = cand_counts.get(c["status"], 0) + 1
    lines += ["## Counts", ""] + _table(["", "count"], [["symbols processed", len(scan["symbols"])]] +
                                        [["symbols " + k, v] for k, v in sorted(sym_counts.items())] +
                                        [["candidates " + k, v] for k, v in sorted(cand_counts.items())]) + [""]
    sections = ((m.ACTIONABLE, "Actionable candidates: manual checks pending"),
                (m.MANUAL_REVIEW, "Manual review"), (m.REJECTED, "Rejected"),
                (m.STATUS_DATA_INSUFFICIENT, "Data insufficient (candidates)"), (m.BLOCKED_STATUS, "Blocked (candidates)"))
    for status, title in sections:
        rows = []
        for s, c in _cands(scan):
            if c["status"] != status:
                continue
            if status == m.ACTIONABLE:
                rows.append([s["symbol"], _zone(c), c["zone"]["proximal"], c["zone"]["distal"],
                             "pending: " + ", ".join(x["code"] for x in c["manual_checks"])])
            else:
                gate, reason = _deciding(c)
                rows.append([s["symbol"], _zone(c), c["zone"]["proximal"], c["zone"]["distal"], gate + ": " + reason])
        lines += ["## %s (%d)" % (title, len(rows)), ""]
        lines += (_table(["symbol", "zone", "PL", "DL", "manual checks" if status == m.ACTIONABLE else
                          "deciding gate: first reason"], rows) if rows else ["none"]) + [""]
    others = [[s["symbol"], s["status"], "; ".join(s["reasons"]) or "-"] for s in scan["symbols"]
              if not s["candidates"]]
    lines += ["## Symbols without candidates (%d)" % len(others), ""]
    lines += (_table(["symbol", "status", "reasons"], others) if others else ["none"]) + [""]
    blocked = [[s["symbol"], b["tf"] + ":" + b["zone_id"], b["overlay_status"], b["disposition"], b["reasons"]]
               for s in scan["symbols"] for b in s.get("blocked_zones") or []]
    lines += ["## Zones removed by the MTF overlay (%d)" % len(blocked), ""]
    lines += (_table(["symbol", "zone", "overlay status", "disposition", "reasons"], blocked) if blocked else ["none"]) + [""]
    lines += _findings(scan["symbols"])
    issues = explain.inconsistencies(scan)
    lines += ["## Self-check", "", "%d inconsistencies found by explain.inconsistencies (no summary.json is read "
                                   "here; the counts above are computed from the records)." % len(issues), ""]
    lines += ["- %s %s %s: %s" % (i["code"], i["symbol"] or "-", i["zone_id"] or "-", i["detail"]) for i in issues]
    lines += _limitations(_all_limitations(scan, [x["symbol"] for x in scan["symbols"]]))
    return "\n".join(lines).rstrip() + "\n"


def _findings(symbols):
    rows = [[f["symbol"], f["severity"], f["code"], f.get("date"), f["verified"], f["detail"]]
            for s in symbols for f in s.get("findings") or []]
    rows.sort(key=lambda r: (r[0], r[2], str(r[3]), r[5]))
    out = ["## Data-quality findings (%d)" % len(rows), ""]
    return out + (_table(["symbol", "severity", "code", "date", "verified", "detail"], rows) if rows else ["none"]) + [""]


def _all_limitations(scan, symbols):
    """Scan, symbol and candidate limitations for the listed symbols (none is dropped)."""
    out = set(scan.get("limitations") or [])
    for x in scan["symbols"]:
        if x["symbol"] in symbols:
            out |= set(x.get("limitations") or [])
            for c in x.get("candidates") or []:
                out |= set(c.get("limitations") or [])
    return sorted(out)


def _limitations(lims):
    return ["## Limitations", ""] + ["- %s" % x for x in sorted(lims)] + ["- " + explain.AUTHORITY, ""]


def _candidate_section(c):
    z = c["zone"]
    out = ["### Candidate %s: %s" % (_zone(c), c["status"]), "",
           "- %s %s, PL %s, DL %s (normal DL %s), created %s, core %s, overlay %s, test_count %s"
           % (z["side"], z["pattern"], z["proximal"], z["distal"], z["normal_distal"], z["created_time"], z["core"],
              z["overlay_status"], z["test_count"]), ""]
    out += _table(["gate", "check", "outcome", "reasons", "manual items", "sources"],
                  [[g["gate"], m.GATE_TITLES.get(g["gate"]), g["outcome"], "; ".join(g["reasons"]),
                    g["manual_review"], g["sources"]] for g in c["gates"]]) + [""]
    lv = c["levels"]
    g7 = (explain.gate_of(c, "G7") or {}).get("evidence") or {}
    out += ["**Levels** (ranges over every printed buffer tier; no buffer is chosen, B9)", "",
            "- entry: %s to %s" % tuple(lv["entry"]),
            "- SL normal DL: %s to %s; exceptional DL: %s to %s" % tuple(lv["sl"]["normal"] + lv["sl"]["exceptional"]),
            "- target: %s" % ((g7.get("target") or {}).get("proximal", "not available")),
            "- R:R: %s (%s)" % ((g7.get("rr") or {}).get("rr", "not computed"), (g7.get("rr") or {}).get("status", "-")),
            ""]
    out += ["**Manual checklist (pending, a person decides)**", ""]
    out += ["- [ ] %s: %s (%s)" % (x["code"], x["check"], x["source"]) for x in c["manual_checks"]] + [""]
    out += ["**Evidence for**", ""] + ["- " + _md(x) for x in c["evidence_for"] or ["none"]] + [""]
    out += ["**Evidence against**", ""] + ["- " + _md(x) for x in c["evidence_against"] or ["none"]] + [""]
    return out


def stock_report(scan, symbol):
    lines = _head(scan, "Stock report %s at %s" % (symbol, scan["as_of"]))
    s = explain.symbol_record(scan, symbol)
    if s is None:
        lines += ["%s is NOT_IN_SCAN: this scan holds nothing about it." % symbol, ""]
        return "\n".join(lines + _limitations(scan["limitations"])).rstrip() + "\n"
    lines += ["- status: %s%s" % (s["status"], ": " + "; ".join(s["reasons"]) if s["reasons"] else ""),
              "- price (last completed candle at or before as_of): %s" % (s["price"] if s["price"] is not None
                                                                         else "not available"), ""]
    rows = []
    for r in s.get("tda") or []:
        d, u = r.get("fresh_demand_below"), r.get("fresh_supply_above")
        rows.append([r["tf"], r["series"]["status"], r["series"].get("completed_candles"),
                     "%s %s-%s" % (d["zone_id"], d["proximal"], d["distal"]) if d else "none found",
                     "%s %s-%s" % (u["zone_id"], u["proximal"], u["distal"]) if u else "none found",
                     len(r.get("unknown_freshness_closer") or []), r.get("missing")])
    lines += ["## Top-down analysis", ""]
    lines += (_table(["TF", "series", "completed candles", "fresh demand below", "fresh supply above",
                      "unknown-freshness zones closer", "missing"], rows) if rows else
              ["not available (the symbol was not evaluated)"]) + [""]
    lines += ["## Candidates (%d)" % len(s["candidates"]), ""]
    if not s["candidates"]:
        lines += ["none", ""]
    for c in s["candidates"]:
        lines += _candidate_section(c)
    blocked = [[b["tf"] + ":" + b["zone_id"], b["engine_status"], b["overlay_status"], b["disposition"], b["reasons"]]
               for b in s.get("blocked_zones") or []]
    lines += ["## Zones removed by the MTF overlay (%d)" % len(blocked), ""]
    lines += (_table(["zone", "engine status", "overlay status", "disposition", "reasons"], blocked)
              if blocked else ["none"]) + [""]
    fresh = [[r["tf"] + ":" + r["zone_id"], r["side"], r["pattern"], r["proximal"], r["distal"], r["core"],
              r["zone_level"]] for r in s.get("fresh_zones") or []]
    lines += ["## Fresh zones (overlay-fresh only; tested and invalidated zones are not listed, D3)", ""]
    lines += (_table(["zone", "side", "pattern", "PL", "DL", "core", "level"], fresh) if fresh else ["none"]) + [""]
    lines += _findings([s])
    lines += _limitations(sorted(set(scan["limitations"]) | set(s.get("limitations") or [])))
    return "\n".join(lines).rstrip() + "\n"


def comparison_report(scan, symbols):
    lines = _head(scan, "Comparison %s at %s" % (", ".join(symbols), scan["as_of"]))
    rows = []
    for sym in symbols:
        s = explain.symbol_record(scan, sym)
        if s is None:
            rows.append([sym, "NOT_IN_SCAN", "-", "-"] + ["-"] * len(m.GATES) + ["-"])
            continue
        if not s["candidates"]:
            rows.append([sym, s["status"], "-", "-"] + ["-"] * len(m.GATES) + ["; ".join(s["reasons"]) or "-"])
        for c in s["candidates"]:
            gate, reason = _deciding(c)
            rows.append([sym, s["status"], _zone(c), c["status"]] +
                        [explain.gate_of(c, g)["outcome"] for g in m.GATES] + [gate + ": " + reason])
    lines += _table(["symbol", "symbol status", "zone", "status"] + list(m.GATES) + ["deciding gate"], rows) + [""]
    lines += _limitations(_all_limitations(scan, symbols))
    return "\n".join(lines).rstrip() + "\n"


def cmd_report(args):
    try:
        scan = explain.load_scan(args.scan)
        if args.daily:
            text = daily_report(scan)
        elif args.stock:
            text = stock_report(scan, args.stock)
        else:
            syms = [x.strip() for x in args.compare.split(",") if x.strip()]
            if not syms:
                raise ValueError("--compare needs at least one symbol")
            text = comparison_report(scan, syms)
        if args.out:
            os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
            with open(args.out, "w", encoding="utf-8", newline="") as fh:
                fh.write(text)
            print("wrote %s" % args.out)
        else:
            sys.stdout.write(text)
    except (OSError, ValueError) as e:
        print("error: %s" % e, file=sys.stderr)
        return 2
    return 0


def add_commands(subparsers):
    p = subparsers.add_parser("report", help="markdown narrative report from a scan.json")
    p.add_argument("--scan", required=True)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--daily", action="store_true")
    g.add_argument("--stock", metavar="SYMBOL")
    g.add_argument("--compare", metavar="A,B,...")
    p.add_argument("--out", help="write the markdown here instead of stdout")
    p.set_defaults(func=cmd_report)
    return p
