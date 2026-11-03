"""Watchlist alerts over REAL point-in-time scans of the long SYNTHETIC history.

Pairs of scans come from scanner.scan at consecutive as_of times (no lookahead: each scan
reads only candles at or before its own as_of). The tests check the alert contract in
nse/research/alerts.py: stable ids and no duplicates, first-run semantics, an explicit
proximity pct (no invented threshold), the manual-checks warning on BECAME_ACTIONABLE
(spec 8: no status approves a trade) and the idempotent append-only JSONL file.
"""

import io
import json
import os
import shutil
import tempfile
import unittest

import _research as R
from nse.research import alerts, explain, models as m, reports, scanner
from test_research_explain import ZONE, run_cli, scan_dict

CAL = R.WeekdayCalendar()
KEY = "D:" + ZONE
ALL_RULES = list(alerts.RULES[:-1]) + [{"rule": alerts.ZONE_PROXIMITY, "pct": 15.0}]


def scan_at(candles, as_of, symbol="SYN"):
    cfg = scanner.ScanConfig(as_of=as_of, calendar=CAL, calendar_label="TEST_WEEKDAYS", risk_per_trade=1000.0)
    return reports.to_dict(scanner.scan([R.daily_input(symbol, candles)], cfg))


def watchlist(rules=None, symbols=()):
    return alerts.parse_watchlist({"name": "test", "symbols": list(symbols), "rules": rules or ALL_RULES})


def rules_of(events):
    return [(e["rule"], e["symbol"], e["zone"]) for e in events]


class Pairs(object):
    """legout day (no candidate yet) -> follow-through day (ACTIONABLE) -> PL touched (gone)."""
    _c = {}

    @classmethod
    def get(cls):
        if not cls._c:
            cs = R.extend(R.long_mit_candles(), [(176.0, 176.5, 159.5, 170.0)])     # last candle tests the PL
            legout = [i for i, c in enumerate(cs) if c.close == round(101.5 * R.LONG_K, 2)][0]
            cls._c["before"] = scan_at(cs, cs[legout].end)
            cls._c["became"] = scan_at(cs, cs[legout + 1].end)
            cls._c["held"] = scan_at(cs, cs[-2].end)
            cls._c["touched"] = scan_at(cs, cs[-1].end)
        return dict(cls._c)


class Watchlists(unittest.TestCase):
    def test_vocabulary_is_fixed(self):
        with self.assertRaises(alerts.WatchlistError):
            watchlist(["PRICE_UP"])
        with self.assertRaises(alerts.WatchlistError):
            alerts.parse_watchlist({"name": "x", "symbols": "INFY", "rules": ["SCAN_COMPLETED"]})
        with self.assertRaises(alerts.WatchlistError):
            watchlist([alerts.NEW_CANDIDATE, alerts.NEW_CANDIDATE])

    def test_proximity_needs_an_explicit_pct(self):
        for bad in (alerts.ZONE_PROXIMITY, {"rule": alerts.ZONE_PROXIMITY}, {"rule": alerts.ZONE_PROXIMITY, "pct": 0},
                    {"rule": alerts.ZONE_PROXIMITY, "pct": -1}, {"rule": alerts.ZONE_PROXIMITY, "pct": "2"},
                    {"rule": alerts.ZONE_PROXIMITY, "pct": True}, {"rule": alerts.ZONE_PROXIMITY, "pct": float("nan")}):
            with self.assertRaises(alerts.WatchlistError, msg=repr(bad)):
                watchlist([bad])
        self.assertEqual(watchlist([{"rule": alerts.ZONE_PROXIMITY, "pct": 2}])["rules"][alerts.ZONE_PROXIMITY],
                         {"pct": 2.0})


