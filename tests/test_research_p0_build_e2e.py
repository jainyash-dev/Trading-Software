"""End-to-end P0 certification build on a SYNTHETIC dataset (review REV-1, Milestone 1).

Every input is a small invented file in the real format: a calendar folder with a hashed
BASE circular, legacy bhavcopy archives matched by a manifest, a membership universe,
instrument records, corporate-action bodies, an action list and a completeness register.
The real `p0_certification.build()` and the shared `dataset_eligibility` classifier run on
them. This proves the code path and the gate logic, not any historical NSE fact.

Window 2022-01-04..2022-01-21. Calendar: 2022-01-08 (Saturday) is a Muhurat session with a
held file; 2022-01-14 is a holiday; 2022-01-18 has no file held; 2022-01-20 is UNRESOLVED.

Symbols:
  AAA  verified member, resolved, completeness register window -> certified on clean steps
  BBB  verified member, dividend-only response, no completeness window -> exploratory only;
       BE-only on 2022-01-11; PREVCLOSE break across the held Muhurat session
  CCC  membership period without a verified source hash; removed from 2022-01-13
  DDD  added 2022-01-12, verified, `[]` response inside a completeness window
  EEE  no instrument record (unknown identity)
  OLDX -> NEWX  verified rename effective 2022-01-13 (same ISIN)
  FOO  -> BAR   rename record whose source does not verify (never joined)
  ISX  ISIN change effective 2022-01-13 (two periods)
  SPL  recorded 1:10 split, ex-date 2022-01-12 (PREVCLOSE printed unadjusted)
  GAP  unrecorded 50% price drop on 2022-01-12
"""

import csv
import datetime
import hashlib
import io
import json
import os
import shutil
import tempfile
import unittest
import zipfile

import _research  # noqa: F401  (puts the repository root on sys.path)
from nse.research import corporate_actions as ca, dataset_eligibility as de, instruments, p0_certification as p0
from nse.research import universe as univ
from nse.research.deps import bhavcopy, calendar as cal_mod

D = datetime.date
MON = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
START, END = D(2022, 1, 4), D(2022, 1, 21)
MUHURAT, HOLIDAY, NO_FILE, UNRESOLVED = D(2022, 1, 8), D(2022, 1, 14), D(2022, 1, 18), D(2022, 1, 20)

ISIN = {"AAA": "INE000A01011", "BBB": "INE000B01011", "CCC": "INE000C01011", "DDD": "INE000D01011",
        "EEE": "INE000E01011", "OLDX": "INE000F01011", "NEWX": "INE000F01011", "FOO": "INE000G01011",
        "BAR": "INE000G01011", "SPL": "INE000H01011", "GAP": "INE000J01011"}
ISX_OLD, ISX_NEW = "INE000K01011", "INE000K01029"


def _sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def _sha_file(path):
    with open(path, "rb") as fh:
        return _sha_bytes(fh.read())


