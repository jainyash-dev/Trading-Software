"""UDiFF bhavcopy support, source selection by date and cross-format checks (B18, ED-20).

Two kinds of input:
- SYNTHETIC UDiFF files built here from the column lists recorded from official samples
  (nse_bhavcopy.UDIFF_SCHEMAS). Their rows are invented test values, not market data.
- The REAL official samples in nse/data/eod/evidence/ (git-ignored archives). Those tests run
  only when the files are present and are skipped otherwise; nothing stands in for them.
"""

import csv
import datetime
import hashlib
import os
import shutil
import tempfile
import unittest
import zipfile
from decimal import Decimal

from _load import ROOT, load, require_local

bc = load(os.path.join("nse", "eod"), "nse_bhavcopy")
rp = load(os.path.join("nse", "eod"), "nse_replay")
D = datetime.date
EVIDENCE = os.path.join(ROOT, "nse", "data", "eod", "evidence")
SAMPLES = os.path.join(EVIDENCE, "samples")
OVERLAP_DATES = (D(2024, 1, 20), D(2024, 3, 2), D(2024, 5, 18), D(2024, 7, 5))


def urow(d, **over):
    """One SYNTHETIC UDiFF data row (34 fields) for date d."""
    v = dict.fromkeys(bc.UDIFF_COLUMNS, "")
    v.update(TradDt=d.isoformat(), BizDt=d.isoformat(), Sgmt="CM", Src="NSE", FinInstrmTp="STK", FinInstrmId="1594",
             ISIN="INE000A01019", TckrSymb="AAAA", SctySrs="EQ", FinInstrmNm="AAAA LIMITED", OpnPric="100.50",
             HghPric="104.00", LwPric="99.25", ClsPric="103.10", LastPric="103.00", PrvsClsgPric="100.00",
             SttlmPric="103.10", TtlTradgVol="1500", TtlTrfVal="153000.75", TtlNbOfTxsExctd="42", SsnId="F1",
             NewBrdLotQty="1")
    v.update(over)
    return ",".join(v[c] for c in bc.UDIFF_COLUMNS)


def utext(rows, schema="UDIFF_2024B"):
    return ",".join(bc.UDIFF_SCHEMAS[schema]) + "\n" + "".join(r + "\n" for r in rows)


def ltext(d, **over):
    """One-row SYNTHETIC legacy CSV with the same values as urow()."""
    v = {"SYMBOL": "AAAA", "SERIES": "EQ", "OPEN": "100.5", "HIGH": "104", "LOW": "99.25", "CLOSE": "103.1",
         "LAST": "103", "PREVCLOSE": "100", "TOTTRDQTY": "1500", "TOTTRDVAL": "153000.75",
         "TIMESTAMP": d.strftime("%d-%b-%Y").upper(), "TOTALTRADES": "42", "ISIN": "INE000A01019"}
    v.update(over)
    return ",".join(bc.LEGACY_HEADER) + "\n" + ",".join(v[c] for c in bc.LEGACY_HEADER[:-1]) + ",\n"


class Tmp(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="nse-udiff-test-")
        self.addCleanup(shutil.rmtree, self.dir, True)

    def put(self, d, body, fmt=bc.FORMAT_UDIFF, archive=True):
        name = bc.official_name(d, fmt)
        path = os.path.join(self.dir, name if archive else name[:-len(".zip")])
        data = body.encode() if isinstance(body, str) else body
        if archive:
            with zipfile.ZipFile(path, "w") as z:
                z.writestr(name[:-len(".zip")], data)
        else:
            with open(path, "wb") as fh:
                fh.write(data)
        return path

    def refuse(self, err, body, d=D(2024, 7, 8)):
        with self.assertRaises(err):
            bc.load(self.put(d, body))


