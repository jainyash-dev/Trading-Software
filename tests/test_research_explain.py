"""Explanations, the report auditor and narrative reports over REAL scans (SYNTHETIC prices).

The scans come from the real pipeline (scanner.scan: replay -> overlay -> G0-G8) on the
long synthetic histories of tests/_research.py, plus one symbol evaluated by the real
qualification pathway on a SnapBuilder snapshot (a falling Weekly trend, so G4 rejects:
LOC + Down, RB 1896). Nothing is market data. The tests check that the explanations
restate the recorded gates, never guess (NOT_IN_SCAN, D3), and that the auditor finds
nothing on real scans and does find tampering.
"""

import argparse
import contextlib
import copy
import io
import json
import os
import shutil
import tempfile
import unittest

import _research as R
from nse.research import explain, models as m, narrative, qualification, reports, scanner
from nse.research.deps import mtf

CAL = R.WeekdayCalendar()
ZONE = "demand-1250-1251"          # the long-history Daily zone (engine id)
_CACHE = {}


def flat(cs, n=2):
    p = cs[-1].close
    return R.extend(cs, [(p, p * 1.002, p * 0.998, p)] * n)


def falling(n, start):
    return [start * (0.99 ** i) for i in range(n)]


def rejected_symbol(as_of):
    """SYNTHETIC: the ideal MIT scenario with a falling Weekly trend (LOC + Down -> G4 FAIL),
    plus a gap-blocked and a tested Daily zone for the overlay audit records."""
    b = R.SnapBuilder(as_of)
    b.add_series("D", [940.0] * 60)
    b.add_zone("D", "demand", 890.0, 870.0, normal_dl=875.0, created_index=50)
    b.add_zone("D", "demand", 920.0, 910.0, status=mtf.UNKNOWN_DATA_GAP, created_index=52, zid="d-gap")
    b.add_zone("D", "demand", 930.0, 925.0, status=mtf.TESTED, created_index=53, zid="d-tested")
    b.add_series("W", falling(60, 1000.0))
    b.add_zone("W", "supply", 1200.0, 1230.0)
    b.add_series("M", [800.0 + i for i in range(60)])
    b.add_zone("M", "demand", 900.0, 850.0, status=mtf.TESTED, zid="m-coinciding")
    b.add_zone("M", "demand", 700.0, 650.0, zid="m-bottom")
    b.add_zone("M", "supply", 1500.0, 1550.0, zid="m-top")
    for tf in ("Q", "HY", "Y"):
        b.add_series(tf, [800.0, 820.0, 840.0, 860.0])
    snap = b.build()
    ctx = qualification.SymbolContext("REJ", m.MIT, snap, 950.0, risk_per_trade=1000.0)
    ev = qualification.evaluate_symbol(ctx)
    return scanner.SymbolResult("REJ", scanner.SYMBOL_EVALUATED, [], 950.0, ev["candidates"], ev["blocked_zones"],
                                scanner._fresh_zone_rows("REJ", snap), ev["tda"], ev["series"], [],
                                {"source": "SYNTHETIC_TEST_FIXTURE (SnapBuilder)"}, ev["limitations"])


def build_result():
    base = R.long_mit_candles()
    act = flat(base)
    gap = act[:-4] + act[-3:]                       # one weekday missing: MISSING_SESSION
    touched = R.extend(base, [(176.0, 176.5, 159.5, 170.0), (170.0, 171.0, 169.0, 170.5)])   # PL test
    agr = flat(R.long_mit_candles(k=1.75))          # wholly above the Monthly demand: Aggressive
    inputs = [R.daily_input("ACT", act), R.daily_input("GAP", gap), R.daily_input("TST", touched),
              R.daily_input("AGR", agr)]
    cfg = scanner.ScanConfig(as_of=act[-1].end, calendar=CAL, calendar_label="TEST_WEEKDAYS",
                             risk_per_trade=1000.0, generated_at="test-label")
    res = scanner.scan(inputs, cfg)
    res.symbols = sorted(res.symbols + [rejected_symbol(act[-1].end)], key=lambda s: s.symbol)
    return res


