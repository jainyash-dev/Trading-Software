"""nse/eod tests. Two kinds of input:

- SYNTHETIC files built here from the verified legacy header (nse/docs/EOD_FORMAT_EVIDENCE.md
  section 5). Their rows are invented test values, not market data.
- The two REAL samples in nse/data/eod/raw/ (local, ignored by git). Those tests run only
  when the files are present and are skipped otherwise; nothing stands in for them.
"""

import csv
import datetime
import hashlib
import io
import os
import shutil
import tempfile
import unittest
import zipfile
from decimal import Decimal

from _load import ROOT, load, require_local

bc = load(os.path.join("nse", "eod"), "nse_bhavcopy")
D = datetime.date

HEADER = "SYMBOL,SERIES,OPEN,HIGH,LOW,CLOSE,LAST,PREVCLOSE,TOTTRDQTY,TOTTRDVAL,TIMESTAMP,TOTALTRADES,ISIN,"
GOOD = {"SYMBOL": "AAAA", "SERIES": "EQ", "OPEN": "100.5", "HIGH": "104", "LOW": "99.25",
        "CLOSE": "103.1", "LAST": "103", "PREVCLOSE": "100", "TOTTRDQTY": "1500",
        "TOTTRDVAL": "153000.75", "TIMESTAMP": "03-JAN-2022", "TOTALTRADES": "42",
        "ISIN": "INE000A01019"}
NAME = "cm03JAN2022bhav.csv"


def line(**over):
    v = dict(GOOD, **over)
    return ",".join(v[c] for c in bc.LEGACY_HEADER[:-1]) + ","


def text(*rows):
    return HEADER + "\n" + "".join(r + "\n" for r in rows)


class Tmp(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="nse-bhav-test-")
        self.addCleanup(shutil.rmtree, self.dir, True)

    def write(self, data, name=NAME):
        path = os.path.join(self.dir, name)
        with open(path, "wb") as fh:
            fh.write(data.encode("ascii") if isinstance(data, str) else data)
        return path

    def archive(self, members, name=NAME + ".zip"):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for member, data in members:
                z.writestr(member, data)
        return self.write(buf.getvalue(), name)

    def refuse(self, error, data, name=NAME):
        with self.assertRaises(error):
            bc.load(self.write(data, name))


class ValidFile(Tmp):
    def test_field_mapping_and_exact_values(self):
        f = bc.load(self.write(text(line(), line(SYMBOL="BBBB", SERIES="BE", ISIN="INE000B01017"))))
        r = f.rows[0]
        self.assertEqual((r.symbol, r.series, r.trade_date, r.isin, r.line), ("AAAA", "EQ", D(2022, 1, 3), "INE000A01019", 2))
        self.assertEqual((r.open, r.high, r.low, r.close, r.last, r.prev_close, r.traded_value),
                         (Decimal("100.5"), Decimal("104"), Decimal("99.25"), Decimal("103.1"),
                          Decimal("103"), Decimal("100"), Decimal("153000.75")))
        self.assertEqual((r.traded_qty, r.total_trades), (1500, 42))
        self.assertIsInstance(r.close, Decimal)                          # never float
        self.assertEqual((f.trade_date, f.format, f.loader_version, f.price_adjustment, f.provenance),
                         (D(2022, 1, 3), "NSE_CM_BHAVCOPY_LEGACY", bc.LOADER_VERSION, "NONE", None))

    def test_trailing_empty_column_is_required_and_must_stay_empty(self):
        self.assertEqual(bc.LEGACY_HEADER[-1], "")
        self.assertEqual(len(bc.load(self.write(text(line()))).rows), 1)
        self.refuse(bc.MalformedFileError, text(line() + "x"))          # 14th column not empty
        self.refuse(bc.MalformedFileError, text(line()[:-1]))           # 13 fields

    def test_source_identity_and_hash(self):
        data = text(line())
        f = bc.load(self.write(data))
        self.assertEqual(f.source, bc.SourceInfo(NAME, "CSV", len(data), hashlib.sha256(data.encode()).hexdigest(),
                                                 None, None, None))


