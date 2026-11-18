"""Symbol-date eligibility. SYNTHETIC gates, plus one scan that uses a synthetic universe.

GRASIM's unresolved identity excludes GRASIM. It does not rewrite another symbol's
gates, and the day is not the complete Nifty 100 while index-wide evidence is open.
"""

import csv
import datetime
import os
import unittest

import _research as R
from nse.research import dataset_eligibility as de, models as m, scanner, universe

DAY = "2020-12-31"
D = datetime.date(2020, 12, 31)


def _row(symbol, **overrides):
    gates = de.passing_gates()
    gates.update(overrides)
    return {"symbol": symbol, "trade_date": DAY, "isin": "INE000A01000", "gates": gates,
            "evidence": "SYNTHETIC"}


class SymbolDateEligibility(unittest.TestCase):
    def test_grasim_does_not_block_an_independently_passing_symbol(self):
        certified = de.certify_members([
            _row("INFY"),
            _row("GRASIM", identity="UNRESOLVED"),
        ], index_evidence_resolved=False, required_symbols=["INFY", "GRASIM"])
        by = {r["symbol"]: r for r in certified["rows"]}
        self.assertEqual(by["INFY"]["final_eligibility"], de.ELIGIBLE)
        self.assertEqual(by["INFY"]["blocking_gate"], "")
        self.assertNotIn("GRASIM", by["INFY"]["exclusion_reason"])
        self.assertEqual(by["GRASIM"]["final_eligibility"], de.EXCLUDED_IDENTITY)
        self.assertIn("GRASIM 2020-12-31", by["GRASIM"]["exclusion_reason"])
        self.assertIn("identity=UNRESOLVED", by["GRASIM"]["exclusion_reason"])
        self.assertEqual(certified["label"], de.LABEL_SUBSET)
        self.assertFalse(certified["full_index_certified"])
        self.assertFalse(certified["complete_nifty100"])
        self.assertFalse(certified["authorises_order"])
        self.assertFalse(by["INFY"]["authorises_order"])

    def test_blank_membership_fails_closed_and_names_the_symbol(self):
        row = de.classify_symbol_date("INFY", DAY, "INE009A01021",
                                      dict(de.passing_gates(), membership="UNVERIFIED"))
        self.assertEqual(row["final_eligibility"], de.EXCLUDED_MEMBERSHIP)
        self.assertEqual(row["blocking_gate"], "membership")
        self.assertIn("INFY 2020-12-31", row["exclusion_reason"])
        missing = de.classify_symbol_date("INFY", DAY, "INE009A01021", {})
        self.assertEqual(missing["final_eligibility"], de.EXCLUDED_MEMBERSHIP)
        self.assertIn("membership=UNKNOWN", missing["exclusion_reason"])

    def test_unknown_identity_and_an_inferred_isin_fail_closed(self):
        unknown = de.classify_symbol_date("YESBANK", DAY, "INE528G01035",
                                          dict(de.passing_gates(), identity="UNKNOWN"))
        inferred = de.classify_symbol_date("DUMMYITC", "2025-01-06", "INE379A01028",
                                           dict(de.passing_gates(), identity="INFERRED_ISIN"))
        self.assertEqual(unknown["final_eligibility"], de.EXCLUDED_IDENTITY)
        self.assertIn("YESBANK 2020-12-31", unknown["exclusion_reason"])
        self.assertEqual(inferred["final_eligibility"], de.EXCLUDED_IDENTITY)
        self.assertIn("DUMMYITC 2025-01-06", inferred["exclusion_reason"])
        self.assertIn("INFERRED_ISIN", inferred["exclusion_reason"])

    def test_empty_corporate_action_response_and_unchecked_price_fail_closed(self):
        empty = de.classify_symbol_date("SRTRANSFIN", DAY, "INE000A01000", dict(
            de.passing_gates(), corporate_action="EMPTY_RESPONSE_COMPLETENESS_UNKNOWN"))
        price = de.classify_symbol_date("CROMPGREAV", "2016-03-15", "INE000A01000", dict(
            de.passing_gates(), price_continuity="UNRESOLVED_EVENT"))
        self.assertEqual(empty["blocking_gate"], "corporate_action")
        self.assertEqual(price["final_eligibility"], de.EXCLUDED_PRICE)
        self.assertIn("CROMPGREAV 2016-03-15", price["exclusion_reason"])

    def test_a_fully_passing_sample_is_still_not_the_complete_index(self):
        certified = de.certify_members([_row("INFY"), _row("TCS")], index_evidence_resolved=False,
                                       required_symbols=["INFY", "TCS"])
        self.assertEqual(certified["eligible_count"], 2)
        self.assertEqual(certified["label"], de.LABEL_SUBSET)
        self.assertFalse(certified["full_index_certified"])

    def test_complete_index_requires_an_explicit_index_evidence_flag(self):
        rows = [_row("INFY"), _row("TCS")]
        closed = de.certify_members(rows, index_evidence_resolved=False, required_symbols=["INFY", "TCS"])
        opened = de.certify_members(rows, index_evidence_resolved=True, required_symbols=["INFY", "TCS"])
        self.assertFalse(closed["complete_nifty100"])
        self.assertTrue(opened["full_index_certified"])
        self.assertEqual(opened["label"], de.LABEL_FULL)
        # One unresolved required member keeps the full-index label off.
        partial = de.certify_members(
            [_row("INFY"), _row("GRASIM", membership="UNVERIFIED")],
            index_evidence_resolved=True, required_symbols=["INFY", "GRASIM"])
        self.assertEqual(partial["rows"][0]["final_eligibility"], de.ELIGIBLE)
        self.assertFalse(partial["full_index_certified"])
        self.assertEqual(partial["label"], de.LABEL_SUBSET)

    def test_no_eligible_rows_are_not_labelled_as_a_subset_of_passes(self):
        certified = de.certify_members([_row("GRASIM", identity="UNRESOLVED")], index_evidence_resolved=False)
        self.assertEqual(certified["eligible_count"], 0)
        self.assertEqual(certified["label"], de.LABEL_NONE)
        self.assertFalse(certified["full_index_certified"])