def scan_dict():
    if "scan" not in _CACHE:
        res = build_result()
        _CACHE["result"] = res
        _CACHE["scan"] = reports.to_dict(res)
        _CACHE["summary"] = json.loads(json.dumps(reports.summary(res)))
    return copy.deepcopy(_CACHE["scan"])


def summary_dict():
    scan_dict()
    return copy.deepcopy(_CACHE["summary"])


def wit_scan():
    cs = R.long_mit_candles()
    cfg = scanner.ScanConfig(as_of=cs[-1].end, trade_type=m.WIT_75, calendar=CAL, calendar_label="TEST_WEEKDAYS")
    return reports.to_dict(scanner.scan([R.daily_input("WIT", cs)], cfg))


def run_cli(module, argv):
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd")
    module.add_commands(sub)
    args = p.parse_args(argv)
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = args.func(args)
    return code, out.getvalue(), err.getvalue()


class Fixture(unittest.TestCase):
    def test_the_fixture_exercises_every_status_path(self):
        scan = scan_dict()
        got = {s["symbol"]: (s["status"], [c["status"] for c in s["candidates"]]) for s in scan["symbols"]}
        self.assertEqual(got["ACT"], ("EVALUATED", [m.ACTIONABLE]))
        self.assertEqual(got["AGR"], ("EVALUATED", [m.MANUAL_REVIEW]))
        self.assertEqual(got["REJ"], ("EVALUATED", [m.REJECTED]))
        self.assertEqual(got["GAP"], ("DATA_INSUFFICIENT", []))
        self.assertEqual(got["TST"], ("NO_FRESH_EXECUTION_ZONE", []))


class Why(unittest.TestCase):
    def test_names_the_deciding_gate_of_a_rejected_candidate(self):
        ans = explain.why(scan_dict(), "REJ")
        deciding = [l for l in ans["answer_lines"] if "deciding" in l]
        # every FAIL gate decides REJECTED: G4 (LOC + Down, RB 1896) and G8 (RF3, trend clearly down)
        self.assertEqual([l.split(":")[0].strip() for l in deciding],
                         ["deciding (REJECTED) G4 FAIL", "deciding (REJECTED) G8 FAIL"])
        self.assertIn("RB 1896", deciding[0])
        self.assertIn("RF3 trend strongly against: FAIL", deciding[1])
        self.assertIn("G4", ans["citations"]["gates"])
        self.assertIn("D14", ans["citations"]["rule_refs"])     # from the gate's own sources
        self.assertIn(explain.AUTHORITY, ans["limitations"])

    def test_manual_review_lists_the_manual_gate_and_items(self):
        ans = explain.why(scan_dict(), "AGR")
        text = "\n".join(ans["answer_lines"])
        self.assertIn("deciding (MANUAL_REVIEW) G6 MANUAL", text)
        self.assertIn("AGGRESSIVE_ENTRY_REVIEW", text)

    def test_actionable_still_lists_the_pending_checklist(self):
        text = "\n".join(explain.why(scan_dict(), "ACT")["answer_lines"])
        self.assertIn(m.ACTIONABLE, text)
        for code, _, _ in m.CHECKLIST:
            self.assertIn(code, text)

    def test_data_insufficient_symbol_cites_its_findings(self):
        ans = explain.why(scan_dict(), "GAP")
        self.assertIn("DATA_INSUFFICIENT", ans["answer_lines"][0])
        self.assertIn("MISSING_SESSION", ans["citations"]["finding_codes"])

    def test_unknown_symbol_is_not_guessed(self):
        ans = explain.why(scan_dict(), "NOPE")
        self.assertEqual(ans["result"], explain.SYMBOL_NOT_IN_SCAN)
        self.assertEqual(ans["citations"]["gates"], [])


