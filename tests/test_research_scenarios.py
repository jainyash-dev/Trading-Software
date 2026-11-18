"""Scenario laboratory (nse/research/scenarios.py, nse/scenarios/). The seed library is
SYNTHETIC: each scenario's expectation comes from a rule (rule_refs + explanation) and runs
through the real scanner. These tests check the runner itself: strict schema, provenance
of SYNTHETIC data, UNAVAILABLE never counted as a pass, a wrong expectation reported as FAIL
with the mismatching gate named, and a byte-identical report for identical inputs.
"""

import argparse
import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest

import _research as R
from _load import ROOT
from nse.research import scenarios as S
from nse.scenarios import generate

LIB = os.path.join(ROOT, "nse", "scenarios")


def seed(sid):
    with open(os.path.join(LIB, sid + ".json"), encoding="utf-8") as fh:
        return json.load(fh)


def cli(argv):
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd")
    S.add_commands(sub)
    args = p.parse_args(argv)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = args.func(args)
    return code, out.getvalue()


def real_scenario(path, sha="0" * 64):
    s = seed("mit_fresh_7of7_actionable")
    s.update(id="real_case", data_kind=S.HISTORICAL_REAL, calendar=S.CAL_NONE,
             source_note="test: local bhavcopy reference",
             data={"INFY": {"bhavcopy": [{"path": path, "sha256": sha}], "series": "EQ", "manifest": None}},
             expected={"symbol_status": "DATA_INSUFFICIENT"})
    return s


class TempLibrary(object):
    """A copy of the seed data folder plus the given scenarios, in a tempfile.mkdtemp() dir."""

    def __init__(self, scenarios, copy_data=True):
        self.scenarios = scenarios
        self.copy_data = copy_data

    def __enter__(self):
        self.root = tempfile.mkdtemp()
        if self.copy_data:
            shutil.copytree(os.path.join(LIB, "data"), os.path.join(self.root, "data"))
        for s in self.scenarios:
            with open(os.path.join(self.root, s["id"] + ".json"), "w", encoding="utf-8") as fh:
                json.dump(s, fh)
        return self.root

    def __exit__(self, *exc):
        shutil.rmtree(self.root)


class Schema(unittest.TestCase):
    def setUp(self):
        self.s = seed("mit_fresh_7of7_actionable")

    def test_seed_scenario_is_valid(self):
        self.assertEqual(S.validate(self.s), [])

    def test_unknown_keys_are_rejected_at_every_level(self):
        self.s["colour"] = "blue"
        self.s["expected"]["bonus"] = 1
        self.s["expected"]["candidates"][0]["match"]["width"] = 2
        errs = " ".join(S.validate(self.s))
        for key in ("'colour'", "'bonus'", "'width'"):
            self.assertIn(key, errs)

    def test_bad_data_kind(self):
        self.s["data_kind"] = "REAL_ISH"
        self.assertTrue(any("data_kind" in e for e in S.validate(self.s)))

    def test_missing_expected_or_status(self):
        del self.s["expected"]
        self.assertIn("scenario: missing key 'expected'", S.validate(self.s))
        s2 = seed("mit_fresh_7of7_actionable")
        del s2["expected"]["symbol_status"]
        self.assertIn("expected: missing key 'symbol_status'", S.validate(s2))

    def test_unknown_gate_outcome_and_status_values(self):
        c = self.s["expected"]["candidates"][0]
        c["gates"]["G9"] = "PASS"
        c["gates"]["G1"] = "OK"
        c["status"] = "APPROVED"              # no status approves a trade (spec 8)
        errs = " ".join(S.validate(self.s))
        for text in ("unknown gate 'G9'", "gates.G1", "status must be one of"):
            self.assertIn(text, errs)

    def test_rule_refs_are_required_and_structured(self):
        self.s["rule_refs"] = []
        self.assertIn("rule_refs must be a non-empty list", S.validate(self.s))
        self.s["rule_refs"] = ["the rulebook somewhere"]
        self.assertTrue(any("is not a reference" in e for e in S.validate(self.s)))

    def test_weekday_calendar_only_for_synthetic_data(self):
        # D28: no weekday fallback for real or owner data
        self.s.update(data_kind=S.OWNER_CHART, source_note="owner")
        self.assertTrue(any("WEEKDAYS_SYNTHETIC" in e for e in S.validate(self.s)))

    def test_real_and_owner_data_need_a_source_note(self):
        s = real_scenario("nse/data/eod/raw/x.zip")
        del s["source_note"]
        self.assertTrue(any("source_note" in e for e in S.validate(s)))

    def test_paths_cannot_leave_their_folder(self):
        self.s["data"] = {"SYN": "../outside.csv"}
        self.assertTrue(any("relative to the library" in e for e in S.validate(self.s)))

    def test_file_name_and_duplicate_keys(self):
        tmp = tempfile.mkdtemp()
        try:
            p = os.path.join(tmp, "other_name.json")
            with open(p, "w", encoding="utf-8") as fh:
                json.dump(self.s, fh)
            self.assertTrue(any("must equal the file name" in e for e in S.load_file(p).errors))
            with open(p, "w", encoding="utf-8") as fh:
                fh.write('{"id": "a", "id": "b"}')
            self.assertTrue(any("duplicate key" in e for e in S.load_file(p).errors))
        finally:
            shutil.rmtree(tmp)

    def test_invalid_scenario_is_never_run(self):
        self.s["data_kind"] = "NOPE"
        r = S.run_scenario(self.s, LIB)
        self.assertEqual((r["result"], r["assertions"], r["actual"]), (S.INVALID, [], None))


