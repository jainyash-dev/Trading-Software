"""Offline EOD acquisition (nse/research/acquisition.py): D31 local files only, the two
verified formats with source selection by date (ED-20), provenance from the owner. Every archive built here is SYNTHETIC (symbol
SYNTHETIC, made-up prices) and lives in a tempfile.mkdtemp() folder; the real
nse/data folders are only ever read (one guarded test copies a real archive OUT of them)."""

import argparse
import datetime
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout, redirect_stderr

sys.dont_write_bytecode = True
from _load import ROOT, require_local  # noqa: E402
sys.path.insert(0, ROOT)
from nse.research import acquisition as acq  # noqa: E402
from nse.research.deps import bhavcopy as bc, calendar as cal_mod  # noqa: E402

D = datetime.date
MON = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
PROV = ("SYNTHETIC TEST PAGE", "2026-11-02", "TEST_ONLY")
UDIFF_HEADER = "TradDt,BizDt,Sgmt,Src,FinInstrmTp,FinInstrmId,ISIN,TckrSymb,SctySrs\n"  # SYNTHETIC header


def legacy_body(d, close="10.5"):
    """SYNTHETIC legacy bhavcopy CSV for date d (header from nse_bhavcopy.LEGACY_HEADER)."""
    ts = "%02d-%s-%04d" % (d.day, MON[d.month - 1], d.year)
    return (",".join(bc.LEGACY_HEADER) + "\n"
            + "SYNTHETIC,EQ,10,11,9,%s,10.5,10,1000,10000,%s,10,INE000A01019,\n" % (close, ts))


def udiff_body(d, close="10.50"):
    """SYNTHETIC UDiFF CSV for date d (columns from nse_bhavcopy.UDIFF_COLUMNS, schema UDIFF_2024B)."""
    v = dict.fromkeys(bc.UDIFF_COLUMNS, "")
    v.update(TradDt=d.isoformat(), BizDt=d.isoformat(), Sgmt="CM", Src="NSE", FinInstrmTp="STK", FinInstrmId="1",
             ISIN="INE000A01019", TckrSymb="SYNTHETIC", SctySrs="EQ", FinInstrmNm="SYNTHETIC LTD", OpnPric="10.00",
             HghPric="11.00", LwPric="9.00", ClsPric=close, LastPric="10.50", PrvsClsgPric="10.00", SttlmPric=close,
             TtlTradgVol="1000", TtlTrfVal="10000.00", TtlNbOfTxsExctd="10", SsnId="F1", NewBrdLotQty="1")
    return ",".join(bc.UDIFF_COLUMNS) + "\n" + ",".join(v[c] for c in bc.UDIFF_COLUMNS) + "\n"


def make_zip(folder, d, body=None, name=None, member=None):
    name = name or acq.legacy_name(d)
    path = os.path.join(folder, name)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(member or name[:-len(".zip")], body if body is not None else legacy_body(d))
    return path


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


class _Tmp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.inbox = os.path.join(self.tmp, "inbox")
        self.raw = os.path.join(self.tmp, "raw")
        self.quar = os.path.join(self.tmp, "quarantine")
        self.ledger = os.path.join(self.tmp, "ledger.jsonl")
        self.manifest = os.path.join(self.tmp, "manifest.csv")
        os.makedirs(self.inbox)
        with open(self.manifest, "w") as fh:
            fh.write(",".join(bc.MANIFEST_COLUMNS) + "\n")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def ingest(self, paths, recorded_at="T1"):
        return acq.ingest(paths, self.raw, self.manifest, self.quar, self.ledger, *PROV, recorded_at=recorded_at)

    def manifest_rows(self):
        return bc.read_manifest(self.manifest)


