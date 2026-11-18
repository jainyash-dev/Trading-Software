"""Instrument search identity behaviour (Phase 01, T-014).

Synthetic fixture files only: these tests pin the search contract, they do not
validate the repository's identity data.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

PLATFORM = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLATFORM))
sys.path.append(str(PLATFORM.parent))

from gtf_platform.integration import reference  # noqa: E402
from test_platform_api import settings  # noqa: E402

# NSE's EQUITY_L.csv puts a space after each comma in the header.
EQUITY_L = (
    "SYMBOL,NAME OF COMPANY, SERIES, DATE OF LISTING, PAID UP VALUE, MARKET LOT, ISIN NUMBER, FACE VALUE\n"
    "AAA,Alpha Finance Limited,EQ,01-APR-2003,1,1,INE000A01032,1\n"
    "BBB,Beta Industries Limited,EQ,01-APR-2003,2,1,INE000B01011,2\n"
)
RECORDS = (
    "record_type,symbol,new_symbol,isin,series,effective_from,effective_to,source,source_file,"
    "source_sha256,recorded_on,notes\n"
    "LISTING,AAA,,INE000A01016,EQ,2016-01-01,,s,f,h,2026-11-10,\n"
    "LISTING,AAA,,INE000A01024,EQ,2016-09-09,,s,f,h,2026-11-10,\n"
    "ISIN_CHANGE,AAA,,INE000A01032,EQ,2025-06-16,,s,f,h,2026-11-10,\n"
    "LISTING,OLDB,,INE000B01011,EQ,2010-01-01,,s,f,h,2026-11-10,\n"
    "SYMBOL_CHANGE,OLDB,BBB,INE000B01011,EQ,2015-01-01,,s,f,h,2026-11-10,\n"
)


class InstrumentSearch(unittest.TestCase):
    def setUp(self):
        reference._CACHE.clear()
        self.tmp = tempfile.TemporaryDirectory()
        tmp = Path(self.tmp.name)
        (tmp / "EQUITY_L.csv").write_text(EQUITY_L, encoding="utf-8")
        (tmp / "records.csv").write_text(RECORDS, encoding="utf-8")
        self.settings = settings(tmp, equity_names_path=tmp / "EQUITY_L.csv", instruments_path=tmp / "records.csv")

    def tearDown(self):
        reference._CACHE.clear()
        self.tmp.cleanup()

    def search(self, query):
        return [(r["symbol"], r["isin"]) for r in reference.search_instruments(self.settings, query)]

    def test_names_file_isin_is_read_despite_spaced_header(self):
        self.assertEqual(self.search("Alpha Finance"), [("AAA", "INE000A01032")])

    def test_current_isin_finds_the_current_symbol(self):
        self.assertEqual(self.search("INE000A01032"), [("AAA", "INE000A01032")])

    def test_each_historical_isin_is_searchable(self):
        self.assertEqual(self.search("INE000A01016"), [("AAA", "INE000A01016")])
        self.assertEqual(self.search("INE000A01024"), [("AAA", "INE000A01024")])

    def test_isins_of_one_symbol_are_listed_separately_never_merged(self):
        self.assertEqual(
            self.search("AAA"),
            [("AAA", "INE000A01032"), ("AAA", "INE000A01016"), ("AAA", "INE000A01024")],
        )

    def test_historical_symbol_is_found_under_its_own_name(self):
        self.assertEqual(self.search("OLDB"), [("OLDB", "INE000B01011")])

    def test_no_match_returns_nothing(self):
        self.assertEqual(self.search("ZZZNOTHING"), [])
        self.assertEqual(self.search("   "), [])

    def test_without_a_verified_universe_every_result_is_unverified(self):
        rows = reference.search_instruments(self.settings, "AAA")
        self.assertTrue(rows)
        for row in rows:
            self.assertFalse(row["verified"])
            self.assertEqual(row["verification"], "UNVERIFIED")

    def test_verification_is_per_isin_not_per_symbol(self):
        universe = SimpleNamespace(rows=[SimpleNamespace(symbol="AAA", isin="INE000A01032", verified=True)])
        with mock.patch.object(reference, "_universe", return_value=universe):
            rows = {(r["symbol"], r["isin"]): r["verified"] for r in reference.search_instruments(self.settings, "AAA")}
        self.assertEqual(
            rows,
            {("AAA", "INE000A01032"): True, ("AAA", "INE000A01016"): False, ("AAA", "INE000A01024"): False},
        )


if __name__ == "__main__":
    unittest.main()
