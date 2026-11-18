#!/usr/bin/env python3
"""Deterministic evidence pack for the council (Mode B, Trading Product Council). Standard library only.

Reads a scan.json written by `python3 -m nse.research.cli scan ... --out <dir>` and prints, for
one symbol (and optionally one zone), the scanner's own decisions and the STRONGEST verdict
the council is allowed to give. It computes nothing about the market and changes nothing:
the cap comes only from the deterministic status (G0-G8 via MtfSnapshot.eligible_after_overlay).

Verdict cap (the council may give the cap or anything weaker, never stronger):
  ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING -> BUY CANDIDATE (user approval + manual checklist)
  MANUAL_REVIEW                              -> WAIT (the listed manual items are open)
  REJECTED                                   -> AVOID
  DATA_INSUFFICIENT, BLOCKED                 -> INSUFFICIENT DATA
  symbol BLOCKED (e.g. WIT), with or without --zone-id / --zone-pl -> INSUFFICIENT DATA
  zone not a candidate (tested, invalidated, below 7/7, never formed) -> AVOID
  symbol absent from the scan / no scan      -> INSUFFICIENT DATA

Usage (from the repository root):
  python3 .claude/skills/llm-council/scripts/evidence_pack.py --scan nse/output/<run>/scan.json --symbol INFY
  ... --zone-pl 159.94 | --zone-id demand-1250-1251   # one zone
  ... --check-verdict "BUY CANDIDATE"   # exit 1 if that verdict exceeds the cap
"""

import argparse
import json
import os
import sys

# the one status derivation (nse.research.models.derive_status), not a copy of it
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))
from nse.research import models  # noqa: E402

BUY, WAIT, AVOID, INSUFFICIENT = "BUY CANDIDATE", "WAIT", "AVOID", "INSUFFICIENT DATA"
STATUS_CAP = {
    "ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING": BUY,
    "MANUAL_REVIEW": WAIT,
    "REJECTED": AVOID,
    "DATA_INSUFFICIENT": INSUFFICIENT,
    "BLOCKED": INSUFFICIENT,
}
# what the council may say for each cap (it may weaken, never strengthen)
ALLOWED = {
    BUY: (BUY, WAIT, AVOID, INSUFFICIENT),
    WAIT: (WAIT, AVOID, INSUFFICIENT),
    AVOID: (AVOID,),
    INSUFFICIENT: (INSUFFICIENT, AVOID),
}
STRENGTH = {BUY: 3, WAIT: 2, INSUFFICIENT: 1, AVOID: 0}


def _derived_cap(c):
    """(cap, problem): the cap of the status the gate outcomes give. A recorded status that
    differs, or gates that cannot be read, cap at INSUFFICIENT DATA: an edited or mixed
    scan.json must not raise the council's ceiling (audit 2026-11-06, Agent 3 D3)."""
    try:
        derived = models.derive_status([models.GateResult(g["gate"], g["outcome"]) for g in c["gates"]])
    except (KeyError, TypeError, ValueError) as e:
        return INSUFFICIENT, "GATES_UNREADABLE: %s" % e
    if derived != c.get("status"):
        return INSUFFICIENT, "STATUS_INCONSISTENT_WITH_GATES: recorded %s, gates give %s" % (c.get("status"), derived)
    return STATUS_CAP[derived], None


def _candidate(c):
    gates = {g["gate"]: g["outcome"] for g in c["gates"]}
    g7 = next(g for g in c["gates"] if g["gate"] == "G7")["evidence"]
    cap, problem = _derived_cap(c)
    return {
        "zone_id": c["zone"]["zone_id"], "tf": c["zone"]["tf"], "proximal": c["zone"]["proximal"],
        "distal": c["zone"]["distal"], "created": c["zone"]["created_time"], "core": c["zone"]["core"],
        "overlay_status": c["zone"]["overlay_status"], "status": c["status"], "verdict_cap": cap,
        "status_problem": problem,
        "gates": gates,
        "not_passed": {g["gate"]: g["reasons"][:3] for g in c["gates"] if g["outcome"] != "PASS"},
        "manual_review": c["manual_review"], "manual_checks": [x["code"] for x in c["manual_checks"]],
        "levels": {"entry": c["levels"].get("entry"), "sl": c["levels"].get("sl"), "valid": c["levels"].get("valid")},
        "target": (g7.get("target") or {}).get("proximal"), "rr": (g7.get("rr") or {}).get("rr"),
        "limitations": c["limitations"],
    }