class FormatDetection(_Tmp):
    """Format triage is a label only; acceptance is the strict parse of the file's own format."""

    def test_legacy_udiff_and_garbage(self):
        self.assertEqual(acq.detect_format(make_zip(self.inbox, D(2024, 1, 8))), acq.LEGACY_BHAVCOPY)
        udiff = make_zip(self.inbox, None, UDIFF_HEADER, name="BhavCopy_NSE_CM_0_0_0_20240108_F_0000.csv.zip",
                         member="BhavCopy_NSE_CM_0_0_0_20240108_F_0000.csv")
        self.assertEqual(acq.detect_format(udiff), acq.UDIFF_UNVERIFIED)
        junk = os.path.join(self.inbox, "junk.csv.zip")
        with open(junk, "wb") as fh:
            fh.write(b"\x00\x01 not a zip, not a header")
        self.assertEqual(acq.detect_format(junk), acq.UNKNOWN)
        empty_zip = os.path.join(self.inbox, "two.zip")
        with zipfile.ZipFile(empty_zip, "w") as z:            # two members: not the legacy layout
            z.writestr("a.csv", legacy_body(D(2024, 1, 8)))
            z.writestr("b.csv", legacy_body(D(2024, 1, 8)))
        self.assertEqual(acq.detect_format(empty_zip), acq.UNKNOWN)
        self.assertEqual(acq.detect_format(os.path.join(self.inbox, "absent.zip")), acq.UNKNOWN)

    def test_udiff_content_under_a_legacy_name_is_refused_by_the_strict_parse(self):
        # ED-20 (specification correction): UDiFF is now a verified format, but the file name
        # fixes which parser applies; a UDiFF body under a legacy name fails it and is never ingested
        d = D(2024, 1, 8)
        p = make_zip(self.inbox, d, UDIFF_HEADER)                # legacy file name, UDiFF content
        [r] = self.ingest([p])
        self.assertEqual((r["outcome"], r["reason"], r["format"]),
                         (acq.QUARANTINED, acq.PARSE_FAILED, acq.UDIFF_BHAVCOPY))
        self.assertIn("UnsupportedFormatError", r["detail"])
        self.assertEqual(self.manifest_rows(), [])
        self.assertFalse(os.path.exists(os.path.join(self.raw, acq.legacy_name(d))))
        self.assertTrue(os.path.isfile(r["quarantine_path"]))
        with open(r["quarantine_path"] + ".reason.json") as fh:
            self.assertEqual(json.load(fh)["reason"], acq.PARSE_FAILED)

    def test_garbage_is_quarantined_as_unknown(self):
        p = os.path.join(self.inbox, "cm08JAN2024bhav.csv.zip")
        with open(p, "wb") as fh:
            fh.write(b"garbage")
        [r] = self.ingest([p])
        self.assertEqual((r["outcome"], r["reason"]), (acq.QUARANTINED, acq.FORMAT_UNKNOWN))
        self.assertEqual(self.manifest_rows(), [])