class ZoneAnswers(unittest.TestCase):
    def test_a_tested_zone_is_not_in_scan_and_never_called_fresh(self):
        ans = explain.zone_freshness(scan_dict(), "TST", ZONE)
        self.assertEqual(ans["result"], explain.NOT_IN_SCAN)
        text = " ".join(ans["answer_lines"])
        self.assertIn("D3", text)
        self.assertNotIn("FRESH", text.replace("fresh-zone row", ""))

    def test_candidate_zone_answers_from_the_overlay_record(self):
        ans = explain.zone_freshness(scan_dict(), "ACT", "D:" + ZONE)
        self.assertEqual(ans["result"], explain.OK)
        recs = sorted(e["record"] for e in ans["evidence"] if "record" in e)
        self.assertEqual(recs, ["candidate.zone", "fresh_zones"])
        self.assertIn("overlay_status FRESH", ans["answer_lines"][0])

    def test_blocked_zone_answers_from_the_blocked_record(self):
        scan = scan_dict()
        gap = explain.zone_freshness(scan, "GAP", ZONE)
        self.assertIn("UNKNOWN_DATA_GAP", " ".join(gap["answer_lines"]))
        tested = explain.zone_freshness(scan, "REJ", "d-tested")
        self.assertIn("removed by the MTF overlay: overlay_status TESTED", " ".join(tested["answer_lines"]))
        self.assertNotIn("fresh-zone report", " ".join(tested["answer_lines"]))

    def test_gate_answer_carries_the_recorded_evidence(self):
        scan = scan_dict()
        [c] = scan["symbols"][[s["symbol"] for s in scan["symbols"]].index("REJ")]["candidates"]
        ans = explain.gate(scan, "REJ", c["zone"]["zone_id"], "G4")
        self.assertEqual(ans["evidence"][0]["evidence"], explain.gate_of(c, "G4")["evidence"])
        self.assertIn("G4 (%s): FAIL" % m.GATE_TITLES["G4"], ans["answer_lines"][0])
        self.assertEqual(explain.gate(scan, "REJ", "missing-zone", "G4")["result"], explain.NOT_IN_SCAN)
        with self.assertRaises(ValueError):
            explain.gate(scan, "REJ", c["zone"]["zone_id"], "G9")

    def test_confluence_cites_the_htf_zone(self):
        ans = explain.confluence(scan_dict(), "ACT", ZONE)
        text = "\n".join(ans["answer_lines"])
        self.assertIn("class COINCIDING", text)
        self.assertIn("HTF zone cited: M:", text)
        self.assertIn("freshness TESTED", text)                 # cited evidence only (D15)
        agr = "\n".join(explain.confluence(scan_dict(), "AGR", ZONE)["answer_lines"])
        self.assertIn("class AGGRESSIVE", agr)

    def test_what_would_change_states_conditions_not_advice(self):
        scan = scan_dict()
        zid = [s for s in scan["symbols"] if s["symbol"] == "REJ"][0]["candidates"][0]["zone"]["zone_id"]
        text = "\n".join(explain.what_would_change(scan, "REJ", zid)["answer_lines"])
        self.assertIn("G4 FAIL: ", text)
        self.assertIn("RB 1896", text)
        self.assertIn("qualification would need the W trend gate", text)
        self.assertIn("no status approves a trade", text)
        for word in ("buy now", "you should", "recommend"):
            self.assertNotIn(word, text.lower())
        agr = "\n".join(explain.what_would_change(scan, "AGR", ZONE)["answer_lines"])
        self.assertIn("G6 MANUAL", agr)
        self.assertIn("a person must resolve AGGRESSIVE_ENTRY_REVIEW", agr)

    def test_compare_is_a_gate_table(self):
        ans = explain.compare(scan_dict(), "ACT", "REJ")
        table = ans["evidence"][0]["table"]
        self.assertEqual([r[0] for r in table["rows"]], ["status"] + list(m.GATES))
        g4 = [r for r in table["rows"] if r[0] == "G4"][0]
        self.assertEqual(g4[1:], [m.PASS, m.FAIL])
        missing = explain.compare(scan_dict(), "ACT", "NOPE")
        self.assertEqual(missing["result"], explain.SYMBOL_NOT_IN_SCAN)
        self.assertIn("NOPE (NOT_IN_SCAN)", missing["evidence"][0]["table"]["columns"])