class SeedLibrary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = S.run_library(LIB)

    def test_every_seed_scenario_passes(self):
        bad = [(r["id"], r["result"], r["reason"], r["failures"]) for r in self.report["scenarios"]
               if r["result"] != S.PASS]
        self.assertEqual(bad, [])
        self.assertGreaterEqual(self.report["summary"]["total"], 12)
        self.assertEqual(self.report["summary"]["PASS"], self.report["summary"]["total"])
        self.assertEqual(self.report["verdict"], "PASSED")

    def test_required_cases_are_present_and_documented(self):
        ids = set(r["id"] for r in self.report["scenarios"])
        for sid in ("mit_fresh_7of7_actionable", "mit_tested_after_pl_touch", "mit_invalidated_close_below_dl",
                    "mit_wick_below_dl_without_close", "mit_missing_session_after_formation",
                    "mit_no_calendar_never_actionable", "wit75_blocked", "mit_legout_window_open",
                    "mit_prefix_invariance_later_candles", "mit_data_quality_error_before_as_of"):
            self.assertIn(sid, ids)
        for r in self.report["scenarios"]:
            self.assertEqual(r["data_kind"], S.SYNTHETIC, r["id"])     # nothing real or owner-supplied is invented
            self.assertTrue(r["rule_refs"] and r["explanation"], r["id"])
            self.assertTrue(r["assertions"], r["id"])                 # a PASS always checked something
            self.assertEqual(r["assertions"][0]["check"], "symbol_status")

    def test_no_seed_scenario_reports_a_trade_approval(self):
        # spec 8: the best status is ACTIONABLE with manual checks pending; tested, invalidated and
        # unknown-freshness zones (D3, R4, D27) never appear as candidates
        by_id = {r["id"]: r for r in self.report["scenarios"]}
        for sid in ("mit_tested_after_pl_touch", "mit_invalidated_close_below_dl",
                    "mit_wick_below_dl_without_close", "mit_missing_session_after_formation"):
            self.assertEqual(by_id[sid]["actual"]["candidates"], [], sid)
        self.assertIn("No status approves a trade", self.report["note"])
        self.assertIn("not external validation", self.report["note"])

    def test_report_is_deterministic(self):
        again = S.run_library(LIB)
        self.assertEqual(S.report_json(again), S.report_json(self.report))
        self.assertEqual(S.report_csv(again), S.report_csv(self.report))
        self.assertIsNone(self.report["generated_at"])               # no clock is read
        self.assertEqual(S.run_library(LIB, generated_at="label-1")["generated_at"], "label-1")

    def test_csv_reconciles_with_the_json(self):
        rows = S.report_csv(self.report).splitlines()[1:]
        self.assertEqual(len(rows), self.report["summary"]["total"])
        self.assertEqual(sum(1 for r in rows if ",PASS," in r), self.report["summary"]["PASS"])


