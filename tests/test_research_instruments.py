"""Instrument identity tests (nse/research/instruments.py; spec 9.1, D1, D31, B11).

Every record and bhavcopy here is SYNTHETIC (made-up symbols and ISINs). The expected
behaviour comes from the requirements: effective dates are point in time (B11), a row
without source and sha256 is UNVERIFIED (D31), an uncovered symbol is UNKNOWN_INSTRUMENT
(unknown is never a guess), and SYMBOL_CHANGE chains are followed both ways without looping.
"""

import argparse
import contextlib
import datetime
import io
import json
import os
import shutil
import tempfile
import unittest

from nse.research import instruments as ins, marketdata

D = datetime.date
SHA = "a" * 64
HEADER = ",".join(ins.COLUMNS)
I1, I2, I3 = "INE000A01011", "INE000B01012", "INE000C01013"


def row(kind, symbol, isin, start, new="", end="", verified=True, notes="SYNTHETIC"):
    src, sha = ("SYNTHETIC test document", SHA) if verified else ("", "")
    return ",".join([kind, symbol, new, isin, "EQ", start, end, src, "doc.pdf" if verified else "", sha,
                     "2026-01-01", notes])


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def write(self, *rows, header=HEADER, name="records.csv"):
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(header + "\n" + "".join(r + "\n" for r in rows))
        return path

    def load(self, *rows):
        return ins.load(self.write(*rows))


class Loading(Base):
    def test_header_must_be_exact(self):
        with self.assertRaises(ins.InstrumentError):
            ins.load(self.write(header=HEADER.replace("isin,series", "series,isin")))

    def test_strict_rows(self):
        bad = [row("RENAME", "AAA", I1, "2020-01-01"),
               row("LISTING", "AAA", I1, "2020-13-01"),
               row("LISTING", "", I1, "2020-01-01"),
               row("LISTING", "AAA", "XX123", "2020-01-01"),
               row("LISTING", "AAA", I1, "2020-02-01", end="2020-01-01"),
               row("SYMBOL_CHANGE", "AAA", I1, "2020-01-01"),                 # no new symbol
               row("SYMBOL_CHANGE", "AAA", I1, "2020-01-01", new="AAA"),
               row("DELISTING", "AAA", I1, "2020-01-01", end="2020-02-01"),   # effective_to on LISTING only
               row("LISTING", "AAA", I1, "2020-01-01", new="BBB")]
        for r in bad:
            with self.assertRaises(ins.InstrumentError, msg=r):
                self.load(r)

    def test_unverified_rows(self):
        recs = self.load(row("LISTING", "AAA", I1, "2020-01-01", verified=False),
                         row("LISTING", "BBB", I2, "2020-01-01"))
        self.assertEqual({r.symbol: r.verified for r in recs}, {"AAA": False, "BBB": True})
        r = ins.resolve(recs, "AAA", D(2021, 1, 1))
        self.assertEqual(r["status"], ins.RESOLVED)
        self.assertFalse(r["verified"])
        self.assertEqual(r["limitations"], [ins.UNVERIFIED])
        self.assertTrue(ins.resolve(recs, "BBB", D(2021, 1, 1))["verified"])
        [f] = [f for f in ins.isin_consistency(recs, []) if f.code == ins.UNVERIFIED]
        self.assertEqual((f.symbol, f.verified), ("AAA", False))

    def test_no_records_built_in(self):
        self.assertEqual(ins.resolve([], "INFY", D(2022, 1, 3))["status"], ins.UNKNOWN_INSTRUMENT)


