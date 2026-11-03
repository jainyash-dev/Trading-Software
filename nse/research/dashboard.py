"""Static research dashboard: HTML pages from a scan output folder (reports.write_all).

build(scan_dir, out_dir, bundles_dir=None) reads scan.json, summary.json, readiness.json
and data_quality.csv and writes:
  index.html            overview: as_of, generated_at label, universe and limitations,
                        status counts reconciled with the records, data-quality counts,
                        readiness with every state in its own column (never one tick)
  scanner.html          every symbol and candidate, including rejected, blocked,
                        data-insufficient and manual ones; search, status filter, sorting
  symbol-<slug>.html    gate-by-gate breakdown, manual items, checklist, evidence,
                        limitations, TDA; with a decision bundle (decision_replay) for the
                        same as_of and trade type, an SVG chart per timeframe
render_decision(bundle) is the same symbol page for one replay-decision bundle.

Display only: every status, gate outcome and zone label is copied from the scan or the
bundle, never recomputed. Pages work offline from file:// (no external URL, font or
script), every text is html.escape'd, and no clock is read: the same inputs give
identical bytes. No status shown here approves a trade (spec 8, 11).
"""

import bisect
import csv
import html
import json
import os
import sys

from nse.research import decision_replay as dr, models as m

BANNER = ("Research decision support only. No status approves a trade: %s means every automated "
          "gate passed and the manual checklist is still pending. Nothing here is externally "
          "validated (%s)." % (m.ACTIONABLE, m.NOT_EXTERNALLY_VALIDATED))
CHART_BARS = 180                       # last completed candles drawn per timeframe (display only)
TF_ORDER = ("D", "W", "M", "Q", "HY", "Y", "75m", "125m")
REQUIRED = ("scan.json", "summary.json", "readiness.json", "data_quality.csv")
READINESS_COLUMNS = ("implemented", "unit_tested", "unit_tested_state", "integration_tested",
                     "integration_tested_state", "reference_validated", "externally_validated",
                     "deferred", "blocked", "requires_human_decision", "limits")
LEGEND = ((dr.CLASS_FRESH_DEMAND, "fresh demand (overlay FRESH)"),
          (dr.CLASS_FRESH_SUPPLY, "fresh supply (context only, never a candidate)"),
          (dr.CLASS_TESTED, "tested (not fresh; never a fresh candidate)"),
          (dr.CLASS_INVALIDATED, "invalidated"),
          (dr.CLASS_UNKNOWN, "unknown freshness (gap, unverified session, manual flag)"),
          ("lv-entry", "entry range"), ("lv-sl", "stop-loss range"), ("lv-target", "target (proximal)"))

CSS = """
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:0 1.2em 2em;color:#1d232a;font-size:14px}
nav{padding:.6em 0;border-bottom:1px solid #ccd}nav a{margin-right:1.2em}
.banner{background:#fff4d6;border:2px solid #c98a00;padding:.7em 1em;margin:.8em 0;font-weight:600}
table{border-collapse:collapse;margin:.4em 0 1em}th,td{border:1px solid #ccd;padding:3px 6px;text-align:left;vertical-align:top}
th{background:#eef0f4}th.sortable{cursor:pointer}td.num{text-align:right;font-variant-numeric:tabular-nums}
.mismatch{background:#ffd6d6;font-weight:700}.ok{font-weight:600}
.s-PASS{color:#1f6f2f}.s-FAIL,.s-REJECTED{color:#b00020;font-weight:600}
.s-MANUAL,.s-MANUAL_REVIEW{color:#8a5a00;font-weight:600}.s-DATA_INSUFFICIENT,.s-BLOCKED{color:#5b2a86;font-weight:600}
.s-NOT_EVALUATED{color:#666}.st-true{font-weight:600}.st-false{color:#666}
.controls input,.controls select{margin-right:1em;padding:3px}
.tfbtn{margin-right:.3em;padding:3px 10px}.tfbtn.on{background:#1d232a;color:#fff}
svg.chart{border:1px solid #ccd;background:#fff}
.c-up{fill:#fff;stroke:#1d232a}.c-down{fill:#1d232a;stroke:#1d232a}.wick{stroke:#1d232a}
.zone{stroke-width:1.2}
.z-fresh-demand{fill:#2e9e4a;fill-opacity:.28;stroke:#1f6f2f}
.z-fresh-supply-context{fill:#3a6fd8;fill-opacity:.2;stroke:#2a4fa0}
.z-tested{fill:#e08a00;fill-opacity:.16;stroke:#a86200;stroke-dasharray:6 3}
.z-invalidated{fill:#888;fill-opacity:.14;stroke:#555;stroke-dasharray:2 2}
.z-unknown{fill:#8e44ad;fill-opacity:.14;stroke:#6c2f86;stroke-dasharray:1 3}
.lv-entry{fill:#00a0a0;fill-opacity:.25;stroke:#007070}.lv-sl{fill:#d02020;fill-opacity:.2;stroke:#a01010}
.lv-target{stroke:#2a4fa0;stroke-width:2;stroke-dasharray:8 4;fill:none}
.axis{font-size:10px;fill:#444}.legend span.sw{display:inline-block;width:18px;height:10px;margin:0 4px 0 12px;border:1px solid #555}
.sw.z-fresh-demand{background:#9fd4ad}.sw.z-fresh-supply-context{background:#b5c8ef}.sw.z-tested{background:#f5d9ad;border-style:dashed}.sw.z-invalidated{background:#ddd;border-style:dotted}.sw.z-unknown{background:#ddc6e6;border-style:dotted}.sw.lv-entry{background:#a6dede}.sw.lv-sl{background:#f1b3b3}.sw.lv-target{height:0;border:0;border-top:2px dashed #2a4fa0}
tr.z-tested td,tr.z-invalidated td,tr.z-unknown td{color:#555}
"""

