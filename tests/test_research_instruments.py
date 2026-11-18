"""Instrument identity tests (nse/research/instruments.py; spec 9.1, D1, D31, B11).

Every record and bhavcopy here is SYNTHETIC (made-up symbols and ISINs). The expected
behaviour comes from the requirements: effective dates are point in time (B11), a row
without source and sha256 is UNVERIFIED (D31), an uncovered symbol is UNKNOWN_INSTRUMENT
(unknown is never a guess), and SYMBOL_CHANGE chains are followed both ways without looping.
"""

import argparse
import contextlib
import datetime
import hashlib
import io
import json
import os
import shutil
import tempfile
import unittest

from nse.research import instruments as ins, marketdata

D = datetime.date
# provenance is verified by hashing the cited file (audit 2026-11-06), so each test
# folder holds a SYNTHETIC doc.pdf with exactly these bytes
DOC = b"SYNTHETIC test document"
SHA = hashlib.sha256(DOC).hexdigest()
HEADER = ",".join(ins.COLUMNS)
I1, I2, I3 = "INE000A01011", "INE000B01012", "INE000C01013"


def row(kind, symbol, isin, start, new="", end="", verified=True, notes="SYNTHETIC"):
    src, sha = ("SYNTHETIC test document", SHA) if verified else ("", "")
    return ",".join([kind, symbol, new, isin, "EQ", start, end, src, "doc.pdf" if verified else "", sha,
                     "2026-01-01", notes])


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        with open(os.path.join(self.tmp, "doc.pdf"), "wb") as fh:
            fh.write(DOC)

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
        self.bhav(D(2024, 1, 8), [("AAA", I1), ("BBB", I2)])
        folder = self.bhav(D(2024, 1, 9), [("AAA", I1), ("BBB", I2)])
        out = os.path.join(self.tmp, "o", "check.json")
        code, _ = self.run_cli(["instruments-check", "--records", recs, "--bhavcopy-dir", folder, "--out", out])
        self.assertEqual(code, 0)
        with open(out, encoding="utf-8") as fh:
            d = json.load(fh)
        self.assertEqual((d["observations"], d["findings"], d["bhavcopy_files"]), (4, [], 2))
        self.assertEqual([r["status"] for r in d["resolved_at_last_date"]], [ins.RESOLVED, ins.RESOLVED])

    def test_check_command_fails_on_an_unexplained_isin_change(self):
        recs = self.write(row("LISTING", "AAA", I1, "2015-01-01"))
        self.bhav(D(2024, 1, 8), [("AAA", I1)])
        folder = self.bhav(D(2024, 1, 9), [("AAA", I2)])
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