class SourceSelection(_Tmp):
    """ED-20 (NSE/MSD/62424): legacy up to 2024-07-05, UDiFF from 2024-07-08. SYNTHETIC files."""
    LAST_LEGACY, FIRST_UDIFF = D(2024, 7, 5), D(2024, 7, 8)

    def udiff_zip(self, d, body=None):
        return make_zip(self.inbox, d, body if body is not None else udiff_body(d), name=bc.official_name(d, bc.FORMAT_UDIFF))

    def test_udiff_after_the_switch_is_ingested_and_loads_against_its_manifest(self):
        p = self.udiff_zip(self.FIRST_UDIFF)
        [r] = self.ingest([p])
        self.assertEqual((r["outcome"], r["format"], r["schema_version"]), (acq.INGESTED, acq.UDIFF_BHAVCOPY, "UDIFF_2024B"))
        self.assertEqual([x["kind"] for x in self.manifest_rows()], ["ARCHIVE", "ARCHIVE_MEMBER"])
        [f] = bc.load_many(bc.archive_paths(self.raw), self.manifest)
        self.assertEqual((f.trade_date, f.format, f.eq_rows[0].close), (self.FIRST_UDIFF, bc.FORMAT_UDIFF, bc.Decimal("10.50")))
        [again] = self.ingest([p], recorded_at="T2")               # idempotent: nothing is added twice
        self.assertEqual(again["outcome"], acq.DUPLICATE)
        self.assertEqual(len(self.manifest_rows()), 2)

    def test_overlap_udiff_is_quarantined_not_mixed_with_legacy(self):
        [r] = self.ingest([self.udiff_zip(self.LAST_LEGACY)])
        self.assertEqual((r["outcome"], r["reason"]), (acq.QUARANTINED, acq.FORMAT_NOT_SELECTED_FOR_DATE))
        self.assertEqual(self.manifest_rows(), [])

    def test_legacy_after_the_switch_is_quarantined(self):
        [r] = self.ingest([make_zip(self.inbox, self.FIRST_UDIFF)])
        self.assertEqual((r["outcome"], r["reason"]), (acq.QUARANTINED, acq.FORMAT_NOT_SELECTED_FOR_DATE))
        self.assertEqual(self.manifest_rows(), [])

    def test_one_session_never_gets_a_second_source(self):
        self.ingest([make_zip(self.inbox, self.LAST_LEGACY)])
        [r] = self.ingest([self.udiff_zip(self.LAST_LEGACY)], recorded_at="T2")
        self.assertEqual(r["outcome"], acq.QUARANTINED)
        self.assertEqual(len(self.manifest_rows()), 2)

    def test_malformed_udiff_row_is_quarantined_with_the_line(self):
        bad = udiff_body(self.FIRST_UDIFF).replace(",11.00,9.00,", ",9.50,9.00,")     # high below open
        [r] = self.ingest([self.udiff_zip(self.FIRST_UDIFF, bad)])
        self.assertEqual((r["outcome"], r["reason"]), (acq.QUARANTINED, acq.PARSE_FAILED))
        self.assertIn("line 2", r["detail"])

    def test_manifest_rows_refuse_the_unselected_format(self):
        from nse.research import manifest_tool
        with self.assertRaisesRegex(manifest_tool.ManifestError, "not the format selected"):
            manifest_tool.rows_for([self.udiff_zip(self.LAST_LEGACY)], self.manifest, *PROV)

    def test_plan_and_provider_name_the_selected_format(self):
        rows = acq.plan(FakeCalendar(), self.LAST_LEGACY, self.FIRST_UDIFF, self.manifest, self.raw)
        self.assertEqual({r["session_date"]: r["file_name"] for r in rows},
                         {"2024-07-05": "cm05JUL2024bhav.csv.zip",
                          "2024-07-08": "BhavCopy_NSE_CM_0_0_0_20240708_F_0000.csv.zip"})
        self.assertEqual([r["url"] for r in rows],
                         ["https://nsearchives.nseindia.com/content/historical/EQUITIES/2024/JUL/cm05JUL2024bhav.csv.zip",
                          "https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_20240708_F_0000.csv.zip"])
        prov = acq.LocalInboxProvider(self.inbox)
        p = self.udiff_zip(self.FIRST_UDIFF)
        self.assertEqual(prov.list_available(self.FIRST_UDIFF), [p])
        self.assertEqual(prov.list_available(self.LAST_LEGACY), [])


