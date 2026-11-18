"""Identity policy for P0 (D51, review REV-1): tickers join only through VERIFIED, dated renames.

SYNTHETIC instrument records except RealRecords, which reads the committed
nse/data/universe/instrument_records.csv and checks the verified mappings named in the
P0 tracker. No name similarity, shared promoter or later relationship ever links two tickers.
"""

import csv
import datetime
import hashlib
import os
import shutil
import tempfile
import unittest

import _research  # noqa: F401
from nse.research import instruments as I

D = datetime.date
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class _Records(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="identity-policy-")
        self.addCleanup(shutil.rmtree, self.tmp)
        src = os.path.join(self.tmp, "src.txt")
        with open(src, "w") as fh:
            fh.write("SYNTHETIC identity evidence\n")
        with open(src, "rb") as fh:
            self.sha = hashlib.sha256(fh.read()).hexdigest()

    def records(self, rows):
        path = os.path.join(self.tmp, "records.csv")
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(I.COLUMNS), lineterminator="\n")
            w.writeheader()
            for kind, sym, new, isin, start, verified in rows:
                w.writerow({"record_type": kind, "symbol": sym, "new_symbol": new, "isin": isin, "series": "EQ",
                            "effective_from": start, "effective_to": "", "source": "SYNTHETIC",
                            "source_file": "src.txt", "source_sha256": self.sha if verified else "",
                            "recorded_on": "2026-11-15", "notes": ""})
        return I.load(path)


class VerifiedRenames(_Records):
    def test_a_verified_chain_links_and_an_unverified_record_does_not(self):
        R = self.records([("LISTING", "A1", "", "INE000A01011", "2016-01-01", True),
                          ("SYMBOL_CHANGE", "A1", "A2", "INE000A01011", "2020-01-01", True),
                          ("SYMBOL_CHANGE", "A2", "A3", "INE000A01011", "2023-01-01", True),
                          ("LISTING", "B1", "", "INE000B01011", "2016-01-01", True),
                          ("SYMBOL_CHANGE", "B1", "B2", "INE000B01011", "2021-01-01", False)])
        self.assertEqual(I.verified_rename_names(R, "A3"), ["A1", "A2", "A3"])
        self.assertEqual(I.verified_rename_names(R, "A1"), ["A1", "A2", "A3"])
        self.assertEqual(I.verified_rename_names(R, "B2"), ["B2"])
        self.assertEqual(I.verified_rename_names(R, "B1"), ["B1"])
        status = {(x["previous_symbol"], x["new_symbol"]): x["status"] for x in I.rename_links(R)}
        self.assertEqual(status[("A1", "A2")], I.RENAME_VERIFIED)
        self.assertEqual(status[("B1", "B2")], I.RENAME_UNVERIFIED)
        self.assertTrue(all(x["evidence_file"] and x["record_line"] for x in I.rename_links(R)))

    def test_a_rename_under_another_isin_ends_the_chain(self):
        R = self.records([("SYMBOL_CHANGE", "C1", "C2", "INE000C01011", "2019-01-01", True),
                          ("SYMBOL_CHANGE", "C2", "C3", "INE000Z01011", "2022-01-01", True)])
        self.assertEqual(I.verified_rename_names(R, "C1"), ["C1", "C2"])

    def test_the_join_is_dated(self):
        R = self.records([("SYMBOL_CHANGE", "A1", "A2", "INE000A01011", "2020-01-06", True)])
        hit = I.verified_rename_into(R, "A2", D(2020, 1, 3), D(2020, 1, 6))
        self.assertEqual((hit.symbol, hit.new_symbol), ("A1", "A2"))
        self.assertIsNone(I.verified_rename_into(R, "A2", D(2020, 1, 6), D(2020, 1, 7)))   # after the step
        self.assertIsNone(I.verified_rename_into(R, "A2", D(2019, 12, 30), D(2020, 1, 3)))  # before it
        self.assertIsNone(I.verified_rename_into(R, "A1", D(2020, 1, 3), D(2020, 1, 6)))   # wrong direction

    def test_renames_under_two_isins_on_one_ticker_join_nothing(self):
        # review L-1: the result must not depend on record order
        R = self.records([("SYMBOL_CHANGE", "A", "X", "INE000A01011", "2019-01-01", True),
                          ("SYMBOL_CHANGE", "B", "X", "INE000B01011", "2021-01-01", True)])
        self.assertEqual(I.verified_rename_names(R, "X"), ["X"])

    def test_two_renames_into_one_ticker_in_one_step_are_ambiguous(self):
        R = self.records([("SYMBOL_CHANGE", "X1", "Z", "INE000X01011", "2020-01-06", True),
                          ("SYMBOL_CHANGE", "Y1", "Z", "INE000X01011", "2020-01-06", True)])
        self.assertIsNone(I.verified_rename_into(R, "Z", D(2020, 1, 3), D(2020, 1, 6)))

    def test_an_unverified_rename_is_never_a_dated_join(self):
        R = self.records([("SYMBOL_CHANGE", "B1", "B2", "INE000B01011", "2021-01-04", False)])
        self.assertIsNone(I.verified_rename_into(R, "B2", D(2021, 1, 1), D(2021, 1, 4)))

    def test_a_symbol_without_records_stays_alone_and_unknown(self):
        R = self.records([("LISTING", "A1", "", "INE000A01011", "2016-01-01", True)])
        self.assertEqual(I.verified_rename_names(R, "DUMMYX"), ["DUMMYX"])
        self.assertEqual(I.resolve(R, "DUMMYX", D(2022, 1, 3))["status"], I.UNKNOWN_INSTRUMENT)

    def test_two_isins_for_one_symbol_stay_unresolved(self):
        R = self.records([("LISTING", "G", "", "INE047A01013", "2016-01-01", True),
                          ("LISTING", "G", "", "INE047A01021", "2016-10-06", True)])
        self.assertEqual(I.resolve(R, "G", D(2021, 1, 4))["status"], I.UNKNOWN_INSTRUMENT)