class EffectiveDates(Base):
    def setUp(self):
        super().setUp()
        self.recs = self.load(row("LISTING", "OLDCO", I1, "2015-01-01"),
                              row("SYMBOL_CHANGE", "OLDCO", I1, "2020-06-01", new="NEWCO"),
                              row("LISTING", "GONE", I2, "2015-01-01", end="2019-12-31"))

    def test_symbol_change_boundary(self):
        self.assertEqual(ins.symbol_at(self.recs, I1, D(2020, 5, 31)), "OLDCO")
        self.assertEqual(ins.symbol_at(self.recs, I1, D(2020, 6, 1)), "NEWCO")       # effective_from inclusive
        self.assertIsNone(ins.symbol_at(self.recs, I1, D(2014, 12, 31)))              # before listing
        self.assertEqual(ins.resolve(self.recs, "OLDCO", D(2020, 6, 1))["status"], ins.UNKNOWN_INSTRUMENT)
        a, b = ins.resolve(self.recs, "OLDCO", D(2020, 5, 31)), ins.resolve(self.recs, "NEWCO", D(2020, 6, 1))
        self.assertEqual((a["status"], b["status"]), (ins.RESOLVED, ins.RESOLVED))
        self.assertEqual(a["canonical_id"], b["canonical_id"])
        self.assertEqual(b["symbols"], ["OLDCO", "NEWCO"])

    def test_listing_end_is_inclusive(self):
        self.assertEqual(ins.symbol_at(self.recs, I2, D(2019, 12, 31)), "GONE")
        self.assertIsNone(ins.symbol_at(self.recs, I2, D(2020, 1, 1)))

    def test_point_in_time_ignores_later_records(self):
        self.assertEqual(ins.resolve(self.recs, "NEWCO", D(2020, 5, 31))["status"], ins.UNKNOWN_INSTRUMENT)

    def test_delisting_and_merger(self):
        recs = self.load(row("LISTING", "AAA", I1, "2015-01-01"), row("DELISTING", "AAA", I1, "2021-03-01"),
                         row("LISTING", "BBB", I2, "2015-01-01"), row("MERGER", "BBB", I2, "2022-04-01", new="CCC"),
                         row("LISTING", "CCC", I3, "2015-01-01"))
        self.assertEqual(ins.symbol_at(recs, I1, D(2021, 2, 28)), "AAA")
        self.assertIsNone(ins.symbol_at(recs, I1, D(2021, 3, 1)))
        self.assertIsNone(ins.symbol_at(recs, I2, D(2022, 4, 1)))
        c = ins.resolve(recs, "CCC", D(2022, 4, 1))
        self.assertEqual(c["isin"], I3)                       # a merger is not a rename: CCC keeps its own ISIN
        self.assertNotIn("BBB", c["symbols"])

    def test_isin_change_keeps_the_canonical_identity(self):
        recs = self.load(row("LISTING", "AAA", I1, "2015-01-01"), row("ISIN_CHANGE", "AAA", I2, "2018-07-02"))
        old, new = ins.resolve(recs, "AAA", D(2018, 7, 1)), ins.resolve(recs, "AAA", D(2018, 7, 2))
        self.assertEqual((old["isin"], new["isin"]), (I1, I2))
        self.assertEqual(old["canonical_id"], new["canonical_id"])
        self.assertEqual(new["canonical_id"], "ISIN:" + I1)
        self.assertEqual(new["isin_lineage"], [I1, I2])
        self.assertIsNone(ins.symbol_at(recs, I1, D(2018, 7, 2)))

    def test_two_isins_for_one_symbol_is_unknown(self):
        recs = self.load(row("LISTING", "AAA", I1, "2015-01-01"), row("LISTING", "AAA", I2, "2016-01-01"))
        r = ins.resolve(recs, "AAA", D(2017, 1, 1))
        self.assertEqual(r["status"], ins.UNKNOWN_INSTRUMENT)
        self.assertIn("two or more ISINs", r["reason"])


class History(Base):
    def test_chain_followed_both_directions(self):
        recs = self.load(row("LISTING", "A", I1, "2010-01-01"),
                         row("SYMBOL_CHANGE", "A", I1, "2012-01-01", new="B"),
                         row("SYMBOL_CHANGE", "B", I1, "2015-01-01", new="C"),
                         row("LISTING", "X", I2, "2010-01-01"))
        for s in ("A", "B", "C"):
            h = ins.history(recs, s)
            self.assertEqual(h["symbols"], ["A", "B", "C"])
            self.assertEqual(h["isins"], [I1])
            self.assertFalse(h["cycle"])
        self.assertEqual(ins.history(recs, "X")["symbols"], ["X"])
        self.assertFalse(ins.history(recs, "NOPE")["known"])

    def test_cycle_safe(self):
        recs = self.load(row("LISTING", "A", I1, "2010-01-01"),
                         row("SYMBOL_CHANGE", "A", I1, "2012-01-01", new="B"),
                         row("SYMBOL_CHANGE", "B", I1, "2014-01-01", new="A"))
        h = ins.history(recs, "B")
        self.assertTrue(h["cycle"])
        self.assertEqual(h["symbols"], ["A", "B"])
        self.assertEqual(len(h["changes"]), 2)
        self.assertEqual(ins.symbol_at(recs, I1, D(2014, 1, 1)), "A")