class Mutation(unittest.TestCase):
    """A wrong expectation must FAIL and name what disagreed: the runner is not a rubber stamp."""

    def test_wrong_gate_expectation_fails_and_names_the_gate(self):
        s = seed("mit_hoc_strong_up_rejected")
        s["expected"]["candidates"][0]["gates"]["G4"] = "PASS"      # R5 says HOC + Up is REJECT
        r = S.run_scenario(s, LIB)
        self.assertEqual(r["result"], S.FAIL)
        [f] = r["failures"]
        self.assertIn(" G4: expected \"PASS\", actual \"FAIL\"", f)

    def test_wrong_status_and_count_fail(self):
        s = seed("mit_tested_after_pl_touch")
        s["expected"]["candidate_count"] = 1
        s["expected"]["overlay_zone_states"][0]["overlay_status"] = "FRESH"
        r = S.run_scenario(s, LIB)
        self.assertEqual(r["result"], S.FAIL)
        self.assertEqual(sorted(a["check"] for a in r["assertions"] if not a["passed"]),
                         ["candidate_count", "overlay zone {proximal: 159.94, tf: D} status"])
        self.assertEqual(len(r["failures"]), 2)

    def test_wick_is_not_reported_as_invalidated(self):
        s = seed("mit_wick_below_dl_without_close")
        s["expected"]["overlay_zone_states"][0]["overlay_status"] = "INVALIDATED"   # R4: a wick is not a breach
        self.assertEqual(S.run_scenario(s, LIB)["result"], S.FAIL)

    def test_same_decisions_comparison_is_live(self):
        s = seed("mit_tested_after_pl_touch")
        s["expected"] = {"symbol_status": "NO_FRESH_EXECUTION_ZONE", "same_decisions_as": "mit_fresh_7of7_actionable"}
        lib = {x: (seed(x), LIB) for x in ("mit_fresh_7of7_actionable",)}
        r = S.run_scenario(s, LIB, lib)
        self.assertEqual(r["result"], S.FAIL)
        self.assertIn("candidates", r["failures"][0])
        s["expected"]["same_decisions_as"] = "no_such_scenario"
        self.assertEqual(S.run_scenario(s, LIB, lib)["result"], S.INVALID)

    def test_a_candidate_match_that_hits_nothing_fails(self):
        s = seed("mit_fresh_7of7_actionable")
        s["expected"]["candidates"][0]["match"] = {"proximal": 1.0}
        r = S.run_scenario(s, LIB)
        self.assertEqual(r["result"], S.FAIL)
        self.assertIn("matches exactly one candidate: expected 1, actual 0", r["failures"][0])

    def test_cli_exits_1_on_failure_and_2_on_unknown_id(self):
        s = seed("mit_hoc_strong_up_rejected")
        s["expected"]["symbol_status"] = "BLOCKED"
        with TempLibrary([s, seed("wit75_blocked")]) as lib:
            out = os.path.join(lib, "out")
            code, text = cli(["scenarios-run", "--library", lib, "--out", out])
            self.assertEqual(code, 1)
            self.assertIn("FAIL         mit_hoc_strong_up_rejected", text)
            code, _ = cli(["scenarios-run", "--library", lib, "--only", "wit75_blocked", "--out", out])
            self.assertEqual(code, 0)
            with open(os.path.join(out, "scenarios_report.json"), encoding="utf-8") as fh:
                self.assertEqual(json.load(fh)["summary"]["total"], 1)
            code, _ = cli(["scenarios-run", "--library", lib, "--only", "nope", "--out", out])
            self.assertEqual(code, 2)