class RealRecords(unittest.TestCase):
    """The committed records: the verified mappings the P0 tracker lists, and the dummy rule."""

    @classmethod
    def setUpClass(cls):
        cls.R = I.load(os.path.join(ROOT, "nse", "data", "universe", "instrument_records.csv"))

    def test_named_mappings_are_verified_dated_renames(self):
        links = {(x["previous_symbol"], x["new_symbol"]): x for x in I.rename_links(self.R)}
        for old, new, day in (("TELCO", "TATAMOTORS", "2003-12-26"), ("TATAMOTORS", "TMPV", "2025-10-24"),
                              ("ADANITRANS", "ADANIENSOL", "2023-08-24"), ("CADILAHC", "ZYDUSLIFE", "2022-03-07"),
                              ("ZOMATO", "ETERNAL", "2025-04-09"), ("MCDOWELL-N", "UNITDSPR", "2024-06-07"),
                              ("LTI", "LTIM", "2022-12-05")):
            x = links[(old, new)]
            self.assertEqual((x["status"], x["effective_from"]), (I.RENAME_VERIFIED, day), (old, new))
        self.assertTrue(all(x["status"] == I.RENAME_VERIFIED for x in links.values()))

    def test_dummy_seats_link_to_nothing(self):
        for dummy in ("DUMMYREL", "DUMMYITC", "DUMMYSIEMS", "DUMMYTATAM", "DUMMYHDLVR"):
            self.assertEqual(I.verified_rename_names(self.R, dummy), [dummy])
            self.assertEqual(I.resolve(self.R, dummy, D(2025, 1, 6))["status"], I.UNKNOWN_INSTRUMENT)
        self.assertNotIn("DUMMYREL", I.verified_rename_names(self.R, "JIOFIN"))

    def test_grasim_and_bajfinance_stay_unresolved_before_their_open_notices(self):
        self.assertEqual(I.resolve(self.R, "GRASIM", D(2021, 1, 4))["status"], I.UNKNOWN_INSTRUMENT)
        self.assertEqual(I.resolve(self.R, "BAJFINANCE", D(2021, 1, 4))["status"], I.UNKNOWN_INSTRUMENT)


if __name__ == "__main__":
    unittest.main()