class UdiffSchemas(Tmp):
    """SYNTHETIC files; header variants as recorded from the official samples."""

    def test_both_recorded_header_variants_load_with_their_schema_version(self):
        d = D(2024, 7, 8)
        for schema in ("UDIFF_2024A", "UDIFF_2024B"):
            with self.subTest(schema=schema):
                f = bc.load(self.put(d, utext([urow(d)], schema)))
                self.assertEqual((f.format, f.schema_version, f.trade_date), (bc.FORMAT_UDIFF, schema, d))
                [r] = f.eq_rows
                self.assertEqual((r.symbol, r.series, r.isin, r.open, r.high, r.low, r.close, r.last, r.prev_close),
                                 ("AAAA", "EQ", "INE000A01019", Decimal("100.50"), Decimal("104.00"),
                                  Decimal("99.25"), Decimal("103.10"), Decimal("103.00"), Decimal("100.00")))
                self.assertEqual((r.traded_qty, r.traded_value, r.total_trades), (1500, Decimal("153000.75"), 42))
                self.assertEqual(dict(r.extra), {"FinInstrmId": "1594", "FinInstrmNm": "AAAA LIMITED",
                                                 "SttlmPric": "103.10", "NewBrdLotQty": "1", "Rmks": ""})

    def test_a_bare_csv_loads_like_the_archive(self):
        d = D(2024, 7, 8)
        f = bc.load(self.put(d, utext([urow(d)]), archive=False))
        self.assertEqual((f.source.kind, f.format), ("CSV", bc.FORMAT_UDIFF))

    def test_any_other_header_is_refused(self):
        d = D(2024, 7, 8)
        cols = list(bc.UDIFF_COLUMNS)
        variants = {
            "missing column": cols[:-1],
            "reordered": [cols[1], cols[0]] + cols[2:],
            "extra column": cols + ["NewCol"],
            "renamed": ["TradeDate"] + cols[1:],
            "2024B with trailing comma": cols + [""],
        }
        for label, header in variants.items():
            with self.subTest(label):
                self.refuse(bc.UnsupportedFormatError, ",".join(header) + "\n" + urow(d) + "\n")

    def test_the_2024a_header_does_not_admit_a_35_field_data_row(self):
        # QA 2026-11-09: the 2024A header has a trailing comma, its data rows do not
        d = D(2024, 7, 8)
        with self.assertRaisesRegex(bc.MalformedFileError, "35 fields, expected 34"):
            bc.load(self.put(d, utext([urow(d) + ","], "UDIFF_2024A")))

    def test_legacy_content_under_a_udiff_name_and_udiff_under_a_legacy_name(self):
        d = D(2024, 7, 5)
        self.refuse(bc.UnsupportedFormatError, ltext(d), d)
        with self.assertRaises(bc.UnsupportedFormatError):
            bc.load(self.put(d, utext([urow(d)]), fmt=bc.FORMAT_LEGACY))

    def test_encoding_rules_match_legacy(self):
        d = D(2024, 7, 8)
        good = utext([urow(d)])
        self.refuse(bc.UnsupportedFormatError, b"\xef\xbb\xbf" + good.encode())
        self.refuse(bc.UnsupportedFormatError, good.replace("\n", "\r\n"))
        self.refuse(bc.UnsupportedFormatError, utext([urow(d, FinInstrmNm='"AAAA, LTD"')]))
        self.refuse(bc.MalformedFileError, good[:-1])
        self.refuse(bc.MalformedFileError, ",".join(bc.UDIFF_COLUMNS) + "\n")


