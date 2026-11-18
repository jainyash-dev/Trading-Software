"""Decision replay bundle and static dashboard, on the REAL pipeline with SYNTHETIC data.

Inputs are tests/_research.py builders (long_mit_candles, random_walk): synthetic prices,
not market data. Every scan goes through scanner.scan / scan_symbol and reports.write_all;
nothing is mocked. Requirements checked:
  - prefix invariance: a decision at T never depends on candles after T (spec 13; D3)
  - tested / invalidated zones keep that label and are never styled fresh (D3, RB 264, 683-697)
  - reports and pages never hide rejected, blocked or data-insufficient results (spec 12)
  - counts reconcile with the records (spec 12, scan summary)
  - no status approves a trade; nothing is externally validated (spec 8, 11, 15)
  - offline, escaped, deterministic output (D31; contract rules 5)
"""

import argparse
import contextlib
import io
import json
import os
import re
import shutil
import tempfile
import unittest

import _research as R
from nse.research import dashboard, decision_replay as dr, marketdata, models as m, reports, scanner

CAL = R.WeekdayCalendar()
TOUCH = [(176.0, 176.5, 159.5, 170.0), (170.0, 171.0, 169.0, 170.5)]   # low 159.5 <= PL 159.94: a test


def cfg(as_of, trade_type=m.MIT, risk=1000.0, calendar=CAL):
    return scanner.ScanConfig(as_of=as_of, trade_type=trade_type, calendar=calendar,
                              calendar_label="TEST_WEEKDAYS", risk_per_trade=risk,
                              corporate_action_coverage=R.verified_ca("ACT", "RW", "SYN"))


def bad_input(symbol):
    """An input with an undated ERROR finding: G0 stops it (DATA_INSUFFICIENT)."""
    return marketdata.DailyInput(symbol, [], {"source": "SYNTHETIC_TEST_FIXTURE"}, [],
                                 [marketdata.Finding(symbol, marketdata.ERROR, "NO_INPUT_FILE", "synthetic: no file")])


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def pages(folder):
    return {n: read(os.path.join(folder, n)) for n in sorted(os.listdir(folder)) if n.endswith(".html")}


class Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.base = R.long_mit_candles()
        cls.as_of = cls.base[-1].end
        cls.touched = R.extend(cls.base, TOUCH)
        cls.inputs = [R.daily_input("ACT", cls.base), R.daily_input("RW", R.random_walk(0, 900)), bad_input("<X>")]
        cls.result = scanner.scan(cls.inputs, cfg(cls.as_of))
        cls.scan_dir = os.path.join(cls.tmp, "scan")
        reports.write_all(cls.result, cls.scan_dir)
        cls.bundles_dir = os.path.join(cls.tmp, "bundles")
        os.makedirs(cls.bundles_dir)
        cls.bundles = {}
        for inp in cls.inputs:
            b = dr.bundle(inp, cfg(cls.as_of))
            cls.bundles[inp.symbol] = b
            with open(os.path.join(cls.bundles_dir, dashboard.slug(inp.symbol) + ".json"), "w", encoding="utf-8") as fh:
                fh.write(dr.to_json(b))
        cls.out = os.path.join(cls.tmp, "out")
        cls.written = dashboard.build(cls.scan_dir, cls.out, cls.bundles_dir)
        cls.pages = pages(cls.out)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)


