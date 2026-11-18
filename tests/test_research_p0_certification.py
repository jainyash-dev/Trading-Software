"""P0 certification build (nse/research/p0_certification.py).

The gate functions are tested on SYNTHETIC rows: that proves the code path, not the
historical files. The last class reads the committed outputs in docs/product-discovery/p0
and checks that they reconcile with each other; it does not re-run the build.
"""

import csv
import datetime
import hashlib
import json
import os
import unittest
from decimal import Decimal

import _research  # noqa: F401  (puts the repository root on sys.path)
from nse.research import corporate_actions as ca, dataset_eligibility as de, p0_certification as p0
from nse.research import instruments
from nse.research.deps import bhavcopy, calendar as cal_mod

D0 = datetime.date(2022, 7, 27)
D1 = datetime.date(2022, 7, 28)
P0_DIR = os.path.join(os.path.dirname(__file__), "..", "docs", "product-discovery", "p0")


def _bar(symbol, day, close, prev_close, low=None, high=None, series="EQ", isin="INE081A01012"):
    c = Decimal(str(close))
    return bhavcopy.BhavRow(symbol=symbol, series=series, trade_date=day, open=c,
                            high=Decimal(str(high if high is not None else close)),
                            low=Decimal(str(low if low is not None else close)), close=c, last=c,
                            prev_close=Decimal(str(prev_close)), traded_qty=1, traded_value=c, total_trades=1,
                            isin=isin, line=2)


class _NoExcludedSessions(object):
    def is_excluded_session(self, d):
        return False

    def is_trading_day(self, d):
        return d.weekday() < 5


class _MuhuratBetween(_NoExcludedSessions):
    def is_excluded_session(self, d):
        return d == datetime.date(2022, 10, 24)


class _UnresolvedBetween(_NoExcludedSessions):
    """2022-10-24 cannot be classified (review F3)."""

    def is_trading_day(self, d):
        if d == datetime.date(2022, 10, 24):
            raise cal_mod.CalendarAmbiguityError("2022-10-24 UNRESOLVED (synthetic)")
        return d.weekday() < 5


def _action(symbol, ex_date, action="SPLIT"):
    return ca.Action(symbol, ex_date, action, 1.0, 10.0, True, "SYNTHETIC")


class CorporateActionGate(unittest.TestCase):
    def test_no_saved_response_status_becomes_a_passing_gate(self):
        passing = {de.CA_COMPLETE, de.CA_COVERED_NONE}
        for status in (ca.MISSING_COVERAGE, ca.EMPTY_RESPONSE, ca.UNPARSED_EVENT, ca.COVERED_WITH_VERIFIED_EVENTS,
                       ca.RESPONSE_PRESENT_COMPLETENESS_NOT_PROVED, "", None):
            self.assertNotIn(p0.ca_gate_value(status), passing, status)

    def test_an_empty_body_stays_completeness_unknown(self):
        self.assertEqual(p0.ca_gate_value(ca.response_status("[]")), ca.EMPTY_RESPONSE)

    def test_parsed_price_events_do_not_prove_completeness(self):
        self.assertEqual(p0.ca_gate_value(ca.response_status('[{"subject": "Split"}]', parsed_price_events=2)),
                         p0.CA_EVENTS_COMPLETENESS_NOT_PROVED)

    def test_a_body_that_is_not_a_list_of_events_is_malformed(self):
        # review M-1: an error page, an object, null or a list of non-events is never a response
        for body in ('{"error": "Not Found"}', "<html>Access Denied</html>", "null", "[1]", '[{"x": 1}]'):
            self.assertEqual(ca.response_status(body), ca.MALFORMED_RESPONSE, body)
            self.assertEqual(ca.evidence_tier(ca.response_status(body), True, True), ca.CA_UNVERIFIED, body)
        for body in ("[]", "[ ]", "[\n]"):
            self.assertEqual(ca.response_status(body), ca.EMPTY_RESPONSE, body)


class EvidenceTier(unittest.TestCase):
    """D62: response integrity is a weaker tier than completeness and never passes the gate."""

    def test_integrity_with_passing_price_checks_is_the_weaker_tier(self):
        for status in (ca.COVERED_WITH_VERIFIED_EVENTS, ca.RESPONSE_PRESENT_COMPLETENESS_NOT_PROVED):
            self.assertEqual(ca.evidence_tier(status, True), ca.CA_RESPONSE_PRESENT_NOT_COMPLETE)

    def test_everything_else_stays_unverified(self):
        for status in (ca.EMPTY_RESPONSE, ca.UNPARSED_EVENT, ca.MISSING_COVERAGE, p0.CA_HASH_MISMATCH,
                       p0.CA_OUTSIDE_WINDOW, None):
            self.assertEqual(ca.evidence_tier(status, True), ca.CA_UNVERIFIED, status)
        self.assertEqual(ca.evidence_tier(ca.COVERED_WITH_VERIFIED_EVENTS, False), ca.CA_UNVERIFIED)
        self.assertEqual(ca.CA_UNVERIFIED, "CORPORATE_ACTIONS_UNVERIFIED")

    def test_completeness_is_never_inferred(self):
        for status in (ca.COVERED_WITH_VERIFIED_EVENTS, ca.RESPONSE_PRESENT_COMPLETENESS_NOT_PROVED):
            for integrity in (True, False):
                self.assertNotEqual(ca.evidence_tier(status, integrity), ca.CA_COMPLETENESS_VERIFIED)

    def _row(self, **g):
        gates = {k: v for k, v in de.passing_gates().items() if k in de.DATA_GATES}
        gates.update(g)
        return de.classify_symbol_date("INFY", "2022-01-03", "INE009A01021", gates, "SYNTHETIC",
                                       required_gates=de.DATA_GATES)

    def test_the_weaker_tier_is_exploratory_and_not_certified(self):
        row = self._row(corporate_action=p0.CA_EVENTS_COMPLETENESS_NOT_PROVED)
        self.assertNotEqual(row["final_eligibility"], de.ELIGIBLE)
        self.assertEqual(p0.research_use(row, ca.CA_RESPONSE_PRESENT_NOT_COMPLETE), p0.USE_EXPLORATORY)
        self.assertEqual(p0.research_use(row, ca.CA_UNVERIFIED), p0.USE_EXCLUDED)

    def test_another_failed_gate_is_not_exploratory(self):
        row = self._row(corporate_action=p0.CA_EVENTS_COMPLETENESS_NOT_PROVED, membership="UNVERIFIED")
        self.assertEqual(p0.research_use(row, ca.CA_RESPONSE_PRESENT_NOT_COMPLETE), p0.USE_EXCLUDED)

    def test_only_a_passing_row_is_certified(self):
        self.assertEqual(p0.research_use(self._row(), ca.CA_UNVERIFIED), p0.USE_CERTIFIED)