class Ingestion(_Tmp):

    def test_accepted_file_is_copied_and_registered_source_kept(self):
        d = D(2024, 1, 8)
        p = make_zip(self.inbox, d)
        [r] = self.ingest([p])
        self.assertEqual(r["outcome"], acq.INGESTED)
        self.assertTrue(os.path.isfile(p), "the source file must never be moved or deleted")
        self.assertEqual(acq.sha256_file(os.path.join(self.raw, acq.legacy_name(d))), acq.sha256_file(p))
        rows = self.manifest_rows()
        self.assertEqual([x["kind"] for x in rows], ["ARCHIVE", "ARCHIVE_MEMBER"])
        self.assertEqual((rows[0]["source_page"], rows[0]["downloaded_on"], rows[0]["provenance_status"]), PROV)
        # the strict loader now accepts the ingested file against the manifest (D31 provenance)
        [f] = bc.load_many([os.path.join(self.raw, acq.legacy_name(d))], self.manifest)
        self.assertEqual(f.trade_date, d)

    def test_same_file_twice_is_duplicate_and_writes_nothing(self):
        p = make_zip(self.inbox, D(2024, 1, 8))
        self.ingest([p])
        before = read(self.manifest)
        [r] = self.ingest([p], recorded_at="T2")
        self.assertEqual(r["outcome"], acq.DUPLICATE)
        self.assertEqual(read(self.manifest), before)
        self.assertFalse(os.path.exists(self.quar))

    def test_revised_file_never_overwrites_the_held_one(self):
        d = D(2024, 1, 8)
        first = make_zip(self.inbox, d)
        self.ingest([first])
        held = os.path.join(self.raw, acq.legacy_name(d))
        held_sha = acq.sha256_file(held)
        other = os.path.join(self.tmp, "later")
        os.makedirs(other)
        revised = make_zip(other, d, legacy_body(d, close="10.4"))   # same session, different bytes
        [r] = self.ingest([revised], recorded_at="T2")
        self.assertEqual((r["outcome"], r["reason"]), (acq.REVISED_FILE_QUARANTINED, acq.REVISION_OF_HELD_SESSION))
        self.assertEqual(acq.sha256_file(held), held_sha)
        self.assertEqual(len([x for x in self.manifest_rows() if x["kind"] == "ARCHIVE"]), 1)
        with open(r["quarantine_path"] + ".reason.json") as fh:
            self.assertEqual(json.load(fh)["held_sha256"], held_sha)

    def test_parse_failure_is_quarantined_with_the_loader_error(self):
        d = D(2024, 1, 8)
        bad = legacy_body(d).replace(",9,10.5,", ",12,10.5,")      # LOW above HIGH: strict loader refuses
        p = make_zip(self.inbox, d, bad)
        [r] = self.ingest([p])
        self.assertEqual((r["outcome"], r["reason"]), (acq.QUARANTINED, acq.PARSE_FAILED))
        # ED-30: a value failure is a RowValueError (a MalformedFileError subclass); on an EQ row
        # it still refuses the whole file
        self.assertRegex(r["detail"], r"^(MalformedFileError|RowValueError): ")
        self.assertIn("OHLC inconsistent", r["detail"])
        self.assertEqual(self.manifest_rows(), [])
        self.assertTrue(os.path.isfile(p))
        self.assertFalse(os.path.isdir(self.raw) and os.listdir(self.raw))

    def test_crlf_legacy_is_labelled_legacy_then_refused_strictly(self):
        d = D(2024, 1, 8)
        p = make_zip(self.inbox, d, legacy_body(d).replace("\n", "\r\n"))
        self.assertEqual(acq.detect_format(p), acq.LEGACY_BHAVCOPY)
        [r] = self.ingest([p])
        self.assertEqual(r["reason"], acq.PARSE_FAILED)
        self.assertIn("UnsupportedFormatError", r["detail"])

    def test_the_13_column_crlf_variant_is_triaged_legacy_and_ingested(self):
        # ED-38: the triage labels the 13-column header legacy; the strict loader decides
        d = D(2024, 1, 8)
        body = legacy_body(d).replace(",\n", "\n").replace("\n", "\r\n")
        p = make_zip(self.inbox, d, body)
        self.assertEqual(acq.detect_format(p), acq.LEGACY_BHAVCOPY)
        [r] = self.ingest([p])
        self.assertEqual(r["outcome"], acq.INGESTED, r)

    def test_standalone_csv_is_not_ingested(self):
        d = D(2024, 1, 8)
        p = os.path.join(self.inbox, "cm08JAN2024bhav.csv")
        with open(p, "w", newline="") as fh:
            fh.write(legacy_body(d))
        [r] = self.ingest([p])
        self.assertEqual((r["outcome"], r["reason"]), (acq.QUARANTINED, acq.NOT_AN_ARCHIVE))

    def test_missing_source_and_raw_name_conflict(self):
        d = D(2024, 1, 8)
        [r] = self.ingest([os.path.join(self.inbox, "absent.zip")])
        self.assertEqual(r["outcome"], acq.SOURCE_NOT_FOUND)
        os.makedirs(self.raw)
        make_zip(self.raw, d, legacy_body(d, close="10.1"))            # an unregistered raw file
        before = acq.sha256_file(os.path.join(self.raw, acq.legacy_name(d)))
        [r] = self.ingest([make_zip(self.inbox, d)])
        self.assertEqual(r["reason"], acq.RAW_NAME_CONFLICT)
        self.assertEqual(acq.sha256_file(os.path.join(self.raw, acq.legacy_name(d))), before)
        self.assertEqual(self.manifest_rows(), [])

    def test_owner_provenance_is_required_before_anything_happens(self):
        p = make_zip(self.inbox, D(2024, 1, 8))
        from nse.research import manifest_tool as mt
        for page, dl, st in (("", "2026-11-02", "S"), ("pg", "yesterday", "S"), ("pg", "2026-11-02", "")):
            with self.assertRaises(mt.ManifestError):
                acq.ingest([p], self.raw, self.manifest, self.quar, self.ledger, page, dl, st, "T1")
        with self.assertRaises(acq.AcquisitionError):
            acq.ingest([p], self.raw, self.manifest, self.quar, self.ledger, *PROV, recorded_at="")
        self.assertFalse(os.path.exists(self.ledger))
        self.assertEqual(self.manifest_rows(), [])

    def test_two_files_for_one_session_in_one_batch(self):
        d = D(2024, 1, 8)
        a = make_zip(self.inbox, d)
        other = os.path.join(self.tmp, "b")
        os.makedirs(other)
        b = make_zip(other, d, legacy_body(d, close="10.2"))
        outs = [r["outcome"] for r in self.ingest([b, a])]
        self.assertEqual(sorted(outs), [acq.INGESTED, acq.REVISED_FILE_QUARANTINED])