class Archives(Tmp):
    def test_single_member_archive_records_both_hashes(self):
        data = text(line())
        path = self.archive([(NAME, data)])
        f = bc.load(path)
        with open(path, "rb") as fh:
            raw = fh.read()
        self.assertEqual((f.source.kind, f.source.sha256, f.source.size_bytes), ("ARCHIVE", hashlib.sha256(raw).hexdigest(), len(raw)))
        self.assertEqual((f.source.member_name, f.source.member_size_bytes, f.source.member_sha256),
                         (NAME, len(data), hashlib.sha256(data.encode()).hexdigest()))

    def test_unexpected_archive_layouts_are_refused(self):
        for members in ([(NAME, text(line())), ("extra.csv", "x")],      # two members
                        [("other.csv", text(line()))],                  # wrong member name
                        [("dir/" + NAME, text(line()))],                # nested path
                        []):                                            # empty archive
            with self.subTest(members=[m for m, _ in members]):
                with self.assertRaises(bc.UnsupportedFormatError):
                    bc.load(self.archive(members))

    def test_corrupt_archive_is_refused(self):
        self.refuse(bc.MalformedFileError, b"PK\x03\x04 not really a zip", NAME + ".zip")
        with open(self.archive([(NAME, text(line()))]), "rb") as fh:
            good = bytearray(fh.read())
        good[40] ^= 0xFF                                                # damage the compressed data
        self.refuse(bc.MalformedFileError, bytes(good), NAME + ".zip")


class UnsupportedFormats(Tmp):
    def test_headers_that_are_not_the_verified_legacy_header(self):
        for header in (HEADER[:-1],                                      # no trailing column
                       HEADER.replace("OPEN,HIGH", "HIGH,OPEN"),         # reordered
                       HEADER.lower(),                                   # renamed
                       "A,B,C,D,E,F,G,H,I,J,K,L,M,"):                    # e.g. another layout
            with self.subTest(header=header):
                self.refuse(bc.UnsupportedFormatError, header + "\n" + line() + "\n")

    def test_encoding_line_endings_and_quotes_outside_the_evidence(self):
        self.refuse(bc.UnsupportedFormatError, b"\xef\xbb\xbf" + text(line()).encode())
        self.refuse(bc.UnsupportedFormatError, text(line()).replace("\n", "\r\n"))
        self.refuse(bc.UnsupportedFormatError, HEADER + "\n" + line() + "\r\n")   # CR in a data row only
        self.refuse(bc.UnsupportedFormatError, text(line(SYMBOL="\xc4AAA")).encode("latin-1"))
        self.refuse(bc.UnsupportedFormatError, text(line(SYMBOL='"AAAA"')))

    def test_file_names_outside_the_legacy_pattern(self):
        for name in ("bhavcopy.csv", "cm3JAN2022bhav.csv", "cm03jan2022bhav.csv", "cm03XYZ2022bhav.csv",
                     "cm31FEB2022bhav.csv", "BhavCopy_NSE_CM_0_0_0_20240708_F_0000.csv"):
            with self.subTest(name=name):
                self.refuse(bc.UnsupportedFormatError, text(line()), name)


class MalformedFiles(Tmp):
    def test_empty_header_only_and_truncated(self):
        self.refuse(bc.MalformedFileError, b"")
        self.refuse(bc.MalformedFileError, HEADER + "\n")
        self.refuse(bc.MalformedFileError, text(line())[:-1])            # no final newline
        self.refuse(bc.MalformedFileError, text(line(), "", line(SYMBOL="BBBB")))   # blank line

    def test_error_names_the_line(self):
        with self.assertRaisesRegex(bc.MalformedFileError, "line 3"):
            bc.load(self.write(text(line(), line(SYMBOL="BBBB", CLOSE="abc"))))

    def test_symbol_series_and_isin(self):
        for over in ({"SYMBOL": ""}, {"SERIES": ""}, {"SYMBOL": "AA AA"}, {"ISIN": ""},
                     {"ISIN": "US0378331005"}, {"ISIN": "INE000A0101"}):
            with self.subTest(**over):
                self.refuse(bc.MalformedFileError, text(line(**over)))

    def test_dates(self):
        for ts in ("2022-01-03", "03-Jan-2022", "3-JAN-2022", "03-JAN-22", "31-FEB-2022", "",
                   "04-JAN-2022"):                                        # last: differs from the file name
            with self.subTest(ts=ts):
                self.refuse(bc.MalformedFileError, text(line(TIMESTAMP=ts)))

    def test_numbers(self):
        for col in ("OPEN", "HIGH", "LOW", "CLOSE", "LAST", "PREVCLOSE", "TOTTRDVAL"):
            for bad in ("", "-5", "1e3", " 101", "1 001", "abc", "101.", ".5"):
                with self.subTest(col=col, value=bad):
                    self.refuse(bc.MalformedFileError, text(line(**{col: bad})))
        for col in ("TOTTRDQTY", "TOTALTRADES"):
            for bad in ("", "10.5", "-1", "1e3"):
                with self.subTest(col=col, value=bad):
                    self.refuse(bc.MalformedFileError, text(line(**{col: bad})))

    def test_ohlc_consistency_and_positive_prices(self):
        for over in ({"LOW": "101"},                                     # low above open
                     {"HIGH": "103"},                                    # high below close
                     {"LOW": "105", "HIGH": "104"},                      # low above high
                     {"OPEN": "0", "LOW": "0"}):                         # zero price
            with self.subTest(**over):
                self.refuse(bc.MalformedFileError, text(line(**over)))

    def test_no_price_is_filled_in_or_repaired(self):
        f = bc.load(self.write(text(line(), line(SYMBOL="BBBB", ISIN="INE000B01017"))))
        self.assertEqual([r.symbol for r in f.rows], ["AAAA", "BBBB"])   # one row per line, nothing added