class PriceStep(unittest.TestCase):
    def _step(self, today, prior, actions=(), linked=("TATASTEEL",), cal=None):
        return p0.price_step("TATASTEEL", D1, D0, {"TATASTEEL": {"EQ": today}} if today else {},
                             prior, list(linked), list(actions), cal or _NoExcludedSessions())

    def test_a_split_with_an_intact_prevclose_chain_is_not_continuous(self):
        # the 2022-07-28 shape: PREVCLOSE prints the unadjusted 959.4, the session trades near 100
        today = _bar("TATASTEEL", D1, 100.35, 959.4, low=97, high=101)
        prior = {"TATASTEEL": {"EQ": _bar("TATASTEEL", D0, 959.4, 949.5)}}
        value, _ = self._step(today, prior, [_action("TATASTEEL", D1)])
        self.assertEqual(value, p0.PX_PRICE_EVENT + ":SPLIT")

    def test_an_unrecorded_scale_change_is_flagged_not_called_continuous(self):
        today = _bar("TATASTEEL", D1, 100.35, 959.4, low=97, high=101)
        prior = {"TATASTEEL": {"EQ": _bar("TATASTEEL", D0, 959.4, 949.5)}}
        self.assertEqual(self._step(today, prior)[0], p0.PX_SCALE_GAP)

    def test_an_event_filed_under_a_linked_symbol_is_found(self):
        today = _bar("TATASTEEL", D1, 100.35, 959.4, low=97, high=101)
        prior = {"TATASTEEL": {"EQ": _bar("TATASTEEL", D0, 959.4, 949.5)}}
        value, _ = self._step(today, prior, [_action("TISCO", D1, "DEMERGER")], linked=("TATASTEEL", "TISCO"))
        self.assertEqual(value, p0.PX_PRICE_EVENT + ":DEMERGER")

    def test_an_ordinary_session_is_continuous(self):
        today = _bar("TATASTEEL", D1, 965, 959.4, low=950, high=970)
        prior = {"TATASTEEL": {"EQ": _bar("TATASTEEL", D0, 959.4, 949.5)}}
        self.assertEqual(self._step(today, prior)[0], de.PRICE_CONTINUOUS)

    def test_a_be_only_prior_session_stays_missing_eq(self):
        today = _bar("TATASTEEL", D1, 965, 959.4)
        prior = {"TATASTEEL": {"BE": _bar("TATASTEEL", D0, 959.4, 949.5, series="BE")}}
        self.assertEqual(self._step(today, prior)[0], p0.PX_PRIOR_NON_EQ + ":BE")

    def test_no_eq_row_today(self):
        prior = {"TATASTEEL": {"EQ": _bar("TATASTEEL", D0, 959.4, 949.5)}}
        self.assertEqual(self._step(None, prior)[0], p0.PX_NO_EQ_ROW)

    def test_a_prevclose_break_with_no_explanation_fails(self):
        today = _bar("TATASTEEL", D1, 965, 950, low=950, high=970)
        prior = {"TATASTEEL": {"EQ": _bar("TATASTEEL", D0, 959.4, 949.5)}}
        self.assertEqual(self._step(today, prior)[0], p0.PX_UNEXPLAINED)

    def test_a_break_across_an_excluded_session_is_named_and_fails(self):
        a, b = datetime.date(2022, 10, 21), datetime.date(2022, 10, 25)
        today = _bar("TATASTEEL", b, 105, 104, low=100, high=106)
        prior = {"TATASTEEL": {"EQ": _bar("TATASTEEL", a, 103, 101)}}
        value, detail = p0.price_step("TATASTEEL", b, a, {"TATASTEEL": {"EQ": today}}, prior, ["TATASTEEL"], [],
                                      _MuhuratBetween())
        self.assertEqual(value, p0.PX_EXCLUDED_SESSION)
        self.assertIn("2022-10-24", detail)

    def test_an_isin_change_is_not_spliced(self):
        today = _bar("TATASTEEL", D1, 960, 959.4, low=955, high=965, isin="INE081A01020")
        prior = {"TATASTEEL": {"EQ": _bar("TATASTEEL", D0, 959.4, 949.5)}}
        self.assertEqual(self._step(today, prior)[0], p0.PX_ISIN_CHANGE)

    def test_a_different_isin_under_a_linked_symbol_is_not_the_prior_row(self):
        today = _bar("TATASTEEL", D1, 960, 959.4, low=955, high=965)
        prior = {"TISCO": {"EQ": _bar("TISCO", D0, 959.4, 949.5, isin="INE999X01010")}}
        value, _ = self._step(today, prior, linked=("TATASTEEL", "TISCO"))
        self.assertEqual(value, p0.PX_PRIOR_MISSING)

    def test_an_unclassifiable_date_inside_the_step_fails_even_with_an_intact_chain(self):
        # review F3: 2022-10-21 -> 2022-10-25 across an UNRESOLVED 2022-10-24 (D54)
        a, b = datetime.date(2022, 10, 21), datetime.date(2022, 10, 25)
        today = _bar("TATASTEEL", b, 104, 103, low=102, high=105)
        prior = {"TATASTEEL": {"EQ": _bar("TATASTEEL", a, 103, 101)}}
        value, detail = p0.price_step("TATASTEEL", b, a, {"TATASTEEL": {"EQ": today}}, prior, ["TATASTEEL"], [],
                                      _UnresolvedBetween())
        self.assertEqual(value, p0.PX_CALENDAR_UNRESOLVED)
        self.assertIn("2022-10-24", detail)

    def test_scale_gap_is_the_shared_definition(self):
        self.assertIs(p0.SCALE_GAP_BAND, ca.SCALE_GAP_BAND)
        for args in (("100", "70", "84"), ("100", "80", "86"), ("100", "118", "130")):
            self.assertEqual(p0.scale_gap(*[Decimal(x) for x in args]), ca.price_scale_gap(*args))

    def test_scale_gap_band(self):
        self.assertTrue(p0.scale_gap(Decimal("100"), Decimal("70"), Decimal("84")))
        self.assertFalse(p0.scale_gap(Decimal("100"), Decimal("80"), Decimal("86")))
        self.assertTrue(p0.scale_gap(Decimal("100"), Decimal("118"), Decimal("130")))
        self.assertTrue(p0.scale_gap(Decimal("0"), Decimal("1"), Decimal("2")))