class InputIdentityIntegration(Base):
    """ED-21: bhavcopy inputs carry the identity check (inputs.load -> apply_to_input).
    SYNTHETIC bhavcopies and records; G0 turns a dated ERROR finding into DATA_INSUFFICIENT
    from that date (marketdata.findings_at), which these tests check through findings_at."""
    MON = Cli.MON
    D1, D2 = D(2024, 1, 8), D(2024, 1, 9)

    def bhav(self, d, rows):
        return Cli.bhav(self, d, rows)

    def load_input(self, records=None, isin2=I1):
        from nse.research import inputs
        self.bhav(self.D1, [("AAA", I1)])
        folder = os.path.join(self.tmp, "bhav")
        self.bhav(self.D2, [("AAA", isin2)])
        # bare CSVs are what the Cli fixture writes; archive_paths takes archives, so load them directly
        from nse.research.deps import bhavcopy as bc
        files = bc.load_many(sorted(os.path.join(folder, n) for n in os.listdir(folder)))
        inp = marketdata.from_bhavcopy(files, "AAA")
        return ins.apply_to_input(inp, files, records), inputs

    def errors_at(self, inp, d):
        return [f.code for f in inp.findings_at(d) if f.severity == marketdata.ERROR]

    def test_without_records_identity_is_unverified_but_a_stable_isin_is_not_an_error(self):
        from nse.research import models as m
        inp, _ = self.load_input()
        self.assertIn(m.IDENTITY_UNVERIFIED, inp.limitations)
        self.assertEqual(self.errors_at(inp, self.D2), [])
        self.assertEqual((inp.provenance["identity"]["records_supplied"], inp.provenance["identity"]["records_verified"]),
                         (False, False))

    def test_an_unexplained_isin_change_blocks_from_its_date_only(self):
        inp, _ = self.load_input(isin2=I2)
        self.assertEqual(self.errors_at(inp, self.D1), [])                      # earlier scans unchanged (D44)
        self.assertEqual(self.errors_at(inp, self.D2), [ins.ISIN_CHANGED_WITHOUT_RECORD])

    def test_verified_records_clear_the_limitation(self):
        from nse.research import models as m
        inp, _ = self.load_input(self.load(row("LISTING", "AAA", I1, "2015-01-01")))
        self.assertNotIn(m.IDENTITY_UNVERIFIED, inp.limitations)
        self.assertTrue(inp.provenance["identity"]["records_verified"])

    def test_an_isin_change_record_explains_the_change(self):
        recs = self.load(row("LISTING", "AAA", I1, "2015-01-01"), row("ISIN_CHANGE", "AAA", I2, "2024-01-09"))
        inp, _ = self.load_input(recs, isin2=I2)
        self.assertEqual(self.errors_at(inp, self.D2), [])

    def test_records_that_contradict_the_file_are_an_error(self):
        inp, _ = self.load_input(self.load(row("LISTING", "AAA", I2, "2015-01-01")))
        self.assertIn(ins.ISIN_RECORD_MISMATCH, self.errors_at(inp, self.D1))

    def test_unverified_records_keep_the_limitation(self):
        from nse.research import models as m
        inp, _ = self.load_input(self.load(row("LISTING", "AAA", I1, "2015-01-01", verified=False)))
        self.assertIn(m.IDENTITY_UNVERIFIED, inp.limitations)
        self.assertFalse(inp.provenance["identity"]["records_verified"])

    def test_inputs_load_applies_the_check_to_bhavcopy_archives(self):
        import zipfile
        from nse.research import inputs, models as m
        from nse.research.deps import bhavcopy as bc
        arch = os.path.join(self.tmp, "arch")
        os.makedirs(arch)
        for d, isin in ((self.D1, I1), (self.D2, I2)):
            name = bc.official_name(d)
            body = (",".join(bc.LEGACY_HEADER) + "\n" + "AAA,EQ,100,100,100,100,100,100,1000,100000,%s,10,%s,\n"
                    % (d.strftime("%d-%b-%Y").upper(), isin))
            with zipfile.ZipFile(os.path.join(arch, name), "w") as z:
                z.writestr(name[:-4], body)
        [inp] = inputs.load(["AAA"], bhavcopy_dir=arch)
        self.assertIn(m.IDENTITY_UNVERIFIED, inp.limitations)
        self.assertEqual(self.errors_at(inp, self.D2), [ins.ISIN_CHANGED_WITHOUT_RECORD])
        recs = self.write(row("LISTING", "AAA", I1, "2015-01-01"), row("ISIN_CHANGE", "AAA", I2, "2024-01-09"))
        [inp] = inputs.load(["AAA"], bhavcopy_dir=arch, instrument_records=recs)
        self.assertEqual(self.errors_at(inp, self.D2), [])
        self.assertNotIn(m.IDENTITY_UNVERIFIED, inp.limitations)

    def test_the_scanner_reports_data_insufficient_from_the_change_and_keeps_the_limitation(self):
        from nse.research import models as m, scanner
        inp, _ = self.load_input(isin2=I2)
        at = lambda d: scanner.scan_symbol(inp, scanner.ScanConfig(as_of=datetime.datetime.combine(d, datetime.time(15, 30))))
        after = at(self.D2)
        self.assertEqual(after.status, scanner.SYMBOL_DATA_INSUFFICIENT)
        self.assertEqual(after.candidates, [])
        self.assertTrue(any(r.startswith(ins.ISIN_CHANGED_WITHOUT_RECORD) for r in after.reasons))
        self.assertIn(m.IDENTITY_UNVERIFIED, after.limitations)
        before = at(self.D1)                       # the change is not known yet: not blocked by identity
        self.assertFalse(any(ins.ISIN_CHANGED_WITHOUT_RECORD in r for r in before.reasons))


