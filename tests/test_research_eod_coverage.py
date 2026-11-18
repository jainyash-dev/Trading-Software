"""EOD coverage report (nse/research/eod_coverage.py) over copies of the real local files and
two hand-made files (a non-bhavcopy file and a header-only UDiFF-like file, labelled
SYNTHETIC). No assertion pins how much real data is held, so adding files cannot break it."""

import datetime
import os
import shutil
import tempfile
import unittest

from _load import ROOT
from nse.research import acquisition, eod_coverage as cov

RAW = os.path.join(ROOT, "nse", "data", "eod", "raw")
MANIFEST = os.path.join(ROOT, "nse", "data", "eod", "manifest.csv")
CALENDAR = os.path.join(ROOT, "nse", "data", "calendar")
D = datetime.date


class Coverage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        for name in ("cm03JAN2022bhav.csv", "cm03JAN2022bhav.csv.zip", "cm04JAN2022bhav.csv.zip",
                     "cm06JAN2022bhav.csv.zip"):
            shutil.copy(os.path.join(RAW, name), self.tmp)
        with open(os.path.join(self.tmp, "notes.txt"), "w") as fh:
            fh.write("SYNTHETIC: not a bhavcopy\n")
        with open(os.path.join(self.tmp, "udiff_like.csv"), "w") as fh:
            fh.write("TradDt,BizDt,Sgmt\n")                 # SYNTHETIC header stub, not an NSE file

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_each_file_gets_its_own_verdict(self):
        rep = cov.coverage(self.tmp, MANIFEST, CALENDAR, D(2022, 1, 3), D(2022, 1, 7), ["INFY"])
        status = {f["file"]: (f["format"], f["status"]) for f in rep["files"]}
        self.assertEqual(status["notes.txt"], (acquisition.UNKNOWN, "NOT_LOADED"))
        # ED-20 (specification correction): UDiFF is verified, so a UDiFF-like file now goes
        # through the strict loader, which refuses this stub (no official name, no rows)
        self.assertEqual(status["udiff_like.csv"], (acquisition.UDIFF_BHAVCOPY, "REFUSED"))
        self.assertEqual(status["cm04JAN2022bhav.csv.zip"], (acquisition.LEGACY_BHAVCOPY, "LOADED"))
        self.assertEqual(rep["udiff"]["files"], ["udiff_like.csv"])
        loaded = [f for f in rep["files"] if f["status"] == "LOADED"]
        self.assertTrue(all(f["eq_rows"] > 0 and f["isin_missing_eq_rows"] == 0 for f in loaded))

    def test_file_states_are_distinct_and_cumulative(self):
        rep = cov.coverage(self.tmp, MANIFEST, CALENDAR, D(2022, 1, 3), D(2022, 1, 7))
        state = {f["file"]: f["state"] for f in rep["files"]}
        self.assertEqual(state["notes.txt"], cov.DOWNLOADED)
        self.assertEqual(state["udiff_like.csv"], cov.DOWNLOADED)
        self.assertEqual(state["cm04JAN2022bhav.csv.zip"], cov.ACCEPTED)
        # 3 Jan is supplied twice with identical bytes (zip and its member): the archive is
        # accepted once, the standalone copy stays validated and is not a blocker
        self.assertEqual((state["cm03JAN2022bhav.csv"], state["cm03JAN2022bhav.csv.zip"]),
                         (cov.VALIDATED, cov.ACCEPTED))
        by = rep["counts"]["by_state"]
        self.assertEqual((by[cov.DOWNLOADED], by[cov.PARSED], by[cov.VALIDATED], by[cov.ACCEPTED]), (6, 4, 4, 3))
        self.assertEqual((rep["calendar"]["accepted"], rep["calendar"]["coverage_pct"]), (3, 60.0))
        self.assertEqual(rep["eod_ready"]["standalone_copies_of_accepted_archives"], ["cm03JAN2022bhav.csv"])

    def test_a_conflicting_duplicate_blocks_its_date(self):
        with open(os.path.join(self.tmp, "cm03JAN2022bhav.csv.zip"), "ab") as fh:
            fh.write(b"x")                                    # the archive is refused; the CSV copy loads
        rep = cov.coverage(self.tmp, MANIFEST, CALENDAR, D(2022, 1, 3), D(2022, 1, 7))
        state = {f["file"]: f["state"] for f in rep["files"]}
        self.assertNotEqual(state["cm03JAN2022bhav.csv.zip"], cov.ACCEPTED)
        self.assertNotEqual(state["cm03JAN2022bhav.csv"], cov.ACCEPTED)
        self.assertTrue(any("conflicting or refused duplicate" in b for b in rep["eod_ready"]["blockers"]))

    def test_a_parsed_file_without_matching_provenance_is_not_validated(self):
        with open(os.path.join(self.tmp, "cm04JAN2022bhav.csv.zip"), "rb") as fh:
            data = fh.read()
        other = os.path.join(self.tmp, "manifest.csv")              # a manifest that does not list the file
        with open(MANIFEST) as src, open(other, "w") as dst:
            dst.write("".join(l for l in src if "cm04JAN2022" not in l))
        rep = cov.coverage(self.tmp, other, CALENDAR, D(2022, 1, 3), D(2022, 1, 7))
        [f] = [f for f in rep["files"] if f["file"] == "cm04JAN2022bhav.csv.zip"]
        self.assertEqual((f["status"], f["state"]), ("REFUSED_PROVENANCE", cov.PARSED))
        self.assertTrue(data)

    def test_eod_ready_and_dataset_identity(self):
        rep = cov.coverage(self.tmp, MANIFEST, CALENDAR, D(2022, 1, 3), D(2022, 1, 7))
        self.assertFalse(rep["eod_ready"]["ready"])
        self.assertFalse(rep["data_ready"]["ready"])          # never claimed by an EOD report (owner 2026-11-09)
        self.assertTrue(any("2 calendar trading days without a file" in b for b in rep["eod_ready"]["blockers"]))
        again = cov.coverage(self.tmp, MANIFEST, CALENDAR, D(2022, 1, 3), D(2022, 1, 7))
        self.assertEqual(rep["dataset"]["dataset_id"], again["dataset"]["dataset_id"])     # reproducible
        os.remove(os.path.join(self.tmp, "cm06JAN2022bhav.csv.zip"))
        fewer = cov.coverage(self.tmp, MANIFEST, CALENDAR, D(2022, 1, 3), D(2022, 1, 7))
        self.assertNotEqual(rep["dataset"]["dataset_id"], fewer["dataset"]["dataset_id"])
        self.assertEqual(rep["dataset"]["source_selection"]["legacy_last_trade_date"], "2024-07-05")
        self.assertTrue(rep["known_limitations"])

    def test_a_zip_and_its_member_are_an_identical_duplicate(self):
        rep = cov.coverage(self.tmp, MANIFEST, CALENDAR, D(2022, 1, 3), D(2022, 1, 7))
        self.assertEqual(rep["duplicates"], [{"trade_date": "2022-01-03", "kind": "IDENTICAL_CONTENT",
                                              "files": ["cm03JAN2022bhav.csv", "cm03JAN2022bhav.csv.zip"]}])
        self.assertEqual(rep["dates"]["distinct_trade_dates"], 3)

    def test_a_calendar_trading_day_without_a_file_is_missing_not_a_holiday(self):
        rep = cov.coverage(self.tmp, MANIFEST, CALENDAR, D(2022, 1, 3), D(2022, 1, 7))
        self.assertEqual(rep["calendar"]["missing"]["count"], 2)              # 5 and 7 Jan 2022
        self.assertEqual(rep["calendar"]["trading_days_in_window"], 5)

    def test_without_a_calendar_nothing_is_called_missing(self):
        rep = cov.coverage(self.tmp, MANIFEST, None, D(2022, 1, 3), D(2022, 1, 7))
        self.assertEqual(rep["calendar"]["status"], "UNAVAILABLE")
        self.assertNotIn("missing", rep["calendar"])

    def test_a_tampered_file_is_refused_on_provenance_and_others_still_load(self):
        with open(os.path.join(self.tmp, "cm04JAN2022bhav.csv.zip"), "ab") as fh:
            fh.write(b"x")
        rep = cov.coverage(self.tmp, MANIFEST, CALENDAR, D(2022, 1, 3), D(2022, 1, 7))
        status = {f["file"]: f["status"] for f in rep["files"]}
        self.assertNotEqual(status["cm04JAN2022bhav.csv.zip"], "LOADED")
        self.assertEqual(status["cm06JAN2022bhav.csv.zip"], "LOADED")
        self.assertEqual(rep["calendar"]["missing"]["count"], 3)              # 4 Jan is no longer held


    def test_a_refused_file_for_a_held_date_is_reported(self):
        # QA 2026-11-08: the zip of 3 Jan is tampered (refused), its extracted CSV still loads
        with open(os.path.join(self.tmp, "cm03JAN2022bhav.csv.zip"), "ab") as fh:
            fh.write(b"x")
        rep = cov.coverage(self.tmp, MANIFEST, CALENDAR, D(2022, 1, 3), D(2022, 1, 7))
        self.assertIn({"trade_date": "2022-01-03", "kind": "ONE_REFUSED",
                       "files": ["cm03JAN2022bhav.csv", "cm03JAN2022bhav.csv.zip"]}, rep["duplicates"])

    def test_a_date_the_calendar_cannot_classify_is_never_called_non_trading(self):
        # QA 2026-11-08: the tables cover 2021-2025; a held file dated in 2020 (here simulated by
        # a fake calendar that raises) is unclassifiable, not a file on a non-trading day
        from unittest import mock
        from nse.research.deps import calendar as cal_mod

        class Uncovered(object):
            covered_years = []

            def is_trading_day(self, d):
                raise cal_mod.CalendarCoverageError("not covered (SYNTHETIC)")

            is_excluded_session = session_type = is_trading_day

        with mock.patch.object(cal_mod.NseCalendar, "load", return_value=Uncovered()):
            rep = cov.coverage(self.tmp, MANIFEST, "ANY", D(2022, 1, 1), D(2022, 1, 9))
        self.assertEqual(rep["calendar"]["files_on_non_trading_days"], [])
        self.assertEqual(rep["calendar"]["files_on_unclassifiable_dates"], ["2022-01-03", "2022-01-04", "2022-01-06"])


class RealHoldings(unittest.TestCase):
    def test_every_held_file_loads_and_every_duplicate_is_identical(self):
        rep = cov.coverage(RAW, MANIFEST, CALENDAR, D(2022, 1, 1), D(2023, 12, 31), ["INFY"])
        self.assertEqual(rep["counts"]["loaded"], rep["counts"]["files"])
        self.assertTrue(all(d["kind"] == "IDENTICAL_CONTENT" for d in rep["duplicates"]))
        self.assertEqual(rep["calendar"]["unresolved_dates"], [])
        held = rep["calendar"]["held"]
        self.assertEqual(rep["calendar"]["missing"]["count"], rep["calendar"]["trading_days_in_window"] - held)


if __name__ == "__main__":
    unittest.main()