JS_TABLE = """
(function(){
var t=document.getElementById('scan-table');if(!t)return;
var q=document.getElementById('q'),f=document.getElementById('status-filter'),b=t.tBodies[0];
function apply(){var s=q.value.toLowerCase(),st=f.value,n=0;
for(var i=0;i<b.rows.length;i++){var r=b.rows[i];
var ok=(!st||r.getAttribute('data-status')===st)&&(!s||r.textContent.toLowerCase().indexOf(s)>=0);
r.style.display=ok?'':'none';if(ok)n++;}
document.getElementById('shown').textContent=n;}
q.addEventListener('input',apply);f.addEventListener('change',apply);
var hs=t.tHead.rows[0].cells;
for(var j=0;j<hs.length;j++){(function(k){hs[k].addEventListener('click',function(){
var dir=hs[k].getAttribute('data-dir')==='asc'?'desc':'asc';hs[k].setAttribute('data-dir',dir);
var rows=Array.prototype.slice.call(b.rows);
rows.sort(function(x,y){var a=x.cells[k].getAttribute('data-sort'),c=y.cells[k].getAttribute('data-sort');
var na=parseFloat(a),nc=parseFloat(c),r;
if(!isNaN(na)&&!isNaN(nc)&&String(na)===a&&String(nc)===c){r=na-nc;}else{r=a<c?-1:(a>c?1:0);}
return dir==='asc'?r:-r;});
for(var i=0;i<rows.length;i++)b.appendChild(rows[i]);});})(j);}
apply();})();
"""

JS_TF = """
(function(){
var bs=document.querySelectorAll('.tfbtn'),ps=document.querySelectorAll('.tfpanel');
for(var i=0;i<bs.length;i++){bs[i].addEventListener('click',function(){
var tf=this.getAttribute('data-tf');
for(var j=0;j<ps.length;j++){ps[j].hidden=ps[j].getAttribute('data-tf')!==tf;}
for(var k=0;k<bs.length;k++){bs[k].className=bs[k].getAttribute('data-tf')===tf?'tfbtn on':'tfbtn';}});}
})();
"""


# --- text helpers -------------------------------------------------------------------------

def e(v):
    return html.escape(fmt(v), quote=True)


def fmt(v):
    if v is None:
        return "-"
    if isinstance(v, bool):
        return "YES" if v else "NO"
    if isinstance(v, float):
        return "%g" % v
    if isinstance(v, (list, tuple)):
        return ", ".join(fmt(x) for x in v) if v else "none"
    if isinstance(v, dict):
        return json.dumps(v, sort_keys=True)
    return str(v)


def slug(symbol):
    """File-name-safe and injective: ASCII letters and digits kept, every other character
    (including "_") written as _XX hex."""
    return "".join(ch if (ord(ch) < 128 and ch.isalnum()) or ch == "-" else "_%02X" % ord(ch) for ch in symbol)


def symbol_href(symbol):
    return "symbol-%s.html" % slug(symbol)


def _cls(outcome):
    return "s-%s" % "".join(ch for ch in str(outcome) if ch.isalnum() or ch == "_")


def _table(headers, rows, cls=None, row_classes=None):
    out = ["<table%s><thead><tr>%s</tr></thead><tbody>" % (
        ' class="%s"' % cls if cls else "", "".join("<th>%s</th>" % e(h) for h in headers))]
    for i, r in enumerate(rows):
        rc = row_classes[i] if row_classes else None
        out.append("<tr%s>%s</tr>" % (' class="%s"' % e(rc) if rc else "", "".join("<td>%s</td>" % e(c) for c in r)))
    if not rows:
        out.append('<tr><td colspan="%d">none</td></tr>' % len(headers))
    out.append("</tbody></table>")
    return "".join(out)