class Auditor(unittest.TestCase):
    def test_real_scans_have_no_inconsistencies(self):
        self.assertEqual(explain.inconsistencies(scan_dict(), summary_dict()), [])
        self.assertEqual(explain.inconsistencies(wit_scan()), [])

    def _codes(self, scan, summary=None):
        return set(i["code"] for i in explain.inconsistencies(scan, summary))

    def _cand(self, scan, sym):
        return [s for s in scan["symbols"] if s["symbol"] == sym][0]["candidates"][0]

    def test_actionable_with_a_failed_gate_is_found(self):
        scan = scan_dict()
        self._cand(scan, "REJ")["status"] = m.ACTIONABLE         # G4 still FAIL
        self.assertIn("STATUS_NOT_DERIVED_FROM_GATES", self._codes(scan))

    def test_a_dropped_checklist_is_found(self):
        scan = scan_dict()
        self._cand(scan, "ACT")["manual_checks"] = []
        self.assertIn("ACTIONABLE_WITHOUT_CHECKLIST", self._codes(scan))

    def test_a_broken_count_is_found(self):
        summ = summary_dict()
        summ["candidate_status_counts"][m.ACTIONABLE] = 2
        self.assertIn("SUMMARY_COUNT_MISMATCH", self._codes(scan_dict(), summ))
        summ = summary_dict()
        summ["symbols_processed"] += 1
        self.assertIn("SUMMARY_COUNT_MISMATCH", self._codes(scan_dict(), summ))

    def test_a_non_fresh_candidate_zone_is_found(self):
        scan = scan_dict()
        self._cand(scan, "ACT")["zone"]["overlay_status"] = mtf.TESTED
        self.assertIn("CANDIDATE_ZONE_NOT_OVERLAY_FRESH", self._codes(scan))

    def test_other_tampering_is_found(self):
        scan = scan_dict()
        self._cand(scan, "AGR")["manual_review"] = []
        self._cand(scan, "REJ")["status_reasons"] = []
        scan["limitations"].remove(m.NOT_EXTERNALLY_VALIDATED)
        [s for s in scan["symbols"] if s["symbol"] == "ACT"][0]["fresh_zones"] = []
        self.assertTrue({"MANUAL_ITEM_DROPPED", "STATUS_REASON_DROPPED", "LIMITATION_DROPPED",
                         "CANDIDATE_ZONE_NOT_IN_FRESH_REPORT"} <= self._codes(scan))

    def test_audit_cli_exit_codes(self):
        tmp = tempfile.mkdtemp()
        try:
            res = build_result()
            reports.write_all(res, tmp)
            path = os.path.join(tmp, "scan.json")
            code, out, _ = run_cli(explain, ["explain", "--scan", path, "--audit"])
            self.assertEqual(code, 0, out)
            self.assertIn("0 inconsistencies", out)
            self.assertNotIn("NOT_RECONCILED", out)              # summary.json next to scan.json was used
            scan = explain.load_scan(path)
            [x for x in scan["symbols"] if x["symbol"] == "AGR"][0]["candidates"][0]["status"] = m.ACTIONABLE
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(scan, fh)
            self.assertEqual(run_cli(explain, ["explain", "--scan", path, "--audit"])[0], 1)
            code, out, _ = run_cli(explain, ["explain", "--scan", path, "--why", "REJ", "--format", "json"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["question"], "why does REJ have its status?")
            bad = os.path.join(tmp, "bad.json")
            with open(bad, "w", encoding="utf-8") as fh:
                fh.write("[]")
            self.assertEqual(run_cli(explain, ["explain", "--scan", bad, "--why", "X"])[0], 2)
        finally:
            shutil.rmtree(tmp)

    def test_answers_are_deterministic(self):
        a, b = scan_dict(), reports.to_dict(build_result())
        for fn, args in ((explain.why, ("REJ",)), (explain.zone_freshness, ("TST", ZONE)),
                         (explain.what_would_change, ("AGR", ZONE)), (explain.compare, ("ACT", "AGR"))):
            self.assertEqual(json.dumps(fn(a, *args), sort_keys=True), json.dumps(fn(b, *args), sort_keys=True))


class Narrative(unittest.TestCase):
    def test_daily_report_hides_nothing(self):
        text = narrative.daily_report(scan_dict())
        self.assertTrue(text.startswith("# Daily scan report"))
        self.assertIn("No status approves a trade", text)
        self.assertIn("## Rejected (1)", text)
        self.assertIn("G4 FAIL: ", text)                         # the deciding gate
        self.assertIn("## Manual review (1)", text)
        self.assertIn("## Actionable candidates: manual checks pending (1)", text)
        self.assertIn("pending: EXPLOSIVE_RELATIVE_SIZE_CONTEXT", text)
        self.assertIn("| GAP | DATA_INSUFFICIENT |", text)
        self.assertIn("| TST | NO_FRESH_EXECUTION_ZONE |", text)
        self.assertIn("d-tested", text)                          # overlay-removed zones stay visible
        self.assertIn("MISSING_SESSION", text)
        self.assertIn("0 inconsistencies", text)
        self.assertIn(m.NOT_EXTERNALLY_VALIDATED, text)

    def test_blocked_results_are_reported(self):
        text = narrative.daily_report(wit_scan())
        self.assertIn("| WIT | BLOCKED |", text)
        self.assertIn("INTRADAY_DESIGN_NOT_APPROVED", text)

    def test_stock_report_has_every_section(self):
        text = narrative.stock_report(scan_dict(), "REJ")
        for part in ("## Top-down analysis", "| G0 |", "| G8 |", "**Levels**", "**Manual checklist",
                     "**Evidence against**", "G4 FAIL", "d-gap", "UNKNOWN_DATA_GAP"):
            self.assertIn(part, text)
        self.assertIn("NOT_IN_SCAN", narrative.stock_report(scan_dict(), "NOPE"))

    def test_comparison_and_determinism(self):
        text = narrative.comparison_report(scan_dict(), ["ACT", "REJ", "GAP", "NOPE"])
        self.assertIn("| NOPE | NOT_IN_SCAN |", text)
        self.assertIn("| GAP | DATA_INSUFFICIENT |", text)
        other = reports.to_dict(build_result())
        for fn, args in ((narrative.daily_report, ()), (narrative.stock_report, ("ACT",)),
                         (narrative.comparison_report, (["ACT", "AGR"],))):
            self.assertEqual(fn(scan_dict(), *args), fn(other, *args))
            self.assertNotIn("\u2014", fn(scan_dict(), *args))

    def test_report_cli_writes_markdown(self):
        tmp = tempfile.mkdtemp()
        try:
            reports.write_all(build_result(), tmp)
            out = os.path.join(tmp, "daily.md")
            code, _, _ = run_cli(narrative, ["report", "--scan", os.path.join(tmp, "scan.json"), "--daily",
                                             "--out", out])
            self.assertEqual(code, 0)
            with open(out, encoding="utf-8") as fh:
                self.assertEqual(fh.read(), narrative.daily_report(explain.load_scan(os.path.join(tmp, "scan.json"))))
            code, text, _ = run_cli(narrative, ["report", "--scan", os.path.join(tmp, "scan.json"),
                                                "--compare", "ACT,AGR"])
            self.assertEqual(code, 0)
            self.assertIn("| ACT |", text)
            self.assertEqual(run_cli(narrative, ["report", "--scan", os.path.join(tmp, "nope.json"), "--daily"])[0], 2)
        finally:
            shutil.rmtree(tmp)



class NarrativeLimitationsReviewRegression(unittest.TestCase):
    def test_symbol_and_candidate_limitations_reach_the_daily_report(self):
        scan = scan_dict()
        scan["symbols"][0]["limitations"] = sorted(set(scan["symbols"][0].get("limitations") or []) | {"ZZ_SYMBOL_ONLY"})
        self.assertIn("ZZ_SYMBOL_ONLY", narrative.daily_report(scan))
        sym = scan["symbols"][0]["symbol"]
        self.assertIn("ZZ_SYMBOL_ONLY", narrative.comparison_report(scan, [sym]))

if __name__ == "__main__":
    unittest.main()