class Duplicates(Tmp):
    def test_same_symbol_and_series_twice_in_a_file(self):
        with self.assertRaisesRegex(bc.MalformedFileError, "duplicate AAAA EQ"):
            bc.load(self.write(text(line(), line(CLOSE="102"))))

    def test_same_symbol_in_two_series_is_not_a_duplicate(self):
        self.assertEqual(len(bc.load(self.write(text(line(), line(SERIES="BE")))).rows), 2)

    def test_two_files_for_one_trade_date(self):
        csv_path = self.write(text(line()))
        zip_path = self.archive([(NAME, text(line()))])
        with self.assertRaisesRegex(bc.BhavcopyError, "two files for trade date 2022-01-03"):
            bc.load_many([csv_path, zip_path])

    def test_load_many_orders_by_date(self):
        later = self.write(text(line(TIMESTAMP="04-JAN-2022")), "cm04JAN2022bhav.csv")
        earlier = self.write(text(line()))
        self.assertEqual([f.trade_date for f in bc.load_many([later, earlier])], [D(2022, 1, 3), D(2022, 1, 4)])


class NonEqSeries(Tmp):
    def test_non_eq_rows_are_kept_and_reported(self):
        f = bc.load(self.write(text(line(), line(SERIES="BE"), line(SYMBOL="CCCC", SERIES="BE", ISIN="INE000C01015"),
                                    line(SYMBOL="DDDD", SERIES="GS", ISIN="IN0020010081"))))
        self.assertEqual(len(f.rows), 4)                                 # nothing dropped
        self.assertEqual([r.symbol for r in f.eq_rows], ["AAAA"])
        self.assertEqual(f.series_counts, {"EQ": 1, "BE": 2, "GS": 1})
        self.assertEqual(f.non_eq_series, {"BE": 2, "GS": 1})
        self.assertEqual(f.non_eq_only_symbols, ["CCCC", "DDDD"])        # rows today, but no EQ row


class Provenance(Tmp):
    COLUMNS = bc.MANIFEST_COLUMNS

    def manifest(self, rows):
        path = os.path.join(self.dir, "manifest.csv")
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=self.COLUMNS, lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
        return path

    def record(self, path, kind, name=None, parent="", **over):
        if kind == "ARCHIVE_MEMBER":
            with zipfile.ZipFile(path) as z:
                data = z.read(name)
        else:
            with open(path, "rb") as fh:
                data = fh.read()
        r = {"file_name": name or os.path.basename(path), "kind": kind, "parent_archive": parent,
             "trade_date": "2022-01-03", "size_bytes": str(len(data)), "sha256": hashlib.sha256(data).hexdigest(),
             "source_page": "SYNTHETIC TEST", "downloaded_on": "2026-10-27", "provenance_status": "TEST"}
        r.update(over)
        return r

    def test_matching_records_are_attached(self):
        z = self.archive([(NAME, text(line()))])
        m = self.manifest([self.record(z, "ARCHIVE"), self.record(z, "ARCHIVE_MEMBER", NAME, NAME + ".zip")])
        f = bc.load(z, m)
        self.assertEqual((f.provenance["kind"], f.provenance["source_page"]), ("ARCHIVE", "SYNTHETIC TEST"))
        c = self.write(text(line()))
        f = bc.load(c, self.manifest([self.record(c, "STANDALONE_COPY", parent=NAME + ".zip")]))
        self.assertEqual(f.provenance["kind"], "STANDALONE_COPY")

    def test_mismatches_are_refused(self):
        z = self.archive([(NAME, text(line()))])
        good_archive = self.record(z, "ARCHIVE")
        good_member = self.record(z, "ARCHIVE_MEMBER", NAME, NAME + ".zip")
        cases = {
            "no record": [good_member],
            "archive sha": [dict(good_archive, sha256="0" * 64), good_member],
            "archive size": [dict(good_archive, size_bytes="1"), good_member],
            "member sha": [good_archive, dict(good_member, sha256="0" * 64)],
            "member missing": [good_archive],
            "trade date": [dict(good_archive, trade_date="2022-01-04"), good_member],
            "two records": [good_archive, good_archive, good_member],
        }
        for label, rows in cases.items():
            with self.subTest(label):
                with self.assertRaises(bc.ProvenanceError):
                    bc.load(z, self.manifest(rows))

    def test_manifest_with_another_header_is_refused(self):
        path = os.path.join(self.dir, "manifest.csv")
        with open(path, "w") as fh:
            fh.write("file_name,sha256\n")
        with self.assertRaises(bc.ProvenanceError):
            bc.load(self.write(text(line())), path)


