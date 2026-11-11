"""IndexInclExcl.xls is a company-name change log, not a Nifty 100 baseline.

The RK date check is synthetic. The workbook check runs only when the local file
cited in the evidence register is present.
"""

import datetime
import os
import unittest

from _load import ROOT, require_local
from nse.research.index_incl_excl import _excel_date, _rk, inspect

XLS = os.path.join(ROOT, "nse", "data", "universe", "evidence", "baseline", "IndexInclExcl.xls")
RECORDED_SHA = "8869bb7c4df67403131a494a8cc65509e80828f9438bc150b506cdbf55378046"


class RkDates(unittest.TestCase):
    def test_rk_values_from_the_workbook_are_june_and_july_2020(self):
        self.assertEqual(_excel_date(_rk(1088781568)), datetime.date(2020, 6, 26))
        self.assertEqual(_excel_date(_rk(1088782688)), datetime.date(2020, 7, 31))


class Workbook(unittest.TestCase):
    def test_nifty100_sheet_is_not_a_baseline(self):
        require_local(os.path.isfile(XLS), "IndexInclExcl.xls")
        got = inspect(XLS)
        self.assertEqual(got["sha256"], RECORDED_SHA)
        self.assertIn("Nifty 100", got["sheets"])
        self.assertEqual(got["header"], ["Index Name", "Event Date", "Scrip Name", "Description"])
        self.assertEqual(got["isin_cells"], 0)
        self.assertGreater(got["nifty100_rows"], 0)
        self.assertEqual((got["inclusions"], got["exclusions"]), (168, 168))
        self.assertEqual(got["earliest_event"], "2003-03-19")
        self.assertEqual(got["latest_event"], "2020-07-31")
        self.assertTrue(all(row["index_name"] == "Nifty 100" for row in got["rows"]))
        self.assertFalse(got["baseline_established"])
        text = " ".join(got["reasons"])
        self.assertIn("no ISIN", text)
        self.assertIn("not an opening list", text)
        self.assertTrue(any("Ltd" in row["scrip_name"] for row in got["rows"]))
        self.assertNotIn("INE", " ".join(row["scrip_name"] for row in got["rows"]))