class Consistency(Base):
    def codes(self, recs, obs):
        return [(f.code, f.symbol, f.date) for f in ins.isin_consistency(recs, obs) if f.code != ins.UNVERIFIED]

    def test_consistent_observations_have_no_findings(self):
        recs = self.load(row("LISTING", "OLDCO", I1, "2015-01-01"),
                         row("SYMBOL_CHANGE", "OLDCO", I1, "2020-06-01", new="NEWCO"))
        obs = [(D(2020, 5, 29), "OLDCO", I1), (D(2020, 6, 1), "NEWCO", I1)]
        self.assertEqual(self.codes(recs, obs), [])

    def test_isin_changed_without_record(self):
        recs = self.load(row("LISTING", "AAA", I1, "2015-01-01"))
        obs = [(D(2020, 1, 1), "AAA", I1), (D(2020, 1, 2), "AAA", I2), (D(2020, 1, 3), "AAA", I2)]
        got = self.codes(recs, obs)
        self.assertIn((ins.ISIN_CHANGED_WITHOUT_RECORD, "AAA", D(2020, 1, 2)), got)
        self.assertEqual([c for c in got if c[0] == ins.ISIN_RECORD_MISMATCH],
                         [(ins.ISIN_RECORD_MISMATCH, "AAA", D(2020, 1, 2))])        # reported once

    def test_recorded_isin_change_is_explained(self):
        recs = self.load(row("LISTING", "AAA", I1, "2015-01-01"), row("ISIN_CHANGE", "AAA", I2, "2020-01-02"))
        self.assertEqual(self.codes(recs, [(D(2020, 1, 1), "AAA", I1), (D(2020, 1, 2), "AAA", I2)]), [])

    def test_symbol_reused_for_different_isin(self):
        recs = self.load(row("LISTING", "AAA", I1, "2015-01-01", end="2019-06-30"),
                         row("LISTING", "AAA", I2, "2020-01-01"))
        got = self.codes(recs, [(D(2019, 6, 28), "AAA", I1), (D(2020, 1, 1), "AAA", I2)])
        self.assertEqual(got, [(ins.SYMBOL_REUSED_FOR_DIFFERENT_ISIN, "AAA", D(2020, 1, 1))])
        self.assertNotEqual(ins.resolve(recs, "AAA", D(2019, 6, 28))["canonical_id"],
                            ins.resolve(recs, "AAA", D(2020, 1, 1))["canonical_id"])

    def test_symbol_changed_without_record_and_unknown(self):
        recs = self.load(row("LISTING", "AAA", I1, "2015-01-01"))
        got = self.codes(recs, [(D(2020, 1, 1), "AAA", I1), (D(2020, 1, 2), "ZZZ", I1)])
        self.assertIn((ins.SYMBOL_CHANGED_WITHOUT_RECORD, "ZZZ", D(2020, 1, 2)), got)
        self.assertIn((ins.UNKNOWN_INSTRUMENT, "ZZZ", D(2020, 1, 2)), got)

    def test_findings_sorted_and_deterministic(self):
        recs = self.load(row("LISTING", "AAA", I1, "2015-01-01", verified=False))
        obs = [(D(2020, 1, 2), "AAA", I2), (D(2020, 1, 1), "BBB", I3), (D(2020, 1, 1), "AAA", I1)]
        a = [f.to_dict() for f in ins.isin_consistency(recs, obs)]
        b = [f.to_dict() for f in ins.isin_consistency(recs, list(reversed(obs)))]
        self.assertEqual(a, b)
        self.assertEqual([x["date"] for x in a], sorted(x["date"] for x in a))