class Register(unittest.TestCase):
    def test_runs_split_on_a_gate_change_and_sessions_add_up(self):
        def row(sym, day, **g):
            gates = de.passing_gates()
            gates.update(g)
            return de.classify_symbol_date(sym, day, "INE000A01000", gates, "SYNTHETIC")
        rows = [row("A", "2021-01-01", membership="UNVERIFIED"), row("A", "2021-01-04", membership="UNVERIFIED"),
                row("A", "2021-01-05", corporate_action=ca.EMPTY_RESPONSE), row("B", "2021-01-01"),
                row("A", "2021-01-06", membership="UNVERIFIED")]
        reg = p0.register(rows)
        self.assertEqual([(r["symbol"], r["from_date"], r["to_date"], r["sessions"]) for r in reg],
                         [("A", "2021-01-01", "2021-01-04", 2), ("A", "2021-01-05", "2021-01-05", 1),
                          ("A", "2021-01-06", "2021-01-06", 1)])
        self.assertEqual(sum(r["sessions"] for r in reg), 4)       # B passed and is not excluded


class RegisterAcrossGaps(unittest.TestCase):
    """Review F1: a run never spans window sessions on which the symbol was not a member,
    and a new membership period starts a new row."""

    def _row(self, sym, day, period):
        gates = {k: v for k, v in de.passing_gates().items() if k in de.DATA_GATES}
        gates["membership"] = "UNVERIFIED"
        r = de.classify_symbol_date(sym, day, "INE000A01000", gates, "SYNTHETIC", required_gates=de.DATA_GATES)
        r.update(period_from=period, ca_tier=ca.CA_UNVERIFIED, research_use=p0.USE_EXCLUDED)
        return r

    def test_a_non_member_gap_and_a_new_period_split_the_run(self):
        days = ["2021-01-01", "2021-01-04", "2021-01-05", "2021-01-06", "2021-01-07"]
        rows = [self._row("B", d, "2020-12-31") for d in days]
        rows += [self._row("A", days[0], "2020-12-31"), self._row("A", days[1], "2020-12-31"),
                 self._row("A", days[3], "2021-01-06"), self._row("A", days[4], "2021-01-06")]
        reg = p0.register(rows)
        a = [(x["from_date"], x["to_date"], x["sessions"], x["membership_period_from"]) for x in reg if x["symbol"] == "A"]
        self.assertEqual(a, [("2021-01-01", "2021-01-04", 2, "2020-12-31"), ("2021-01-06", "2021-01-07", 2, "2021-01-06")])
        self.assertTrue(p0.register_covers_exactly_once(rows, reg))

    def test_same_period_with_a_gap_still_splits(self):
        days = ["2021-01-01", "2021-01-04", "2021-01-05"]
        rows = [self._row("B", d, "2020-12-31") for d in days]
        rows += [self._row("A", days[0], "2020-12-31"), self._row("A", days[2], "2020-12-31")]
        a = [x["sessions"] for x in p0.register(rows) if x["symbol"] == "A"]
        self.assertEqual(a, [1, 1])

    def test_the_exactly_once_check_catches_a_bad_register(self):
        days = ["2021-01-01", "2021-01-04"]
        rows = [self._row("A", d, "2020-12-31") for d in days]
        reg = p0.register(rows)
        self.assertTrue(p0.register_covers_exactly_once(rows, reg))
        self.assertFalse(p0.register_covers_exactly_once(rows, reg + reg))
        self.assertFalse(p0.register_covers_exactly_once(rows, []))