def _list(items):
    if not items:
        return "<p>none</p>"
    return "<ul>%s</ul>" % "".join("<li>%s</li>" % e(x) for x in items)


def _page(title, body, nav=True, scripts=()):
    links = '<nav><a href="index.html">Overview</a><a href="scanner.html">Scanner</a></nav>' if nav else ""
    js = "".join("<script>%s</script>" % s for s in scripts)
    return ('<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            "<title>%s</title><style>%s</style></head><body>%s"
            '<div class="banner" id="banner">%s</div>%s%s</body></html>\n'
            % (e(title), CSS, links, e(BANNER), body, js))


# --- loading -----------------------------------------------------------------------------

def load_scan(scan_dir):
    missing = [f for f in REQUIRED if not os.path.isfile(os.path.join(scan_dir, f))]
    if missing:
        raise ValueError("%s is not a scan output folder (reports.write_all): missing %s"
                         % (scan_dir, ", ".join(missing)))
    out = {}
    for name in REQUIRED[:3]:
        with open(os.path.join(scan_dir, name), encoding="utf-8") as fh:
            out[name.split(".")[0]] = json.load(fh)
    with open(os.path.join(scan_dir, "data_quality.csv"), encoding="utf-8", newline="") as fh:
        out["data_quality"] = list(csv.DictReader(fh))
    return out


def load_bundles(bundles_dir):
    """Bundles in bundles_dir: SOMETHING.json files and SOMETHING/decision.json. Returns
    {symbol: [bundle, ...]} in file-name order."""
    found = {}
    if not bundles_dir:
        return found
    if not os.path.isdir(bundles_dir):
        raise ValueError("bundles folder %s does not exist" % bundles_dir)
    for name in sorted(os.listdir(bundles_dir)):
        path = os.path.join(bundles_dir, name)
        if os.path.isdir(path):
            path = os.path.join(path, "decision.json")
            if not os.path.isfile(path):
                continue
        elif not name.endswith(".json"):
            continue
        with open(path, encoding="utf-8") as fh:
            b = json.load(fh)
        if not isinstance(b, dict) or "bundle_version" not in b or "symbol" not in b:
            continue                                  # not a decision bundle
        found.setdefault(b["symbol"], []).append(b)
    return found


def _matching_bundle(bundles, symbol, as_of, trade_type, calendar=None, symbol_record=None):
    """The bundle for the scan's as_of and trade type, or (None, note). When the scan's
    calendar label and symbol record are given, the bundle must have the same calendar and an
    identical symbol_result: a chart from another replay is never drawn beside these records."""
    bs = bundles.get(symbol, [])
    if not bs:
        return None, "No decision bundle for this symbol (python3 -m nse.research.cli replay-decision)."
    same = [b for b in bs if b.get("as_of") == as_of and b.get("trade_type") == trade_type]
    if not same:
        return None, ("Decision bundle(s) exist for as_of %s, not this scan's %s %s: not shown."
                      % (", ".join(sorted(set(str(b.get("as_of")) + " " + str(b.get("trade_type")) for b in bs))),
                         as_of, trade_type))
    if any(dr.to_json(b) != dr.to_json(same[0]) for b in same[1:]):
        return None, "Conflicting decision bundles for the same as_of: not shown."
    b = same[0]
    if calendar is not None and b.get("calendar") != calendar:
        return None, ("Decision bundle used calendar %s, this scan %s: a different replay, not shown."
                      % (b.get("calendar"), calendar))
    if symbol_record is not None and b.get("symbol_result") != symbol_record:
        return None, "Decision bundle's decision differs from this scan's record (different inputs): not shown."
    return b, None


# --- scanner rows (copied from the scan, never recomputed) ----------------------------------

def _gate(c, name):
    for g in c["gates"]:
        if g["gate"] == name:
            return g
    return {"outcome": "-", "evidence": {}, "reasons": [], "manual_review": []}


def _range(v):
    if not v or v[0] is None:
        return "-"
    return "%s - %s" % (fmt(v[0]), fmt(v[1]))


def candidate_row(sym, c):
    g3, g4, g6, g7 = (_gate(c, x) for x in ("G3", "G4", "G6", "G7"))
    tg = g4["evidence"].get("gate") or {}
    rr = g7["evidence"].get("rr") or {}
    trend = " ".join(fmt(x) for x in (tg.get("tf"), tg.get("status"), tg.get("position")) if x)
    if tg.get("rulebook_label"):
        trend += " (%s)" % tg["rulebook_label"]
    return {
        "symbol": sym["symbol"], "status": c["status"], "kind": "candidate",
        "zone": "%s %s %s PL %s DL %s" % (c["zone"].get("tf"), c["zone"].get("zone_id"), c["zone"].get("pattern"),
                                         fmt(c["zone"].get("proximal")), fmt(c["zone"].get("distal"))),
        "core": c["zone"].get("core"),
        "location": "%s %s" % (g3["outcome"], fmt(g3["evidence"].get("position_at_price"))),
        "trend": "%s %s" % (g4["outcome"], trend or "-"),
        "coinciding": "%s %s" % (g6["outcome"], fmt(g6["evidence"].get("class"))),
        "rr": "%s %s" % (_range(rr.get("rr")), rr.get("status") or g7["outcome"]),
        "entry": _range(c["levels"].get("entry")),
        "gates": "; ".join("%s %s" % (g["gate"], g["outcome"]) for g in c["gates"] if g["outcome"] != m.PASS) or "none",
    }