class Cli(Base):
    MON = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")

    def bhav(self, d, rows):
        """SYNTHETIC legacy bhavcopy CSV (nse_bhavcopy format), rows of (symbol, isin)."""
        from nse.research.deps import bhavcopy as bc
        stamp = "%02d-%s-%04d" % (d.day, self.MON[d.month - 1], d.year)
        folder = os.path.join(self.tmp, "bhav")
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "cm%02d%s%04dbhav.csv" % (d.day, self.MON[d.month - 1], d.year)), "w",
                  newline="") as fh:
            fh.write(",".join(bc.LEGACY_HEADER) + "\n")
            for s, i in rows:
                fh.write("%s,EQ,100,100,100,100,100,100,1000,100000,%s,10,%s,\n" % (s, stamp, i))
        return folder

    def run_cli(self, argv):
        p = argparse.ArgumentParser()
        sub = p.add_subparsers(dest="cmd")
        ins.add_commands(sub)
        args = p.parse_args(argv)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = args.func(args)
        return code, buf.getvalue()

    def test_check_command(self):
        recs = self.write(row("LISTING", "AAA", I1, "2015-01-01"), row("LISTING", "BBB", I2, "2015-01-01"))
        self.bhav(D(2025, 1, 6), [("AAA", I1), ("BBB", I2)])
        folder = self.bhav(D(2025, 1, 7), [("AAA", I1), ("BBB", I2)])
        out = os.path.join(self.tmp, "o", "check.json")
        code, _ = self.run_cli(["instruments-check", "--records", recs, "--bhavcopy-dir", folder, "--out", out])
        self.assertEqual(code, 0)
        with open(out, encoding="utf-8") as fh:
            d = json.load(fh)
        self.assertEqual((d["observations"], d["findings"], d["bhavcopy_files"]), (4, [], 2))
        self.assertEqual([r["status"] for r in d["resolved_at_last_date"]], [ins.RESOLVED, ins.RESOLVED])

    def test_check_command_fails_on_an_unexplained_isin_change(self):
        recs = self.write(row("LISTING", "AAA", I1, "2015-01-01"))
        self.bhav(D(2025, 1, 6), [("AAA", I1)])
        folder = self.bhav(D(2025, 1, 7), [("AAA", I2)])
        code, text = self.run_cli(["instruments-check", "--records", recs, "--bhavcopy-dir", folder,
                                   "--symbols", "AAA"])
        self.assertEqual(code, 1)
        self.assertIn(ins.ISIN_CHANGED_WITHOUT_RECORD, json.loads(text)["finding_counts"])

    def test_input_errors(self):
        recs = self.write(row("LISTING", "AAA", I1, "2015-01-01"))
        empty = os.path.join(self.tmp, "empty")
        os.makedirs(empty)
        self.assertEqual(self.run_cli(["instruments-check", "--records", recs, "--bhavcopy-dir", empty])[0], 2)
        self.assertEqual(self.run_cli(["instruments-check", "--records", os.path.join(self.tmp, "no.csv"),
                                       "--bhavcopy-dir", empty])[0], 2)

    def test_findings_are_marketdata_findings(self):
        recs = self.load(row("LISTING", "AAA", I1, "2015-01-01"))
        [f] = ins.isin_consistency(recs, [(D(2020, 1, 1), "QQQ", I3)])
        self.assertIsInstance(f, marketdata.Finding)
        self.assertEqual(f.code, ins.UNKNOWN_INSTRUMENT)



class PointInTimeReviewRegression(Base):
    def test_resolve_lists_only_symbols_known_at_the_date(self):
        recs = self.load(row("LISTING", "OLD", I1, "2010-01-01"),
                         row("SYMBOL_CHANGE", "OLD", I1, "2020-06-01", new="NEW"))
        early = ins.resolve(recs, "OLD", D(2019, 1, 1))
        self.assertEqual(early["status"], ins.RESOLVED)
        self.assertNotIn("NEW", early["symbols"])        # the rename is in the future at that date
        self.assertIn("NEW", ins.resolve(recs, "NEW", D(2021, 1, 1))["symbols"])

if __name__ == "__main__":
    unittest.main()