class Ledger(_Tmp):

    def test_append_only_sorted_keys_caller_timestamp_and_deterministic(self):
        p = make_zip(self.inbox, D(2024, 1, 8))
        self.ingest([p], recorded_at="2026-11-02T18:00:00+05:30")
        first = read(self.ledger)
        self.ingest([p], recorded_at="2026-11-02T19:00:00+05:30")
        text = read(self.ledger)
        self.assertTrue(text.startswith(first), "earlier ledger lines are never rewritten")
        lines = text.splitlines()
        self.assertEqual(len(lines), 2)
        for line in lines:
            obj = json.loads(line)
            self.assertEqual(line, json.dumps(obj, sort_keys=True))
        self.assertEqual([json.loads(x)["recorded_at"] for x in lines],
                         ["2026-11-02T18:00:00+05:30", "2026-11-02T19:00:00+05:30"])
        self.assertEqual([x["outcome"] for x in acq.read_ledger(self.ledger)], [acq.INGESTED, acq.DUPLICATE])

    def test_same_inputs_give_byte_identical_ledger(self):
        texts = []
        for _ in range(2):
            self.tearDown()
            self.setUp()
            p = make_zip(self.inbox, D(2024, 1, 8))
            self.ingest([p, p])
            texts.append(read(self.ledger).replace(self.tmp, "<TMP>"))   # temp folder differs
        self.assertEqual(texts[0], texts[1])


class FakeCalendar(object):
    """Test fixture: weekdays trade except `closed`; `excluded` are Muhurat-like, `ambiguous`
    raise CalendarAmbiguityError, years outside `years` raise CalendarCoverageError."""
    def __init__(self, closed=(), excluded=(), ambiguous=(), years=(2024,)):
        self.closed, self.excluded, self.ambiguous, self.years = set(closed), set(excluded), set(ambiguous), years

    def _check(self, d):
        if d.year not in self.years:
            raise cal_mod.CalendarCoverageError("%s: not covered" % d)
        if d in self.ambiguous:
            raise cal_mod.CalendarAmbiguityError("%s: unresolved" % d)

    def is_trading_day(self, d):
        self._check(d)
        return d.weekday() < 5 and d not in self.closed and d not in self.excluded

    def is_excluded_session(self, d):
        self._check(d)
        return d in self.excluded