def scanner_rows(scan):
    rows = []
    for sym in sorted(scan["symbols"], key=lambda s: s["symbol"]):
        if not sym["candidates"]:
            rows.append({"symbol": sym["symbol"], "status": sym["status"], "kind": "symbol", "zone": "-",
                         "core": "-", "location": "-", "trend": "-", "coinciding": "-", "rr": "-", "entry": "-",
                         "gates": "symbol: " + ("; ".join(sym["reasons"]) or "no candidate")})
            continue
        for c in sorted(sym["candidates"], key=lambda c: (c["zone"].get("created_time") or "", c["zone"]["zone_id"])):
            rows.append(candidate_row(sym, c))
    return rows


SCANNER_COLUMNS = (("symbol", "Symbol"), ("status", "Status"), ("zone", "Zone"), ("core", "Core"),
                   ("location", "Location (G3)"), ("trend", "Trend (G4)"), ("coinciding", "Coinciding (G6)"),
                   ("rr", "R:R range (G7)"), ("entry", "Entry range"), ("gates", "Failing / manual gates"))


def scanner_page(scan):
    rows = scanner_rows(scan)
    statuses = sorted(set(r["status"] for r in rows))
    body = ['<h1>Scanner: %s %s</h1>' % (e(scan["trade_type"]), e(scan["as_of"])),
            "<p>Every symbol and every candidate, including rejected, blocked, data-insufficient and "
            "manual-review results. A symbol without a candidate is one row with its own status and reason.</p>",
            '<div class="controls"><label>Search <input id="q" type="search"></label>'
            '<label>Status <select id="status-filter"><option value="">all</option>%s</select></label>'
            'Showing <span id="shown">%d</span> of %d rows</div>'
            % ("".join('<option value="%s">%s</option>' % (e(s), e(s)) for s in statuses), len(rows), len(rows)),
            '<table id="scan-table"><thead><tr>%s</tr></thead><tbody>'
            % "".join('<th class="sortable">%s</th>' % e(t) for _, t in SCANNER_COLUMNS)]
    for r in rows:
        cells = []
        for k, _ in SCANNER_COLUMNS:
            v = fmt(r[k])
            inner = '<a href="%s">%s</a>' % (e(symbol_href(r["symbol"])), e(v)) if k == "symbol" else e(v)
            cls = ' class="%s"' % _cls(v) if k == "status" else ""
            cells.append('<td data-sort="%s"%s>%s</td>' % (e(v), cls, inner))
        body.append('<tr data-status="%s" data-kind="%s">%s</tr>' % (e(r["status"]), e(r["kind"]), "".join(cells)))
    body.append("</tbody></table>")
    return _page("Scanner %s" % scan["as_of"], "".join(body), scripts=(JS_TABLE,))


# --- overview ------------------------------------------------------------------------------

def _counts(items):
    out = {}
    for x in items:
        out[x] = out.get(x, 0) + 1
    return out


def _reconcile_table(title, key, from_summary, from_records):
    rows = []
    for k in sorted(set(from_summary) | set(from_records)):
        a, b = from_summary.get(k, 0), from_records.get(k, 0)
        rows.append('<tr><td>%s</td><td class="num" data-count="%s:%s">%d</td><td class="num">%d</td>'
                    '<td class="%s">%s</td></tr>' % (e(k), e(key), e(k), a, b, "ok" if a == b else "mismatch",
                                                     "RECONCILED" if a == b else "MISMATCH"))
    if not rows:
        rows.append('<tr><td colspan="4">none</td></tr>')
    return ("<h2>%s</h2><table><thead><tr><th>Status</th><th>summary.json</th><th>records</th><th>check</th></tr>"
            "</thead><tbody>%s</tbody></table>" % (e(title), "".join(rows)))


def _state_cell(v):
    cls = "st-true" if v is True else "st-false" if v in (False, [], "NO", None) else "st-text"
    return '<td class="%s">%s</td>' % (cls, e(v))