class RenameRegression(Base):
    """Contrarian review 2026-11-09 (confirmed defect): a rename keeping the ISIN (e.g.
    ZOMATO -> ETERNAL) must not give the new symbol a silently truncated history. SYNTHETIC."""
    MON, D1, D2 = Cli.MON, InputIdentityIntegration.D1, InputIdentityIntegration.D2
    bhav = InputIdentityIntegration.bhav
    errors_at = InputIdentityIntegration.errors_at

    def renamed(self, records=None):
        from nse.research.deps import bhavcopy as bc
        self.bhav(self.D1, [("OLDSYM", I1)])
        self.bhav(self.D2, [("NEWSYM", I1)])
        folder = os.path.join(self.tmp, "bhav")
        files = bc.load_many(sorted(os.path.join(folder, n) for n in os.listdir(folder)))
        return ins.apply_to_input(marketdata.from_bhavcopy(files, "NEWSYM"), files, records)

    def test_unrecorded_rename_is_data_insufficient_from_the_rename(self):
        inp = self.renamed()
        self.assertIn(ins.SYMBOL_HISTORY_SPLIT, self.errors_at(inp, self.D2))
        self.assertIn(ins.SYMBOL_CHANGED_WITHOUT_RECORD, self.errors_at(inp, self.D2))

    def test_without_the_lineage_join_a_recorded_rename_still_blocks(self):
        # apply_to_input alone (no segments) cannot join; inputs.load joins verified renames (D51)
        recs = self.load(row("LISTING", "OLDSYM", I1, "2015-01-01"),
                         row("SYMBOL_CHANGE", "OLDSYM", I1, "2024-01-09", new="NEWSYM"))
        inp = self.renamed(recs)
        errs = self.errors_at(inp, self.D2)
        self.assertNotIn(ins.SYMBOL_CHANGED_WITHOUT_RECORD, errs)          # the record explains it...
        self.assertEqual(errs, [ins.SYMBOL_HISTORY_SPLIT])                  # ...but the series is still cut

    def test_the_old_symbol_is_not_flagged_by_its_successor(self):
        from nse.research.deps import bhavcopy as bc
        self.renamed()
        folder = os.path.join(self.tmp, "bhav")
        files = bc.load_many(sorted(os.path.join(folder, n) for n in os.listdir(folder)))
        inp = ins.apply_to_input(marketdata.from_bhavcopy(files, "OLDSYM"), files, None)
        self.assertNotIn(ins.SYMBOL_HISTORY_SPLIT, self.errors_at(inp, self.D2))


class QaRegressions20261109(Base):
    """Independent QA 2026-11-09 (confirmed defects). SYNTHETIC records and bhavcopies."""
    MON, D1, D2 = Cli.MON, InputIdentityIntegration.D1, InputIdentityIntegration.D2
    bhav = InputIdentityIntegration.bhav
    errors_at = InputIdentityIntegration.errors_at

    def inp(self, days, records, symbol="AAA"):
        from nse.research.deps import bhavcopy as bc
        for d, rows in days:
            self.bhav(d, rows)
        folder = os.path.join(self.tmp, "bhav")
        files = bc.load_many(sorted(os.path.join(folder, n) for n in os.listdir(folder)))
        return ins.apply_to_input(marketdata.from_bhavcopy(files, symbol), files, records)

    def test_symbol_reused_for_another_isin_blocks_from_the_reuse(self):
        recs = self.load(row("LISTING", "AAA", I1, "2015-01-01", end="2024-01-08"), row("LISTING", "AAA", I2, "2024-01-09"))
        inp = self.inp([(self.D1, [("AAA", I1)]), (self.D2, [("AAA", I2)])], recs)
        self.assertEqual(self.errors_at(inp, self.D1), [])
        self.assertEqual(self.errors_at(inp, self.D2), [ins.SYMBOL_REUSED_FOR_DIFFERENT_ISIN])

    def test_a_symbol_the_supplied_records_do_not_cover_is_an_error_from_that_date(self):
        recs = self.load(row("LISTING", "AAA", I1, "2015-01-01", end="2024-01-08"))
        inp = self.inp([(self.D1, [("AAA", I1)]), (self.D2, [("AAA", I1)])], recs)
        self.assertEqual(self.errors_at(inp, self.D1), [])
        self.assertEqual(self.errors_at(inp, self.D2), [ins.UNKNOWN_INSTRUMENT])

    def test_labels_do_not_depend_on_later_files(self):
        # the same scan date must get the same limitation and provenance with or without a later file
        recs = self.load(row("LISTING", "AAA", I1, "2015-01-01", end="2024-01-08"))
        short = self.inp([(self.D1, [("AAA", I1)])], recs)
        shutil.rmtree(os.path.join(self.tmp, "bhav"))
        full = self.inp([(self.D1, [("AAA", I1)]), (self.D2, [("AAA", I1)])], recs)
        self.assertEqual((short.limitations, short.provenance["identity"]), (full.limitations, full.provenance["identity"]))
        self.assertEqual([f.code for f in short.findings_at(self.D1)], [f.code for f in full.findings_at(self.D1)])