class UdiffRows(Tmp):
    """Each row rule, one SYNTHETIC violation at a time."""
    d = D(2024, 7, 8)

    def bad(self, err, **over):
        with self.subTest(**over):
            self.refuse(err, utext([urow(self.d), urow(self.d, **dict({"TckrSymb": "BBBB"}, **over))]))

    def test_dates_and_cash_market_constants(self):
        self.bad(bc.MalformedFileError, TradDt="2024-07-09")              # not the file-name date
        self.bad(bc.MalformedFileError, TradDt="08-07-2024")
        self.bad(bc.UnsupportedFormatError, BizDt="2024-07-09")
        self.bad(bc.UnsupportedFormatError, Sgmt="FO")
        self.bad(bc.UnsupportedFormatError, Src="BSE")
        self.bad(bc.UnsupportedFormatError, FinInstrmTp="OPTSTK")
        self.bad(bc.UnsupportedFormatError, SsnId="F2")
        for col in ("XpryDt", "StrkPric", "OptnTp", "UndrlygPric", "OpnIntrst", "ChngInOpnIntrst", "Rsvd1", "Rsvd4"):
            self.bad(bc.UnsupportedFormatError, **{col: "1"})

    def test_prices_quantities_and_identity(self):
        self.bad(bc.MalformedFileError, HghPric="100.00")                 # high below open and close
        self.bad(bc.MalformedFileError, LwPric="101.00")                  # low above open
        self.bad(bc.MalformedFileError, OpnPric="0.00")
        self.bad(bc.MalformedFileError, ClsPric="-1.00")
        self.bad(bc.MalformedFileError, ClsPric="")
        self.bad(bc.MalformedFileError, PrvsClsgPric="")
        self.bad(bc.MalformedFileError, SttlmPric="")
        self.bad(bc.MalformedFileError, TtlTradgVol="15.5")
        self.bad(bc.MalformedFileError, TtlNbOfTxsExctd="")
        self.bad(bc.MalformedFileError, NewBrdLotQty="x")
        self.bad(bc.MalformedFileError, ISIN="US0000000001")
        self.bad(bc.MalformedFileError, SctySrs="")
        self.bad(bc.MalformedFileError, TckrSymb="A A")

    def test_field_count_duplicate_and_line_number(self):
        with self.assertRaisesRegex(bc.MalformedFileError, "line 3: 33 fields"):
            bc.load(self.put(self.d, utext([urow(self.d), urow(self.d, TckrSymb="BBBB").rsplit(",", 1)[0]])))
        with self.assertRaisesRegex(bc.MalformedFileError, "duplicate AAAA EQ"):
            bc.load(self.put(self.d, utext([urow(self.d), urow(self.d)])))

    def test_empty_last_price_is_none_never_filled(self):
        f = bc.load(self.put(self.d, utext([urow(self.d, SctySrs="NT", LastPric="")])))
        self.assertIsNone(f.rows[0].last)
        self.assertEqual(f.eq_rows, [])
        self.assertEqual(f.non_eq_only_symbols, ["AAAA"])


class NonEqRowIsolation(Tmp):
    """ED-30: an invalid row of a non-EQ series (e.g. T0, whose CLOSE can lie outside the T0
    high/low in official files from 2024-03-28) is rejected and listed; EQ rows never are."""

    def test_udiff_t0_row_with_close_outside_its_range_is_isolated(self):
        d = D(2024, 7, 8)
        t0 = urow(d, SctySrs="T0", OpnPric="762.00", HghPric="762.00", LwPric="762.00", ClsPric="768.30")
        f = bc.load(self.put(d, utext([urow(d), t0])))
        self.assertEqual([r.series for r in f.rows], ["EQ"])
        [(line, series, symbol, reason)] = f.rejected_rows
        self.assertEqual((line, series, symbol), (3, "T0", "AAAA"))
        self.assertIn("OHLC inconsistent", reason)

    def test_legacy_non_eq_row_with_a_bad_isin_is_isolated(self):
        d = D(2021, 2, 16)
        body = ltext(d) + ltext(d, SYMBOL="ABFRLPP1", SERIES="E1", ISIN="DUMMY").split("\n", 1)[1]
        f = bc.load(self.put(d, body, fmt=bc.FORMAT_LEGACY))
        self.assertEqual([(r.symbol, r.series) for r in f.rows], [("AAAA", "EQ")])
        self.assertEqual([x[1:3] for x in f.rejected_rows], [("E1", "ABFRLPP1")])

    def test_an_invalid_eq_row_still_refuses_the_file(self):
        d = D(2024, 7, 8)
        with self.assertRaises(bc.MalformedFileError):
            bc.load(self.put(d, utext([urow(d, TckrSymb="BBBB"), urow(d, HghPric="100.00")])))

    def test_structural_failures_in_non_eq_rows_still_refuse_the_file(self):
        # QA 2026-11-09: only VALUE failures are isolated; structure always refuses
        d = D(2022, 1, 3)
        good = ltext(d)
        cases = {
            "14th column not empty": good + ltext(d, SYMBOL="BBBB", SERIES="BE").split("\n", 1)[1].rstrip("\n") + "X\n",
            "TIMESTAMP of another day": good + ltext(d, SYMBOL="BBBB", SERIES="BE", TIMESTAMP="04-JAN-2022",
                                                      HIGH="1").split("\n", 1)[1],
            "comma in an EQ symbol": good + "BAJAJ,AUTO,EQ,10,11,9,10,10,10,1,10,03-JAN-2022,1,INE917I01010\n",
            "lowercase series": good + ltext(d, SYMBOL="BBBB", SERIES="eq", HIGH="1").split("\n", 1)[1],
        }
        for label, body in cases.items():
            with self.subTest(label):
                with self.assertRaises(bc.MalformedFileError):
                    bc.load(self.put(d, body, fmt=bc.FORMAT_LEGACY))

    def test_format_failures_in_non_eq_rows_still_refuse_the_file(self):
        d = D(2024, 7, 8)
        with self.assertRaises(bc.UnsupportedFormatError):           # a format-level value, not a price
            bc.load(self.put(d, utext([urow(d), urow(d, SctySrs="T0", FinInstrmTp="OPTSTK")])))
        with self.assertRaises(bc.MalformedFileError):               # field count: the series is unreadable
            bc.load(self.put(d, utext([urow(d), urow(d, SctySrs="T0").rsplit(",", 1)[0]])))