class Bundle(Fixture):
    def test_prefix_invariance(self):
        # spec 13: a decision at T must not change when candles after T are added
        later = dr.bundle(R.daily_input("ACT", self.touched), cfg(self.as_of))
        self.assertEqual(dr.to_json(later), dr.to_json(self.bundles["ACT"]))
        rw = R.random_walk(0, 900)
        t = rw[600].end
        self.assertEqual(dr.to_json(dr.bundle(R.daily_input("RW", rw[:601]), cfg(t))),
                         dr.to_json(dr.bundle(R.daily_input("RW", rw), cfg(t))))

    def test_the_later_touch_is_visible_only_after_it_happened(self):
        # not vacuous: at the later as_of the same zone is TESTED (RB 264, 683-697) and no longer a candidate
        b = dr.bundle(R.daily_input("ACT", self.touched), cfg(self.touched[-1].end))
        [z] = [z for z in b["zones"]["D"] if z["proximal"] == R.LONG_PL]
        self.assertEqual((z["freshness"], z["display_class"], z["overlay_kept"]), (m.Z_TESTED, dr.CLASS_TESTED, None))
        self.assertNotIn(z["zone_id"], [c["zone"]["zone_id"] for c in b["symbol_result"]["candidates"]])
        [z0] = [z for z in self.bundles["ACT"]["zones"]["D"] if z["proximal"] == R.LONG_PL]
        self.assertEqual((z0["freshness"], z0["display_class"]), (m.Z_FRESH, dr.CLASS_FRESH_DEMAND))
        page = dashboard.render_decision(b)
        rects = re.findall(r'<rect class="zone ([^"]+)" data-zone="D:%s"' % re.escape(z["zone_id"]), page)
        self.assertEqual(rects, [dr.CLASS_TESTED])

    def test_candles_end_at_or_before_as_of_and_match_the_scanner_series(self):
        b = self.bundles["ACT"]
        for tf, cs in b["candles"].items():
            self.assertTrue(cs, tf)
            self.assertLessEqual(max(c["end"] for c in cs), b["as_of"], tf)
            self.assertEqual(len(cs), b["symbol_result"]["series"][tf]["completed_candles"], tf)

    def test_symbol_result_is_the_scanner_result(self):
        [s] = [s for s in reports.to_dict(self.result)["symbols"] if s["symbol"] == "ACT"]
        self.assertEqual(self.bundles["ACT"]["symbol_result"], s)
        self.assertEqual(s["candidates"][0]["status"], m.ACTIONABLE)

    def test_zone_labels_follow_the_overlay_and_never_call_a_stale_zone_fresh(self):
        seen = set()
        for b in self.bundles.values():
            for tf, zones in b["zones"].items():
                kept = set(c["zone"]["zone_id"] for c in b["symbol_result"]["candidates"]) if tf == "D" else set()
                for z in zones:
                    seen.add(z["freshness"])
                    if z["freshness"] != m.Z_FRESH:
                        self.assertNotIn("fresh", z["display_class"], z)
                        self.assertIsNone(z["overlay_kept"], z)       # eligible_after_overlay never keeps it
                        self.assertNotIn(z["zone_id"], kept, z)
                for zid in kept:                                       # every candidate is overlay-kept
                    [z] = [z for z in zones if z["zone_id"] == zid]
                    self.assertIsNotNone(z["overlay_kept"])
        self.assertTrue({m.Z_TESTED, m.Z_INVALIDATED, m.Z_FRESH} <= seen, seen)   # the fixture exercises each

    def test_no_replay_for_blocked_or_data_insufficient_inputs(self):
        b = dr.bundle(R.daily_input("ACT", self.base), cfg(self.as_of, trade_type=m.WIT_75))
        self.assertEqual((b["replay"], b["candles"], b["symbol_result"]["status"]), ("NOT_RUN", {}, scanner.SYMBOL_BLOCKED))
        self.assertTrue(any("M4b" in x for x in b["limitations"]))
        x = self.bundles["<X>"]
        self.assertEqual((x["replay"], x["candles"], x["symbol_result"]["status"]),
                         ("NOT_RUN", {}, scanner.SYMBOL_DATA_INSUFFICIENT))

    def test_limitations_are_carried(self):
        b = dr.bundle(R.daily_input("ACT", self.base), cfg(self.as_of, calendar=None))
        for lim in (m.NOT_EXTERNALLY_VALIDATED, m.TRADINGVIEW_PARITY_UNVERIFIED, m.CALENDAR_UNVALIDATED):
            self.assertIn(lim, b["limitations"])
        self.assertNotEqual(b["symbol_result"]["candidates"][0]["status"], m.ACTIONABLE)   # P-CAL-1: G0 MANUAL

    def test_bundle_is_deterministic(self):
        self.assertEqual(dr.to_json(dr.bundle(self.inputs[1], cfg(self.as_of))), dr.to_json(self.bundles["RW"]))