class LineageD51(Base):
    """D51 (owner 2026-11-09): connect a renamed company's history only through verified ISIN
    continuity and effective dates; never by ticker or name. SYNTHETIC archives and records."""
    DAYS = [D(2024, 1, 8), D(2024, 1, 9), D(2024, 1, 10), D(2024, 1, 11)]

    def archives(self, rows_by_day):
        import zipfile
        from nse.research.deps import bhavcopy as bc
        folder = os.path.join(self.tmp, "arch")
        os.makedirs(folder, exist_ok=True)
        for d, rows in zip(self.DAYS, rows_by_day):
            name = bc.official_name(d)
            body = ",".join(bc.LEGACY_HEADER) + "\n" + "".join(
                "%s,EQ,100,101,99,100,100,100,1000,100000,%s,10,%s,\n" % (sym, d.strftime("%d-%b-%Y").upper(), isin)
                for sym, isin in rows)
            with zipfile.ZipFile(os.path.join(folder, name), "w") as z:
                z.writestr(name[:-4], body)
        return folder

    def load_input(self, rows_by_day, *recs, symbol="NEW"):
        from nse.research import inputs
        [inp] = inputs.load([symbol], bhavcopy_dir=self.archives(rows_by_day), instrument_records=self.write(*recs))
        return inp

    def errors(self, inp, d):
        return sorted(f.code for f in inp.findings_at(d) if f.severity == marketdata.ERROR)

    RENAMED = [[("OLD", I1)], [("OLD", I1)], [("NEW", I1)], [("NEW", I1)]]

    def test_verified_rename_with_isin_continuity_is_one_history(self):
        inp = self.load_input(self.RENAMED, row("LISTING", "OLD", I1, "2015-01-01"),
                              row("SYMBOL_CHANGE", "OLD", I1, "2024-01-10", new="NEW"))
        self.assertEqual([c.start.date() for c in inp.candles], self.DAYS)          # all four bars, one series
        self.assertEqual(self.errors(inp, self.DAYS[-1]), [])
        lin = inp.provenance["identity"]["lineage"]
        self.assertEqual([(x["symbol"], x["from"], x["to"]) for x in lin],
                         [("OLD", None, "2024-01-09"), ("NEW", "2024-01-10", None)])

    def test_an_unverified_rename_record_does_not_join(self):
        inp = self.load_input(self.RENAMED, row("LISTING", "OLD", I1, "2015-01-01"),
                              row("SYMBOL_CHANGE", "OLD", I1, "2024-01-10", new="NEW", verified=False))
        self.assertEqual(len(inp.candles), 2)
        self.assertIn(ins.SYMBOL_HISTORY_SPLIT, self.errors(inp, self.DAYS[-1]))
        self.assertTrue(any(f.code == "LINEAGE_NOT_JOINED" for f in inp.findings))

    def test_a_different_isin_after_the_change_blocks_from_that_day(self):
        # QA 2026-11-09 (prefix invariance): evidence dated on or after the change never undoes
        # the join retroactively; it is a dated ERROR, so no decision is ever made on a series
        # mixing two ISINs: from the first NEW row (I2) every scan is DATA_INSUFFICIENT.
        rows = [[("OLD", I1)], [("OLD", I1)], [("NEW", I2)], [("NEW", I2)]]
        inp = self.load_input(rows, row("LISTING", "OLD", I1, "2015-01-01"),
                              row("SYMBOL_CHANGE", "OLD", I1, "2024-01-10", new="NEW"))
        self.assertEqual(self.errors(inp, self.DAYS[1]), [])
        self.assertIn("LINEAGE_CONFLICT", self.errors(inp, self.DAYS[2]))

    def test_overlapping_rows_block_from_the_overlap(self):
        rows = [[("OLD", I1)], [("OLD", I1)], [("NEW", I1), ("OLD", I1)], [("NEW", I1)]]
        inp = self.load_input(rows, row("LISTING", "OLD", I1, "2015-01-01"),
                              row("SYMBOL_CHANGE", "OLD", I1, "2024-01-10", new="NEW"))
        self.assertEqual(self.errors(inp, self.DAYS[1]), [])
        self.assertIn("LINEAGE_CONFLICT", self.errors(inp, self.DAYS[2]))

    def test_the_join_does_not_depend_on_later_files(self):
        # QA 2026-11-09 reproduction: a recorded ISIN change of NEW after the rename (e.g. a
        # face-value split) must not undo the join seen with fewer files
        recs = (row("LISTING", "OLD", I1, "2015-01-01"), row("SYMBOL_CHANGE", "OLD", I1, "2024-01-10", new="NEW"),
                row("ISIN_CHANGE", "NEW", I2, "2024-01-11"))
        short = self.load_input(self.RENAMED[:3], *recs)
        shutil.rmtree(os.path.join(self.tmp, "arch"))
        full = self.load_input(self.RENAMED[:3] + [[("NEW", I2)]], *recs)
        self.assertEqual(short.provenance["identity"]["lineage"], full.provenance["identity"]["lineage"])
        self.assertEqual([c.start.date() for c in short.candles], [c.start.date() for c in full.candles][:3])
        self.assertEqual(self.errors(full, self.DAYS[2]), self.errors(short, self.DAYS[2]))

    def test_a_chain_of_verified_renames_is_joined(self):
        rows = [[("AAA", I1)], [("BBB", I1)], [("NEW", I1)], [("NEW", I1)]]
        inp = self.load_input(rows, row("LISTING", "AAA", I1, "2015-01-01"),
                              row("SYMBOL_CHANGE", "AAA", I1, "2024-01-09", new="BBB"),
                              row("SYMBOL_CHANGE", "BBB", I1, "2024-01-10", new="NEW"))
        self.assertEqual(len(inp.candles), 4)
        self.assertEqual(self.errors(inp, self.DAYS[-1]), [])
        self.assertEqual([x["symbol"] for x in inp.provenance["identity"]["lineage"]], ["AAA", "BBB", "NEW"])

    def test_a_shared_ticker_without_a_record_is_never_joined(self):
        inp = self.load_input(self.RENAMED, row("LISTING", "OLD", I1, "2015-01-01", end="2024-01-09"),
                              row("LISTING", "NEW", I1, "2024-01-10"))
        self.assertEqual(len(inp.candles), 2)
        self.assertIn(ins.SYMBOL_HISTORY_SPLIT, self.errors(inp, self.DAYS[-1]))