class Plan(_Tmp):

    def _hold(self, *dates):
        self.ingest([make_zip(self.inbox, d) for d in dates])

    def test_statuses_held_missing_mismatch_not_in_manifest(self):
        held, tampered, orphan = D(2024, 1, 8), D(2024, 1, 9), D(2024, 1, 11)
        self._hold(held, tampered)
        with zipfile.ZipFile(os.path.join(self.raw, acq.legacy_name(tampered)), "a") as z:
            z.writestr("extra.txt", "tamper")                 # raw bytes no longer match the manifest
        make_zip(self.raw, orphan)
        rows = acq.plan(FakeCalendar(), D(2024, 1, 8), D(2024, 1, 14), self.manifest, self.raw)
        got = {r["session_date"]: (r["calendar_status"], r["status"]) for r in rows}
        self.assertEqual(got, {"2024-01-08": (acq.EXPECTED, acq.HELD),
                               "2024-01-09": (acq.EXPECTED, acq.HASH_MISMATCH),
                               "2024-01-10": (acq.EXPECTED, acq.MISSING),
                               "2024-01-11": (acq.EXPECTED, acq.NOT_IN_MANIFEST),
                               "2024-01-12": (acq.EXPECTED, acq.MISSING)})      # weekend omitted
        cov = acq.coverage(rows)
        self.assertEqual(cov["missing_sessions"], ["2024-01-10", "2024-01-12"])
        self.assertEqual((cov["first_held"], cov["last_held"]), ("2024-01-08", "2024-01-08"))
        self.assertEqual(cov["hash_mismatch"], ["2024-01-09"])
        self.assertFalse(cov["complete"])

    def test_manifest_record_without_raw_file_is_missing(self):
        d = D(2024, 1, 8)
        self._hold(d)
        os.remove(os.path.join(self.raw, acq.legacy_name(d)))
        [r] = acq.plan(FakeCalendar(), d, d, self.manifest, self.raw)
        self.assertEqual(r["status"], acq.MISSING)
        self.assertIn("raw file absent", r["detail"])

    def test_without_calendar_weekdays_are_candidates_never_expected(self):
        rows = acq.plan(None, D(2024, 1, 8), D(2024, 1, 14), self.manifest, self.raw)
        self.assertEqual(len(rows), 5)
        self.assertTrue(all(r["calendar_status"] == acq.CALENDAR_UNVALIDATED for r in rows))
        cov = acq.coverage(rows)
        self.assertEqual(cov["missing_sessions"], [], "no calendar: nothing is known to be missing")
        self.assertEqual(len(cov["missing_candidate_weekdays_calendar_unvalidated"]), 5)
        self.assertFalse(cov["complete"])

    def test_uncovered_year_ambiguous_excluded_and_closed_days(self):
        hol, muh, amb = D(2024, 1, 9), D(2024, 1, 10), D(2024, 1, 11)
        cal = FakeCalendar(closed=[hol], excluded=[muh], ambiguous=[amb])
        self._hold(hol)                                   # a file on a closed day is reported
        rows = acq.plan(cal, D(2023, 12, 29), D(2024, 1, 12), self.manifest, self.raw)
        got = {r["session_date"]: r["calendar_status"] for r in rows}
        self.assertEqual(got["2023-12-29"], acq.CALENDAR_UNVALIDATED)   # year not covered
        self.assertEqual(got["2024-01-09"], acq.CLOSED_DAY)
        self.assertEqual(got["2024-01-10"], acq.EXCLUDED_SESSION)
        self.assertEqual(got["2024-01-11"], acq.CALENDAR_AMBIGUOUS)
        cov = acq.coverage(rows)
        self.assertEqual(cov["files_on_closed_days"], ["2024-01-09"])
        self.assertNotIn("2024-01-10", cov["missing_sessions"])
        self.assertNotIn("2024-01-11", cov["missing_sessions"])
        self.assertEqual(cov["missing_on_ambiguous_dates"], ["2024-01-11"])

    def test_resumes_as_files_arrive(self):
        cal = FakeCalendar()
        before = acq.coverage(acq.plan(cal, D(2024, 1, 8), D(2024, 1, 9), self.manifest, self.raw))
        self.assertEqual(before["missing_sessions"], ["2024-01-08", "2024-01-09"])
        self._hold(D(2024, 1, 8))
        after = acq.coverage(acq.plan(cal, D(2024, 1, 8), D(2024, 1, 9), self.manifest, self.raw))
        self.assertEqual(after["missing_sessions"], ["2024-01-09"])
        self._hold(D(2024, 1, 9))
        done = acq.coverage(acq.plan(cal, D(2024, 1, 8), D(2024, 1, 9), self.manifest, self.raw))
        self.assertTrue(done["complete"])

    def test_bad_range(self):
        with self.assertRaises(acq.AcquisitionError):
            acq.plan(None, D(2024, 1, 9), D(2024, 1, 8), self.manifest, self.raw)

    def test_real_calendar_holiday_is_not_expected(self):
        cal_dir = os.path.join(ROOT, "nse", "data", "calendar")
        require_local(os.path.isdir(os.path.join(cal_dir, "circulars")), "calendar circulars (nse/data/calendar/circulars)")
        cal = cal_mod.NseCalendar.load(cal_dir)
        require_local(2022 in cal.covered_years, "a verified 2022 BASE calendar circular")
        rows = acq.plan(cal, D(2022, 1, 25), D(2022, 1, 27), self.manifest, self.raw)
        self.assertEqual([r["session_date"] for r in rows], ["2022-01-25", "2022-01-27"])  # 26 Jan holiday