class DataGateScope(unittest.TestCase):
    """D63: P0 data certification evaluates the six data gates; the default stays all seven."""

    def test_default_still_requires_the_gtf_gate(self):
        gates = de.passing_gates()
        del gates["gtf"]
        self.assertEqual(de.classify_symbol_date("INFY", DAY, "INE009A01021", gates)["final_eligibility"],
                         de.EXCLUDED_GTF)

    def test_data_scope_does_not_need_the_gtf_gate_and_still_fails_closed(self):
        gates = de.passing_gates()
        del gates["gtf"]
        ok = de.classify_symbol_date("INFY", DAY, "INE009A01021", gates, required_gates=de.DATA_GATES)
        self.assertEqual(ok["final_eligibility"], de.ELIGIBLE)
        self.assertNotIn("gtf", ok["gate_results"])
        self.assertFalse(ok["authorises_order"])
        gates.pop("price_continuity")
        missing = de.classify_symbol_date("INFY", DAY, "INE009A01021", gates, required_gates=de.DATA_GATES)
        self.assertEqual(missing["final_eligibility"], de.EXCLUDED_PRICE)

    def test_parsed_events_without_proved_completeness_do_not_pass(self):
        # review F4 / D62: COVERED_WITH_VERIFIED_EVENTS is the weaker tier, never the gate
        for scope in (None, de.DATA_GATES):
            row = de.classify_symbol_date("INFY", DAY, "INE009A01021",
                                          dict(de.passing_gates(), corporate_action=de.CA_COVERED_EVENTS),
                                          required_gates=scope)
            self.assertEqual(row["final_eligibility"], de.EXCLUDED_CORPORATE_ACTION)

    def test_an_unknown_empty_or_partial_gate_list_is_refused(self):
        for bad in (("membership", "typo"), (), ("calendar",), de.DATA_GATES[:-1]):
            with self.assertRaises(ValueError):
                de.classify_symbol_date("INFY", DAY, "INE009A01021", de.passing_gates(), required_gates=bad)

    def test_data_scope_never_labels_the_complete_index_without_the_flag(self):
        res = de.certify_members([_row("INFY"), _row("TCS")], index_evidence_resolved=False,
                                 required_gates=de.DATA_GATES)
        self.assertEqual(res["label"], de.LABEL_SUBSET)
        self.assertFalse(res["full_index_certified"])


class ScanIsolation(unittest.TestCase):
    def test_unverified_grasim_does_not_make_infy_data_insufficient(self):
        # SYNTHETIC universe. INFY's period is verified. GRASIM's is not.
        # The scan limitation stays UNIVERSE_UNVERIFIED. INFY is still scanned.
        u = universe.Universe("NIFTY 100", [
            universe.Membership("INFY", "EQ", D, None, True, "SYNTHETIC"),
            universe.Membership("GRASIM", "EQ", D, None, False, "SYNTHETIC"),
        ])
        self.assertIn(m.UNIVERSE_UNVERIFIED, u.limitations(D))
        self.assertTrue(next(r for r in u.members(D) if r.symbol == "INFY").verified)
        self.assertFalse(next(r for r in u.members(D) if r.symbol == "GRASIM").verified)
        candles = R.random_walk(1, 40, start=D, price=1000.0)
        cfg = scanner.ScanConfig(as_of=candles[-1].end, calendar=R.WeekdayCalendar())
        res = scanner.scan([R.daily_input("INFY", candles)], cfg, universe=u)
        status = {s.symbol: s for s in res.symbols}
        self.assertIn(m.UNIVERSE_UNVERIFIED, res.limitations)
        self.assertNotEqual(status["INFY"].status, scanner.SYMBOL_DATA_INSUFFICIENT)
        self.assertFalse(any("GRASIM" in reason for reason in status["INFY"].reasons))
        self.assertEqual(status["GRASIM"].status, scanner.SYMBOL_DATA_INSUFFICIENT)
        self.assertTrue(status["GRASIM"].reasons[0].startswith("NO_INPUT_FOR_UNIVERSE_MEMBER"))
        self.assertNotEqual(res.universe, "COMPLETE_NIFTY100")


class CertifiedFile(unittest.TestCase):
    def test_the_certified_universe_file_has_no_symbol_dates(self):
        path = os.path.join(os.path.dirname(__file__), "..", "docs", "product-discovery", "p0",
                            "P0_CERTIFIED_RESEARCH_UNIVERSE.csv")
        with open(path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)
            self.assertIn("authorises_order", reader.fieldnames)
        self.assertEqual(rows, [])