class LegacyCrlfSchema(Tmp):
    """LEGACY_13_CRLF (D55 backfill: cm10JUL2017bhav.csv.zip): CRLF on every line and a
    13-column header. Accepted only exactly; SYNTHETIC files."""
    d = D(2017, 7, 10)

    def body(self, eol="\r\n", header=",".join(bc.LEGACY_HEADER_13), row=None):
        row = row or "AAAA,EQ,10,11,9,10.5,10.5,10,100,1000,10-JUL-2017,5,INE000A01019"
        return header + eol + row + eol

    def test_exact_variant_loads_with_its_schema(self):
        f = bc.load(self.put(self.d, self.body(), fmt=bc.FORMAT_LEGACY))
        self.assertEqual((f.schema_version, len(f.eq_rows), f.eq_rows[0].close), ("LEGACY_13_CRLF", 1, Decimal("10.5")))

    def test_anything_else_is_refused(self):
        for label, body in (("LF with the 13-column header", self.body(eol="\n")),
                            ("CRLF with the 14-column header", self.body(header=",".join(bc.LEGACY_HEADER))),
                            ("mixed endings", self.body().replace("\r\n", "\n", 1)),
                            ("a stray CR", self.body(row="AAAA,EQ,10,11,9,10.5,10.5,10,100,1000,10-JUL-2017,5,INE0\rA01019")),
                            ("a 14th column in a row", self.body(row="AAAA,EQ,10,11,9,10.5,10.5,10,100,1000,10-JUL-2017,5,INE000A01019,"))):
            with self.subTest(label):
                with self.assertRaises(bc.BhavcopyError):
                    bc.load(self.put(self.d, body, fmt=bc.FORMAT_LEGACY))


class LegacyShortDateAndNestedMember(Tmp):
    """ED-38 (D55 backfill: cm13JUL2020bhav.csv.zip): the member stored as "<name>/<name>"
    and every TIMESTAMP the file date as DD-Mon-YY, inside the LEGACY_13_CRLF schema.
    Accepted only exactly; SYNTHETIC files."""
    d = D(2020, 7, 13)
    row = "%s,EQ,10,11,9,10.5,10.5,10,100,1000,%s,5,INE000A0%d019"

    def body(self, *stamps, eol="\r\n"):
        rows = [self.row % ("SYM" + "ABCD"[i], s, i) for i, s in enumerate(stamps)]
        return eol.join([",".join(bc.LEGACY_HEADER_13)] + rows) + eol

    def archive(self, body, members):
        path = os.path.join(self.dir, bc.official_name(self.d, bc.FORMAT_LEGACY))
        with zipfile.ZipFile(path, "w") as z:
            for m in members:
                z.writestr(m, body.encode())
        return path

    def test_exact_variant_loads_with_its_schema_and_real_member_path(self):
        f = bc.load(self.archive(self.body("13-Jul-20", "13-Jul-20"), ["cm13JUL2020bhav.csv/cm13JUL2020bhav.csv"]))
        self.assertEqual((f.schema_version, len(f.eq_rows), f.eq_rows[0].trade_date, f.source.member_name),
                         ("LEGACY_13_CRLF_SHORTDATE", 2, self.d, "cm13JUL2020bhav.csv/cm13JUL2020bhav.csv"))

    def test_other_short_dates_layouts_and_endings_are_refused(self):
        for label, body, members in (
                ("another date", self.body("14-Jul-20"), ["cm13JUL2020bhav.csv"]),
                ("mixed forms", self.body("13-Jul-20", "13-JUL-2020"), ["cm13JUL2020bhav.csv"]),
                ("upper-case short form", self.body("13-JUL-20"), ["cm13JUL2020bhav.csv"]),
                ("short form with LF", self.body("13-Jul-20", eol="\n"), ["cm13JUL2020bhav.csv"]),
                ("other folder", self.body("13-JUL-2020"), ["x/cm13JUL2020bhav.csv"]),
                ("two members", self.body("13-JUL-2020"), ["cm13JUL2020bhav.csv", "cm13JUL2020bhav.csv/cm13JUL2020bhav.csv"])):
            with self.subTest(label):
                with self.assertRaises(bc.BhavcopyError):
                    bc.load(self.archive(body, members))