class Evaluate(unittest.TestCase):
    def test_first_run_emits_only_first_run_rules(self):
        p = Pairs.get()
        ev = alerts.evaluate(None, p["became"], watchlist())
        self.assertEqual(set(e["rule"] for e in ev), {alerts.SCAN_COMPLETED, alerts.NEW_CANDIDATE})
        self.assertLessEqual(set(e["rule"] for e in ev), set(alerts.FIRST_RUN_RULES))
        [new] = [e for e in ev if e["rule"] == alerts.NEW_CANDIDATE]
        self.assertEqual((new["zone"], new["status"]), (KEY, m.ACTIONABLE))
        self.assertIn("manual checks are pending and no trade is approved", new["text"])

    def test_became_actionable_carries_the_warning(self):
        p = Pairs.get()
        ev = alerts.evaluate(p["before"], p["became"], watchlist())
        self.assertIn((alerts.NEW_CANDIDATE, "SYN", KEY), rules_of(ev))
        [b] = [e for e in ev if e["rule"] == alerts.BECAME_ACTIONABLE]
        self.assertEqual((b["previous_status"], b["status"]), (None, m.ACTIONABLE))
        self.assertIn("manual checks are pending and no trade is approved", b["text"])

    def test_left_actionable_when_the_zone_is_tested(self):
        p = Pairs.get()
        ev = alerts.evaluate(p["held"], p["touched"], watchlist())
        [left] = [e for e in ev if e["rule"] == alerts.LEFT_ACTIONABLE]
        self.assertEqual((left["zone"], left["status"], left["previous_status"]), (KEY, None, m.ACTIONABLE))
        self.assertIn("D3", left["text"])
        self.assertNotIn(alerts.BECAME_ACTIONABLE, [e["rule"] for e in ev])

    def test_no_change_no_candidate_alerts(self):
        p = Pairs.get()
        ev = alerts.evaluate(p["held"], p["held"], watchlist([alerts.NEW_CANDIDATE, alerts.STATUS_CHANGED,
                                                               alerts.BECAME_ACTIONABLE, alerts.LEFT_ACTIONABLE]))
        self.assertEqual(ev, [])

    def test_status_changed_on_a_real_status_difference(self):
        scan = scan_dict()
        prev = json.loads(json.dumps(scan))
        prev["as_of"] = "2024-02-05T15:30:00"
        agr = [s for s in prev["symbols"] if s["symbol"] == "AGR"][0]["candidates"][0]
        agr["status"] = m.REJECTED                       # a previous record with another status ...
        [g4] = [g for g in agr["gates"] if g["gate"] == "G4"]
        g4["outcome"] = m.FAIL                           # ... that its own gates really give
        ev = alerts.evaluate(prev, scan, watchlist([alerts.STATUS_CHANGED]))
        self.assertEqual(rules_of(ev), [(alerts.STATUS_CHANGED, "AGR", KEY)])
        self.assertEqual((ev[0]["previous_status"], ev[0]["status"]), (m.REJECTED, m.MANUAL_REVIEW))

    def test_data_failure_and_watchlist_filter(self):
        scan = scan_dict()
        ev = alerts.evaluate(None, scan, watchlist([alerts.DATA_FAILURE]))
        self.assertEqual(rules_of(ev), [(alerts.DATA_FAILURE, "GAP", "")])
        self.assertEqual(alerts.evaluate(None, scan, watchlist([alerts.DATA_FAILURE], ["ACT"])), [])
        only = alerts.evaluate(None, scan, watchlist([alerts.NEW_CANDIDATE], ["REJ"]))
        self.assertEqual([e["symbol"] for e in only], ["REJ"])

    def test_proximity_uses_only_the_supplied_pct(self):
        scan = scan_dict()
        act = [s for s in scan["symbols"] if s["symbol"] == "ACT"][0]
        dist = (act["price"] - act["candidates"][0]["zone"]["proximal"]) / act["candidates"][0]["zone"]["proximal"] * 100
        near = alerts.evaluate(None, scan, watchlist([{"rule": alerts.ZONE_PROXIMITY, "pct": dist + 0.01}], ["ACT"]))
        far = alerts.evaluate(None, scan, watchlist([{"rule": alerts.ZONE_PROXIMITY, "pct": dist - 0.01}], ["ACT"]))
        self.assertEqual(near, [])                       # first run: proximity is not a first-run rule
        prev = json.loads(json.dumps(scan))
        near = alerts.evaluate(prev, scan, watchlist([{"rule": alerts.ZONE_PROXIMITY, "pct": dist + 0.01}], ["ACT"]))
        far = alerts.evaluate(prev, scan, watchlist([{"rule": alerts.ZONE_PROXIMITY, "pct": dist - 0.01}], ["ACT"]))
        self.assertEqual(rules_of(near), [(alerts.ZONE_PROXIMITY, "ACT", KEY)])
        self.assertIn("not an entry signal", near[0]["text"])
        self.assertEqual(far, [])

    def test_ids_are_stable_and_never_duplicated(self):
        p = Pairs.get()
        a = alerts.evaluate(p["before"], p["became"], watchlist())
        b = alerts.evaluate(p["before"], p["became"], watchlist())
        self.assertEqual(a, b)
        self.assertEqual(len(set(e["id"] for e in a)), len(a))
        self.assertEqual(a[0]["id"], alerts.alert_id(a[0]["rule"], a[0]["symbol"], a[0]["zone"], a[0]["as_of"]))

    def test_out_of_order_or_mixed_scans_are_refused(self):
        p = Pairs.get()
        with self.assertRaises(ValueError):
            alerts.evaluate(p["became"], p["before"], watchlist())
        wit = json.loads(json.dumps(p["became"]))
        wit["trade_type"] = m.WIT_75
        with self.assertRaises(ValueError):
            alerts.evaluate(p["before"], wit, watchlist())


