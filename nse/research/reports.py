"""JSON and CSV reports for a ScanResult. Deterministic: keys sorted, rows sorted, no clock.

Files written by write_all(result, folder):
  scan.json            everything: every symbol, candidate, gate, blocked zone, finding
  candidates.csv       qualification report: one row per candidate, every gate outcome
  fresh_zones.csv      fresh-zone report (overlay-fresh zones only; D3)
  blocked_zones.csv    execution zones the overlay removed, with reasons (audit view)
  data_quality.csv     findings: missing, inconsistent or unverified inputs
  summary.json         symbol and status counts that reconcile with the records
  readiness.json       capability readiness (readiness.py)
No report hides a rejected, blocked or data-insufficient result.
"""

import csv
import datetime
import io
import json
import os
from dataclasses import asdict

from nse.research import models as m, readiness

CANDIDATE_COLUMNS = (
    "symbol", "trade_type", "execution_tf", "as_of", "status", "zone_id", "pattern", "proximal", "distal",
    "normal_distal", "created_time", "core", "overlay_status") + m.GATES + (
    "location", "trend_gate", "entry_min", "entry_max", "target", "rr_min", "rr_max",
    "status_reasons", "manual_review", "manual_checks", "limitations", "pre_entry_score")
FRESH_COLUMNS = ("symbol", "tf", "zone_id", "side", "pattern", "proximal", "distal", "normal_distal",
                 "base_count_pine", "base_count_incl_transitions", "zero_base", "legout_count",
                 "legout_count_pine", "has_gap", "gap_size", "strong_closing", "created_time",
                 "dl_touched", "core", "tags", "zone_level")
BLOCKED_COLUMNS = ("symbol", "tf", "zone_id", "engine_status", "overlay_status", "disposition", "reasons")
DQ_COLUMNS = ("symbol", "severity", "code", "detail", "verified")


def _default(v):
    if isinstance(v, (datetime.date, datetime.datetime)):
        return v.isoformat()
    if isinstance(v, (set, frozenset)):
        return sorted(v)
    raise TypeError("not JSON-serialisable: %s" % type(v).__name__)


def to_dict(result):
    return json.loads(json.dumps(asdict(result), default=_default, sort_keys=True))


def to_json(result):
    return json.dumps(to_dict(result), sort_keys=True, indent=1)


def summary(result):
    statuses = {}
    symbol_statuses = {}
    for s in result.symbols:
        symbol_statuses[s.status] = symbol_statuses.get(s.status, 0) + 1
        for c in s.candidates:
            statuses[c.status] = statuses.get(c.status, 0) + 1
    return {
        "as_of": result.as_of, "generated_at": result.generated_at, "trade_type": result.trade_type,
        "calendar": result.calendar, "universe": result.universe, "pipeline_version": result.pipeline_version,
        "symbols_processed": len(result.symbols), "symbol_status_counts": dict(sorted(symbol_statuses.items())),
        "candidate_records": sum(statuses.values()), "candidate_status_counts": dict(sorted(statuses.items())),
        "blocked_zone_records": sum(len(s.blocked_zones) for s in result.symbols),
        "fresh_zone_records": sum(len(s.fresh_zones) for s in result.symbols),
        "data_quality_findings": sum(len(s.findings) for s in result.symbols),
        "limitations": result.limitations,
        "note": "No status approves a trade. ACTIONABLE means every automated gate passed; the manual "
                "checklist is still pending. Nothing here is externally validated.",
    }


def _cell(v):
    if v is None:
        return ""
    if isinstance(v, (list, tuple)):
        return " | ".join(str(x) for x in v)
    return str(v)


def candidate_rows(result):
    """One row per candidate. limitations carries the scan's and the symbol's as well as the
    candidate's own, so a CSV row alone never hides UNIVERSE_UNVERIFIED or similar (audit
    2026-11-06, Agent 6 #6)."""
    rows = []
    outer = {}
    for s in result.symbols:
        outer[s.symbol] = set(result.limitations or []) | set(s.limitations or [])
    for c in result.candidates():
        g = {x.gate: x.outcome for x in c.gates}
        g3 = c.gate("G3").evidence
        g4 = c.gate("G4").evidence.get("gate") or {}
        g7 = c.gate("G7").evidence
        rr = (g7.get("rr") or {}).get("rr") or [None, None]
        row = {"symbol": c.symbol, "trade_type": c.trade_type, "execution_tf": c.execution_tf, "as_of": c.as_of,
               "status": c.status, "zone_id": c.zone["zone_id"], "pattern": c.zone["pattern"],
               "proximal": c.zone["proximal"], "distal": c.zone["distal"], "normal_distal": c.zone["normal_distal"],
               "created_time": c.zone["created_time"], "core": c.zone["core"],
               "overlay_status": c.zone["overlay_status"],
               "location": "CMP %s" % g3.get("position_at_price") if g3 else "",
               "trend_gate": "%s %s %s%s" % (g4.get("tf", ""), g4.get("status", ""),
                                               g4.get("position") or "",
                                               " (" + g4["rulebook_label"] + ")" if g4.get("rulebook_label") else ""),
               "entry_min": c.levels["entry"][0], "entry_max": c.levels["entry"][1],
               "target": (g7.get("target") or {}).get("proximal"), "rr_min": rr[0], "rr_max": rr[1],
               "status_reasons": c.status_reasons, "manual_review": c.manual_review,
               "manual_checks": [x["code"] for x in c.manual_checks],
               "limitations": sorted(set(c.limitations) | outer.get(c.symbol, set(result.limitations or []))),
               "pre_entry_score": (c.zone.get("pre_entry_score") or {}).get("display")}
        row.update(g)
        rows.append(row)
    return sorted(rows, key=lambda r: (r["symbol"], r["created_time"], r["zone_id"]))


def _csv(columns, rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(columns), lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: _cell(r.get(k)) for k in columns})
    return buf.getvalue()


def candidates_csv(result):
    return _csv(CANDIDATE_COLUMNS, candidate_rows(result))


def fresh_zones_csv(result):
    rows = [r for s in result.symbols for r in s.fresh_zones]
    return _csv(FRESH_COLUMNS, sorted(rows, key=lambda r: (r["symbol"], r["tf"], r["created_time"], r["zone_id"])))


def blocked_zones_csv(result):
    rows = [dict(b, symbol=s.symbol) for s in result.symbols for b in s.blocked_zones]
    return _csv(BLOCKED_COLUMNS, sorted(rows, key=lambda r: (r["symbol"], r["tf"], r["zone_id"])))


def data_quality_csv(result):
    rows = [f for s in result.symbols for f in s.findings]
    return _csv(DQ_COLUMNS, sorted(rows, key=lambda r: (r["symbol"], r["code"], r["detail"])))


def write_all(result, folder, passed_modules=None):
    os.makedirs(folder, exist_ok=True)
    files = {
        "scan.json": to_json(result) + "\n",
        "candidates.csv": candidates_csv(result),
        "fresh_zones.csv": fresh_zones_csv(result),
        "blocked_zones.csv": blocked_zones_csv(result),
        "data_quality.csv": data_quality_csv(result),
        "summary.json": json.dumps(summary(result), sort_keys=True, indent=1) + "\n",
        "readiness.json": json.dumps(readiness.report(passed_modules), sort_keys=True, indent=1) + "\n",
    }
    for name, text in sorted(files.items()):
        with open(os.path.join(folder, name), "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
    return sorted(files)