class SourceSelection(Tmp):
    """ED-20: legacy up to 2024-07-05, UDiFF from 2024-07-08 (NSE/MSD/62424). SYNTHETIC files."""

    def test_boundaries_and_names(self):
        self.assertEqual(bc.selected_format(D(2024, 7, 5)), bc.FORMAT_LEGACY)
        self.assertEqual(bc.selected_format(D(2024, 7, 8)), bc.FORMAT_UDIFF)
        self.assertEqual(bc.selected_format(D(2016, 1, 1)), bc.FORMAT_LEGACY)
        self.assertEqual(bc.official_name(D(2024, 7, 5)), "cm05JUL2024bhav.csv.zip")
        self.assertEqual(bc.official_name(D(2024, 7, 8)), "BhavCopy_NSE_CM_0_0_0_20240708_F_0000.csv.zip")
        self.assertEqual(bc.name_info("BhavCopy_NSE_CM_0_0_0_20240708_F_0000.csv"), (D(2024, 7, 8), bc.FORMAT_UDIFF))
        with self.assertRaises(bc.UnsupportedFormatError):
            bc.name_info("BhavCopy_NSE_CM_0_0_0_20240231_F_0000.csv.zip")

    def test_official_urls_match_the_evidence_manifest(self):
        rows = {r["file_name"]: r["source_page"] for r in bc.read_manifest(os.path.join(EVIDENCE, "manifest.csv"))
                if r["kind"] == "ARCHIVE"}
        for d, fmt in ((D(2024, 7, 5), bc.FORMAT_LEGACY), (D(2024, 7, 8), bc.FORMAT_UDIFF),
                       (D(2024, 1, 20), bc.FORMAT_UDIFF)):
            self.assertEqual(bc.official_url(d, fmt), rows[bc.official_name(d, fmt)], d)

    def test_load_many_spans_the_switch_with_one_source_per_date(self):
        a = self.put(D(2024, 7, 5), ltext(D(2024, 7, 5)), fmt=bc.FORMAT_LEGACY)
        b = self.put(D(2024, 7, 8), utext([urow(D(2024, 7, 8))]))
        files = bc.load_many(bc.archive_paths(self.dir))
        self.assertEqual([(f.trade_date, f.format) for f in files],
                         [(D(2024, 7, 5), bc.FORMAT_LEGACY), (D(2024, 7, 8), bc.FORMAT_UDIFF)])
        self.assertEqual(bc.archive_paths(self.dir), sorted([a, b]))
        daily = rp.daily_series(files, "AAAA")                     # one series across the switch
        self.assertEqual([b_.close for b_ in daily.bars], [Decimal("103.1"), Decimal("103.10")])

    def test_the_unselected_format_is_refused_for_a_dataset(self):
        for d, fmt, body in ((D(2024, 7, 5), bc.FORMAT_UDIFF, utext([urow(D(2024, 7, 5))])),
                             (D(2024, 7, 8), bc.FORMAT_LEGACY, ltext(D(2024, 7, 8)))):
            with self.subTest(d=d):
                p = self.put(d, body, fmt=fmt)
                self.assertEqual(bc.load(p).format, fmt)              # parseable for a cross-check...
                with self.assertRaises(bc.SourceSelectionError):     # ...but never part of a dataset
                    bc.load_many([p])
                os.remove(p)

    def test_two_formats_for_one_date_are_refused(self):
        d = D(2024, 7, 5)
        paths = [self.put(d, ltext(d), fmt=bc.FORMAT_LEGACY), self.put(d, utext([urow(d)]))]
        with self.assertRaises(bc.BhavcopyError):
            bc.load_many(paths)