class Dashboard(Fixture):
    def test_pages_written(self):
        self.assertEqual(self.written, sorted(["index.html", "scanner.html", "symbol-ACT.html", "symbol-RW.html",
                                               "symbol-_3CX_3E.html"]))

    def test_every_result_is_in_the_scanner_including_rejected_and_data_insufficient(self):
        page = self.pages["scanner.html"]
        rows = re.findall(r'<tr data-status="([^"]+)" data-kind="([^"]+)"', page)
        records = [c.status for s in self.result.symbols for c in s.candidates] + \
                  [s.status for s in self.result.symbols if not s.candidates]
        self.assertEqual(sorted(r[0] for r in rows), sorted(records))
        for st in (m.ACTIONABLE, m.REJECTED, scanner.SYMBOL_DATA_INSUFFICIENT):
            self.assertIn('data-status="%s"' % st, page)
        self.assertIn('id="status-filter"', page)
        self.assertIn('id="q"', page)

    def test_blocked_scan_is_shown_as_blocked(self):
        tmp = tempfile.mkdtemp()
        try:
            res = scanner.scan(self.inputs[:2], cfg(self.as_of, trade_type=m.WIT_75))
            reports.write_all(res, os.path.join(tmp, "scan"))
            dashboard.build(os.path.join(tmp, "scan"), os.path.join(tmp, "out"))
            page = read(os.path.join(tmp, "out", "scanner.html"))
            self.assertEqual(re.findall(r'<tr data-status="([^"]+)"', page), [scanner.SYMBOL_BLOCKED] * 2)
            self.assertIn("M4B", read(os.path.join(tmp, "out", "symbol-ACT.html")).upper())
        finally:
            shutil.rmtree(tmp)

    def test_index_counts_reconcile_with_summary(self):
        summ = json.loads(read(os.path.join(self.scan_dir, "summary.json")))
        page = self.pages["index.html"]
        got = dict(re.findall(r'data-count="([^"]+)">([0-9]+)<', page))
        for k, v in summ["symbol_status_counts"].items():
            self.assertEqual(int(got["symbol:" + k]), v)
        for k, v in summ["candidate_status_counts"].items():
            self.assertEqual(int(got["candidate:" + k]), v)
        for k in ("symbols_processed", "candidate_records", "fresh_zone_records", "data_quality_findings"):
            self.assertEqual(int(got["total:" + k]), summ[k])
        self.assertNotIn("MISMATCH", page)
        self.assertEqual(sum(summ["candidate_status_counts"].values()), len(self.result.candidates()))

    def test_a_tampered_summary_is_flagged(self):
        tmp = tempfile.mkdtemp()
        try:
            scan = os.path.join(tmp, "scan")
            shutil.copytree(self.scan_dir, scan)
            p = os.path.join(scan, "summary.json")
            summ = json.loads(read(p))
            summ["candidate_status_counts"][m.REJECTED] += 1
            with open(p, "w", encoding="utf-8") as fh:
                json.dump(summ, fh)
            dashboard.build(scan, os.path.join(tmp, "out"))
            self.assertIn("MISMATCH", read(os.path.join(tmp, "out", "index.html")))
        finally:
            shutil.rmtree(tmp)

    def test_banner_and_validation_state_on_every_page(self):
        for name, page in self.pages.items():
            self.assertIn('id="banner"', page, name)
            self.assertIn("No status approves a trade", page, name)
            self.assertIn(m.NOT_EXTERNALLY_VALIDATED, page, name)
        idx = self.pages["index.html"]
        for col in dashboard.READINESS_COLUMNS:
            self.assertIn("<th>%s</th>" % col, idx)
        self.assertIn("externally_validated", idx)
        self.assertNotIn("\u2713", idx)          # no tick mark: each state stands alone
        self.assertNotIn("\u2714", idx)

    def test_html_escaping(self):
        for name, page in self.pages.items():
            self.assertNotIn("<X>", page, name)
        self.assertIn("&lt;X&gt;", self.pages["symbol-_3CX_3E.html"])
        self.assertIn('href="symbol-_3CX_3E.html"', self.pages["scanner.html"])
        self.assertNotEqual(dashboard.slug("A_3C"), dashboard.slug("A<"))       # injective file names

    def test_no_external_resources(self):
        decision = dashboard.render_decision(self.bundles["ACT"])
        for name, page in list(self.pages.items()) + [("decision", decision)]:
            for bad in ("http://", "https://", "<link", " src=", "@import", "url("):
                self.assertNotIn(bad, page, (name, bad))
            self.assertNotIn("\u2014", page, name)

    def test_deterministic_bytes(self):
        out2 = os.path.join(self.tmp, "out2")
        dashboard.build(self.scan_dir, out2, self.bundles_dir)
        self.assertEqual(pages(out2), self.pages)

    def test_chart_shows_status_classes_and_levels(self):
        act, rw = self.pages["symbol-ACT.html"], self.pages["symbol-RW.html"]
        self.assertIn('class="tfbtn on" data-tf="D"', act)
        self.assertIn('class="lv-entry"', act)
        self.assertIn('class="lv-sl"', act)
        self.assertIn('class="lv-target"', act)
        drawn = re.findall(r'<rect class="zone ([^"]+)" data-zone="[^"]+" data-freshness="([^"]+)"', rw)
        self.assertTrue(drawn)
        for klass, fr in drawn:
            if fr == m.Z_FRESH:
                self.assertIn(klass, (dr.CLASS_FRESH_DEMAND, dr.CLASS_FRESH_SUPPLY))
            else:
                self.assertEqual(klass, dr.display_class("demand", fr))
                self.assertNotIn("fresh", klass)
        self.assertIn(dr.CLASS_INVALIDATED, [k for k, _ in drawn])
        # zone tables list tested and invalidated zones with their own row class
        self.assertIn('<tr class="%s">' % dr.CLASS_TESTED, rw)
        self.assertIn('<tr class="%s">' % dr.CLASS_INVALIDATED, rw)
        for cls_, _ in dashboard.LEGEND:
            self.assertIn('class="sw %s"' % cls_, rw)

    def test_symbol_page_has_gates_checklist_evidence_and_tda(self):
        act = self.pages["symbol-ACT.html"]
        for g in m.GATES:
            self.assertIn("<td>%s</td><td>%s</td>" % (g, dashboard.e(m.GATE_TITLES[g])), act)
        for code, _, _ in m.CHECKLIST:
            self.assertIn(code, act)
        for head in ("Evidence for", "Evidence against", "Top-down analysis", "Manual-review items",
                     "Candidate limitations"):
            self.assertIn(head, act)

    def test_bundle_for_another_as_of_is_not_embedded(self):
        tmp = tempfile.mkdtemp()
        try:
            b = dr.bundle(R.daily_input("ACT", self.base), cfg(self.base[-3].end))
            with open(os.path.join(tmp, "ACT.json"), "w", encoding="utf-8") as fh:
                fh.write(dr.to_json(b))
            dashboard.build(self.scan_dir, os.path.join(tmp, "out"), tmp)
            page = read(os.path.join(tmp, "out", "symbol-ACT.html"))
            self.assertNotIn("<svg", page)
            self.assertIn("not shown", page)
        finally:
            shutil.rmtree(tmp)

    def test_missing_scan_files_are_an_error(self):
        tmp = tempfile.mkdtemp()
        try:
            with self.assertRaises(ValueError):
                dashboard.build(tmp, os.path.join(tmp, "out"))
        finally:
            shutil.rmtree(tmp)