class FilteredLoadingEquivalence(Base):
    """ED-41: inputs.load keeps in memory only the rows it needs (the symbol, its rename chain
    and other symbols sharing its ISINs). The result must equal loading every row. SYNTHETIC."""
    DAYS, RENAMED, archives = LineageD51.DAYS, LineageD51.RENAMED, LineageD51.archives

    def both(self, rows_by_day, *recs, symbol="NEW"):
        from unittest import mock
        from nse.research import inputs
        from nse.research.deps import bhavcopy as bc
        folder = self.archives(rows_by_day)
        path = self.write(*recs)
        dump = lambda inp: (json.dumps(inp.provenance, sort_keys=True, default=str), [c.start for c in inp.candles],
                            [c.close for c in inp.candles], sorted(json.dumps(f.to_dict(), sort_keys=True) for f in inp.findings),
                            sorted(inp.limitations))
        [filtered] = inputs.load([symbol], bhavcopy_dir=folder, instrument_records=path)
        full_rows = lambda paths, manifest, symbols, records, series: bc.load_many(paths, manifest)
        with mock.patch.object(inputs, "_load_needed_rows", full_rows):
            [full] = inputs.load([symbol], bhavcopy_dir=folder, instrument_records=path)
        shutil.rmtree(folder)
        self.assertEqual(dump(filtered), dump(full))
        return filtered

    def test_equal_to_loading_every_row(self):
        noise = ("ZZZ", I3)
        cases = [
            # verified rename, plus an unrelated symbol on every day
            ([r + [noise] for r in self.RENAMED], (row("LISTING", "OLD", I1, "2015-01-01"),
                                                    row("SYMBOL_CHANGE", "OLD", I1, "2024-01-10", new="NEW"))),
            # the same ISIN under another ticker before NEW, without a record (SYMBOL_HISTORY_SPLIT)
            ([[("OLD", I1), noise], [("OLD", I1)], [("NEW", I1)], [("NEW", I1), noise]],
             (row("LISTING", "NEW", I1, "2024-01-10"),)),
            # NEW's ISIN also traded by a third symbol after NEW appears, and an ISIN change of NEW
            ([[("NEW", I1)], [("NEW", I1), ("OTH", I1)], [("NEW", I2)], [("NEW", I2), ("OTH", I2)]],
             (row("LISTING", "NEW", I1, "2015-01-01"), row("ISIN_CHANGE", "NEW", I2, "2024-01-10"))),
            # no records at all
            ([[("OLD", I1)], [("OLD", I1)], [("NEW", I1)], [("NEW", I1)]], ()),
        ]
        for i, (rows, recs) in enumerate(cases):
            with self.subTest(case=i):
                self.both(rows, *recs)

    def test_rows_of_other_isins_are_not_kept(self):
        from nse.research import inputs
        folder = self.archives([[("NEW", I1), ("ZZZ", I3)]] * 4)
        from nse.research.deps import bhavcopy as bc
        files = inputs._load_needed_rows(bc.archive_paths(folder), None, ["NEW"], [], "EQ")
        self.assertEqual(sorted(set(r.symbol for f in files for r in f.rows)), ["NEW"])
        self.assertEqual([f.series_counts["EQ"] for f in files], [2] * 4)        # counts describe the whole file