class CrossCheck(Tmp):
    """Exact, field-by-field comparison of two files for one date. SYNTHETIC files."""
    d = D(2024, 7, 5)

    def pair(self, legacy_over=None, udiff_rows=None):
        a = bc.load(self.put(self.d, ltext(self.d, **(legacy_over or {})), fmt=bc.FORMAT_LEGACY))
        b = bc.load(self.put(self.d, utext(udiff_rows or [urow(self.d)])))
        return bc.cross_check(a, b)

    def test_same_values_in_different_text_are_identical(self):
        r = self.pair()                                  # "104" vs "104.00", "103.1" vs "103.10"
        self.assertTrue(r["identical"])
        self.assertEqual((r["common_rows"], r["mismatches"], r["last_empty_vs_zero"]), (1, [], 0))

    def test_any_value_difference_is_a_mismatch(self):
        r = self.pair({"CLOSE": "103.15"})
        self.assertFalse(r["identical"])
        self.assertEqual([(m["symbol"], m["field"]) for m in r["mismatches"]], [("AAAA", "close")])
        r = self.pair({"ISIN": "INE000A01027"})
        self.assertEqual([m["field"] for m in r["mismatches"]], ["isin"])

    def test_missing_rows_are_reported(self):
        r = self.pair(udiff_rows=[urow(self.d), urow(self.d, TckrSymb="BBBB")])
        self.assertFalse(r["identical"])
        self.assertEqual(r["only_in_second"], [["BBBB", "EQ"]])

    def test_empty_last_against_zero_is_counted_not_hidden(self):
        r = self.pair({"LAST": "0.0"}, [urow(self.d, LastPric="")])
        self.assertTrue(r["identical"])
        self.assertEqual(r["last_empty_vs_zero"], 1)
        r = self.pair({"LAST": "5"}, [urow(self.d, LastPric="")])        # empty is not equal to a real price
        self.assertEqual([m["field"] for m in r["mismatches"]], ["last"])

    def test_different_dates_are_refused(self):
        a = bc.load(self.put(self.d, ltext(self.d), fmt=bc.FORMAT_LEGACY))
        b = bc.load(self.put(D(2024, 7, 8), utext([urow(D(2024, 7, 8))])))
        with self.assertRaises(bc.BhavcopyError):
            bc.cross_check(a, b)