class DailyUpdate(_Tmp):

    def run_day(self, d, cal, max_attempts=3, at="T1"):
        return acq.daily_update(d, acq.LocalInboxProvider(self.inbox), cal, self.raw, self.manifest, self.quar,
                                self.ledger, *PROV, recorded_at=at, max_attempts=max_attempts)

    def test_holiday_is_not_a_trading_session(self):
        d = D(2024, 1, 9)
        make_zip(self.inbox, d)
        r = self.run_day(d, FakeCalendar(closed=[d]))
        self.assertEqual(r["status"], acq.NOT_A_TRADING_SESSION)
        self.assertIsNone(r["alert"])
        self.assertEqual(self.manifest_rows(), [])

    def test_missing_retries_then_alert(self):
        d = D(2024, 1, 8)
        cal = FakeCalendar()
        r1 = self.run_day(d, cal, at="T1")
        r2 = self.run_day(d, cal, at="T2")
        self.assertEqual([r1["status"], r2["status"]], [acq.FILE_NOT_YET_AVAILABLE] * 2)
        self.assertEqual([r1["attempt"], r2["attempt"]], [1, 2])
        self.assertIsNone(r2["alert"])
        r3 = self.run_day(d, cal, at="T3")
        self.assertEqual((r3["status"], r3["attempt"]), (acq.SESSION_MISSING_ALERT, 3))
        self.assertEqual(r3["alert"]["alert"], "SESSION_MISSING")
        self.assertEqual(r3["alert"]["recorded_at"], "T3")
        # attempts on another session are counted separately
        self.assertEqual(self.run_day(D(2024, 1, 9), cal)["attempt"], 1)

    def test_ingested_then_duplicate_then_already_held(self):
        d = D(2024, 1, 8)
        p = make_zip(self.inbox, d)
        cal = FakeCalendar()
        self.assertEqual(self.run_day(d, cal)["status"], acq.INGESTED)
        self.assertEqual(self.run_day(d, cal)["status"], acq.DUPLICATE)
        os.remove(p)                                          # test's own temp file
        r = self.run_day(d, cal)
        self.assertEqual(r["status"], acq.ALREADY_HELD)
        self.assertIsNone(r["alert"])

    def test_quality_failure_raises_alert(self):
        d = D(2024, 1, 8)
        make_zip(self.inbox, d, UDIFF_HEADER)
        r = self.run_day(d, FakeCalendar())
        self.assertEqual(r["status"], acq.QUARANTINED)
        self.assertEqual(r["alert"]["alert"], "QUALITY_FAILURE")
        self.assertIn(acq.PARSE_FAILED, r["alert"]["reason"])

    def test_no_calendar_never_claims_missing(self):
        d = D(2024, 1, 8)
        r = self.run_day(d, None, max_attempts=1)
        self.assertEqual(r["status"], acq.CALENDAR_UNVALIDATED)
        self.assertIsNone(r["alert"], "an unknown session cannot be reported missing")
        make_zip(self.inbox, d)
        r = self.run_day(d, None)
        self.assertEqual((r["status"], r["outcome_if_expected"]), (acq.CALENDAR_UNVALIDATED, acq.INGESTED))

    def test_ambiguous_date_is_calendar_unvalidated(self):
        d = D(2024, 1, 8)
        r = self.run_day(d, FakeCalendar(ambiguous=[d]), max_attempts=1)
        self.assertEqual(r["status"], acq.CALENDAR_UNVALIDATED)
        self.assertEqual(r["calendar_status"], acq.CALENDAR_AMBIGUOUS)

    def test_max_attempts_required(self):
        with self.assertRaises(acq.AcquisitionError):
            self.run_day(D(2024, 1, 8), FakeCalendar(), max_attempts=0)

    def test_provider_contract(self):
        self.assertEqual(acq.legacy_name(D(2022, 1, 3)), "cm03JAN2022bhav.csv.zip")
        prov = acq.LocalInboxProvider(self.inbox)
        self.assertEqual(prov.list_available(D(2024, 1, 8)), [])
        p = make_zip(self.inbox, D(2024, 1, 8))
        make_zip(self.inbox, None, UDIFF_HEADER, name="BhavCopy_NSE_CM_0_0_0_20240108_F_0000.csv.zip",
                 member="x.csv")
        self.assertEqual(prov.list_available(D(2024, 1, 8)), [p])
        with self.assertRaises(NotImplementedError):
            acq.Provider().list_available(D(2024, 1, 8))