class Notifiers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_jsonl_is_append_only_and_idempotent(self):
        p = Pairs.get()
        path = os.path.join(self.tmp, "a", "alerts.jsonl")
        n = alerts.JsonlFileNotifier(path)
        ev = alerts.evaluate(p["before"], p["became"], watchlist())
        self.assertEqual(len(n.notify(ev)), len(ev))
        self.assertEqual(n.notify(ev), [])
        self.assertEqual(n.notify(alerts.evaluate(p["before"], p["became"], watchlist())), [])
        more = alerts.evaluate(p["held"], p["touched"], watchlist())
        added = n.notify(more)
        with open(path, encoding="utf-8") as fh:
            lines = [json.loads(x) for x in fh]
        self.assertEqual([x["id"] for x in lines], [e["id"] for e in ev] + [e["id"] for e in added])
        self.assertEqual(len(set(x["id"] for x in lines)), len(lines))

    def test_a_corrupt_file_is_an_error_not_skipped(self):
        path = os.path.join(self.tmp, "bad.jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("not json\n")
        with self.assertRaises(ValueError):
            alerts.JsonlFileNotifier(path).notify([])

    def test_stdout_notifier(self):
        buf = io.StringIO()
        ev = alerts.evaluate(None, Pairs.get()["became"], watchlist())
        alerts.StdoutNotifier(buf).notify(ev)
        self.assertEqual(len(buf.getvalue().splitlines()), len(ev))

    def test_cli(self):
        p = Pairs.get()
        paths = {}
        for k in ("before", "became"):
            paths[k] = os.path.join(self.tmp, k + ".json")
            with open(paths[k], "w", encoding="utf-8") as fh:
                json.dump(p[k], fh)
        wl = os.path.join(self.tmp, "w.json")
        with open(wl, "w", encoding="utf-8") as fh:
            json.dump({"name": "t", "symbols": [], "rules": [alerts.BECAME_ACTIONABLE]}, fh)
        jl = os.path.join(self.tmp, "alerts.jsonl")
        argv = ["alerts", "--watchlist", wl, "--scan", paths["became"], "--previous", paths["before"], "--jsonl", jl]
        code, out, _ = run_cli(alerts, argv)
        self.assertEqual(code, 0)
        self.assertIn("appended 1 of 1", out)
        self.assertIn("not implemented", out)               # external delivery needs owner approval
        self.assertIn("appended 0 of 1", run_cli(alerts, argv)[1])
        with open(wl, "w", encoding="utf-8") as fh:
            json.dump({"name": "t", "symbols": [], "rules": [alerts.ZONE_PROXIMITY]}, fh)
        self.assertEqual(run_cli(alerts, argv)[0], 2)
        self.assertEqual(explain.inconsistencies(p["became"]), [])



class ReviewRegressions(unittest.TestCase):
    """Independent review 2026-11-02: an edited status is refused; limitations and manual-review
    items survive into every event."""

    def test_a_status_its_gates_do_not_give_is_refused(self):
        scan = scan_dict()
        agr = [s for s in scan["symbols"] if s["symbol"] == "AGR"][0]["candidates"][0]
        agr["status"] = m.ACTIONABLE
        with self.assertRaises(ValueError):
            alerts.evaluate(None, scan, watchlist([alerts.NEW_CANDIDATE]))

    def test_events_carry_limitations_and_manual_review(self):
        scan = scan_dict()
        ev = [e for e in alerts.evaluate(None, scan, watchlist([alerts.NEW_CANDIDATE])) if e["symbol"] == "AGR"]
        self.assertTrue(ev)
        for e in ev:
            self.assertIn(m.NOT_EXTERNALLY_VALIDATED, e["limitations"])
            self.assertTrue(set(scan["limitations"]) <= set(e["limitations"]))
            self.assertTrue(e["manual_review"])

if __name__ == "__main__":
    unittest.main()