RAW = os.path.join(ROOT, "nse", "data", "eod", "raw")
MANIFEST = os.path.join(ROOT, "nse", "data", "eod", "manifest.csv")
SAMPLES = ("cm03JAN2022bhav.csv.zip", "cm03JAN2022bhav.csv", "cm29DEC2023bhav.csv.zip", "cm29DEC2023bhav.csv")


class RealSamples(unittest.TestCase):
    """Expected values come from nse/docs/EOD_FORMAT_EVIDENCE.md, not from this loader. (Its
    2022-01-03 count of 70 distinct series was corrected from 69 after an independent awk
    count.)"""

    @classmethod
    def setUpClass(cls):
        missing = [s for s in SAMPLES if not os.path.isfile(os.path.join(RAW, s))]
        require_local(not missing, "real NSE samples in nse/data/eod/raw/ (git-ignored): %s" % ", ".join(missing))
    EXPECT = {
        "cm03JAN2022bhav": (D(2022, 1, 3), 2227, 1666, 70, 210,
                            ("1887.75", "1914.05", "1887.75", "1898.45", "1899", "1887.75", 3329616, "6342326137.5", 128107)),
        "cm29DEC2023bhav": (D(2023, 12, 29), 2647, 1799, 81, 300,
                            ("1541.05", "1559.45", "1540", "1542.9", "1542.65", "1562.65", 4388990, "6779338989.4", 218692)),
    }

    def test_samples_load_against_the_manifest(self):
        for stem, (day, rows, eq, n_series, be, infy) in self.EXPECT.items():
            for name in (stem + ".csv.zip", stem + ".csv"):
                with self.subTest(name):
                    f = bc.load(os.path.join(RAW, name), MANIFEST)
                    self.assertEqual((f.trade_date, len(f.rows), len(f.eq_rows), len(f.series_counts), f.series_counts["BE"]),
                                     (day, rows, eq, n_series, be))
                    r = [x for x in f.eq_rows if x.symbol == "INFY"]
                    self.assertEqual(len(r), 1)
                    r = r[0]
                    self.assertEqual((r.isin, str(r.open), str(r.high), str(r.low), str(r.close), str(r.last),
                                      str(r.prev_close), r.traded_qty, str(r.traded_value), r.total_trades),
                                     ("INE009A01021",) + infy)
                    self.assertIn(f.provenance["provenance_status"],
                                  ("USER_CONFIRMED", "USER_CONFIRMED_COPY_OF_ARCHIVE_MEMBER"))

    def test_archive_and_copy_give_identical_rows(self):
        for stem in self.EXPECT:
            z = bc.load(os.path.join(RAW, stem + ".csv.zip"))
            c = bc.load(os.path.join(RAW, stem + ".csv"))
            self.assertEqual(z.rows, c.rows)
            self.assertEqual(z.source.member_sha256, c.source.sha256)

    def test_both_dates_together_and_no_double_loading(self):
        files = bc.load_many([os.path.join(RAW, "cm29DEC2023bhav.csv.zip"), os.path.join(RAW, "cm03JAN2022bhav.csv.zip")], MANIFEST)
        self.assertEqual([f.trade_date for f in files], [D(2022, 1, 3), D(2023, 12, 29)])
        with self.assertRaises(bc.BhavcopyError):
            bc.load_many([os.path.join(RAW, "cm03JAN2022bhav.csv.zip"), os.path.join(RAW, "cm03JAN2022bhav.csv")])


if __name__ == "__main__":
    unittest.main()