class Cli(_Tmp):

    def call(self, argv):
        p = argparse.ArgumentParser()
        sub = p.add_subparsers(dest="cmd")
        acq.add_commands(sub)
        args = p.parse_args(argv)
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = args.func(args)
        return code, out.getvalue(), err.getvalue()

    def ingest_args(self):
        return ["--raw-dir", self.raw, "--manifest", self.manifest, "--quarantine-dir", self.quar,
                "--ledger", self.ledger, "--source-page", PROV[0], "--downloaded-on", PROV[1],
                "--provenance-status", PROV[2], "--recorded-at", "T1"]

    def test_ingest_plan_coverage_daily(self):
        d = D(2024, 1, 8)
        p = make_zip(self.inbox, d)
        code, out, _ = self.call(["acquire-ingest", p] + self.ingest_args())
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["results"][0]["outcome"], acq.INGESTED)
        bad = make_zip(os.path.join(self.tmp), D(2024, 1, 9), UDIFF_HEADER)
        code, _, _ = self.call(["acquire-ingest", bad] + self.ingest_args())
        self.assertEqual(code, 1)
        target = os.path.join(self.tmp, "out", "plan.json")
        code, out, _ = self.call(["acquire-plan", "--start", "2024-01-08", "--end", "2024-01-09",
                                  "--manifest", self.manifest, "--raw-dir", self.raw, "--out", target])
        self.assertEqual(code, 0)
        self.assertEqual(read(target), out)
        obj = json.loads(out)
        self.assertEqual(obj["calendar"], acq.CALENDAR_UNVALIDATED)
        self.assertEqual([r["status"] for r in obj["rows"]], [acq.HELD, acq.MISSING])
        code, out, _ = self.call(["acquire-coverage", "--start", "2024-01-08", "--end", "2024-01-09",
                                  "--manifest", self.manifest, "--raw-dir", self.raw])
        self.assertEqual((code, json.loads(out)["first_held"]), (0, "2024-01-08"))
        code, out, _ = self.call(["daily-update", "--session-date", "2024-01-10", "--inbox", self.inbox,
                                  "--max-attempts", "1"] + self.ingest_args())
        self.assertEqual((code, json.loads(out)["status"]), (0, acq.CALENDAR_UNVALIDATED))

    def test_usage_errors_exit_2(self):
        code, _, err = self.call(["acquire-plan", "--start", "2025-13-01", "--end", "2024-01-09",
                                  "--manifest", self.manifest, "--raw-dir", self.raw])
        self.assertEqual(code, 2)
        self.assertIn("error", err)
        code, _, _ = self.call(["acquire-plan", "--start", "2024-01-08", "--end", "2024-01-09",
                                "--manifest", os.path.join(self.tmp, "nope.csv"), "--raw-dir", self.raw])
        self.assertEqual(code, 2)


class RealArchive(_Tmp):
    """A real archive copied OUT of nse/data/eod/raw into a temp inbox (git-ignored evidence)."""

    def test_real_legacy_archive_ingests_with_the_recorded_hash(self):
        name = "cm03JAN2022bhav.csv.zip"
        src = os.path.join(ROOT, "nse", "data", "eod", "raw", name)
        require_local(os.path.isfile(src), "nse/data/eod/raw/" + name)
        p = os.path.join(self.inbox, name)
        shutil.copyfile(src, p)
        self.assertEqual(acq.detect_format(p), acq.LEGACY_BHAVCOPY)
        [r] = self.ingest([p])
        self.assertEqual(r["outcome"], acq.INGESTED)
        real = [x for x in bc.read_manifest(os.path.join(ROOT, "nse", "data", "eod", "manifest.csv"))
                if x["file_name"] == name and x["kind"] == "ARCHIVE"]
        self.assertEqual(r["sha256"], real[0]["sha256"])


if __name__ == "__main__":
    unittest.main()