class Fixture(object):
    def __init__(self, root, completeness=True, duplicate_coverage=False):
        self.root = root
        # Membership / identity still cite evidence.txt; completeness uses that plus an
        # independent second official extract (D66).
        self.ev = os.path.join(root, "evidence.txt")
        self.ev_b = os.path.join(root, "evidence_b.txt")
        with open(self.ev, "w") as fh:
            fh.write("SYNTHETIC evidence document A (official extract)\n")
        with open(self.ev_b, "w") as fh:
            fh.write("SYNTHETIC evidence document B (independent official extract)\n")
        self.ev_sha = _sha_file(self.ev)
        self.ev_sha_a = self.ev_sha
        self.ev_sha_b = _sha_file(self.ev_b)
        self.calendar()
        self.eod()
        self.universe()
        self.records()
        self.corporate_actions(completeness, duplicate_coverage)

    # --- calendar --------------------------------------------------------------------
    def calendar(self):
        self.cal_dir = os.path.join(self.root, "calendar")
        os.makedirs(os.path.join(self.cal_dir, "circulars"))
        data = b"SYNTHETIC holiday circular 2022"
        with open(os.path.join(self.cal_dir, "circulars", "base2022.pdf"), "wb") as fh:
            fh.write(data)
        src = {"source_ref": "SYN/2022", "kind": "BASE", "applicable_year": "2022", "doc_date": "2021-12-01",
               "title": "Trading holidays 2022 (synthetic)", "file_name": "base2022.pdf", "sha256": _sha_bytes(data),
               "downloaded_on": "2026-11-15", "url": "https://example.invalid/base2022.pdf"}
        events = [
            {"date": HOLIDAY.isoformat(), "event": "HOLIDAY", "description": "synthetic", "session_start": "",
             "session_end": "", "source_ref": "SYN/2022", "status": "CONFIRMED", "note": ""},
            {"date": MUHURAT.isoformat(), "event": "MUHURAT_SESSION", "description": "synthetic",
             "session_start": "18:15", "session_end": "19:15", "source_ref": "SYN/2022", "status": "CONFIRMED",
             "note": ""},
            {"date": UNRESOLVED.isoformat(), "event": "SPECIAL_SESSION", "description": "synthetic",
             "session_start": "", "session_end": "", "source_ref": "", "status": "UNRESOLVED",
             "note": "synthetic: hours not printed"},
        ]
        self._csv(os.path.join(self.cal_dir, "sources.csv"), cal_mod.SOURCE_COLUMNS, [src])
        self._csv(os.path.join(self.cal_dir, "events.csv"), cal_mod.EVENT_COLUMNS, events)

    # --- EOD archives ----------------------------------------------------------------
    def prices(self):
        """{date: [(symbol, series, open, high, low, close, prevclose, isin)]} for every held file."""
        days = [D(2022, 1, 3) + datetime.timedelta(i) for i in range(19)]
        held = [d for d in days if (d.weekday() < 5 and d not in (HOLIDAY, NO_FILE)) or d == MUHURAT]
        last = {}
        out = {}
        for i, d in enumerate(held):
            rows = []
            for sym, base in (("AAA", 100.0), ("BBB", 200.0), ("CCC", 300.0), ("DDD", 400.0), ("EEE", 500.0),
                              ("SPL", 1000.0), ("GAP", 600.0), ("ISX", 700.0)):
                close = round(base * (1 + 0.002 * i), 2)
                if sym == "SPL" and d >= D(2022, 1, 12):
                    close = round(close / 10, 2)
                if sym == "GAP" and d >= D(2022, 1, 12):
                    close = round(close / 2, 2)
                if sym == "AAA" and d == MUHURAT:
                    close = last.get("AAA")                      # AAA's chain survives the Muhurat file
                isin = ISX_NEW if sym == "ISX" and d >= D(2022, 1, 13) else (ISX_OLD if sym == "ISX" else ISIN[sym])
                series = "BE" if (sym == "BBB" and d == D(2022, 1, 11)) else "EQ"
                rows.append((sym, series, close, close * 1.005, close * 0.995, close, last.get(sym, close), isin))
                last[sym] = close
            rename = "NEWX" if d >= D(2022, 1, 13) else "OLDX"
            rclose = round(800.0 * (1 + 0.002 * i), 2)
            rows.append((rename, "EQ", rclose, rclose * 1.005, rclose * 0.995, rclose, last.get("X", rclose),
                         ISIN["OLDX"]))
            last["X"] = rclose
            foo = "BAR" if d >= D(2022, 1, 13) else "FOO"
            fclose = round(900.0 * (1 + 0.002 * i), 2)
            rows.append((foo, "EQ", fclose, fclose * 1.005, fclose * 0.995, fclose, last.get("F", fclose),
                         ISIN["FOO"]))
            last["F"] = fclose
            out[d] = rows
        return out

    def eod(self):
        self.raw = os.path.join(self.root, "raw")
        os.makedirs(self.raw)
        manifest = []
        self.prices_by_day = self.prices()
        for d, rows in self.prices_by_day.items():
            stamp = "%02d-%s-%04d" % (d.day, MON[d.month - 1], d.year)
            member = "cm%02d%s%04dbhav.csv" % (d.day, MON[d.month - 1], d.year)
            text = ",".join(bhavcopy.LEGACY_HEADER) + "\n"
            for sym, series, o, h, lo, c, pc, isin in rows:
                text += "%s,%s,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,1000,100000,%s,10,%s,\n" % (
                    sym, series, o, h, lo, c, c, pc, stamp, isin)
            data = text.encode("ascii")
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
                info = zipfile.ZipInfo(member, date_time=(2022, 1, 1, 0, 0, 0))
                z.writestr(info, data)
            archive = buf.getvalue()
            with open(os.path.join(self.raw, member + ".zip"), "wb") as fh:
                fh.write(archive)
            manifest.append({"file_name": member + ".zip", "kind": "ARCHIVE", "parent_archive": "",
                             "trade_date": d.isoformat(), "size_bytes": str(len(archive)),
                             "sha256": _sha_bytes(archive), "source_page": "SYNTHETIC",
                             "downloaded_on": "2026-11-15", "provenance_status": "SYNTHETIC"})
            manifest.append({"file_name": member, "kind": "ARCHIVE_MEMBER", "parent_archive": member + ".zip",
                             "trade_date": d.isoformat(), "size_bytes": str(len(data)), "sha256": _sha_bytes(data),
                             "source_page": "SYNTHETIC", "downloaded_on": "2026-11-15",
                             "provenance_status": "SYNTHETIC"})
        self.manifest = os.path.join(self.root, "manifest.csv")
        self._csv(self.manifest, bhavcopy.MANIFEST_COLUMNS, manifest)

    # --- membership ------------------------------------------------------------------
    def universe(self):
        self.universe_dir = os.path.join(self.root, "universe")
        os.makedirs(self.universe_dir)
        ok = ("../evidence.txt", self.ev_sha)
        none = ("../evidence.txt", "")
        periods = [("AAA", ISIN["AAA"], "2022-01-03", "", ok), ("BBB", ISIN["BBB"], "2022-01-03", "", ok),
                   ("CCC", ISIN["CCC"], "2022-01-03", "2022-01-12", none),
                   ("DDD", ISIN["DDD"], "2022-01-12", "", ok), ("EEE", ISIN["EEE"], "2022-01-03", "", ok),
                   ("OLDX", ISIN["OLDX"], "2022-01-03", "2022-01-12", ok),
                   ("NEWX", ISIN["NEWX"], "2022-01-13", "", ok),
                   ("FOO", ISIN["FOO"], "2022-01-03", "2022-01-12", ok), ("BAR", ISIN["BAR"], "2022-01-13", "", ok),
                   ("ISX", ISX_OLD, "2022-01-03", "2022-01-12", ok), ("ISX", ISX_NEW, "2022-01-13", "", ok),
                   ("SPL", ISIN["SPL"], "2022-01-03", "", ok), ("GAP", ISIN["GAP"], "2022-01-03", "", ok)]
        rows = [{"symbol": s, "series": "EQ", "isin": i, "index_name": "SYNTHETIC 13", "effective_from": a,
                 "effective_to": b, "source": "SYNTHETIC release", "source_file": f, "source_sha256": h,
                 "recorded_on": "2026-11-15", "notes": "SYNTHETIC"} for s, i, a, b, (f, h) in periods]
        self.universe_csv = os.path.join(self.universe_dir, "nifty100_universe.csv")
        self._csv(self.universe_csv, univ.COLUMNS, rows)

    def records(self):
        def rec(kind, sym, isin, start, new="", sha=None):
            return {"record_type": kind, "symbol": sym, "new_symbol": new, "isin": isin, "series": "EQ",
                    "effective_from": start, "effective_to": "", "source": "SYNTHETIC", "source_file": "../evidence.txt",
                    "source_sha256": self.ev_sha if sha is None else sha, "recorded_on": "2026-11-15", "notes": ""}
        rows = [rec("LISTING", s, ISIN[s], "2016-01-01") for s in ("AAA", "BBB", "CCC", "DDD", "SPL", "GAP")]
        rows += [rec("LISTING", "OLDX", ISIN["OLDX"], "2016-01-01"),
                 rec("SYMBOL_CHANGE", "OLDX", ISIN["OLDX"], "2022-01-13", new="NEWX"),
                 rec("LISTING", "FOO", ISIN["FOO"], "2016-01-01"),
                 rec("SYMBOL_CHANGE", "FOO", ISIN["FOO"], "2022-01-13", new="BAR", sha=""),       # unverified
                 rec("LISTING", "ISX", ISX_OLD, "2016-01-01"),
                 rec("ISIN_CHANGE", "ISX", ISX_NEW, "2022-01-13")]
        self.records_csv = os.path.join(self.universe_dir, "instrument_records.csv")
        self._csv(self.records_csv, instruments.COLUMNS, rows)

    # --- corporate actions -----------------------------------------------------------
    def corporate_actions(self, completeness, duplicate):
        self.ca_dir = os.path.join(self.root, "ca")
        os.makedirs(os.path.join(self.ca_dir, "raw"))
        bodies = {"AAA": '[{"subject": "Dividend - Rs 5 Per Share"}]',
                  "BBB": '[{"subject": "Dividend - Rs 2 Per Share"}]',
                  "CCC": '[{"subject": "Dividend - Rs 1 Per Share"}]',
                  "DDD": "[]",
                  "NEWX": '[{"subject": "Dividend - Rs 3 Per Share"}]',
                  "SPL": '[{"subject": "Face Value Split (Sub-Division) - From Rs 10/- Per Share To Re 1/- Per Share"}]',
                  "GAP": '[{"subject": "Dividend - Rs 4 Per Share"}]',
                  "ISX": '[{"subject": "Dividend - Rs 6 Per Share"}]',
                  "OLDX": "[]",                                  # renamed ticker: NSE files under NEWX (M-3)
                  "FOO": "[]",                                   # empty body missing from the log (M-2)
                  "EEE": "<html>Access Denied</html>"}           # not a JSON list of events (M-1)
        cov, log = [], []
        for sym, body in sorted(bodies.items()):
            name = "ca_%s_2016_2025.json" % sym
            with open(os.path.join(self.ca_dir, "raw", name), "w") as fh:
                fh.write(body)
            if body != "[]":
                cov.append({"symbol": sym, "from_date": "2016-01-01", "to_date": "2025-12-31",
                            "source_file": "raw/" + name, "source_sha256": _sha_bytes(body.encode()), "rows": "1",
                            "retrieved_on": "2026-11-15", "notes": "SYNTHETIC"})
            elif sym != "FOO":
                log.append({"file": "raw/" + name, "sha256": _sha_bytes(body.encode()), "symbol": sym})
        with open(os.path.join(self.ca_dir, "collection_log.jsonl"), "w") as fh:
            for rec in log:
                fh.write(json.dumps(rec, sort_keys=True) + "\n")
        self.decision_log = os.path.join(self.root, "DECISION_LOG.md")
        recon_dir = os.path.join(self.ca_dir, "reconciliation")
        os.makedirs(recon_dir, exist_ok=True)
        self.recon_sha = {}
        for sym in ("AAA", "DDD", "OLDX", "FOO", "EEE", "CCC", "BBB", "GAP", "ISX", "SPL"):
            body = json.dumps({
                "schema": ca.RECONCILIATION_SCHEMA,
                "symbol": sym,
                "from_date": "2016-01-01",
                "to_date": "2025-12-31",
                "source_a_sha256": self.ev_sha_a,
                "source_b_sha256": self.ev_sha_b,
                "events": [{"key": "DIVIDEND|2022-01-05|", "source_a": "PRESENT", "source_b": "PRESENT",
                            "status": ca.EVENT_MATCH}],
                "unresolved": [],
                "status": ca.RECONCILIATION_OK,
            }, sort_keys=True) + "\n"
            path = os.path.join(recon_dir, "%s.json" % sym)
            with open(path, "w") as fh:
                fh.write(body)
            self.recon_sha[sym] = _sha_file(path)
        with open(self.decision_log, "w") as fh:
            items = "; ".join("%s %s %s %s 2016-01-01..2025-12-31"
                              % (self.ev_sha_a, self.ev_sha_b, self.recon_sha[s], s)
                              for s in ("AAA", "DDD", "OLDX", "FOO", "EEE", "CCC", "BBB", "GAP"))
            fh.write("### D99. SYNTHETIC completeness acceptance\n- **Status:** `USER_APPROVED` (synthetic).\n"
                     "- **Completeness window accepted:** %s\n\n" % items)
            fh.write("### D98. SYNTHETIC general approval\n- **Status:** `USER_APPROVED` (synthetic).\n\n"
                     "### D42. SYNTHETIC stated constraint\n- **Status:** `USER_STATED` (synthetic).\n")
        if duplicate:
            cov.append(dict(cov[0]))
        self.coverage = os.path.join(self.ca_dir, "coverage.csv")
        self._csv(self.coverage, ca.COVERAGE_COLUMNS, cov)
        spl = "raw/ca_SPL_2016_2025.json"
        self.actions = os.path.join(self.ca_dir, "actions.csv")
        self._csv(self.actions, ca.COLUMNS, [
            {"symbol": "SPL", "ex_date": "2022-01-12", "action": "SPLIT", "ratio_from": "1", "ratio_to": "10",
             "source": "NSE corporate actions (saved API response)", "source_file": spl,
             "source_sha256": _sha_file(os.path.join(self.ca_dir, spl)),
             "recorded_on": "2026-11-15", "notes": "SYNTHETIC"}])
        rows = []
        if completeness:
            for sym, decision in (("AAA", "D99"), ("DDD", "D99"), ("BBB", ""), ("GAP", "D99"), ("OLDX", "D99"),
                                  ("FOO", "D99"), ("EEE", "D99"), ("CCC", "D42"), ("ISX", "D99"),
                                  ("SPL", "D98")):
                src_a, sha_a = "../evidence.txt", self.ev_sha_a
                src_b, sha_b = "../evidence_b.txt", self.ev_sha_b
                if sym == "GAP":
                    sha_a = "0" * 64                                  # hash does not match
                if sym == "ISX":                                     # a saved API response is not proof
                    src_a, sha_a = ("raw/ca_ISX_2016_2025.json",
                                    _sha_file(os.path.join(self.ca_dir, "raw", "ca_ISX_2016_2025.json")))
                rows.append({
                    "symbol": sym, "from_date": "2016-01-01", "to_date": "2025-12-31",
                    "source_a": "SYNTHETIC completeness source A", "source_a_file": src_a,
                    "source_a_sha256": sha_a,
                    "source_b": "SYNTHETIC completeness source B", "source_b_file": src_b,
                    "source_b_sha256": sha_b,
                    "reconciliation_file": "reconciliation/%s.json" % sym,
                    "reconciliation_sha256": self.recon_sha[sym],
                    "owner_decision": decision, "recorded_on": "2026-11-15", "notes": "SYNTHETIC",
                })
        self.completeness = os.path.join(self.ca_dir, "completeness.csv")
        self._csv(self.completeness, ca.COMPLETENESS_COLUMNS, rows)

    @staticmethod
    def _csv(path, columns, rows):
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(columns), lineterminator="\n")
            w.writeheader()
            w.writerows(rows)

    def build(self):
        return p0.build(START, END, universe_csv=self.universe_csv, records_csv=self.records_csv,
                        coverage_csv=self.coverage, actions_csv=self.actions, calendar_dir=self.cal_dir,
                        raw_dir=self.raw, manifest=self.manifest, completeness_csv=self.completeness,
                        decision_log=self.decision_log)


class EndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="p0-e2e-")
        cls.fx = Fixture(cls.tmp)
        cls.result = cls.fx.build()
        cls.rows = {(r["symbol"], r["trade_date"]): r for r in cls.result["rows"]}
        cls.fx_bodies = p0.corporate_action_bodies(cls.fx.coverage, cls.fx.actions,
                                                   os.path.join(cls.fx.ca_dir, "raw"),
                                                   os.path.join(cls.fx.ca_dir, "collection_log.jsonl"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def g(self, sym, day, gate):
        return self.rows[(sym, day)]["gate_results"][gate]

    def test_member_dates_follow_the_calendar_and_the_periods(self):
        days = sorted(set(d for _, d in self.rows))
        # sessions 4-7, 10-13, 17-18, 21 plus the UNRESOLVED 20th; no weekend, holiday or Muhurat date
        self.assertEqual(days, ["2022-01-04", "2022-01-05", "2022-01-06", "2022-01-07", "2022-01-10", "2022-01-11",
                                "2022-01-12", "2022-01-13", "2022-01-17", "2022-01-18", "2022-01-19",
                                "2022-01-20", "2022-01-21"])
        self.assertNotIn(("CCC", "2022-01-13"), self.rows)            # REMOVE: member through the day before
        self.assertIn(("CCC", "2022-01-12"), self.rows)
        self.assertNotIn(("DDD", "2022-01-11"), self.rows)            # ADD: member from the effective date
        self.assertIn(("DDD", "2022-01-12"), self.rows)
        self.assertNotIn(("NEWX", "2022-01-12"), self.rows)
        self.assertNotIn(("OLDX", "2022-01-13"), self.rows)
        u = univ.load(self.fx.universe_csv)
        expected = sum(len(u.members(D.fromisoformat(d))) for d in days)
        self.assertEqual(len(self.result["rows"]), expected)
        self.assertEqual(len(self.rows), len(self.result["rows"]))   # one row per symbol-date

    def test_certified_rows_pass_every_data_gate_and_only_with_proved_completeness(self):
        certified = sorted(k for k, r in self.rows.items() if r["final_eligibility"] == de.ELIGIBLE)
        self.assertTrue(certified)
        self.assertEqual({s for s, _ in certified}, {"AAA", "DDD"})
        for k in certified:
            r = self.rows[k]
            self.assertEqual(r["failed_gates"], "")
            self.assertIn(r["gate_results"]["corporate_action"], (de.CA_COMPLETE, de.CA_COVERED_NONE))
            self.assertEqual(r["ca_tier"], ca.CA_COMPLETENESS_VERIFIED)
            self.assertEqual(r["research_use"], p0.USE_CERTIFIED)
            self.assertEqual(r["limitations"], "")
            self.assertFalse(r["authorises_order"])
            self.assertNotIn("gtf", r["gate_results"])
        self.assertEqual(self.g("DDD", "2022-01-13", "corporate_action"), de.CA_COVERED_NONE)   # `[]` + register
        self.assertEqual(self.g("AAA", "2022-01-05", "corporate_action"), de.CA_COMPLETE)

    def test_a_response_without_a_completeness_window_is_exploratory_only(self):
        r = self.rows[("BBB", "2022-01-05")]
        self.assertEqual(r["gate_results"]["corporate_action"], ca.RESPONSE_PRESENT_COMPLETENESS_NOT_PROVED)
        self.assertEqual(r["ca_tier"], ca.CA_RESPONSE_PRESENT_NOT_COMPLETE)
        self.assertEqual(r["research_use"], p0.USE_EXPLORATORY)
        self.assertEqual(r["limitations"], ca.CA_UNVERIFIED)
        # BBB's register row names no owner decision, GAP's cites a hash that does not match
        self.assertNotEqual(self.g("GAP", "2022-01-05", "corporate_action"), de.CA_COMPLETE)

    def test_review_fail_open_paths_stay_closed(self):
        day = "2022-01-05"
        # M-2 and N-1: FOO's `[]` is missing from the collector's log AND FOO is touched by a rename record
        # (unverified); the rename rule catches it first. The unlogged-hash rule alone is unit-tested in
        # test_research_p0_certification (CorporateActionBodies, CompletenessRegister).
        self.assertEqual(self.g("FOO", day, "corporate_action"), p0.CA_EMPTY_RENAMED)
        self.assertFalse(self.fx_bodies["FOO"]["hash_verified"])
        # M-3: an old ticker's empty body never passes, register window or not
        self.assertEqual(self.g("OLDX", day, "corporate_action"), p0.CA_EMPTY_RENAMED)
        # M-1: an error page is not a response
        self.assertEqual(self.g("EEE", day, "corporate_action"), ca.MALFORMED_RESPONSE)
        # M-4: a USER_STATED decision and a saved API response as "proof" both fail
        self.assertNotIn(self.g("CCC", day, "corporate_action"), (de.CA_COMPLETE, de.CA_COVERED_NONE))
        self.assertNotIn(self.g("ISX", day, "corporate_action"), (de.CA_COMPLETE, de.CA_COVERED_NONE))
        # R-2 / D66: a USER_APPROVED decision without a "Completeness window accepted" line does not count
        self.assertNotIn(self.g("SPL", day, "corporate_action"), (de.CA_COMPLETE, de.CA_COVERED_NONE))
        for sym in ("FOO", "OLDX", "EEE", "CCC", "ISX", "SPL"):
            self.assertNotEqual(self.rows[(sym, day)]["ca_tier"], ca.CA_COMPLETENESS_VERIFIED, sym)

    def test_membership_identity_and_rename_gates(self):
        self.assertEqual(self.g("CCC", "2022-01-05", "membership"), p0.MEMBERSHIP_UNVERIFIED)
        self.assertEqual(self.rows[("CCC", "2022-01-05")]["final_eligibility"], de.EXCLUDED_MEMBERSHIP)
        self.assertEqual(self.g("EEE", "2022-01-05", "identity"), p0.ID_UNKNOWN)
        # verified rename: the step into NEWX joins OLDX's prior close
        self.assertEqual(self.g("NEWX", "2022-01-13", "price_continuity"), de.PRICE_CONTINUOUS)
        self.assertEqual(self.g("NEWX", "2022-01-13", "identity"), de.IDENTITY_RESOLVED)
        # unverified rename: never joined; identity of BAR rests on an unverified record
        self.assertEqual(self.g("BAR", "2022-01-13", "price_continuity"), p0.PX_PRIOR_MISSING)
        self.assertEqual(self.g("BAR", "2022-01-13", "identity"), p0.ID_UNVERIFIED_RECORD)
        # ISIN change: two periods, the step across it is never spliced
        self.assertEqual(self.rows[("ISX", "2022-01-12")]["isin"], ISX_OLD)
        self.assertEqual(self.rows[("ISX", "2022-01-13")]["isin"], ISX_NEW)
        self.assertEqual(self.g("ISX", "2022-01-13", "price_continuity"), p0.PX_ISIN_CHANGE)

    def test_eod_calendar_and_price_gates(self):
        self.assertEqual(self.g("BBB", "2022-01-11", "eod"), p0.EOD_NON_EQ_ONLY + ":BE")      # BE never read as EQ
        self.assertEqual(self.g("BBB", "2022-01-12", "price_continuity"), p0.PX_PRIOR_NON_EQ + ":BE")
        self.assertEqual(self.g("AAA", "2022-01-18", "eod"), p0.EOD_NO_FILE)                  # nothing filled
        self.assertEqual(self.g("AAA", "2022-01-19", "price_continuity"), p0.PX_PRIOR_MISSING)
        self.assertEqual(self.g("AAA", "2022-01-20", "calendar"), p0.CAL_UNRESOLVED)
        self.assertEqual(self.g("AAA", "2022-01-21", "price_continuity"), p0.PX_CALENDAR_UNRESOLVED)
        # review M-5: the chain is intact across the held Muhurat file, and the step still fails
        self.assertEqual(self.g("AAA", "2022-01-10", "price_continuity"), p0.PX_ACROSS_EXCLUDED)
        self.assertEqual(self.g("CCC", "2022-01-10", "price_continuity"), p0.PX_EXCLUDED_SESSION)
        self.assertEqual(self.g("SPL", "2022-01-12", "price_continuity"), p0.PX_PRICE_EVENT + ":SPLIT")
        self.assertEqual(self.g("GAP", "2022-01-12", "price_continuity"), p0.PX_SCALE_GAP)
        self.assertEqual(self.g("GAP", "2022-01-13", "price_continuity"), de.PRICE_CONTINUOUS)
        self.assertEqual(self.g("AAA", "2022-01-17", "price_continuity"), de.PRICE_CONTINUOUS)   # holiday gap

    def test_reconciliation_register_and_summary(self):
        s = self.result["summary"]
        self.assertTrue(all(s["reconciliation"].values()), s["reconciliation"])
        self.assertEqual(s["certified_symbol_dates"] + s["excluded_symbol_dates"], s["member_dates"])
        self.assertEqual(s["calendar_unresolved_dates_in_window"], ["2022-01-20"])
        self.assertIn(MUHURAT.isoformat(), s["archives_held_on_non_sessions"])
        self.assertEqual(s["full_index_certified_dates"], 0)
        # counted: AAA, DDD, OLDX, FOO, EEE. Ignored: BBB (no decision), GAP (hash), CCC (D42 is
        # USER_STATED), ISX (cites a saved API response), SPL (D98 is USER_APPROVED but accepts no window)
        self.assertEqual(s["completeness_register"]["proved_windows"], 5)
        self.assertEqual(s["universe_matches_ledger_conversion"], "NOT_CHECKED")
        links = {(x["previous_symbol"], x["new_symbol"]): x["status"] for x in s["rename_links"]}
        self.assertEqual(links, {("OLDX", "NEWX"): instruments.RENAME_VERIFIED,
                                 ("FOO", "BAR"): instruments.RENAME_UNVERIFIED})
        reg = p0.register(self.result["rows"])
        self.assertTrue(p0.register_covers_exactly_once(self.result["rows"], reg))

    def test_outputs_are_deterministic_and_separate(self):
        a, b = os.path.join(self.tmp, "out_a"), os.path.join(self.tmp, "out_b")
        p0.write_outputs(self.result, a, os.path.join(a, "matrix.csv"))
        p0.write_outputs(self.fx.build(), b, os.path.join(b, "matrix.csv"))
        for name in sorted(os.listdir(a)):
            with open(os.path.join(a, name), "rb") as x, open(os.path.join(b, name), "rb") as y:
                self.assertEqual(x.read(), y.read(), name)
        with open(os.path.join(a, "P0_CERTIFIED_RESEARCH_UNIVERSE.csv"), newline="") as fh:
            cert = list(csv.DictReader(fh))
        self.assertEqual(len(cert), self.result["summary"]["certified_symbol_dates"])
        self.assertTrue(all(r["certification_scope"] == p0.SCOPE and r["authorises_order"] == "false"
                            and r["gtf_trade_eligibility"] == p0.GTF_NOT_EVALUATED for r in cert))
        with open(os.path.join(a, "P0_RESEARCH_EXCLUSION_REGISTER.csv"), newline="") as fh:
            reg = list(csv.DictReader(fh))
        self.assertNotIn(p0.USE_CERTIFIED, {r["research_use"] for r in reg})
        # review L-5: expand every register interval over the window's sessions, not its endpoints
        days = sorted(set(d for _, d in self.rows))
        covered = {(r["symbol"], d) for r in reg for d in days if r["from_date"] <= d <= r["to_date"]
                   and (r["symbol"], d) in self.rows}
        self.assertFalse({(r["symbol"], r["trade_date"]) for r in cert} & covered)
        self.assertEqual(len(covered) + len(cert), len(self.rows))
        with open(os.path.join(a, "P0_CERTIFICATION_SUMMARY.json")) as fh:
            self.assertFalse(json.load(fh)["authorises_order"])


class Refusals(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="p0-e2e-ref-")
        self.addCleanup(shutil.rmtree, self.tmp)

    def test_without_the_completeness_register_nothing_certifies(self):
        fx = Fixture(self.tmp, completeness=False)
        res = fx.build()
        self.assertEqual(res["summary"]["certified_symbol_dates"], 0)
        self.assertNotIn(ca.CA_COMPLETENESS_VERIFIED, {r["ca_tier"] for r in res["rows"]})
        self.assertTrue(all(r["limitations"] == ca.CA_UNVERIFIED for r in res["rows"]))

    def test_a_duplicate_coverage_row_stops_the_build(self):
        fx = Fixture(self.tmp, duplicate_coverage=True)
        with self.assertRaises(ValueError):
            fx.build()

    def test_a_tampered_archive_stops_the_build(self):
        fx = Fixture(self.tmp)
        name = sorted(os.listdir(fx.raw))[0]
        with open(os.path.join(fx.raw, name), "ab") as fh:
            fh.write(b"\0")
        with self.assertRaises(bhavcopy.BhavcopyError):
            fx.build()

    def test_an_unreadable_completeness_register_stops_the_build(self):
        fx = Fixture(self.tmp)
        with open(fx.completeness, "w") as fh:
            fh.write("symbol,from_date\nAAA,2016-01-01\n")
        with self.assertRaises(ca.CorporateActionError):
            fx.build()


if __name__ == "__main__":
    unittest.main()