class Availability(unittest.TestCase):
    def test_absent_historical_file_is_unavailable_not_passed(self):
        r = S.run_scenario(real_scenario("nse/data/eod/raw/cm01JAN1990bhav.csv.zip"), LIB)
        self.assertEqual(r["result"], S.UNAVAILABLE)
        self.assertIn("absent", r["reason"])
        self.assertEqual(r["assertions"], [])

    def test_a_different_file_under_the_same_path_is_unavailable(self):
        r = S.run_scenario(real_scenario("nse/scenarios/data/long_mit.csv"), LIB)
        self.assertEqual(r["result"], S.UNAVAILABLE)
        self.assertIn("sha256 differs", r["reason"])

    def test_unavailable_is_reported_and_never_counted_as_pass(self):
        with TempLibrary([real_scenario("nse/data/eod/raw/cm01JAN1990bhav.csv.zip")], copy_data=False) as lib:
            rep = S.run_library(lib)
            self.assertEqual((rep["summary"]["UNAVAILABLE"], rep["summary"]["PASS"]), (1, 0))
            self.assertEqual(rep["verdict"], "PASSED_WITH_UNAVAILABLE")
            code, text = cli(["scenarios-run", "--library", lib, "--out", os.path.join(lib, "out")])
            self.assertEqual(code, 0)
            self.assertIn("UNAVAILABLE  real_case", text)
            code, text = cli(["scenarios-validate", "--library", lib])
            self.assertEqual(code, 0)
            self.assertIn("data UNAVAILABLE", text)


class Provenance(unittest.TestCase):
    """SYNTHETIC data must be the generator's file; synthetic data cannot pose as an owner case."""

    def test_tampered_synthetic_csv_is_invalid(self):
        s = seed("mit_fresh_7of7_actionable")
        with TempLibrary([s]) as lib:
            with open(os.path.join(lib, "data", "long_mit.csv"), "a", encoding="utf-8") as fh:
                fh.write("2024-02-05,176.0,177.0,175.0,176.5\n")
            r = S.run_scenario(s, lib)
            self.assertEqual(r["result"], S.INVALID)
            self.assertIn("sha256", r["reason"])
            code, _ = cli(["scenarios-validate", "--library", lib])
            self.assertEqual(code, 1)

    def test_unlisted_csv_is_invalid(self):
        s = seed("mit_fresh_7of7_actionable")
        with TempLibrary([s]) as lib:
            shutil.copy(os.path.join(lib, "data", "long_mit.csv"), os.path.join(lib, "data", "mine.csv"))
            s["data"] = {"SYN": "data/mine.csv"}
            r = S.run_scenario(s, lib)
            self.assertEqual(r["result"], S.INVALID)
            self.assertIn("not listed as SYNTHETIC", r["reason"])

    def test_synthetic_file_cannot_be_an_owner_chart(self):
        s = seed("mit_no_calendar_never_actionable")          # calendar NONE, so the kind is allowed
        s.update(data_kind=S.OWNER_CHART, source_note="relabelled")
        r = S.run_scenario(s, LIB)
        self.assertEqual(r["result"], S.INVALID)
        self.assertIn("cannot be an OWNER_CHART", r["reason"])

    def test_committed_data_matches_its_generator(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(generate.main(["--check"]), 0)
        man = json.loads(generate.render()["MANIFEST.json"])
        self.assertEqual(man["data_kind"], S.SYNTHETIC)
        self.assertTrue(all(f["data_kind"] == S.SYNTHETIC for f in man["files"].values()))

    def test_generator_copy_equals_the_test_builder(self):
        # nse/ never imports tests/: generate.py is a copy, so it must not drift from it
        rows = [(c.start.date(), c.open, c.high, c.low, c.close) for c in R.long_mit_candles()]
        self.assertEqual(generate.long_mit_rows(), rows)
        rows = [(c.start.date(), c.open, c.high, c.low, c.close) for c in R.long_mit_candles(k=1.75)]
        self.assertEqual(generate.long_mit_rows(k=1.75), rows)

    def test_templates_are_not_scenarios(self):
        ids = [e.scenario["id"] for e in S.load_library(LIB)]
        self.assertFalse([i for i in ids if "REPLACE" in i])
        for name in os.listdir(os.path.join(LIB, "templates")):
            with open(os.path.join(LIB, "templates", name), encoding="utf-8") as fh:
                t = json.load(fh)
            self.assertIn(t["data_kind"], (S.OWNER_CHART, S.HISTORICAL_REAL))
            self.assertTrue(S.validate(t))                       # placeholders never validate as a case


if __name__ == "__main__":
    unittest.main()