class RealEvidence(unittest.TestCase):
    """The official samples and circulars in nse/data/eod/evidence/ (git-ignored files)."""

    @classmethod
    def setUpClass(cls):
        cls.manifest = os.path.join(EVIDENCE, "manifest.csv")
        rows = bc.read_manifest(cls.manifest)
        cls.archives = [r for r in rows if r["kind"] == "ARCHIVE"]
        missing = [r["file_name"] for r in cls.archives if not os.path.isfile(os.path.join(SAMPLES, r["file_name"]))]
        require_local(not missing, "official bhavcopy samples in nse/data/eod/evidence/samples/: %s" % ", ".join(missing))
        cls.files = {}
        for r in cls.archives:
            f = bc.load(os.path.join(SAMPLES, r["file_name"]), cls.manifest)      # size and SHA-256 verified
            cls.files[(f.trade_date, f.format)] = f

    def test_every_sample_verifies_and_has_its_recorded_schema(self):
        self.assertEqual(len(self.files), 9)
        got = {(d.isoformat(), fmt): f.schema_version for (d, fmt), f in self.files.items()}
        for d in ("2024-01-20", "2024-03-02", "2024-05-18"):
            self.assertEqual(got[(d, bc.FORMAT_UDIFF)], "UDIFF_2024A", d)
        for d in ("2024-07-05", "2024-07-08"):
            self.assertEqual(got[(d, bc.FORMAT_UDIFF)], "UDIFF_2024B", d)
        for (d, fmt), schema in got.items():
            if fmt == bc.FORMAT_LEGACY:
                self.assertEqual(schema, bc.LEGACY_SCHEMA, d)

    def test_legacy_and_udiff_agree_exactly_on_every_overlap_date(self):
        for d in OVERLAP_DATES:
            with self.subTest(d=d):
                r = bc.cross_check(self.files[(d, bc.FORMAT_LEGACY)], self.files[(d, bc.FORMAT_UDIFF)])
                self.assertTrue(r["identical"], r["mismatches"][:5] or (r["only_in_first"][:5], r["only_in_second"][:5]))
                self.assertEqual(r["rows"][0], r["rows"][1])
                self.assertLessEqual(r["last_empty_vs_zero"], 2)             # debt rows only (observed 0-2)

    def test_known_values_on_the_last_overlap_date(self):
        # INFY EQ on 2024-07-05, read from both official files (EOD_FORMAT_EVIDENCE.md section 9)
        for fmt in (bc.FORMAT_LEGACY, bc.FORMAT_UDIFF):
            [r] = [r for r in self.files[(D(2024, 7, 5), fmt)].eq_rows if r.symbol == "INFY"]
            self.assertEqual((r.isin, r.open, r.high, r.low, r.close, r.prev_close, r.traded_qty, r.total_trades),
                             ("INE009A01021", Decimal("1651.45"), Decimal("1665.85"), Decimal("1633.35"),
                              Decimal("1647.45"), Decimal("1650.65"), 7065022, 197833), fmt)
        self.assertEqual(len(self.files[(D(2024, 7, 5), bc.FORMAT_UDIFF)].eq_rows), 1906)

    def test_the_first_udiff_only_date_is_the_selected_source(self):
        f = self.files[(D(2024, 7, 8), bc.FORMAT_UDIFF)]
        self.assertEqual(bc.selected_format(f.trade_date), bc.FORMAT_UDIFF)
        self.assertEqual([x.format for x in bc.load_many([os.path.join(SAMPLES, f.source.file_name)], self.manifest)],
                         [bc.FORMAT_UDIFF])

    def test_circulars_match_their_registry(self):
        with open(os.path.join(EVIDENCE, "sources.csv"), newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual([r["source_ref"] for r in rows], ["NSE/MSD/62424", "NSE/MSD/56202", "NSE/MSD/54028"])
        missing = [r["file_name"] for r in rows if not os.path.isfile(os.path.join(EVIDENCE, "circulars", r["file_name"]))]
        require_local(not missing, "format circulars in nse/data/eod/evidence/circulars/: %s" % ", ".join(missing))
        for r in rows:
            with open(os.path.join(EVIDENCE, "circulars", r["file_name"]), "rb") as fh:
                data = fh.read()
            self.assertEqual((hashlib.sha256(data).hexdigest(), str(len(data))), (r["sha256"], r["size_bytes"]), r["source_ref"])

    def test_evidence_copies_agree_with_the_research_dataset(self):
        # MP1 (D47): the backfill put some of the same official files into the research set.
        # The evidence copies stay separate; where a file is in both, the CSV CONTENT must be
        # equal. The zip container may differ: cm05JUL2024bhav.csv.zip fetched twice on
        # 2026-11-09 gave two archive hashes with byte-identical members (NSE re-zips).
        raw = os.path.join(ROOT, "nse", "data", "eod", "raw")
        held = set(os.listdir(raw)) if os.path.isdir(raw) else set()
        both = sorted(held & set(r["file_name"] for r in self.archives))
        self.assertTrue(both)
        for name in both:
            a, b = bc.load(os.path.join(raw, name)), bc.load(os.path.join(SAMPLES, name))
            self.assertEqual(a.source.member_sha256, b.source.member_sha256, name)
        # the UDiFF copies of overlap dates are evidence only: never in the research set (ED-20)
        for d in OVERLAP_DATES:
            self.assertNotIn(bc.official_name(d, bc.FORMAT_UDIFF), held, d)


if __name__ == "__main__":
    unittest.main()