class _Tmp(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp)

    def write(self, rel, text):
        path = os.path.join(self.tmp, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        import hashlib
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()


class IdentityValue(_Tmp):
    """Review F5: the identity gate on SYNTHETIC instrument records."""

    HEADER = ("record_type,symbol,new_symbol,isin,series,effective_from,effective_to,source,source_file,"
              "source_sha256,recorded_on,notes\n")

    def records(self, lines):
        sha = self.write("src.txt", "synthetic source\n")
        body = "".join(l.replace("SHA", sha) for l in lines)
        self.write("records.csv", self.HEADER + body)
        return instruments.load(os.path.join(self.tmp, "records.csv"))

    def test_resolved_and_each_failure(self):
        recs = self.records(["LISTING,INFY,,INE009A01021,EQ,2016-01-01,,NSE,src.txt,SHA,2026-11-13,\n",
                             "LISTING,GRASIM,,INE047A01013,EQ,2016-01-01,,NSE,src.txt,SHA,2026-11-13,\n",
                             "LISTING,GRASIM,,INE047A01021,EQ,2016-01-01,,NSE,src.txt,SHA,2026-11-13,\n",
                             "LISTING,UNV,,INE111A01011,EQ,2016-01-01,,NSE,src.txt,,2026-11-13,\n"])
        day = datetime.date(2022, 1, 3)
        eq = _bar("INFY", day, 1, 1, isin="INE009A01021")
        self.assertEqual(p0.identity_value(recs, "INFY", day, "INE009A01021", eq)[0], de.IDENTITY_RESOLVED)
        self.assertEqual(p0.identity_value(recs, "INFY", day, "INE009A01021", None)[0], de.IDENTITY_RESOLVED)
        self.assertEqual(p0.identity_value(recs, "INFY", day, "INE999A01010", eq)[0], p0.ID_PERIOD_ISIN_MISMATCH)
        self.assertEqual(p0.identity_value(recs, "INFY", day, "INE009A01021",
                                           _bar("INFY", day, 1, 1, isin="INE009A01039"))[0], p0.ID_BHAVCOPY_ISIN_MISMATCH)
        self.assertEqual(p0.identity_value(recs, "GRASIM", day, "INE047A01021", None)[0], p0.ID_UNKNOWN)
        self.assertEqual(p0.identity_value(recs, "DUMMYX", day, "INE000A01000", None)[0], p0.ID_UNKNOWN)
        self.assertEqual(p0.identity_value(recs, "UNV", day, "INE111A01011", None)[0], p0.ID_UNVERIFIED_RECORD)


class CorporateActionBodies(_Tmp):
    """Review F2/F5: response loading on SYNTHETIC coverage, action and raw files."""

    def setup_files(self, coverage_rows, actions_rows=()):
        cov = ",".join(ca.COVERAGE_COLUMNS) + "\n" + "".join(coverage_rows)
        self.write("coverage.csv", cov)
        self.write("actions.csv", ",".join(ca.COLUMNS) + "\n" + "".join(actions_rows))
        return (os.path.join(self.tmp, "coverage.csv"), os.path.join(self.tmp, "actions.csv"),
                os.path.join(self.tmp, "raw"))

    def cov(self, sym, name, sha):
        return "%s,2016-01-01,2025-12-31,raw/%s,%s,1,2026-11-09,synthetic\n" % (sym, name, sha)

    def test_statuses_retry_and_hash_mismatch(self):
        div = self.write("raw/ca_DIV_2016_2025.json", '[{"subject": "Dividend - Rs 5 Per Share"}]')
        unp = self.write("raw/ca_UNP_2016_2025.json", '[{"subject": "Scheme Of Arrangement"}]')
        self.write("raw/ca_BAD_2016_2025.json", '[{"subject": "Dividend"}]')
        self.write("raw/ca_EMP_2016_2025.json", "[]")
        self.write("raw/ca_RTY_2016_2025.retry1.json", "[]")
        paths = self.setup_files(
            [self.cov("DIV", "ca_DIV_2016_2025.json", div), self.cov("UNP", "ca_UNP_2016_2025.json", unp),
             self.cov("BAD", "ca_BAD_2016_2025.json", "0" * 64)],
            ["UNP,2020-01-01,UNPARSED_PRICE_EVENT,0,0,NSE,raw/ca_UNP_2016_2025.json,%s,2026-11-09,x\n" % unp])
        got = {k: v["status"] for k, v in p0.corporate_action_bodies(*paths).items()}
        self.assertEqual(got, {"DIV": ca.RESPONSE_PRESENT_COMPLETENESS_NOT_PROVED, "UNP": ca.UNPARSED_EVENT,
                               "BAD": p0.CA_HASH_MISMATCH, "EMP": ca.EMPTY_RESPONSE, "RTY": ca.EMPTY_RESPONSE})
        self.assertEqual(ca.evidence_tier(got["UNP"], True), ca.CA_UNVERIFIED)
        self.assertEqual(ca.evidence_tier(got["BAD"], True), ca.CA_UNVERIFIED)

    def test_raw_only_bodies_are_verified_against_the_collection_log(self):
        # review M-2: `[]` is hash-verified only through the collector's log; disagreeing retries conflict
        logged = self.write("raw/ca_LOG_2016_2025.json", "[]")
        self.write("raw/ca_NOLOG_2016_2025.json", "[]")
        self.write("raw/ca_MIX_2016_2025.json", "[]")
        self.write("raw/ca_MIX_2016_2025.retry1.json", '[{"subject": "Dividend"}]')
        self.write("collection_log.jsonl", json.dumps({"file": "raw/ca_LOG_2016_2025.json", "sha256": logged}) + "\n")
        paths = self.setup_files([])
        got = p0.corporate_action_bodies(*paths, collection_log=os.path.join(self.tmp, "collection_log.jsonl"))
        self.assertEqual((got["LOG"]["status"], got["LOG"]["hash_verified"]), (ca.EMPTY_RESPONSE, True))
        self.assertEqual((got["NOLOG"]["status"], got["NOLOG"]["hash_verified"]), (ca.EMPTY_RESPONSE, False))
        self.assertEqual(got["MIX"]["status"], p0.CA_CONFLICTING)

    def test_a_price_entry_the_parser_skipped_counts_as_unparsed(self):
        # review N-3: an unreadable ex-date or a non-EQ series on a price-type subject never vanishes
        bodies = {"EXD": '[{"series": "EQ", "exDate": "-", "subject": "Bonus 1:1"}]',
                  "BES": '[{"series": "BE", "exDate": "13-Apr-2016", "subject": "Bonus 1:1"}]',
                  "DIV": '[{"series": "EQ", "exDate": "-", "subject": "Dividend - Rs 2 Per Share"}]'}
        rows = []
        for sym, body in bodies.items():
            sha = self.write("raw/ca_%s_2016_2025.json" % sym, body)
            rows.append(self.cov(sym, "ca_%s_2016_2025.json" % sym, sha))
        got = {k: v["status"] for k, v in p0.corporate_action_bodies(*self.setup_files(rows)).items()}
        self.assertEqual(got, {"EXD": ca.UNPARSED_EVENT, "BES": ca.UNPARSED_EVENT,
                               "DIV": ca.RESPONSE_PRESENT_COMPLETENESS_NOT_PROVED})

    def test_every_entry_the_parser_drops_is_counted_by_its_own_rule(self):
        # review N-3b: no stripping, no defaulting; only a dividend-only or known non-price subject is harmless
        dropped = ('[{"exDate": "01-Jun-2021", "subject": "Bonus 1:1"}]',                       # no series key
                   '[{"series": "eq", "exDate": "01-Jun-2021", "subject": "Bonus 1:1"}]',
                   '[{"series": "EQ ", "exDate": "01-Jun-2021", "subject": "Bonus 1:1"}]',
                   '[{"series": "EQ", "exDate": " 01-Jun-2021", "subject": "Bonus 1:1"}]',
                   '[{"series": "EQ", "subject": "Spin off"}]')                                    # unrecognised
        for body in dropped:
            self.assertEqual(ca.unreadable_price_entries(body), 1, body)
        harmless = ('[{"series": "BE", "exDate": "-", "subject": "Dividend - Rs 2 Per Share"}]',
                    '[{"series": "BE", "exDate": "-", "subject": "Annual General Meeting"}]',
                    '[{"series": "EQ", "exDate": "01-Jun-2021", "subject": "Bonus 1:1"}]')        # read by the parser
        for body in harmless:
            self.assertEqual(ca.unreadable_price_entries(body), 0, body)

    def test_a_duplicate_coverage_row_is_refused(self):
        a = self.write("raw/ca_XYZ_2016_2025.json", '[{"subject": "Scheme Of Arrangement"}]')
        b = self.write("raw/ca_XYZ_2016_2025.retry1.json", '[{"subject": "Dividend"}]')
        paths = self.setup_files([self.cov("XYZ", "ca_XYZ_2016_2025.json", a),
                                  self.cov("XYZ", "ca_XYZ_2016_2025.retry1.json", b)])
        with self.assertRaises(ValueError):
            p0.corporate_action_bodies(*paths)


class CompletenessRegister(_Tmp):
    """D66 / OD-CA-1: two independent sources + reconciliation + USER_APPROVED dual-hash marker."""

    PROOF_A = "synthetic completeness proof A (official extract)\n"
    PROOF_B = "synthetic completeness proof B (independent official extract)\n"

    def _recon_body(self, sym, sha_a, sha_b, unresolved=None, status=None, events=None):
        return json.dumps({
            "schema": ca.RECONCILIATION_SCHEMA,
            "symbol": sym,
            "from_date": "2020-01-01",
            "to_date": "2025-12-31",
            "source_a_sha256": sha_a,
            "source_b_sha256": sha_b,
            "events": events if events is not None else [
                {"key": "DIVIDEND|2022-01-05|", "source_a": "PRESENT", "source_b": "PRESENT",
                 "status": ca.EVENT_MATCH},
            ],
            "unresolved": [] if unresolved is None else unresolved,
            "status": status or ca.RECONCILIATION_OK,
        }, sort_keys=True) + "\n"

    def accepted(self, symbols, sha_a, sha_b, recon_by_sym, decision="D99"):
        return {decision: {(frozenset((sha_a, sha_b)), recon_by_sym[s], s, "2020-01-01", "2025-12-31")
                           for s in symbols}}

    def register(self, rows, accepted=None, file_a="proof_a.txt", file_b="proof_b.txt",
                 bad_recon=None):
        """rows: (symbol, decision, sources_good). bad_recon overrides recon status for a symbol."""
        sha_a = self.write(file_a, self.PROOF_A)
        sha_b = self.write(file_b, self.PROOF_B)
        recon_sha = {}
        lines = ",".join(ca.COMPLETENESS_COLUMNS) + "\n"
        for sym, decision, good in rows:
            body = self._recon_body(sym, sha_a, sha_b,
                                    unresolved=(["x"] if bad_recon == sym else None),
                                    status=("CONFLICT" if bad_recon == ("status", sym) else None))
            rsha = self.write("recon_%s.json" % sym, body)
            recon_sha[sym] = rsha
            sa, sb = (sha_a, sha_b) if good else ("0" * 64, sha_b)
            lines += ("%s,2020-01-01,2025-12-31,SYNTHETIC A,%s,%s,SYNTHETIC B,%s,%s,"
                      "recon_%s.json,%s,%s,2026-11-15,synthetic\n"
                      % (sym, file_a, sa, file_b, sb if good else sha_b, sym, rsha, decision))
        self.write("completeness.csv", lines)
        if accepted is None:
            accepted = self.accepted(tuple(recon_sha), sha_a, sha_b, recon_sha)
        return ca.load_completeness(os.path.join(self.tmp, "completeness.csv"), accepted), sha_a, sha_b, recon_sha

    def test_a_missing_register_is_empty(self):
        self.assertEqual(ca.load_completeness(os.path.join(self.tmp, "none.csv")), {})
        self.assertEqual(ca.load_completeness(None), {})

    def test_only_dual_source_verified_rows_with_an_owner_decision_count(self):
        reg, _, _, _ = self.register([("AAA", "D99", True), ("BBB", "", True), ("CCC", "D99", False),
                                      ("DDD", "approved", True)])
        self.assertEqual(sorted(reg), ["AAA"])
        self.assertTrue(ca.completeness_proved(reg, "AAA", datetime.date(2022, 1, 3)))
        self.assertFalse(ca.completeness_proved(reg, "AAA", datetime.date(2026, 1, 2)))
        self.assertFalse(ca.completeness_proved(reg, "BBB", datetime.date(2022, 1, 3)))

    def test_the_decision_must_have_accepted_this_dual_window(self):
        reg, sha_a, sha_b, recon = self.register([
            ("AAA", "D99", True), ("BBB", "D42", True), ("CCC", "D7", True), ("DDD", "D1", True)])
        self.assertEqual(sorted(reg), ["AAA"])
        self.assertEqual(self.register([("AAA", "D99", True)], accepted={})[0], {})
        wrong_sym = self.accepted(("ZZZ",), sha_a, sha_b, {"ZZZ": recon["AAA"]})
        self.assertEqual(self.register([("AAA", "D99", True)], accepted=wrong_sym)[0], {})
        other = {"D99": {(frozenset(("f" * 64, "e" * 64)), recon["AAA"], "AAA", "2020-01-01", "2025-12-31")}}
        self.assertEqual(self.register([("AAA", "D99", True)], accepted=other)[0], {})

    def test_one_source_alone_never_proves_completeness(self):
        sha_a = self.write("proof_a.txt", self.PROOF_A)
        sha_b = self.write("proof_b.txt", self.PROOF_B)
        rsha = self.write("recon_AAA.json", self._recon_body("AAA", sha_a, sha_b))
        # Legacy single-source header is refused (malformed for D66 schema).
        self.write("completeness.csv",
                   "symbol,from_date,to_date,source,source_file,source_sha256,owner_decision,recorded_on,notes\n"
                   "AAA,2020-01-01,2025-12-31,SYNTHETIC,proof_a.txt,%s,D99,2026-11-15,x\n" % sha_a)
        with self.assertRaises(ca.CorporateActionError):
            ca.load_completeness(os.path.join(self.tmp, "completeness.csv"),
                                 {"D99": {(frozenset((sha_a, sha_b)), rsha, "AAA", "2020-01-01", "2025-12-31")}})

    def test_identical_or_copied_sources_are_not_independent(self):
        sha = self.write("proof_a.txt", self.PROOF_A)
        self.write("proof_b.txt", self.PROOF_A)  # byte-identical copy
        rsha = self.write("recon_AAA.json", self._recon_body("AAA", sha, sha))
        lines = ",".join(ca.COMPLETENESS_COLUMNS) + "\n"
        lines += ("AAA,2020-01-01,2025-12-31,SYNTHETIC A,proof_a.txt,%s,SYNTHETIC B,proof_b.txt,%s,"
                  "recon_AAA.json,%s,D99,2026-11-15,synthetic\n" % (sha, sha, rsha))
        self.write("completeness.csv", lines)
        accepted = {"D99": {(frozenset((sha, sha)), rsha, "AAA", "2020-01-01", "2025-12-31")}}
        # Same hash pair is rejected by completeness_decisions and by sources_independent.
        self.assertEqual(ca.load_completeness(os.path.join(self.tmp, "completeness.csv"), accepted), {})
        # Distinct recorded hashes but identical bytes also fail independence.
        sha_b = self.write("proof_b2.txt", self.PROOF_B)
        rsha2 = self.write("recon_AAA2.json", self._recon_body("AAA", sha, sha_b))
        # Replace B content with A's bytes while keeping sha_b label -> hash verify fails; use copy:
        self.write("proof_copy.txt", self.PROOF_A)
        sha_copy = hashlib.sha256(self.PROOF_A.encode()).hexdigest()
        self.assertEqual(sha_copy, sha)
        lines = ",".join(ca.COMPLETENESS_COLUMNS) + "\n"
        lines += ("AAA,2020-01-01,2025-12-31,SYNTHETIC A,proof_a.txt,%s,SYNTHETIC B,proof_copy.txt,%s,"
                  "recon_AAA2.json,%s,D99,2026-11-15,synthetic\n" % (sha, sha_copy, rsha2))
        self.write("completeness.csv", lines)
        accepted = {"D99": {(frozenset((sha, sha_b)), rsha2, "AAA", "2020-01-01", "2025-12-31")}}
        # acceptance names sha_b (PROOF_B) but file is copy of A: fails hash or independence
        self.assertEqual(ca.load_completeness(os.path.join(self.tmp, "completeness.csv"), accepted), {})
        accepted_copy = {"D99": {(frozenset((sha, sha_copy)), rsha2, "AAA", "2020-01-01", "2025-12-31")}}
        # Even if acceptance matches both hashes of the same bytes, independence rejects.
        rsha3 = self.write("recon_AAA3.json", self._recon_body("AAA", sha, sha_copy))
        lines = ",".join(ca.COMPLETENESS_COLUMNS) + "\n"
        lines += ("AAA,2020-01-01,2025-12-31,SYNTHETIC A,proof_a.txt,%s,SYNTHETIC B,proof_copy.txt,%s,"
                  "recon_AAA3.json,%s,D99,2026-11-15,synthetic\n" % (sha, sha_copy, rsha3))
        self.write("completeness.csv", lines)
        accepted_copy = {"D99": {(frozenset((sha, sha_copy)), rsha3, "AAA", "2020-01-01", "2025-12-31")}}
        self.assertEqual(ca.load_completeness(os.path.join(self.tmp, "completeness.csv"), accepted_copy), {})

    def test_unresolved_reconciliation_fails_closed(self):
        reg, _, _, _ = self.register([("AAA", "D99", True)], bad_recon="AAA")
        self.assertEqual(reg, {})
        cmp_result = ca.reconcile_event_keys(["SPLIT|2022-01-12|1:10"], ["SPLIT|2022-01-13|1:10"])
        self.assertEqual(cmp_result["only_a"], ["SPLIT|2022-01-12|1:10"])
        self.assertEqual(cmp_result["only_b"], ["SPLIT|2022-01-13|1:10"])

    def test_a_conflict_event_fails_closed_even_with_empty_unresolved(self):
        # ENG-4 (ED-60): a record that says RECONCILED with an empty `unresolved` list but carries
        # an event whose status is not MATCH/EQUIVALENT must never prove completeness.
        sha_a = self.write("proof_a.txt", self.PROOF_A)
        sha_b = self.write("proof_b.txt", self.PROOF_B)

        def run(event_status):
            body = self._recon_body("AAA", sha_a, sha_b, events=[
                {"key": "SPLIT|2022-01-12|1:10", "source_a": "PRESENT", "source_b": "PRESENT",
                 "status": event_status}])
            rsha = self.write("recon_AAA.json", body)
            lines = ",".join(ca.COMPLETENESS_COLUMNS) + "\n"
            lines += ("AAA,2020-01-01,2025-12-31,SYNTHETIC A,proof_a.txt,%s,SYNTHETIC B,proof_b.txt,%s,"
                      "recon_AAA.json,%s,D99,2026-11-15,synthetic\n" % (sha_a, sha_b, rsha))
            self.write("completeness.csv", lines)
            accepted = {"D99": {(frozenset((sha_a, sha_b)), rsha, "AAA", "2020-01-01", "2025-12-31")}}
            return ca.load_completeness(os.path.join(self.tmp, "completeness.csv"), accepted)

        # Positive control: the same record with a MATCH event is accepted, so the path is exercised.
        self.assertEqual(sorted(run(ca.EVENT_MATCH)), ["AAA"])
        for bad in ("CONFLICT", "MISSING_IN_A", "MISSING_IN_B", "", "match-ish"):
            self.assertEqual(run(bad), {}, bad)

    def test_empty_events_without_empty_window_flag_fail_closed(self):
        # IR-P0-01: a rubber-stamped empty recon must not prove completeness.
        sha_a = self.write("proof_a.txt", self.PROOF_A)
        sha_b = self.write("proof_b.txt", self.PROOF_B)
        empty = json.dumps({
            "schema": ca.RECONCILIATION_SCHEMA, "symbol": "AAA",
            "from_date": "2020-01-01", "to_date": "2025-12-31",
            "source_a_sha256": sha_a, "source_b_sha256": sha_b,
            "events": [], "unresolved": [], "status": ca.RECONCILIATION_OK,
        }, sort_keys=True) + "\n"
        rsha = self.write("recon_AAA.json", empty)
        lines = ",".join(ca.COMPLETENESS_COLUMNS) + "\n"
        lines += ("AAA,2020-01-01,2025-12-31,SYNTHETIC A,proof_a.txt,%s,SYNTHETIC B,proof_b.txt,%s,"
                  "recon_AAA.json,%s,D99,2026-11-15,synthetic\n" % (sha_a, sha_b, rsha))
        self.write("completeness.csv", lines)
        accepted = {"D99": {(frozenset((sha_a, sha_b)), rsha, "AAA", "2020-01-01", "2025-12-31")}}
        self.assertEqual(ca.load_completeness(os.path.join(self.tmp, "completeness.csv"), accepted), {})
        # Explicit empty_window=true with no events is a valid "both sources: no events" recon.
        ok = json.dumps({
            "schema": ca.RECONCILIATION_SCHEMA, "symbol": "AAA",
            "from_date": "2020-01-01", "to_date": "2025-12-31",
            "source_a_sha256": sha_a, "source_b_sha256": sha_b,
            "events": [], "unresolved": [], "status": ca.RECONCILIATION_OK,
            "empty_window": True,
        }, sort_keys=True) + "\n"
        rsha2 = self.write("recon_AAA2.json", ok)
        lines = ",".join(ca.COMPLETENESS_COLUMNS) + "\n"
        lines += ("AAA,2020-01-01,2025-12-31,SYNTHETIC A,proof_a.txt,%s,SYNTHETIC B,proof_b.txt,%s,"
                  "recon_AAA2.json,%s,D99,2026-11-15,synthetic\n" % (sha_a, sha_b, rsha2))
        self.write("completeness.csv", lines)
        accepted = {"D99": {(frozenset((sha_a, sha_b)), rsha2, "AAA", "2020-01-01", "2025-12-31")}}
        self.assertEqual(sorted(ca.load_completeness(os.path.join(self.tmp, "completeness.csv"), accepted)),
                         ["AAA"])

    def test_a_saved_api_response_is_not_completeness_proof(self):
        os.makedirs(os.path.join(self.tmp, "raw"), exist_ok=True)
        # Put API-shaped file as source_a
        sha_a = self.write("raw/ca_AAA_2016_2025.json", '[{"exDate":"01-Jan-2020","subject":"Dividend"}]')
        sha_b = self.write("proof_b.txt", self.PROOF_B)
        rsha = self.write("recon_AAA.json", self._recon_body("AAA", sha_a, sha_b))
        lines = ",".join(ca.COMPLETENESS_COLUMNS) + "\n"
        lines += ("AAA,2020-01-01,2025-12-31,SYNTHETIC A,raw/ca_AAA_2016_2025.json,%s,SYNTHETIC B,proof_b.txt,%s,"
                  "recon_AAA.json,%s,D99,2026-11-15,synthetic\n" % (sha_a, sha_b, rsha))
        self.write("completeness.csv", lines)
        accepted = {"D99": {(frozenset((sha_a, sha_b)), rsha, "AAA", "2020-01-01", "2025-12-31")}}
        self.assertEqual(ca.load_completeness(os.path.join(self.tmp, "completeness.csv"), accepted), {})

    def test_decision_status_is_read_from_the_log(self):
        self.write("LOG.md", "### D99. x\n- **Status:** `USER_APPROVED` (owner).\n### D42. y\n"
                             "- **Status:** `USER_STATED`.\n- **Status:** `USER_APPROVED` (a later line).\n")
        self.assertEqual(ca.owner_decision_status(os.path.join(self.tmp, "LOG.md")),
                         {"D99": "USER_APPROVED", "D42": "USER_STATED"})
        self.assertEqual(ca.owner_decision_status(os.path.join(self.tmp, "none.md")), {})

    def test_a_malformed_register_is_refused(self):
        self.write("completeness.csv", "symbol,from_date\nAAA,2020-01-01\n")
        with self.assertRaises(ca.CorporateActionError):
            ca.load_completeness(os.path.join(self.tmp, "completeness.csv"))
        bad = ",".join(ca.COMPLETENESS_COLUMNS) + "\nAAA,2025,2020-01-01," + (",".join(["x"] * 11)) + "\n"
        self.write("bad_date.csv", bad)
        with self.assertRaises(ca.CorporateActionError):
            ca.load_completeness(os.path.join(self.tmp, "bad_date.csv"))

    def test_tiers_with_and_without_proof(self):
        self.assertEqual(ca.evidence_tier(ca.RESPONSE_PRESENT_COMPLETENESS_NOT_PROVED, True, True),
                         ca.CA_COMPLETENESS_VERIFIED)
        self.assertEqual(ca.evidence_tier(ca.EMPTY_RESPONSE, False, True), ca.CA_COMPLETENESS_VERIFIED)
        for status in (ca.UNPARSED_EVENT, ca.MISSING_COVERAGE, p0.CA_HASH_MISMATCH, None):
            self.assertEqual(ca.evidence_tier(status, True, True), ca.CA_UNVERIFIED, status)
        self.assertEqual(ca.evidence_tier(ca.EMPTY_RESPONSE, True, False), ca.CA_UNVERIFIED)

    def test_the_gate_value_needs_a_proved_window(self):
        bodies = {"AAA": {"status": ca.RESPONSE_PRESENT_COMPLETENESS_NOT_PROVED, "from": "2016-01-01",
                          "to": "2025-12-31", "file": "x", "hash_verified": True},
                  "EMP": {"status": ca.EMPTY_RESPONSE, "from": "2016-01-01", "to": "2025-12-31", "file": "y",
                          "hash_verified": True},
                  "UNP": {"status": ca.UNPARSED_EVENT, "from": "2016-01-01", "to": "2025-12-31", "file": "z",
                          "hash_verified": True},
                  "NOH": {"status": ca.EMPTY_RESPONSE, "from": "2016-01-01", "to": "2025-12-31", "file": "w",
                          "hash_verified": False}}
        day = datetime.date(2022, 1, 3)
        reg = {s: [(datetime.date(2016, 1, 1), datetime.date(2025, 12, 31), "D99", "p")] for s in bodies}
        self.assertEqual(p0._ca_value(bodies, "AAA", day, reg)[0], de.CA_COMPLETE)
        self.assertEqual(p0._ca_value(bodies, "EMP", day, reg)[0], de.CA_COVERED_NONE)
        self.assertEqual(p0._ca_value(bodies, "UNP", day, reg)[0], ca.UNPARSED_EVENT)     # never passes
        self.assertEqual(p0._ca_value(bodies, "AAA", day, {})[0], ca.RESPONSE_PRESENT_COMPLETENESS_NOT_PROVED)
        self.assertEqual(p0._ca_value(bodies, "EMP", day, {})[0], ca.EMPTY_RESPONSE)
        self.assertEqual(p0._ca_value(bodies, "NOH", day, reg)[0], ca.EMPTY_RESPONSE)
        for state in (p0.RENAME_OLD, p0.RENAME_CURRENT, p0.RENAME_AMBIGUOUS):
            self.assertEqual(p0._ca_value(bodies, "EMP", day, reg, state)[0], p0.CA_EMPTY_RENAMED, state)
        self.assertEqual(p0._ca_value(bodies, "AAA", day, reg, p0.RENAME_CURRENT)[0], de.CA_COMPLETE)
        for state in (p0.RENAME_OLD, p0.RENAME_AMBIGUOUS):
            value, status, _, proved = p0._ca_value(bodies, "AAA", day, reg, state)
            self.assertEqual((value, proved), (p0.CA_OLD_TICKER, False), state)
            self.assertEqual(ca.evidence_tier(status, True, proved), ca.CA_UNVERIFIED, state)

    def test_rename_state(self):
        Rec = instruments.Record
        recs = [Rec(instruments.SYMBOL_CHANGE, "A", "B", "INE000A01011", "EQ", datetime.date(2020, 1, 1), None,
                    True, "s", 2),
                Rec(instruments.SYMBOL_CHANGE, "X", "Z", "INE000X01011", "EQ", datetime.date(2020, 1, 1), None,
                    True, "s", 3),
                Rec(instruments.SYMBOL_CHANGE, "Y", "Z", "INE000Y01011", "EQ", datetime.date(2021, 1, 1), None,
                    False, "s", 4)]
        self.assertEqual([p0.rename_state(recs, s) for s in ("A", "B", "Z", "Q")],
                         [p0.RENAME_OLD, p0.RENAME_CURRENT, p0.RENAME_AMBIGUOUS, p0.RENAME_NONE])

    def test_only_dual_hash_window_marker_items_qualify(self):
        sha_a, sha_b, recon = "a" * 64, "b" * 64, "c" * 64
        self.write("LOG.md",
                   "### D99. x\n- **Status:** `USER_APPROVED` (owner).\n"
                   "- **Completeness window accepted:** %s %s %s AAA 2016-01-01..2025-12-31; "
                   "%s %s %s BBB 2020-01-01..2025-12-31\n"
                   "### D98. y\n- **Status:** `USER_APPROVED` (owner).\n"
                   "- **Completeness source accepted:** %s CCC 2016-01-01..2025-12-31\n"
                   "- **Completeness window accepted:** BSE records 2016-2025\n"
                   "### D97. z\n- **Status:** `PROPOSED`.\n"
                   "- **Completeness window accepted:** %s %s %s DDD 2016-01-01..2025-12-31\n"
                   "## 2. Appendix\n"
                   "- **Completeness window accepted:** %s %s %s EEE 2016-01-01..2025-12-31\n"
                   % (sha_a, sha_b, recon, sha_a, sha_b, recon, sha_a,
                      sha_a, sha_b, recon, sha_a, sha_b, recon))
        got = ca.completeness_decisions(os.path.join(self.tmp, "LOG.md"))
        self.assertEqual(got, {"D99": {
            (frozenset((sha_a, sha_b)), recon, "AAA", "2016-01-01", "2025-12-31"),
            (frozenset((sha_a, sha_b)), recon, "BBB", "2020-01-01", "2025-12-31"),
        }})
        # Real decision log has D66 standard but no per-window acceptance items.
        self.assertEqual(ca.completeness_decisions("nse/docs/DECISION_LOG.md"), {})

    def test_a_renamed_copy_of_a_saved_response_is_not_proof(self):
        csv_path = os.path.join(self.tmp, "completeness.csv")
        self.write("nse_extract.json", '[{"exDate": "13-Apr-2016", "subject": "Dividend", "series": "EQ"}]')
        self.assertTrue(ca._is_saved_api_response(csv_path, "nse_extract.json"))
        self.assertTrue(ca._is_saved_api_response(csv_path, "ca_ABC_2016_2025.json"))
        self.assertTrue(ca._is_saved_api_response(csv_path, "raw/anything.pdf"))
        # IR-P0-02: exDate-only objects and empty JSON lists are API-shaped even without subject.
        self.write("stripped.json", '[{"exDate": "13-Apr-2016"}]')
        self.assertTrue(ca._is_saved_api_response(csv_path, "stripped.json"))
        self.write("empty_list.json", "[]")
        self.assertTrue(ca._is_saved_api_response(csv_path, "empty_list.json"))
        independent = self.write("proof.txt", "an independent reconciliation\n")
        self.assertFalse(ca._is_saved_api_response(csv_path, "proof.txt"))
        self.assertTrue(ca._is_saved_api_response(csv_path, "proof.txt", frozenset([independent])))


class CommittedOutputs(unittest.TestCase):
    """The committed outputs agree with each other. A rebuild is the source of truth."""

    def setUp(self):
        path = os.path.join(P0_DIR, "P0_CERTIFICATION_SUMMARY.json")
        if not os.path.isfile(path):
            self.skipTest("no committed P0 certification summary")
        with open(path, encoding="utf-8") as fh:
            self.summary = json.load(fh)

    def _csv(self, name):
        with open(os.path.join(P0_DIR, name), newline="", encoding="utf-8") as fh:
            return list(csv.DictReader(fh))

    def test_counts_reconcile(self):
        s = self.summary
        self.assertTrue(all(s["reconciliation"].values()), s["reconciliation"])
        self.assertEqual(s["certified_symbol_dates"] + s["excluded_symbol_dates"], s["member_dates"])
        self.assertEqual(sum(s["by_final_eligibility"].values()), s["member_dates"])
        self.assertFalse(s["authorises_order"])

    def test_register_and_certified_file_match_the_summary(self):
        reg = self._csv("P0_RESEARCH_EXCLUSION_REGISTER.csv")
        self.assertEqual(len(reg), self.summary["register_rows"])
        self.assertEqual(sum(int(r["sessions"]) for r in reg), self.summary["excluded_symbol_dates"])
        self.assertTrue(all(r["reason"] and r["blocking_gate"] for r in reg))
        certified = self._csv("P0_CERTIFIED_RESEARCH_UNIVERSE.csv")
        self.assertEqual(len(certified), self.summary["certified_symbol_dates"])
        self.assertTrue(all(r["authorises_order"] == "false" for r in certified))
        self.assertTrue(all(r["certification_scope"] == p0.SCOPE and r["gtf_trade_eligibility"] == p0.GTF_NOT_EVALUATED
                            for r in certified))

    def test_exploratory_rows_stay_out_of_the_certified_count_and_scope_is_data(self):
        s = self.summary
        self.assertEqual(s["certification_scope"], p0.SCOPE)
        self.assertEqual(s["data_gates"], list(de.DATA_GATES))
        self.assertEqual(s["research_use"].get(p0.USE_CERTIFIED, 0), s["certified_symbol_dates"])
        self.assertEqual(sum(s["research_use"].values()), s["member_dates"])
        self.assertNotIn(ca.CA_COMPLETENESS_VERIFIED, s["corporate_action_evidence_tier"])
        self.assertLessEqual(s["research_use"].get(p0.USE_EXPLORATORY, 0),
                             s["corporate_action_evidence_tier"].get(ca.CA_RESPONSE_PRESENT_NOT_COMPLETE, 0))

    def test_no_full_index_claim_and_no_passing_corporate_action_value(self):
        self.assertEqual(self.summary["full_index_certified_dates"], 0)
        values = self.summary["gate_values"]["corporate_action"]
        self.assertNotIn(de.CA_COVERED_NONE, values)
        self.assertNotIn(de.CA_COVERED_EVENTS, values)

    def test_history_lists_every_period(self):
        hist = self._csv("P0_MEMBERSHIP_REFERENCE_HISTORY.csv")
        self.assertEqual(len(hist), self.summary["membership_periods"])
        verified = [h for h in hist if h["membership_status"] == de.MEMBERSHIP_VERIFIED]
        self.assertEqual(len(verified), self.summary["membership_periods_verified"])
        self.assertTrue(all(h["source_sha256"] for h in verified))
        self.assertTrue(all(not h["source_sha256"] for h in hist if h not in verified))


if __name__ == "__main__":
    unittest.main()