def index_page(data):
    scan, summ = data["scan"], data["summary"]
    syms = scan["symbols"]
    sym_records = _counts(s["status"] for s in syms)
    cand_records = _counts(c["status"] for s in syms for c in s["candidates"])
    totals = (("symbols_processed", len(syms)),
              ("candidate_records", sum(len(s["candidates"]) for s in syms)),
              ("blocked_zone_records", sum(len(s["blocked_zones"]) for s in syms)),
              ("fresh_zone_records", sum(len(s["fresh_zones"]) for s in syms)),
              ("data_quality_findings", len(data["data_quality"])))
    body = ["<h1>NSE demand and supply research scan</h1>",
            _table(("Field", "Value"), [
                ("as_of", scan["as_of"]),
                ("generated_at", scan["generated_at"] if scan.get("generated_at") else
                 "not recorded (no clock is read; pass --generated-at to label a scan)"),
                ("trade_type", scan["trade_type"]), ("calendar", scan["calendar"]),
                ("universe", scan["universe"]), ("pipeline_version", scan["pipeline_version"]),
                ("engine_versions", scan["engine_versions"])]),
            "<h2>Scan limitations</h2>", _list(scan["limitations"]),
            "<h2>Totals</h2><table><thead><tr><th>Count</th><th>summary.json</th><th>records</th><th>check</th>"
            "</tr></thead><tbody>"]
    for k, n in totals:
        a = summ.get(k)
        body.append('<tr><td>%s</td><td class="num" data-count="total:%s">%s</td><td class="num">%d</td>'
                    '<td class="%s">%s</td></tr>' % (e(k), e(k), e(a), n, "ok" if a == n else "mismatch",
                                                     "RECONCILED" if a == n else "MISMATCH"))
    body.append("</tbody></table>")
    body.append(_reconcile_table("Symbol status counts", "symbol", summ.get("symbol_status_counts", {}), sym_records))
    body.append(_reconcile_table("Candidate status counts", "candidate", summ.get("candidate_status_counts", {}),
                                 cand_records))
    body.append("<p>%s</p>" % e(summ.get("note", "")))
    dq = data["data_quality"]
    body.append("<h2>Data quality</h2>")
    body.append(_table(("Severity", "Findings"), sorted(_counts(r["severity"] for r in dq).items())))
    body.append(_table(("Code", "Findings"), sorted(_counts(r["code"] for r in dq).items())))
    body.append("<h2>Readiness</h2><p>Each state is shown separately. Unit and integration test claims are "
                "only CONFIRMED when the validation runner passed those modules in the same run.</p>")
    hdr = ("Capability", "Component") + READINESS_COLUMNS
    body.append("<table id=\"readiness\"><thead><tr>%s</tr></thead><tbody>" % "".join("<th>%s</th>" % e(h) for h in hdr))
    for r in sorted(data["readiness"], key=lambda r: r.get("id", "")):
        body.append("<tr><td>%s</td><td>%s</td>%s</tr>" % (e(r.get("id")), e(r.get("component")),
                                                           "".join(_state_cell(r.get(k)) for k in READINESS_COLUMNS)))
    body.append("</tbody></table>")
    body.append("<h2>Symbols</h2><ul>%s</ul>" % "".join(
        '<li><a href="%s">%s</a>: <span class="%s">%s</span></li>' % (e(symbol_href(s["symbol"])), e(s["symbol"]),
                                                                     _cls(s["status"]), e(s["status"]))
        for s in sorted(syms, key=lambda s: s["symbol"])))
    return _page("Scan %s" % scan["as_of"], "".join(body))


# --- chart -----------------------------------------------------------------------------------

def _n(v):
    return "%.2f" % v