class RealIdentityRecords(unittest.TestCase):
    """The held identity records (nse/data/universe/instrument_records.csv, ED-37). Regression
    (PROMPT-01 audit, 2026-11-09): pre-2016 renames carrying today's ISIN made two ISINs active
    under TATASTEEL, JSWSTEEL, CHOLAFIN, SOLARINDS and BAJFINANCE, which would have blocked their
    scans. Real file, no bhavcopies."""
    PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "nse", "data", "universe",
                        "instrument_records.csv")
    # ISIN changes with no single effective date (D56). Both ISINs stay listed, so the symbol
    # is unresolved and is never joined. YESBANK's 2020-03-16 change is separate: NSE/CML/43833
    # names INE528G01035 from that date. BAJFINANCE and GRASIM MSEI circulars each state two dates.
    UNEVIDENCED = {"BAJFINANCE", "GRASIM"}

    def test_every_record_is_verified_and_no_symbol_has_two_isins(self):
        if not os.path.isfile(self.PATH):
            self.skipTest("identity records not held")
        recs = ins.load(self.PATH)
        self.assertTrue(recs and all(r.verified for r in recs))
        doubled = set()
        d = D(2016, 1, 1)
        while d <= D(2025, 12, 31):
            by_symbol = {}
            for isin, (sym, _) in ins.state_at(recs, d)[0].items():
                by_symbol.setdefault(sym, []).append(isin)
            doubled |= set(s for s, isins in by_symbol.items() if len(isins) > 1)
            d += datetime.timedelta(days=7)
        self.assertEqual(doubled, self.UNEVIDENCED)
