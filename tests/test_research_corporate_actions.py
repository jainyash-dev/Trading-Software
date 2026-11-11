"""Corporate-action coverage. An empty API list is not proof that nothing happened.

The window check uses SYNTHETIC files. The ledger check runs only when the local
raw responses are present.
"""

import csv
import datetime
import hashlib
import os
import tempfile
import unittest

from _load import ROOT, require_local
from nse.research import corporate_actions as ca, models as m

RAW = os.path.join(ROOT, "nse", "data", "corporate_actions", "raw")
COVERAGE = os.path.join(ROOT, "nse", "data", "corporate_actions", "coverage.csv")


class ResponseStatus(unittest.TestCase):
    def test_empty_list_is_not_proof_of_no_events(self):
        self.assertEqual(ca.response_status("[]"), ca.EMPTY_RESPONSE)
        self.assertEqual(ca.response_status("[]\n"), ca.EMPTY_RESPONSE)
        self.assertEqual(ca.response_status(None), ca.MISSING_COVERAGE)
        self.assertNotEqual(ca.response_status("[]"), "COVERED_NO_EVENTS_PROVED")

    def test_a_parsed_event_is_not_an_adjustment_and_an_unparsed_event_stays_unparsed(self):
        self.assertEqual(ca.response_status('[{"subject":"Split"}]', parsed_price_events=1),
                         ca.COVERED_WITH_VERIFIED_EVENTS)
        self.assertEqual(ca.response_status('[{"subject":"Scheme"}]', unparsed_price_events=1),
                         ca.UNPARSED_EVENT)
        self.assertEqual(ca.response_status('[{"subject":"AGM"}]'),
                         ca.RESPONSE_PRESENT_COMPLETENESS_NOT_PROVED)


class EmptyWindow(unittest.TestCase):
    def test_a_hash_matched_empty_list_does_not_cover_a_date(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(folder))
        body = b"[]"
        raw = os.path.join(folder, "ca_SRTRANSFIN.json")
        with open(raw, "wb") as fh:
            fh.write(body)
        digest = hashlib.sha256(body).hexdigest()
        path = os.path.join(folder, "coverage.csv")
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=ca.COVERAGE_COLUMNS, lineterminator="\n")
            writer.writeheader()
            writer.writerow({
                "symbol": "SRTRANSFIN", "from_date": "2016-01-01", "to_date": "2025-12-31",
                "source_file": "ca_SRTRANSFIN.json", "source_sha256": digest, "rows": "0",
                "retrieved_on": "2026-11-10", "notes": "SYNTHETIC empty list",
            })
        self.assertTrue(m.source_verified(path, "NSE corporate actions", "ca_SRTRANSFIN.json", digest))
        loaded = ca.load_coverage(path)
        self.assertNotIn("SRTRANSFIN", loaded)
        self.assertFalse(ca.covered(loaded, "SRTRANSFIN", datetime.date(2020, 1, 1), datetime.date(2020, 1, 2)))


class HeldResponses(unittest.TestCase):
    def test_empty_saved_responses_are_not_coverage_rows(self):
        require_local(os.path.isfile(COVERAGE) and os.path.isdir(RAW), "corporate-action raw responses")
        empty_names = []
        for name in os.listdir(RAW):
            if not name.endswith(".json"):
                continue
            path = os.path.join(RAW, name)
            with open(path, encoding="utf-8") as fh:
                if ca.empty_api_body(fh.read()):
                    empty_names.append(name)
        self.assertIn("ca_SRTRANSFIN_2016_2025.json", empty_names)
        register = os.path.join(os.path.dirname(__file__), "..", "docs", "product-discovery", "p0",
                                "P0_EMPTY_CA_RESPONSES.csv")
        with open(register, newline="", encoding="utf-8") as fh:
            recorded = list(csv.DictReader(fh))
        self.assertEqual(sorted(r["file"] for r in recorded), sorted(empty_names))
        self.assertTrue(all(r["status"] == ca.EMPTY_RESPONSE for r in recorded))
        loaded = ca.load_coverage(COVERAGE)
        self.assertNotIn("SRTRANSFIN", loaded)
        with open(COVERAGE, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                path = os.path.join(os.path.dirname(COVERAGE), row["source_file"])
                if not os.path.isfile(path):
                    continue
                with open(path, encoding="utf-8") as body:
                    self.assertFalse(ca.empty_api_body(body.read()), row["symbol"])

    def test_the_ten_unparsed_subjects_do_not_become_ratios(self):
        subjects = (
            "Scheme Of Arrangement",
            "Scheme Of Arangement- Bonus - 1 Debenture For 1 Equity Share Held",
            "Annual General Meeting/Dividend - Rs 2.50 Per Share/Bonus 1:10 (Revised)",
            "Rights - 4:25 Fully Paid Up Shares @ Premium Rs 500/- Per Share / 2:25 Partly Paid Up Shares @ Premium Rs 605/- Per Share",
            "Scheme Of Arrangement - Bonus Ncrps 4:1",
            "Face Value Split (Sub-Division) - From Rs 5/- Per Share To Rs 2/- Per Share",
        )
        for subject in subjects:
            self.assertIsNone(ca._subject_rows(subject), subject)
