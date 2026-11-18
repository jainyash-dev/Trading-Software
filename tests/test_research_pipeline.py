"""Research orchestration (nse/research/pipeline.py). SYNTHETIC prices only.

The scans go through scanner.scan, which is the real replay, overlay and G0-G8 path.
Nothing here is market evidence, and no result is a profitability figure.
"""

import contextlib
import copy
import datetime
import io
import json
import os
import shutil
import tempfile
import unittest

import _research as R
from nse.research import cli, corporate_actions, marketdata, models as m, pipeline, risk, scanner, store, universe

CAL = R.WeekdayCalendar()


def config(as_of, **kw):
    values = dict(as_of=as_of, calendar=CAL, calendar_label="TEST_WEEKDAYS", risk_per_trade=1000.0,
                  generated_at="SYNTHETIC-PIPELINE", corporate_action_coverage=R.verified_ca("SYN"))
    values.update(kw)
    return scanner.ScanConfig(**values)


def _candles():
    return R.long_mit_candles()


class Shared(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candles = _candles()
        cls.research_run = pipeline.run([R.daily_input("SYN", cls.candles)], config(cls.candles[-1].end))
        cls.env = cls.research_run.envelope
        cls.scan = cls.env["scan"]

    def plan(self, env=None):
        env = self.env if env is None else env
        return env["trade_plans"][0]

    def test_fresh_demand_is_eligible_and_does_not_authorise_an_order(self):
        [candidate] = [c for s in self.env["symbols"] for c in s["candidates"]]
        self.assertEqual(candidate["candidate_status"], m.ACTIONABLE)
        self.assertEqual(candidate["zone"]["proximal"], R.LONG_PL)
        self.assertTrue(candidate["trade_plan"]["manual_checks"])
        self.assertFalse(self.env["authorises_order"])
        self.assertEqual(self.env["completeness"], "COMPLETE")
        self.assertFalse(self.env["full_universe_scan"])
        self.assertIn("FIXTURE_NOT_MARKET_DATA", self.env["limitations"])
        self.assertEqual(candidate["trade_plan"]["identity_status"], "STABLE")
        self.assertTrue(candidate["trade_plan"]["plan_usable"])
        self.assertFalse(candidate["trade_plan"]["authorises_order"])
        self.assertIsNone(candidate["trade_plan"]["selected_quantity"])
        self.assertIsNone(candidate["trade_plan"]["levels"]["selected_entry"])
        self.assertIsNone(candidate["trade_plan"]["levels"]["selected_stop"])
        for check in candidate["trade_plan"]["portfolio_checks"]:
            self.assertNotEqual(check["outcome"], m.PASS)
            self.assertEqual(check["outcome"], pipeline.NOT_SUPPLIED)
        text = pipeline.research_report(self.env)
        for heading in pipeline.HEADINGS:
            self.assertIn("## " + heading, text)
        self.assertNotIn("win rate", text.lower())
        self.assertNotIn("profitable", text.lower())
        self.assertIn("manual checks pending", text.lower())

    def test_every_symbol_and_blocked_zone_is_in_the_envelope(self):
        self.assertEqual([s["symbol"] for s in self.env["symbols"]], [s["symbol"] for s in self.scan["symbols"]])
        raw = [(s["symbol"], b["zone_id"]) for s in self.scan["symbols"] for b in s["blocked_zones"]]
        got = [(b["symbol"], b["zone_id"]) for b in self.env["blocked_zones"]]
        self.assertEqual(got, raw)
        self.assertIn("blocked_zones", self.env)
        self.assertGreater(sum(len(s["fresh_zones"]) for s in self.scan["symbols"]), 0)

    def test_status_is_copied_and_the_plan_list_is_not_a_score_ranking(self):
        for view, raw in zip(self.env["symbols"], self.scan["symbols"]):
            self.assertEqual(view["symbol_status"], raw["status"])
            self.assertEqual(sorted(c["candidate_status"] for c in view["candidates"]),
                             sorted(c["status"] for c in raw["candidates"]))
        order = [(p["symbol"], p["created_time"], p["zone_id"]) for p in self.env["trade_plans"]]
        self.assertEqual(order, sorted(order))

    def test_identical_runs_match_and_a_later_candle_does_not_change_the_earlier_one(self):
        again = pipeline.run([R.daily_input("SYN", self.candles)], config(self.candles[-1].end))
        self.assertEqual(pipeline.digest(again.envelope), pipeline.digest(self.env))
        self.assertEqual(again.envelope["idempotency_key"], self.env["idempotency_key"])
        later = R.extend(self.candles, [(176.0, 177.0, 175.0, 176.0)])
        early = pipeline.run([R.daily_input("SYN", later)], config(self.candles[-1].end))
        self.assertEqual(pipeline.digest(early.envelope), pipeline.digest(self.env))
        first = self.env["trade_plans"][0]["stable_zone_reference"]
        second = early.envelope["trade_plans"][0]["stable_zone_reference"]
        self.assertEqual(pipeline.compare_zone_identity(
            {"reference": first, "defining": self.env["trade_plans"][0]["defining_properties"]},
            {"reference": second, "defining": early.envelope["trade_plans"][0]["defining_properties"]})["result"],
            pipeline.SAME_ZONE)
        self.assertNotEqual(first["start_time"], None)

    def test_a_second_as_of_does_not_stick_to_the_first(self):
        early_at = self.candles[-30].end
        first = pipeline.run([R.daily_input("SYN", self.candles)], config(early_at))
        pipeline.run([R.daily_input("SYN", self.candles)], config(self.candles[-1].end))
        second = pipeline.run([R.daily_input("SYN", self.candles)], config(early_at))
        self.assertEqual(pipeline.digest(first.envelope), pipeline.digest(second.envelope))
        self.assertNotEqual(first.envelope["as_of"], self.env["as_of"])

    def test_history_matches_a_single_run_at_the_same_as_of(self):
        moments = [self.candles[-40].end, self.candles[-1].end]
        runs = pipeline.run_history([R.daily_input("SYN", self.candles)], moments, config(moments[-1]))
        alone = pipeline.run([R.daily_input("SYN", self.candles)], config(moments[0]), invocation="historical")
        self.assertEqual(pipeline.digest(runs[0].envelope), pipeline.digest(alone.envelope))
        self.assertNotEqual(pipeline.digest(runs[0].envelope), pipeline.digest(runs[1].envelope))
        with self.assertRaises(ValueError):
            pipeline.run_history([R.daily_input("SYN", self.candles)], moments, config(moments[-1]),
                                 portfolio=pipeline.PortfolioState(0, 0, (), as_of=moments[-1].isoformat()))


class Outcomes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candles = _candles()

    def run_at(self, candles, **kw):
        return pipeline.run([R.daily_input("SYN", candles)], config(candles[-1].end, **kw)).envelope

    def test_tested_and_invalidated_zones_are_not_eligible(self):
        touched = R.extend(self.candles, [(176.0, 176.5, 159.5, 170.0), (170.0, 171.0, 169.0, 170.5)])
        broken = R.extend(self.candles, [(176.0, 176.0, 150.0, 151.0)])
        for candles in (touched, broken):
            env = self.run_at(candles)
            self.assertFalse(any(c["zone"]["proximal"] == R.LONG_PL and c["candidate_status"] == m.ACTIONABLE
                                 for s in env["symbols"] for c in s["candidates"]))
            self.assertTrue(all(p["authorises_order"] is False and p["selected_quantity"] is None
                                for p in env["trade_plans"]))

    def test_a_missing_session_is_data_insufficient(self):
        gap = self.candles[:-3] + self.candles[-2:]
        env = self.run_at(gap)
        self.assertEqual(env["symbols"][0]["symbol_status"], scanner.SYMBOL_DATA_INSUFFICIENT)
        self.assertFalse(any(c["candidate_status"] == m.ACTIONABLE for s in env["symbols"] for c in s["candidates"]))
        self.assertIn("\n## Eligible candidates\n\nnone\n", pipeline.research_report(env))

    def test_an_excluded_session_with_no_candle_stays_manual(self):
        day = self.candles[-2].start.date()
        kept = [c for c in self.candles if c.start.date() != day]

        class Excluded(object):
            def is_trading_day(self, d):
                return d.weekday() < 5 and d != day

            def is_excluded_session(self, d):
                return d == day

        env = pipeline.run([R.daily_input("SYN", kept)],
                           config(kept[-1].end, calendar=Excluded())).envelope
        plans = [c for s in env["symbols"] for c in s["candidates"] if c["zone"]["proximal"] == R.LONG_PL]
        self.assertTrue(plans)
        self.assertEqual(plans[0]["candidate_status"], m.MANUAL_REVIEW)
        g1 = [g for g in plans[0]["gates"] if g["gate"] == "G1"][0]
        self.assertEqual(g1["outcome"], m.MANUAL)
        self.assertIn(m.EXCLUDED_SESSION_UNOBSERVED, g1["manual_review"])
        self.assertFalse(plans[0]["trade_plan"]["authorises_order"])

    def test_no_calendar_is_not_actionable(self):
        env = self.run_at(self.candles, calendar=None, calendar_label="NONE")
        self.assertIn(m.CALENDAR_UNVALIDATED, env["limitations"])
        self.assertFalse(any(c["candidate_status"] == m.ACTIONABLE for s in env["symbols"] for c in s["candidates"]))

    def test_monthly_history_gap_and_aggressive_location_stay_manual(self):
        short = self.run_at(R.long_mit_candles(start=datetime.date(2022, 6, 1)))
        [candidate] = [c for s in short["symbols"] for c in s["candidates"] if c["zone"]["proximal"] == R.LONG_PL]
        g5 = [g for g in candidate["gates"] if g["gate"] == "G5"][0]
        self.assertEqual(g5["outcome"], m.MANUAL)
        self.assertNotEqual(candidate["candidate_status"], m.ACTIONABLE)
        aggressive = self.run_at(R.long_mit_candles(k=1.75))
        pl = round(95.2 * 1.75, 2)
        zone = [c for s in aggressive["symbols"] for c in s["candidates"] if c["zone"]["proximal"] == pl]
        self.assertTrue(zone)
        self.assertTrue(all(c["candidate_status"] == m.MANUAL_REVIEW for c in zone))
        self.assertIn(m.MANUAL, [g["outcome"] for c in zone for g in c["gates"]])

    def test_wit_is_blocked_without_a_candidate(self):
        env = pipeline.run([R.daily_input("SYN", self.candles)],
                           config(self.candles[-1].end, trade_type=m.WIT_75)).envelope
        self.assertEqual(env["symbols"][0]["symbol_status"], scanner.SYMBOL_BLOCKED)
        self.assertEqual(env["symbols"][0]["candidates"], [])
        self.assertIn(env["symbols"][0]["symbol"], pipeline.research_report(env))

    def test_future_and_undated_evidence(self):
        later = self.candles[-1].start.date() + datetime.timedelta(days=30)
        future = marketdata.Finding("SYN", marketdata.ERROR, "LATER", "after as_of", date=later)
        clean = pipeline.run([R.daily_input("SYN", self.candles)], config(self.candles[-1].end))
        leaked = pipeline.run([dataclasses_replace_findings(self.candles, [future])], config(self.candles[-1].end))
        self.assertEqual(pipeline.digest(leaked.envelope), pipeline.digest(clean.envelope))
        undated = marketdata.Finding("SYN", marketdata.ERROR, "UNDATED", "no date")
        blocked = pipeline.run([dataclasses_replace_findings(self.candles, [undated])], config(self.candles[-1].end))
        self.assertEqual(blocked.envelope["symbols"][0]["symbol_status"], scanner.SYMBOL_DATA_INSUFFICIENT)
        self.assertNotEqual(pipeline.digest(blocked.envelope), pipeline.digest(clean.envelope))

    def test_corporate_action_inside_history_is_manual_and_a_future_one_is_ignored(self):
        inside = corporate_actions.Action("SYN", self.candles[len(self.candles) // 2].start.date(), "SPLIT", 1, 5, True, "synthetic")
        future = corporate_actions.Action("SYN", self.candles[-1].start.date() + datetime.timedelta(days=40),
                                         "SPLIT", 1, 5, True, "synthetic")
        base = self.run_at(self.candles)
        later = self.run_at(self.candles, corporate_actions=[future])
        self.assertEqual(pipeline.digest(later), pipeline.digest(base))
        touched = self.run_at(self.candles, corporate_actions=[inside])
        self.assertNotEqual(pipeline.digest(touched), pipeline.digest(base))
        self.assertFalse(any(c["candidate_status"] == m.ACTIONABLE for s in touched["symbols"] for c in s["candidates"]))
        g0 = [g for s in touched["symbols"] for c in s["candidates"] for g in c["gates"] if g["gate"] == "G0"]
        self.assertTrue(g0)
        self.assertTrue(all(g["outcome"] == m.MANUAL for g in g0))

    def test_two_symbols_and_a_non_member_are_all_reported(self):
        inputs = [R.daily_input("BBB", self.candles), R.daily_input("AAA", self.candles)]
        env = pipeline.run(inputs, config(self.candles[-1].end)).envelope
        self.assertEqual([s["symbol"] for s in env["symbols"]], ["AAA", "BBB"])
        as_of = self.candles[-1].start.date()
        book = universe.Universe("SYNTH", [
            universe.Membership("SYN", "EQ", datetime.date(2019, 1, 1), datetime.date(2024, 12, 31), True, "synthetic", "INEEARLY"),
            universe.Membership("SYN", "EQ", datetime.date(2025, 1, 1), None, True, "synthetic", "INELATE"),
            universe.Membership("GHOST", "EQ", datetime.date(2019, 1, 1), None, True, "synthetic", "INEGHOST"),
            universe.Membership("LATER", "EQ", as_of + datetime.timedelta(days=400), None, True, "synthetic", "INELATER"),
        ])
        booked = pipeline.run([R.daily_input("SYN", self.candles)], config(self.candles[-1].end), universe=book).envelope
        symbols = {s["symbol"]: s for s in booked["symbols"]}
        self.assertIn("GHOST", symbols)
        self.assertEqual(symbols["GHOST"]["symbol_status"], scanner.SYMBOL_DATA_INSUFFICIENT)
        self.assertNotIn("LATER", symbols)
        self.assertEqual(symbols["SYN"]["identity"]["universe_isin"], "INEEARLY")
        self.assertNotIn(m.UNIVERSE_UNVERIFIED, booked["limitations"])
        self.assertIn("GHOST", pipeline.research_report(booked))


def dataclasses_replace_findings(candles, findings):
    inp = R.daily_input("SYN", candles)
    return inp.__class__(inp.symbol, list(inp.candles), dict(inp.provenance), list(inp.limitations), list(findings))


class Plans(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Shared.setUpClass()
        cls.candles, cls.research_run, cls.env, cls.scan = Shared.candles, Shared.research_run, Shared.env, Shared.scan

    def plan(self, env=None):
        env = self.env if env is None else env
        return env["trade_plans"][0]

    def cfg(self, **kw):
        values = dict(capital=100000, rpt_pct=1, stage=risk.LEARNING)
        values.update(kw)
        return risk.RiskConfig(**values)

    def assembled(self, edit=None, risk_config=None, portfolio=None):
        scan = copy.deepcopy(self.scan)
        if edit:
            edit(scan["symbols"][0]["candidates"][0])
        return pipeline.assemble_scan(scan, risk_config if risk_config is not None else self.cfg(), portfolio)

    def test_invalid_levels_are_not_repaired_or_sized(self):
        def edit(candidate):
            candidate["levels"]["valid"] = False
            candidate["levels"]["problems"] = ["ZONE_GEOMETRY_INVALID"]
        env = self.assembled(edit)
        plan = self.plan(env)
        self.assertEqual(plan["candidate_status"], m.ACTIONABLE)
        self.assertIsNone(plan["selected_quantity"])
        self.assertIsNone(plan["risk_plan"]["quantity_range"] if "quantity_range" in (plan["risk_plan"] or {}) else None)
        self.assertEqual(plan["risk_plan"]["status"], risk.INVALID_LEVELS)
        self.assertIn("RISK_PLAN", plan["constraints_blocking"])

    def test_a_failed_gate_is_not_sized(self):
        def edit(candidate):
            for gate in candidate["gates"]:
                if gate["gate"] == "G7":
                    gate["outcome"] = m.FAIL
                    gate["reasons"] = ["RF8: synthetic"]
            candidate["status"] = m.derive_status([m.GateResult(g["gate"], g["outcome"]) for g in candidate["gates"]])
        env = self.assembled(edit)
        plan = self.plan(env)
        self.assertEqual(plan["candidate_status"], m.REJECTED)
        self.assertEqual(plan["risk_plan"]["status"], risk.NOT_APPLICABLE_STATUS)
        self.assertIsNone(plan["selected_quantity"])

    def test_a_missing_target_is_not_invented(self):
        def edit(candidate):
            for gate in candidate["gates"]:
                if gate["gate"] == "G7":
                    gate["outcome"] = m.MANUAL
                    gate["evidence"]["target"] = None
                    gate["reasons"] = ["NO_STRUCTURAL_TARGET"]
            candidate["status"] = m.derive_status([m.GateResult(g["gate"], g["outcome"]) for g in candidate["gates"]])
        plan = self.plan(self.assembled(edit))
        self.assertEqual(plan["candidate_status"], m.MANUAL_REVIEW)
        self.assertIsNone(plan["levels"]["target_proximal"])
        self.assertNotIn("mathematical", plan["levels"]["target_provenance"])

    def test_stage_band_and_independent_caps_do_not_change_status(self):
        high = self.assembled(risk_config=self.cfg(rpt_pct=3))
        self.assertEqual(self.plan(high)["candidate_status"], m.ACTIONABLE)
        self.assertEqual(self.plan(high)["risk_plan"]["status"], risk.PLAN_FAIL)
        low = self.assembled(risk_config=self.cfg(rpt_pct=0.25))
        self.assertEqual(self.plan(low)["risk_plan"]["status"], risk.PLAN_MANUAL)
        missing = self.assembled(risk_config=risk.RiskConfig(capital=100000, rpt_pct=1, stage=None))
        self.assertEqual(self.plan(missing)["risk_plan"]["status"], risk.PLAN_MANUAL)
        book = pipeline.PortfolioState(0, 10, ())
        capped = self.assembled(portfolio=book)
        checks = {c["code"]: c["outcome"] for c in self.plan(capped)["portfolio_checks"]}
        self.assertEqual(checks["MONTHLY_TRADE_CAP"], m.PASS)
        self.assertEqual(checks["SIMULTANEOUS_POSITIONS"], m.FAIL)
        self.assertEqual(self.plan(capped)["candidate_status"], m.ACTIONABLE)
        capped_report = pipeline.research_report(capped)
        self.assertIn("SIMULTANEOUS_POSITIONS", capped_report)
        self.assertIn("not a size to place", capped_report)
        month = self.assembled(portfolio=pipeline.PortfolioState(10, 0, ()))
        checks = {c["code"]: c["outcome"] for c in self.plan(month)["portfolio_checks"]}
        self.assertEqual(checks["MONTHLY_TRADE_CAP"], m.FAIL)
        self.assertEqual(checks["SIMULTANEOUS_POSITIONS"], m.PASS)
        held = pipeline.PortfolioState(0, 0, (("SYN", self.plan()["zone_id"], m.MIT, "submitted order"),))
        zone = self.assembled(portfolio=held)
        checks = {c["code"]: c["outcome"] for c in self.plan(zone)["portfolio_checks"]}
        self.assertEqual(checks["ONE_ORDER_PER_ZONE"], m.FAIL)
        clear = self.assembled(portfolio=pipeline.PortfolioState(0, 0, ()))
        self.assertIsNone(self.plan(clear)["selected_quantity"])
        self.assertIsInstance(self.plan(clear)["risk_plan"]["quantity_range"], list)
        self.assertEqual(len(self.plan(clear)["risk_plan"]["quantity_range"]), 2)
        report = pipeline.research_report(clear)
        self.assertNotIn("buy ", report.lower())

    def test_identity_ignores_a_future_segment_and_reports_a_conflict(self):
        day = self.candles[-1].start.date()
        symbol = {"symbol": "SYN", "provenance": {"identity": {
            "records_supplied": True, "records_verified": True, "lineage": [
                {"symbol": "SYN", "from": "2030-01-01", "to": None, "isin": "INEFUTURE"},
                {"symbol": "SYN", "from": "2010-01-01", "to": "2029-12-31", "isin": "INEGOOD"},
            ]}}}
        view = pipeline.identity_view(symbol, day, None)
        self.assertEqual(view["isin"], "INEGOOD")
        clash = pipeline.identity_view(symbol, day, {"member": True, "isin": "INEOTHER"})
        self.assertIsNone(clash["isin"])
        self.assertEqual(clash["isin_status"], "CONFLICT")
        both = {"symbol": "SYN", "provenance": {"identity": {
            "records_supplied": True, "records_verified": True, "lineage": [
                {"symbol": "SYN", "from": "2010-01-01", "to": None, "isin": "INEONE"},
                {"symbol": "SYN", "from": "2011-01-01", "to": None, "isin": "INETWO"},
            ]}}}
        self.assertEqual(pipeline.identity_view(both, day, None)["isin_status"], "CONFLICT")

    def test_zone_identity_contract(self):
        reference = {"symbol": "SYN", "timeframe": "D", "side": "demand",
                     "start_time": "2024-01-02T15:30:00", "created_time": "2024-01-03T15:30:00"}
        defining = {"pattern": "DBR", "proximal": 100.0, "distal": 90.0, "normal_distal": 92.0, "zero_base": False}
        same = pipeline.compare_zone_identity(
            {"reference": reference, "defining": defining, "engine_zone_id": "demand-2-3", "dataset_id": "aaa"},
            {"reference": dict(reference), "defining": dict(defining), "engine_zone_id": "demand-3-4", "dataset_id": "bbb"})
        self.assertEqual(same["result"], pipeline.SAME_ZONE)
        moved = dict(defining)
        moved["distal"] = 80.0
        unresolved = pipeline.compare_zone_identity(
            {"reference": reference, "defining": defining},
            {"reference": dict(reference), "defining": moved})
        self.assertEqual(unresolved["result"], pipeline.ZONE_IDENTITY_UNRESOLVED)
        other = dict(reference)
        other["created_time"] = "2024-02-01T15:30:00"
        missing = pipeline.compare_zone_identity(
            {"reference": reference, "defining": defining},
            {"reference": other, "defining": defining})
        self.assertEqual(missing["result"], pipeline.ZONE_NOT_IN_SERIES)
        blank = pipeline.compare_zone_identity({}, {"reference": reference, "defining": defining})
        self.assertEqual(blank["result"], pipeline.ZONE_IDENTITY_UNRESOLVED)

    def test_an_incomplete_shared_reference_is_ambiguous(self):
        scan = copy.deepcopy(self.scan)
        first = scan["symbols"][0]["candidates"][0]
        first["zone"]["start_time"] = None
        twin = copy.deepcopy(first)
        twin["zone"]["zone_id"] = first["zone"]["zone_id"] + "-twin"
        scan["symbols"][0]["candidates"].append(twin)
        plans = pipeline.assemble_scan(scan)["trade_plans"]
        self.assertEqual({p["identity_status"] for p in plans}, {pipeline.ZONE_IDENTITY_AMBIGUOUS})

    def test_a_partial_scan_is_not_a_full_universe_scan(self):
        scan = copy.deepcopy(self.scan)
        scan["universe"] = "NIFTY100"
        scan["limitations"] = [x for x in scan.get("limitations") or [] if x != m.UNIVERSE_UNVERIFIED]
        env = pipeline.assemble_scan(scan, requested_symbols=["SYN", "TCS"])
        self.assertEqual(env["completeness"], "PARTIAL")
        self.assertFalse(env["full_universe_scan"])
        self.assertNotIn("full-universe scan: yes", pipeline.research_report(env))
        finished = copy.deepcopy(env)
        finished["completeness"] = "COMPLETE"
        self.assertEqual(pipeline.idempotency_key(env), pipeline.idempotency_key(finished))
        other = copy.deepcopy(env)
        other["symbols_not_opened"] = ["OTHER"]
        self.assertNotEqual(pipeline.idempotency_key(env), pipeline.idempotency_key(other))

    def test_ambiguous_or_unresolved_identity_withholds_the_plan(self):
        scan = copy.deepcopy(self.scan)
        first = scan["symbols"][0]["candidates"][0]
        twin = copy.deepcopy(first)
        twin["zone"]["zone_id"] = first["zone"]["zone_id"] + "-twin"
        scan["symbols"][0]["candidates"].append(twin)
        env = pipeline.assemble_scan(scan, self.cfg())
        self.assertEqual(len(env["trade_plans"]), 2)
        for plan in env["trade_plans"]:
            self.assertEqual(plan["identity_status"], pipeline.ZONE_IDENTITY_AMBIGUOUS)
            self.assertFalse(plan["plan_usable"])
            self.assertIsNone(plan["risk_plan"]["quantity_range"])
            self.assertEqual(plan["candidate_status"], first["status"])
        bare = copy.deepcopy(self.scan)
        bare["symbols"][0]["candidates"][0]["zone"]["start_time"] = None
        withheld = pipeline.assemble_scan(bare)["trade_plans"][0]
        self.assertEqual(withheld["identity_status"], pipeline.ZONE_IDENTITY_UNRESOLVED)
        self.assertFalse(withheld["plan_usable"])

    def test_completeness_distinguishes_a_symbol_that_was_never_opened(self):
        partial = pipeline.assemble_scan(copy.deepcopy(self.scan), requested_symbols=["SYN", "NEVER"])
        self.assertEqual(partial["completeness"], "PARTIAL")
        self.assertEqual(partial["symbols_not_opened"], ["NEVER"])
        self.assertIn("not a certified full-universe", pipeline.research_report(partial).replace("\n", " "))
        empty = copy.deepcopy(self.scan)
        empty["symbols"] = []
        self.assertEqual(pipeline.assemble_scan(empty)["completeness"], "FAILED")


class Journal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Shared.setUpClass()
        cls.candles, cls.research_run, cls.scan = Shared.candles, Shared.research_run, Shared.scan

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.conn = store.open_store(os.path.join(self.tmp, "store.db"))
        self.addCleanup(self.cleanup)

    def cleanup(self):
        self.conn.close()
        shutil.rmtree(self.tmp)

    def entry(self, key, when):
        candidate = self.research_run.result.candidates()[0]
        levels = candidate.levels
        return {"symbol": "SYN", "zone_id": candidate.zone["zone_id"], "scan_key": key,
                "planned_entry": levels["entry"][1], "planned_stop": levels["sl"]["normal"][0],
                "planned_target": candidate.gate("G7").evidence["target"]["proximal"], "quantity": 10,
                "alert_note": "synthetic research plan", "checklist": {c: True for c, _, _ in m.CHECKLIST},
                "recorded_at": when}

    def test_portfolio_at_is_point_in_time_and_a_research_run_does_not_write(self):
        _, key = store.import_scan(self.conn, self.scan)
        as_of = datetime.datetime.fromisoformat(self.research_run.result.as_of)
        year, month = (as_of.year + 1, 1) if as_of.month == 12 else (as_of.year, as_of.month + 1)
        start = datetime.datetime(year, month, 3, 10, 0)
        cancel = datetime.datetime(year, month, 8, 10, 0)
        eid = store.journal_add(self.conn, self.entry(key, start.isoformat(timespec="seconds")))
        store.journal_event(self.conn, eid, store.CANCELLED, cancel.isoformat(timespec="seconds"))
        mid = pipeline.PortfolioState.from_journal(self.conn, datetime.datetime(year, month, 5, 10, 0))
        after = pipeline.PortfolioState.from_journal(self.conn, datetime.datetime(year, month, 9, 10, 0))
        zone = self.research_run.result.candidates()[0].zone["zone_id"]
        self.assertTrue(any(z[1] == zone for z in mid.zones_holding_allowance))
        self.assertFalse(any(z[1] == zone for z in after.zones_holding_allowance))
        second = datetime.datetime(year, month, 10, 10, 0)
        trigger = datetime.datetime(year, month, 12, 10, 0)
        exit_at = datetime.datetime(year, month, 14, 10, 0)
        eid = store.journal_add(self.conn, self.entry(key, second.isoformat(timespec="seconds")))
        store.journal_event(self.conn, eid, store.TRIGGERED, trigger.isoformat(timespec="seconds"),
                            price=self.research_run.result.candidates()[0].levels["entry"][1])
        store.journal_event(self.conn, eid, store.STOP_LOSS_HIT, exit_at.isoformat(timespec="seconds"),
                            price=self.research_run.result.candidates()[0].levels["sl"]["normal"][0])
        before = store.portfolio_at(self.conn, second)
        done = store.portfolio_at(self.conn, datetime.datetime(year, month, 15, 10, 0))
        self.assertEqual(before["trades_triggered_this_month"], 0)
        self.assertEqual(before["open_positions"], 0)
        self.assertEqual(done["trades_triggered_this_month"], 1)
        self.assertEqual(done["open_positions"], 0)
        rows = self.conn.execute("SELECT COUNT(*) FROM journal_entries").fetchone()[0]
        import hashlib
        db_path = os.path.join(self.tmp, "store.db")
        self.conn.close()

        def digest_file():
            with open(db_path, "rb") as fh:
                return hashlib.sha256(fh.read()).hexdigest()

        before = digest_file()
        readonly = store.open_readonly(db_path)
        state = pipeline.PortfolioState.from_journal(readonly, exit_at)
        readonly.close()
        self.assertEqual(digest_file(), before)
        self.conn = store.open_store(db_path)
        pipeline.run([R.daily_input("SYN", self.candles)], config(self.candles[-1].end), portfolio=state)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM journal_entries").fetchone()[0], rows)


class Command(unittest.TestCase):
    def test_cli_is_deterministic_and_replay_matches(self):
        candles = _candles()
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        data = os.path.join(tmp, "in")
        os.makedirs(data)
        with open(os.path.join(data, "SYN.csv"), "w", encoding="utf-8") as fh:
            fh.write("date,open,high,low,close\n")
            for candle in candles:
                fh.write("%s,%s,%s,%s,%s\n" % (candle.start.date(), candle.open, candle.high, candle.low, candle.close))
        outs = []
        for name in ("one", "two"):
            out = os.path.join(tmp, name)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(["research", "--as-of", str(candles[-1].start.date()), "--csv-dir", data,
                                           "--risk-per-trade", "1000", "--out", out]), 0)
            outs.append(out)
        with open(os.path.join(outs[0], pipeline.RESEARCH_JSON), encoding="utf-8") as fh:
            first = fh.read()
        with open(os.path.join(outs[1], pipeline.RESEARCH_JSON), encoding="utf-8") as fh:
            second = fh.read()
        self.assertEqual(first, second)
        body = json.loads(first)
        self.assertFalse(body["authorises_order"])
        self.assertIn("blocked_zones", body)
        self.assertTrue(all(p["selected_quantity"] is None for p in body["trade_plans"]))
        with open(os.path.join(outs[0], pipeline.REPORT_MD), encoding="utf-8") as fh:
            report = fh.read()
        for heading in pipeline.HEADINGS:
            self.assertIn("## " + heading, report)
        replay = os.path.join(tmp, "replay")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(["research", "--replay-of", outs[0], "--out", replay]), 0)
        with open(os.path.join(replay, pipeline.RESEARCH_JSON), encoding="utf-8") as fh:
            self.assertEqual(fh.read(), first)


if __name__ == "__main__":
    unittest.main()