class Cli(unittest.TestCase):
    def parser(self):
        p = argparse.ArgumentParser()
        sub = p.add_subparsers(dest="cmd")
        dr.add_commands(sub)
        dashboard.add_commands(sub)
        return p

    def test_replay_decision_then_dashboard(self):
        tmp = tempfile.mkdtemp()
        try:
            cs = R.long_mit_candles()
            data = os.path.join(tmp, "in")
            os.makedirs(data)
            with open(os.path.join(data, "SYN.csv"), "w", encoding="utf-8") as fh:
                fh.write("date,open,high,low,close\n")
                for c in cs:
                    fh.write("%s,%s,%s,%s,%s\n" % (c.start.date(), c.open, c.high, c.low, c.close))
            out = os.path.join(tmp, "dec", "SYN")
            args = self.parser().parse_args(["replay-decision", "--symbol", "syn", "--as-of", str(cs[-1].start.date()),
                                             "--csv-dir", data, "--risk-per-trade", "1000", "--out", out])
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(args.func(args), 0)
            b = json.loads(read(os.path.join(out, "decision.json")))
            self.assertEqual((b["symbol"], b["calendar"]), ("SYN", "NONE"))
            self.assertIn(m.CALENDAR_UNVALIDATED, b["limitations"])
            self.assertIn("<svg", read(os.path.join(out, "decision.html")))
            # the same data through the scan path, then the dashboard with the bundle folder
            res = scanner.scan([marketdata.from_csv(os.path.join(data, "SYN.csv"), "SYN", "USER_CSV", "UNKNOWN")],
                               scanner.ScanConfig(as_of=cs[-1].end, risk_per_trade=1000.0))
            reports.write_all(res, os.path.join(tmp, "scan"))
            args = self.parser().parse_args(["dashboard", "--scan-dir", os.path.join(tmp, "scan"), "--out",
                                             os.path.join(tmp, "dash"), "--bundles-dir", os.path.join(tmp, "dec")])
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(args.func(args), 0)
            self.assertIn("<svg", read(os.path.join(tmp, "dash", "symbol-SYN.html")))
        finally:
            shutil.rmtree(tmp)

    def test_usage_errors_return_2(self):
        tmp = tempfile.mkdtemp()
        try:
            args = self.parser().parse_args(["dashboard", "--scan-dir", tmp, "--out", os.path.join(tmp, "o")])
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(args.func(args), 2)
            args = self.parser().parse_args(["replay-decision", "--symbol", "S", "--as-of", "2024-01-31",
                                             "--bhavcopy-dir", tmp, "--out", os.path.join(tmp, "o")])
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(args.func(args), 2)      # no bhavcopy archives in the folder
            args = self.parser().parse_args(["replay-decision", "--symbol", "S", "--as-of", "not-a-date",
                                             "--csv-dir", tmp, "--out", os.path.join(tmp, "o")])
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(args.func(args), 2)
            self.assertFalse(os.path.exists(os.path.join(tmp, "o")))
        finally:
            shutil.rmtree(tmp)



class BundleMatchReviewRegression(unittest.TestCase):
    def test_a_bundle_from_another_replay_is_not_drawn(self):
        rec = {"symbol": "S", "status": "EVALUATED"}
        b = {"as_of": "T", "trade_type": "MIT", "calendar": "nse/data/calendar", "symbol_result": rec}
        bundles = {"S": [b]}
        self.assertIs(dashboard._matching_bundle(bundles, "S", "T", "MIT", "nse/data/calendar", rec)[0], b)
        none, note = dashboard._matching_bundle(bundles, "S", "T", "MIT", "NONE", rec)
        self.assertIsNone(none)
        self.assertIn("calendar", note)
        none, note = dashboard._matching_bundle(bundles, "S", "T", "MIT", "nse/data/calendar", dict(rec, status="X"))
        self.assertIsNone(none)

if __name__ == "__main__":
    unittest.main()