def pack(scan, symbol, zone_pl=None, zone_id=None):
    out = {"as_of": scan.get("as_of"), "generated_at": scan.get("generated_at"), "calendar": scan.get("calendar"),
           "universe": scan.get("universe"), "scan_limitations": scan.get("limitations", []), "symbol": symbol,
           "source": "deterministic scanner output (scan.json); not a live quote"}
    s = next((x for x in scan.get("symbols", []) if x["symbol"] == symbol), None)
    if s is None:
        out.update(verdict_cap=INSUFFICIENT, reason="symbol not in this scan")
        return out
    out.update(symbol_status=s["status"], symbol_reasons=s["reasons"], price=s.get("price"),
               provenance=s.get("provenance"), data_findings=len(s.get("findings", [])),
               tda=[{"tf": r["tf"], "status": r["series"]["status"],
                     "fresh_demand_below": (r["fresh_demand_below"] or {}).get("proximal"),
                     "fresh_supply_above": (r["fresh_supply_above"] or {}).get("proximal")} for r in s.get("tda", [])])
    cands = [_candidate(c) for c in s.get("candidates", [])]
    if s["status"] == "BLOCKED":
        # the pipeline did not evaluate this symbol, so no zone can be judged: a zone query
        # must not turn "not evaluated" into AVOID (audit finding, council validation case T7)
        out["candidates"] = cands
        out.update(verdict_cap=INSUFFICIENT, reason="BLOCKED: %s" % ", ".join(s.get("reasons", [])))
        return out
    if zone_pl is not None or zone_id is not None:
        def same(z):
            return z["zone_id"] == zone_id if zone_id is not None else abs(z["proximal"] - zone_pl) < 1e-9
        hit = [c for c in cands if same(c)]
        if hit:
            out.update(candidate=hit[0], verdict_cap=hit[0]["verdict_cap"])
            return out
        blocked = [b for b in s.get("blocked_zones", []) if zone_id is not None and b["zone_id"] == zone_id]
        fresh = [z for z in s.get("fresh_zones", []) if z["tf"] == "D" and same(z)]
        if blocked:
            b = blocked[0]
            cap = INSUFFICIENT if b["disposition"] == "DATA_INSUFFICIENT" else AVOID
            out.update(verdict_cap=cap, reason="overlay blocked the zone: %s" % ", ".join(b["reasons"]))
        elif fresh:
            out.update(verdict_cap=AVOID, reason="fresh zone but not an execution candidate: %s" % fresh[0]["zone_level"])
        else:
            out.update(verdict_cap=AVOID if s["status"] != "DATA_INSUFFICIENT" else INSUFFICIENT,
                       reason="no fresh eligible demand zone with this id / PL in the deterministic scan "
                              "(tested, invalidated, below 7/7, or never formed)")
        return out
    out["candidates"] = cands
    if s["status"] == "DATA_INSUFFICIENT":
        out.update(verdict_cap=INSUFFICIENT, reason=s["status"])
    elif s["status"] == "NOT_IN_UNIVERSE_AT_AS_OF":
        out.update(verdict_cap=AVOID, reason="not in the universe at as_of")
    elif not cands:
        out.update(verdict_cap=AVOID, reason="no fresh execution zone passed the MTF overlay")
    else:
        out["verdict_cap"] = max((c["verdict_cap"] for c in cands), key=lambda v: STRENGTH[v])
    return out


def check(verdict, cap):
    """True if the council's verdict does not exceed the deterministic cap."""
    return verdict in ALLOWED[cap]


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--scan", required=True)
    p.add_argument("--symbol", required=True)
    g = p.add_mutually_exclusive_group()
    g.add_argument("--zone-pl", type=float, help="the zone's proximal line, as scan.json reports it")
    g.add_argument("--zone-id", help="the zone id, as scan.json reports it")
    p.add_argument("--check-verdict", choices=(BUY, WAIT, AVOID, INSUFFICIENT),
                   help="entry verdicts only; EXIT is a position verdict (position-review rules), not capped here")
    a = p.parse_args(argv)
    with open(a.scan, encoding="utf-8") as fh:
        scan = json.load(fh)
    out = pack(scan, a.symbol.upper(), a.zone_pl, a.zone_id)
    if a.check_verdict:
        out["proposed_verdict"] = a.check_verdict
        out["verdict_allowed"] = check(a.check_verdict, out["verdict_cap"])
    print(json.dumps(out, indent=1, sort_keys=True))
    return 1 if a.check_verdict and not out["verdict_allowed"] else 0


if __name__ == "__main__":
    sys.exit(main())