def chart_svg(b, tf, sym):
    """Inline SVG of the completed candles on tf (at or before as_of; the bundle holds no
    other), zone rectangles PL to DL classed by the overlay status, and, on the execution
    timeframe, each candidate's entry range, SL range and target."""
    candles = b["candles"].get(tf, [])[-CHART_BARS:]
    if not candles:
        return "<p>No completed candles on %s at as_of.</p>" % e(tf)
    w, h, pl, pr, pt, pb = 960, 420, 8, 64, 10, 26
    n = len(candles)
    step = (w - pl - pr) / float(n)
    lo = min(c["low"] for c in candles)
    hi = max(c["high"] for c in candles)
    levels = []
    if tf == b.get("execution_tf"):
        for c in sym.get("candidates", []):
            lv, g7 = c["levels"], _gate(c, "G7")["evidence"]
            ent = lv.get("entry") or [None, None]
            sls = [x for k in ("normal", "exceptional") for x in (lv.get("sl") or {}).get(k, []) if x is not None]
            tgt = (g7.get("target") or {}).get("proximal")
            levels.append((c["zone"]["zone_id"], ent, [min(sls), max(sls)] if sls else [None, None], tgt))
            for v in ent + ([min(sls), max(sls)] if sls else []) + [tgt]:
                if v is not None:
                    lo, hi = min(lo, v), max(hi, v)
    if hi <= lo:
        hi = lo + 1.0
    pad = (hi - lo) * 0.03
    lo, hi = lo - pad, hi + pad

    def y(p):
        return pt + (hi - min(max(p, lo), hi)) / (hi - lo) * (h - pt - pb)

    ends = [c["end"] for c in candles]
    out = ['<svg class="chart" viewBox="0 0 %d %d" width="%d" height="%d" role="img" aria-label="%s">'
           % (w, h, w, h, e("%s %s candles to %s" % (b["symbol"], tf, b["as_of"])))]
    outside = []
    for z in b["zones"].get(tf, []):
        top, bot = max(z["proximal"], z["distal"]), min(z["proximal"], z["distal"])
        gone = z.get("invalidation_known_at") and z["invalidation_known_at"] < ends[0]
        if bot > hi or top < lo or z["created_time"] > ends[-1] or gone:
            outside.append(z["zone_id"])
            continue
        i0 = bisect.bisect_left(ends, z["created_time"])
        i1 = n
        if z.get("invalidation_known_at"):
            i1 = min(n, bisect.bisect_left(ends, z["invalidation_known_at"]) + 1)
        x0, x1 = pl + i0 * step, pl + max(i1, i0 + 1) * step
        out.append('<rect class="zone %s" data-zone="%s:%s" data-freshness="%s" x="%s" y="%s" width="%s" height="%s">'
                   '<title>%s</title></rect>'
                   % (e(z["display_class"]), e(tf), e(z["zone_id"]), e(z["freshness"]), _n(x0), _n(y(top)),
                      _n(x1 - x0), _n(max(y(bot) - y(top), 1.0)),
                      e("%s %s %s PL %s DL %s: %s (overlay %s)" % (tf, z["zone_id"], z["side"], fmt(z["proximal"]),
                                                                   fmt(z["distal"]), z["freshness"], z["overlay_status"]))))
    for i, c in enumerate(candles):
        cx = pl + (i + 0.5) * step
        bw = max(step * 0.6, 1.0)
        o, cl = c["open"], c["close"]
        out.append('<line class="wick" x1="%s" y1="%s" x2="%s" y2="%s"/>' % (_n(cx), _n(y(c["high"])), _n(cx), _n(y(c["low"]))))
        out.append('<rect class="%s" x="%s" y="%s" width="%s" height="%s"><title>%s</title></rect>'
                   % ("c-up" if cl >= o else "c-down", _n(cx - bw / 2), _n(y(max(o, cl))), _n(bw),
                      _n(max(abs(y(o) - y(cl)), 0.8)),
                      e("%s O %s H %s L %s C %s" % (c["end"], fmt(o), fmt(c["high"]), fmt(c["low"]), fmt(cl)))))
    x_end = pl + n * step
    for zid, ent, sl, tgt in levels:
        for cls, band, label in (("lv-entry", ent, "entry range"), ("lv-sl", sl, "SL range")):
            if band[0] is not None:
                out.append('<rect class="%s" x="%s" y="%s" width="%s" height="%s"><title>%s</title></rect>'
                           % (cls, _n(x_end - 12 * step), _n(y(band[1])), _n(12 * step),
                              _n(max(y(band[0]) - y(band[1]), 1.0)), e("%s %s %s" % (zid, label, _range(band)))))
        if tgt is not None:
            out.append('<line class="lv-target" x1="%s" y1="%s" x2="%s" y2="%s"><title>%s</title></line>'
                       % (_n(pl), _n(y(tgt)), _n(x_end), _n(y(tgt)), e("%s target %s" % (zid, fmt(tgt)))))
    for k in range(5):
        p = lo + (hi - lo) * k / 4.0
        out.append('<text class="axis" x="%s" y="%s">%s</text>' % (_n(x_end + 4), _n(y(p) + 3), e("%.2f" % p)))
    for i in sorted(set((0, n // 2, n - 1))):
        out.append('<text class="axis" x="%s" y="%d">%s</text>' % (_n(pl + i * step), h - 8, e(ends[i][:10])))
    out.append("</svg>")
    note = ""
    if outside:
        note = "<p>%d zone(s) lie outside the drawn price range or window and are listed in the table only.</p>" % len(outside)
    return "".join(out) + note


def chart_section(b, sym):
    tfs = [tf for tf in TF_ORDER if b["candles"].get(tf)]
    if not tfs:
        return "<h2>Chart</h2><p>No candles in the decision bundle (%s).</p>%s" % (e(b.get("replay")), _list(b["limitations"]))
    first = b.get("execution_tf") if b.get("execution_tf") in tfs else tfs[0]
    out = ["<h2>Chart at as_of %s</h2><p>%s Last %d completed candles per timeframe are drawn.</p>"
           % (e(b["as_of"]), e(b["chart_note"]), CHART_BARS),
           '<div class="legend">%s</div>' % "".join(
               '<span class="sw %s"></span>%s' % (e(c), e(t)) for c, t in LEGEND),
           '<div class="tfsel">%s</div>' % "".join(
               '<button type="button" class="tfbtn%s" data-tf="%s">%s</button>' % (" on" if tf == first else "", e(tf), e(tf))
               for tf in tfs)]
    for tf in tfs:
        zones = b["zones"].get(tf, [])
        rows = [(z["zone_id"], z["side"], z["pattern"], z["proximal"], z["distal"], z["created_time"],
                 z["freshness"], z["overlay_status"], z["overlay_kept"], z["engine_status"], z["core"],
                 z["first_touch_at"], z["invalidation_known_at"]) for z in zones]
        out.append('<div class="tfpanel" data-tf="%s"%s><h3>%s (%s)</h3>%s<h4>Zones on %s</h4>%s</div>'
                   % (e(tf), "" if tf == first else " hidden", e(tf), e(b["series"].get(tf, {}).get("status")),
                      chart_svg(b, tf, sym), e(tf),
                      _table(("Zone", "Side", "Pattern", "PL", "DL", "Created", "Freshness", "Overlay status",
                              "Kept by overlay", "Engine status", "Core", "First touch", "Invalidated"),
                             rows, row_classes=[z["display_class"] for z in zones])))
    if b.get("data_gaps"):
        out.append("<h3>Data gaps</h3>" + _table(("Date", "Kind", "Verified"),
                                                 [(g["date"], g["kind"], g["verified"]) for g in b["data_gaps"]]))
    if b.get("excluded_candles"):
        out.append("<h3>Excluded candles</h3>" + _table(("Date", "Classification"),
                                                        [(x["date"], x["classification"]) for x in b["excluded_candles"]]))
    return "".join(out)


# --- symbol page -----------------------------------------------------------------------------

def _candidate_section(c):
    g7 = _gate(c, "G7")["evidence"]
    lv = c["levels"]
    z = c["zone"]
    out = ['<h3 id="%s">%s %s: <span class="%s">%s</span></h3>' % (
        e("c-" + str(z.get("zone_id"))), e(z.get("tf")), e(z.get("zone_id")), _cls(c["status"]), e(c["status"]))]
    out.append(_table(("Zone field", "Value"), sorted((k, v) for k, v in z.items())))
    out.append("<h4>Status reasons</h4>" + _list(c["status_reasons"]))
    out.append("<h4>Gates</h4><table><thead><tr><th>Gate</th><th>Title</th><th>Outcome</th><th>Reasons</th>"
               "<th>Manual review</th><th>Sources</th></tr></thead><tbody>")
    for g in c["gates"]:
        out.append('<tr><td>%s</td><td>%s</td><td class="%s">%s</td><td>%s</td><td>%s</td><td>%s</td></tr>'
                   % (e(g["gate"]), e(m.GATE_TITLES.get(g["gate"])), _cls(g["outcome"]), e(g["outcome"]),
                      _list(g["reasons"]), _list(g["manual_review"]), e(g["sources"])))
    out.append("</tbody></table>")
    out.append("<h4>Manual-review items</h4>" + _list(c["manual_review"]))
    out.append("<h4>Manual checklist (always pending; never ticked by the system)</h4>" +
               _table(("Code", "Check", "Source"), [(x.get("code"), x.get("check"), x.get("source"))
                                                    for x in c["manual_checks"]]))
    out.append("<h4>Evidence for</h4>" + _list(c["evidence_for"]))
    out.append("<h4>Evidence against</h4>" + _list(c["evidence_against"]))
    rr = g7.get("rr") or {}
    out.append("<h4>Levels (ranges; no buffer is chosen, B9)</h4>" + _table(("Level", "Value"), [
        ("entry", _range(lv.get("entry"))),
        ("SL (normal DL)", _range((lv.get("sl") or {}).get("normal"))),
        ("SL (exceptional DL)", _range((lv.get("sl") or {}).get("exceptional"))),
        ("target", (g7.get("target") or {}).get("proximal")),
        ("R:R", "%s %s" % (_range(rr.get("rr")), rr.get("status") or "-")),
        ("quantity", _range(g7.get("quantity"))),
        ("problems", lv.get("problems")), ("manual considerations", lv.get("manual_considerations"))]))
    out.append("<h4>Candidate limitations</h4>" + _list(c["limitations"]))
    return "".join(out)


def _tda_table(tda):
    rows = []
    for r in tda:
        def brief(z):
            return "-" if not z else "%s %s PL %s DL %s (%s)" % (z.get("zone_id"), z.get("pattern"), fmt(z.get("proximal")),
                                                              fmt(z.get("distal")), z.get("freshness"))
        rows.append((r["tf"], (r.get("series") or {}).get("status"), (r.get("series") or {}).get("completed_candles"),
                     brief(r.get("fresh_demand_below")), brief(r.get("fresh_supply_above")),
                     "; ".join(brief(z) for z in r.get("unknown_freshness_closer", [])) or "none",
                     r.get("zone_counts"), r.get("missing")))
    return _table(("TF", "Series", "Completed candles", "Fresh demand below", "Fresh supply above",
                   "Unknown freshness closer", "Zone counts", "Missing"), rows)


def symbol_body(sym, as_of, trade_type, b=None, bundle_note=None):
    out = ['<h1>%s: <span class="%s">%s</span></h1>' % (e(sym["symbol"]), _cls(sym["status"]), e(sym["status"])),
           _table(("Field", "Value"), [("as_of", as_of), ("trade_type", trade_type), ("price at as_of", sym.get("price")),
                                       ("provenance", sym.get("provenance"))]),
           "<h2>Symbol reasons</h2>", _list(sym["reasons"]),
           "<h2>Limitations</h2>", _list(sym["limitations"])]
    if b is not None:
        out.append(chart_section(b, sym))
    elif bundle_note:
        out.append("<h2>Chart</h2><p>%s</p>" % e(bundle_note))
    out.append("<h2>Candidates (%d)</h2>" % len(sym["candidates"]))
    if not sym["candidates"]:
        out.append("<p>none</p>")
    for c in sorted(sym["candidates"], key=lambda c: (c["zone"].get("created_time") or "", c["zone"]["zone_id"])):
        out.append(_candidate_section(c))
    out.append("<h2>Execution zones removed by the MTF overlay</h2>" + _table(
        ("TF", "Zone", "Engine status", "Overlay status", "Disposition", "Reasons"),
        [(x.get("tf"), x.get("zone_id"), x.get("engine_status"), x.get("overlay_status"), x.get("disposition"),
          x.get("reasons")) for x in sym["blocked_zones"]]))
    out.append("<h2>Fresh zones (overlay FRESH, every timeframe)</h2>" + _table(
        ("TF", "Zone", "Side", "Pattern", "PL", "DL", "Created", "Core", "Zone level"),
        [(x.get("tf"), x.get("zone_id"), x.get("side"), x.get("pattern"), x.get("proximal"), x.get("distal"),
          x.get("created_time"), x.get("core"), x.get("zone_level")) for x in sym["fresh_zones"]]))
    out.append("<h2>Top-down analysis</h2>" + _tda_table(sym["tda"]))
    out.append("<h2>Data-quality findings</h2>" + _table(
        ("Severity", "Code", "Detail", "Verified", "Date"),
        [(f.get("severity"), f.get("code"), f.get("detail"), f.get("verified"), f.get("date")) for f in sym["findings"]]))
    return "".join(out)


def render_decision(b):
    """The replay-decision page for one bundle (decision_replay.bundle)."""
    body = symbol_body(b["symbol_result"], b["as_of"], b["trade_type"], b=b)
    body += "<h2>Bundle limitations</h2>" + _list(b["limitations"])
    return _page("Decision %s %s" % (b["symbol"], b["as_of"]), body, nav=False, scripts=(JS_TF,))


# --- build -----------------------------------------------------------------------------------

def build(scan_dir, out_dir, bundles_dir=None):
    """Writes the pages; returns the sorted file names. Raises ValueError when scan_dir is
    not a write_all folder."""
    data = load_scan(scan_dir)
    scan = data["scan"]
    bundles = load_bundles(bundles_dir)
    pages = {"index.html": index_page(data), "scanner.html": scanner_page(scan)}
    for sym in scan["symbols"]:
        b, note = _matching_bundle(bundles, sym["symbol"], scan["as_of"], scan["trade_type"], scan.get("calendar"), sym)
        name = symbol_href(sym["symbol"])
        if name in pages:
            raise ValueError("two symbols map to %s" % name)
        pages[name] = _page("%s %s" % (sym["symbol"], scan["as_of"]),
                            symbol_body(sym, scan["as_of"], scan["trade_type"], b=b, bundle_note=note),
                            scripts=(JS_TF,) if b is not None else ())
    os.makedirs(out_dir, exist_ok=True)
    for name, text in sorted(pages.items()):
        with open(os.path.join(out_dir, name), "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
    return sorted(pages)


def cmd_dashboard(args):
    try:
        written = build(args.scan_dir, args.out, args.bundles_dir)
    except (ValueError, OSError) as ex:
        print("error: %s" % ex, file=sys.stderr)
        return 2
    print("wrote %s: %d pages (open index.html; works offline)" % (args.out, len(written)))
    return 0


def add_commands(subparsers):
    p = subparsers.add_parser("dashboard", help="static HTML pages from a scan output folder")
    p.add_argument("--scan-dir", required=True, help="folder written by the scan command")
    p.add_argument("--out", required=True)
    p.add_argument("--bundles-dir", help="folder of replay-decision outputs (SYMBOL/decision.json or *.json)")
    p.set_defaults(func=cmd_dashboard)
