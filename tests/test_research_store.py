"""Research store and paper-trade journal (nse/research/store.py).

Scans come from the REAL pipeline on the SYNTHETIC long history of tests/_research.py (as in
test_research_e2e). A few scan dicts are then edited to carry a REJECTED or BLOCKED candidate
whose status still follows from its gate outcomes (models.derive_status); those edited
dicts are labelled SYNTHETIC in their universe field. Every database lives in a
tempfile.mkdtemp() folder.
"""

import argparse
import contextlib
import copy
import datetime
import io
import json
import os
import shutil
import sqlite3
import tempfile
import unittest

import _research as R
from nse.research import models as m, reports, scanner, store

CAL = R.WeekdayCalendar()
CODES = [x[0] for x in m.CHECKLIST]


def scan_result(candles, generated_at="SYNTHETIC-TEST"):
    cfg = scanner.ScanConfig(as_of=candles[-1].end, calendar=CAL, calendar_label="TEST_WEEKDAYS",
                             risk_per_trade=1000.0, generated_at=generated_at)
    return scanner.scan([R.daily_input("SYN", candles)], cfg)


def with_status(scan_dict, gate, outcome, status):
    """SYNTHETIC copy whose first candidate has gate set to outcome (status follows)."""
    d = copy.deepcopy(scan_dict)
    d["universe"] = "SYNTHETIC_EDITED_" + status
    c = d["symbols"][0]["candidates"][0]
    for g in c["gates"]:
        if g["gate"] == gate:
            g["outcome"] = outcome
    c["status"] = status
    return d


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = R.long_mit_candles()
        cls.touched = R.extend(cls.base, [(176.0, 176.5, 159.5, 170.0), (170.0, 171.0, 169.0, 170.5)])  # low <= PL
        cls.r1 = scan_result(cls.base)
        cls.r2 = scan_result(cls.touched)
        cls.d1 = reports.to_dict(cls.r1)
        cls.d2 = reports.to_dict(cls.r2)
        [cls.cand] = cls.r1.candidates()
        assert cls.cand.status == m.ACTIONABLE

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db = os.path.join(self.tmp, "store.db")
        self.conn = store.open_store(self.db)

    def tearDown(self):
        self.conn.close()
        shutil.rmtree(self.tmp)

    def entry(self, key, **kw):
        lv = self.cand.levels
        e = {"symbol": "SYN", "zone_id": self.cand.zone["zone_id"], "scan_key": key,
             "planned_entry": lv["entry"][1], "planned_stop": lv["sl"]["normal"][0],
             "planned_target": self.cand.gate("G7").evidence["target"]["proximal"], "quantity": 100,
             "alert_note": "SYN DZ - 7/7, Monthly LOC, Weekly Up. Set & Forget BUY. (SYNTHETIC)",
             "checklist": {c: True for c in CODES}, "recorded_at": "2024-02-02T18:00:00"}
        e.update(kw)
        return e


class Migrations(Base):
    def test_reopening_is_a_noop(self):
        before = store.applied_migrations(self.conn)
        self.conn.close()
        self.conn = store.open_store(self.db)
        self.assertEqual(store.applied_migrations(self.conn), before)
        self.assertEqual([v for v, _, _ in before], [v for v, _, _ in store.MIGRATIONS])

    def test_checksum_drift_is_detected(self):
        self.conn.close()
        edited = ((1, store.MIGRATIONS[0][1], store.MIGRATIONS[0][2] + "\n-- edited"),)
        with self.assertRaises(store.MigrationDriftError):
            store.open_store(self.db, migrations=edited)
        self.conn = store.open_store(self.db)            # the unchanged code still opens it

    def test_unknown_recorded_version_is_detected(self):
        self.conn.close()
        with self.assertRaises(store.MigrationDriftError):
            store.open_store(self.db, migrations=())
        self.conn = store.open_store(self.db)

    def test_no_destructive_sql_in_any_migration(self):
        for v, name, sql in store.MIGRATIONS:
            self.assertEqual(store.destructive_statements(sql), [], name)

    def test_destructive_detector_catches_each_form(self):
        for sql in ("DROP TABLE scans;", "CREATE TABLE x (a); DELETE FROM x;", "UPDATE scans SET as_of = '';",
                    "ALTER TABLE scans DROP COLUMN as_of;"):
            self.assertNotEqual(store.destructive_statements(sql), [], sql)
        self.assertEqual(store.destructive_statements("UPDATE t SET a = 1 WHERE b = 2;"), [])
        self.conn.close()
        bad = store.MIGRATIONS + ((2, "v2_bad", "DROP TABLE alerts;"),)
        with self.assertRaises(store.MigrationDriftError):
            store.open_store(self.db, migrations=bad)
        self.conn = store.open_store(self.db)
        self.assertIsNotNone(self.conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'alerts'").fetchone())

    def test_sql_literals_match_models(self):
        self.assertEqual(store._V1_STATUSES, m.STATUS_ORDER)
        self.assertEqual(store._V1_OUTCOMES, m.OUTCOMES)
        self.assertEqual(store._V1_KINDS, store.EVENT_KINDS)

    def test_foreign_keys_are_on(self):
        self.assertEqual(self.conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)


class Import(Base):
    def test_scan_key_is_sha256_of_scan_json(self):
        import hashlib
        status, key = store.import_scan(self.conn, self.d1)
        self.assertEqual(status, store.IMPORTED)
        self.assertEqual(key, hashlib.sha256(reports.to_json(self.r1).encode("utf-8")).hexdigest())
        self.assertEqual(store.scan_json(self.conn, key), reports.to_json(self.r1))   # stored verbatim

    def test_import_is_idempotent(self):
        _, key = store.import_scan(self.conn, self.d1)
        rows = lambda: [self.conn.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0]
                        for t in ("scans", "symbol_results", "candidates", "gate_results", "findings", "blocked_zones")]
        before = rows()
        self.assertEqual(store.import_scan(self.conn, copy.deepcopy(self.d1)), (store.ALREADY_PRESENT, key))
        self.assertEqual(rows(), before)

    def test_counts_reconcile_with_the_scan_summary(self):
        for r, d in ((self.r1, self.d1), (self.r2, self.d2)):
            _, key = store.import_scan(self.conn, d)
            got, want = store.status_counts(self.conn, key), reports.summary(r)
            for k in ("candidate_status_counts", "candidate_records", "symbol_status_counts", "symbols_processed",
                      "blocked_zone_records", "data_quality_findings"):
                self.assertEqual(got[k], want[k], k)

    def test_statuses_and_gates_stored_verbatim(self):
        _, key = store.import_scan(self.conn, self.d1)
        r = self.conn.execute("SELECT * FROM candidates WHERE scan_key = ?", (key,)).fetchone()
        self.assertEqual(r["status"], self.cand.status)
        self.assertEqual([r[g] for g in m.GATES], [g.outcome for g in self.cand.gates])
        self.assertEqual(json.loads(r["manual_checks"]), self.cand.manual_checks)   # checklist survives
        self.assertIn(m.NOT_EXTERNALLY_VALIDATED, json.loads(r["limitations"]))

    def test_status_outside_status_order_is_rejected(self):
        bad = copy.deepcopy(self.d1)
        bad["symbols"][0]["candidates"][0]["status"] = "APPROVED"
        with self.assertRaises(store.StoreError):
            store.import_scan(self.conn, bad)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM scans").fetchone()[0], 0)
        with self.assertRaises(sqlite3.IntegrityError):         # the CHECK constraint also refuses it
            with self.conn:
                _, key = store.import_scan(self.conn, self.d2)
                self.conn.execute("INSERT INTO candidates (scan_key, symbol, zone_id, trade_type, execution_tf, as_of, "
                                  "status, " + ", ".join(m.GATES) + ", status_reasons, manual_review, manual_checks, "
                                  "levels, zone, limitations) VALUES (?, 'SYN', 'z', 'MIT', 'D', 'x', 'APPROVED', "
                                  + ", ".join(["'PASS'"] * 9) + ", '[]', '[]', '[]', '{}', '{}', '[]')", (key,))

    def test_status_inconsistent_with_gates_is_rejected(self):
        bad = with_status(self.d1, "G3", m.FAIL, m.ACTIONABLE)     # a FAIL gate can never be ACTIONABLE
        with self.assertRaises(store.StoreError):
            store.import_scan(self.conn, bad)

    def test_malformed_scan_is_rejected(self):
        bad = copy.deepcopy(self.d1)
        del bad["symbols"]
        with self.assertRaises(store.StoreError):
            store.import_scan(self.conn, bad)

    def test_archive_is_append_only(self):
        _, key = store.import_scan(self.conn, self.d1)
        for sql in ("UPDATE candidates SET status = 'REJECTED'", "DELETE FROM scans"):
            with self.assertRaises(sqlite3.DatabaseError):
                with self.conn:
                    self.conn.execute(sql)
        self.assertEqual(self.conn.execute("SELECT status FROM candidates").fetchone()[0], m.ACTIONABLE)


class Queries(Base):
    def test_zone_history_fresh_then_tested(self):
        # D3: once tested, the zone is never a fresh candidate again; the store shows it going
        _, k1 = store.import_scan(self.conn, self.d1)
        _, k2 = store.import_scan(self.conn, self.d2)
        zid = self.cand.zone["zone_id"]
        h = store.zone_history(self.conn, "SYN", zid)
        self.assertEqual([x["scan_key"] for x in h], [k1, k2])
        self.assertEqual((h[0]["presence"], h[0]["candidate_status"]), ("CANDIDATE", m.ACTIONABLE))
        self.assertEqual((h[1]["presence"], h[1]["candidate_status"]), ("ABSENT", None))
        self.assertEqual(h[1]["symbol_status"], scanner.SYMBOL_NO_EXECUTION_ZONE)

    def test_zone_history_is_chronological_whatever_the_import_order(self):
        store.import_scan(self.conn, self.d2)
        store.import_scan(self.conn, self.d1)
        h = store.zone_history(self.conn, "SYN", self.cand.zone["zone_id"])
        self.assertEqual([x["as_of"] for x in h], sorted([self.d1["as_of"], self.d2["as_of"]]))

    def test_unknown_zone_has_no_candidate(self):
        store.import_scan(self.conn, self.d1)
        self.assertEqual([x["presence"] for x in store.zone_history(self.conn, "SYN", "demand-0-0")], ["ABSENT"])
        self.assertEqual(store.zone_history(self.conn, "NOPE", "x"), [])

    def test_latest_scan(self):
        self.assertIsNone(store.latest_scan(self.conn))
        _, k1 = store.import_scan(self.conn, self.d1)
        _, k2 = store.import_scan(self.conn, self.d2)
        self.assertEqual(store.latest_scan(self.conn)["scan_key"], k2)
        self.assertEqual(store.latest_scan(self.conn, as_of_max=self.d1["as_of"])["scan_key"], k1)
        self.assertIsNone(store.latest_scan(self.conn, as_of_max="2000-01-01T00:00:00"))

    def test_status_counts_unknown_scan(self):
        with self.assertRaises(store.StoreError):
            store.status_counts(self.conn, "0" * 64)

    def test_backup_copies_and_refuses_to_overwrite(self):
        _, key = store.import_scan(self.conn, self.d1)
        dest = os.path.join(self.tmp, "copy.db")
        store.backup(self.conn, dest)
        copy_conn = store.open_store(dest)
        try:
            self.assertEqual(store.scan_json(copy_conn, key), store.scan_json(self.conn, key))
        finally:
            copy_conn.close()
        size = os.path.getsize(dest)
        with self.assertRaises(FileExistsError):
            store.backup(self.conn, dest)
        self.assertEqual(os.path.getsize(dest), size)

    def test_ingestion_events_and_alerts(self):
        store.record_ingestion_event(self.conn, "BHAVCOPY", "cm01JAN2024bhav.csv.zip", "MISSING",
                                     {"note": "SYNTHETIC"}, "2024-01-02T09:00:00")
        self.assertEqual([e["status"] for e in store.ingestion_events(self.conn, "BHAVCOPY")], ["MISSING"])
        self.assertEqual(store.record_alert(self.conn, "a1", {"x": 1}, "2024-01-02T09:00:00"), store.IMPORTED)
        self.assertEqual(store.record_alert(self.conn, "a1", {"x": 1}, "2024-01-02T09:00:00"), store.ALREADY_PRESENT)
        with self.assertRaises(store.StoreError):
            store.record_alert(self.conn, "a1", {"x": 2}, "2024-01-02T09:00:00")
        with self.assertRaises(store.StoreError):
            store.record_ingestion_event(self.conn, "", "k", "OK", {}, "2024-01-02T09:00:00")


class Journal(Base):
    def setUp(self):
        super().setUp()
        _, self.key = store.import_scan(self.conn, self.d1)

    def add(self, **kw):
        return store.journal_add(self.conn, self.entry(self.key, **kw))

    def test_actionable_entry_records_status_from_the_scan(self):
        eid = self.add()
        r = self.conn.execute("SELECT * FROM journal_entries WHERE entry_id = ?", (eid,)).fetchone()
        self.assertEqual(r["candidate_status"], m.ACTIONABLE)
        self.assertEqual([e["kind"] for e in store.journal_events(self.conn, eid)], [store.PLANNED])

    def test_caller_cannot_supply_the_status(self):
        with self.assertRaises(store.StoreError):
            self.add(candidate_status=m.ACTIONABLE)

    def test_scan_key_must_exist(self):
        with self.assertRaises(store.StoreError):
            store.journal_add(self.conn, self.entry("f" * 64))

    def test_zone_not_a_candidate_is_refused(self):
        _, k2 = store.import_scan(self.conn, self.d2)              # the tested zone is gone (D3)
        with self.assertRaises(store.JournalRefused):
            store.journal_add(self.conn, self.entry(k2))

    def test_rejected_blocked_and_data_insufficient_are_refused(self):
        for gate, outcome, status in (("G3", m.FAIL, m.REJECTED), ("G0", m.BLOCKED, m.BLOCKED_STATUS),
                                      ("G5", m.DATA_INSUFFICIENT, m.STATUS_DATA_INSUFFICIENT)):
            _, k = store.import_scan(self.conn, with_status(self.d1, gate, outcome, status))
            with self.assertRaises(store.JournalRefused) as cm:
                store.journal_add(self.conn, self.entry(k))
            self.assertIn(status, str(cm.exception))
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM journal_entries").fetchone()[0], 0)

    def test_manual_review_needs_a_resolution_note(self):
        _, k = store.import_scan(self.conn, with_status(self.d1, "G6", m.MANUAL, m.MANUAL_REVIEW))
        with self.assertRaises(store.JournalRefused):
            store.journal_add(self.conn, self.entry(k))
        with self.assertRaises(store.StoreError):
            store.journal_add(self.conn, self.entry(k, manual_review_resolution="   "))
        eid = store.journal_add(self.conn, self.entry(k, manual_review_resolution="Owner reviewed G6 chart: coinciding."))
        self.assertEqual(self.conn.execute("SELECT candidate_status FROM journal_entries WHERE entry_id = ?",
                                           (eid,)).fetchone()[0], m.MANUAL_REVIEW)

    def test_every_checklist_code_must_be_explicit(self):
        partial = {c: True for c in CODES[1:]}
        with self.assertRaises(store.JournalRefused):
            self.add(checklist=partial)
        with self.assertRaises(store.JournalRefused):
            self.add(checklist=dict({c: True for c in CODES}, EXTRA=True))
        with self.assertRaises(store.JournalRefused):
            self.add(checklist=dict({c: True for c in CODES}, SECTOR=None))     # unknown is not confirmed
        eid = self.add(checklist=dict({c: True for c in CODES}, SECTOR=False))  # an honest "no" is recorded
        self.assertFalse(json.loads(self.conn.execute("SELECT checklist FROM journal_entries WHERE entry_id = ?",
                                                      (eid,)).fetchone()[0])["SECTOR"])

    def test_plan_inputs_are_validated(self):
        for kw in ({"planned_stop": 999.0}, {"quantity": 0}, {"quantity": 1.5}, {"alert_note": ""},
                   {"planned_entry": float("nan")}, {"recorded_at": "2024-01-01T00:00:00"}, {"recorded_at": "soon"}):
            with self.assertRaises(store.StoreError, msg=str(kw)):
                self.add(**kw)

    def test_stop_is_locked_after_trigger(self):
        eid = self.add()
        stop = self.entry(self.key)["planned_stop"]
        store.journal_event(self.conn, eid, store.PLANNED, "2024-02-03T10:00:00", stop_level=stop - 0.5)  # before trigger
        store.journal_event(self.conn, eid, store.TRIGGERED, "2024-02-05T10:00:00", price=161.0)
        with self.assertRaises(store.JournalRefused):
            store.journal_event(self.conn, eid, store.NOTE, "2024-02-05T11:00:00", stop_level=stop)   # RB 2139
        with self.assertRaises(store.JournalRefused):
            store.journal_event(self.conn, eid, store.PLANNED, "2024-02-05T11:00:00", stop_level=stop - 1)
        with self.assertRaises(store.JournalRefused):
            store.journal_event(self.conn, eid, store.TRIGGERED, "2024-02-05T12:00:00", price=158.0)  # RB 2140
        self.assertNotIn("ADD", " ".join(store.EVENT_KINDS))
        summary = store.journal_summary(self.conn, "2024-02")
        self.assertEqual(summary["trades"][0]["locked_stop"], stop - 0.5)

    def test_stop_loss_hit_and_zone_invalidated_are_distinct(self):
        eid = self.add()
        store.journal_event(self.conn, eid, store.TRIGGERED, "2024-02-05T10:00:00", price=161.0)
        store.journal_event(self.conn, eid, store.ZONE_INVALIDATED, "2024-02-06T15:30:00",
                            note="daily close below DL")
        self.assertEqual(store.journal_summary(self.conn, "2024-02")["trades"][0]["state"], "OPEN")  # not an exit
        store.journal_event(self.conn, eid, store.STOP_LOSS_HIT, "2024-02-07T10:00:00", price=155.76)
        t = store.journal_summary(self.conn, "2024-02")["trades"][0]
        self.assertEqual((t["state"], t["exit_kind"], t["zone_invalidated"]), ("CLOSED", store.STOP_LOSS_HIT, True))
        self.assertEqual([e["kind"] for e in store.journal_events(self.conn, eid)],
                         [store.PLANNED, store.TRIGGERED, store.ZONE_INVALIDATED, store.STOP_LOSS_HIT])

    def test_events_are_chronological_and_follow_the_lifecycle(self):
        eid = self.add()
        with self.assertRaises(store.JournalRefused):
            store.journal_event(self.conn, eid, store.NOTE, "2024-02-02T17:00:00")      # before PLANNED
        with self.assertRaises(store.JournalRefused):
            store.journal_event(self.conn, eid, store.TARGET_HIT, "2024-02-05T10:00:00", price=180.0)  # not triggered
        with self.assertRaises(store.StoreError):
            store.journal_event(self.conn, eid, store.TRIGGERED, "2024-02-05T10:00:00")  # no price
        with self.assertRaises(store.StoreError):
            store.journal_event(self.conn, eid, "ADD_TO_POSITION", "2024-02-05T10:00:00", price=1.0)
        store.journal_event(self.conn, eid, store.CANCELLED, "2024-02-05T10:00:00")
        with self.assertRaises(store.JournalRefused):
            store.journal_event(self.conn, eid, store.TRIGGERED, "2024-02-06T10:00:00", price=161.0)
        store.journal_event(self.conn, eid, store.NOTE, "2024-02-06T10:00:00", note="zone no longer fresh")
        with self.assertRaises(sqlite3.DatabaseError):                                   # append-only
            with self.conn:
                self.conn.execute("UPDATE journal_events SET kind = 'NOTE'")

    def test_monthly_summary_and_ceiling(self):
        ids = [self.add() for _ in range(store.MONTHLY_TRADE_CEILING + 1)]
        e = self.entry(self.key)
        risk = e["planned_entry"] - e["planned_stop"]
        for i, eid in enumerate(ids[:-1]):
            store.journal_event(self.conn, eid, store.TRIGGERED, "2024-02-%02dT10:00:00" % (5 + i),
                                price=e["planned_entry"])
        with self.assertRaises(store.JournalRefused):          # the 11th trade in a month (RB 2392, 2408)
            store.journal_event(self.conn, ids[-1], store.TRIGGERED, "2024-02-28T10:00:00", price=e["planned_entry"])
        store.journal_event(self.conn, ids[0], store.TARGET_HIT, "2024-02-20T10:00:00",
                            price=e["planned_entry"] + 2 * risk)
        store.journal_event(self.conn, ids[1], store.STOP_LOSS_HIT, "2024-02-21T10:00:00", price=e["planned_stop"])
        s = store.journal_summary(self.conn, "2024-02")
        self.assertEqual((s["trades_taken"], s["ceiling"], s["over_ceiling"]), (10, 10, False))
        self.assertEqual((s["closed"], s["open"], s["wins"], s["losses"]), (2, 8, 1, 1))
        self.assertEqual(s["r_multiples"], [2.0, -1.0])
        self.assertEqual(s["win_rate_pct"], 50.0)
        self.assertIn("Not validation", s["note"])
        empty = store.journal_summary(self.conn, "2024-03")
        self.assertEqual((empty["trades_taken"], empty["over_ceiling"], empty["win_rate_pct"]), (0, False, None))
        for bad in ("2024-13", "2024-2", ""):
            with self.assertRaises(store.StoreError):
                store.journal_summary(self.conn, bad)

    def test_ten_trades_is_not_over_the_ceiling(self):
        for i in range(store.MONTHLY_TRADE_CEILING):
            store.journal_event(self.conn, self.add(), store.TRIGGERED, "2024-02-%02dT10:00:00" % (5 + i), price=161.0)
        self.assertFalse(store.journal_summary(self.conn, "2024-02")["over_ceiling"])


class JournalReviewRegressions(Base):
    """Independent review 2026-11-02: a later stored scan in which the zone is tested (no longer
    a candidate) supersedes the earlier ACTIONABLE scan (D3); plans below 2:1 are refused (RB 82)."""

    def setUp(self):
        super().setUp()
        _, self.k1 = store.import_scan(self.conn, self.d1)
        _, self.k2 = store.import_scan(self.conn, self.d2)            # the PL is touched here

    def test_entry_after_a_later_scan_shows_the_zone_gone_is_refused(self):
        with self.assertRaises(store.JournalRefused) as cm:
            store.journal_add(self.conn, self.entry(self.k1, recorded_at=self.d2["as_of"]))
        self.assertIn("ZONE_NO_LONGER_CANDIDATE", str(cm.exception))
        with self.assertRaises(store.JournalRefused):
            store.journal_add(self.conn, self.entry(self.k1, recorded_at="2030-01-01T00:00:00"))

    def test_entry_before_the_later_scan_is_still_accepted(self):
        t1 = datetime.datetime.fromisoformat(self.d1["as_of"])
        self.assertIsInstance(store.journal_add(self.conn, self.entry(self.k1, recorded_at=t1.isoformat())), int)

    def test_plan_below_two_to_one_is_refused(self):
        e = self.entry(self.k1, recorded_at=self.d1["as_of"])
        risk = e["planned_entry"] - e["planned_stop"]
        e["planned_target"] = e["planned_entry"] + 1.99 * risk
        with self.assertRaises(store.JournalRefused):
            store.journal_add(self.conn, e)


class Cli(Base):
    def run_cli(self, argv):
        p = argparse.ArgumentParser()
        sub = p.add_subparsers(dest="cmd")
        store.add_commands(sub)
        args = p.parse_args(argv)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = args.func(args)
        return code, out.getvalue(), err.getvalue()

    def test_import_history_journal_summary_backup(self):
        self.conn.close()
        scan_path = os.path.join(self.tmp, "scan.json")
        with open(scan_path, "w", encoding="utf-8") as fh:
            fh.write(reports.to_json(self.r1) + "\n")
        code, out, _ = self.run_cli(["store-import", "--db", self.db, "--scan", scan_path])
        self.assertEqual(code, 0)
        res = json.loads(out)
        self.assertEqual(res["result"], store.IMPORTED)
        self.assertEqual(res["counts"]["candidate_status_counts"], {m.ACTIONABLE: 1})
        code, out, _ = self.run_cli(["store-import", "--db", self.db, "--scan", scan_path])
        self.assertEqual((code, json.loads(out)["result"]), (0, store.ALREADY_PRESENT))
        code, out, _ = self.run_cli(["store-zone-history", "--db", self.db, "--symbol", "SYN",
                                     "--zone", self.cand.zone["zone_id"]])
        self.assertEqual([x["presence"] for x in json.loads(out)], ["CANDIDATE"])
        entry_path = os.path.join(self.tmp, "entry.json")
        with open(entry_path, "w", encoding="utf-8") as fh:
            json.dump(self.entry(res["scan_key"]), fh)
        code, out, _ = self.run_cli(["journal-add", "--db", self.db, "--entry", entry_path])
        self.assertEqual(code, 0)
        eid = json.loads(out)["entry_id"]
        code, out, _ = self.run_cli(["journal-event", "--db", self.db, "--entry-id", str(eid), "--kind", "TRIGGERED",
                                     "--at", "2024-02-05T10:00:00", "--price", "161.0"])
        self.assertEqual((code, json.loads(out)["seq"]), (0, 2))
        code, _, err = self.run_cli(["journal-event", "--db", self.db, "--entry-id", str(eid), "--kind", "NOTE",
                                     "--at", "2024-02-05T11:00:00", "--stop", "150"])
        self.assertEqual(code, 1)
        self.assertIn("RB 2139", err)
        code, out, _ = self.run_cli(["journal-summary", "--db", self.db, "--month", "2024-02"])
        self.assertEqual((code, json.loads(out)["trades_taken"]), (0, 1))
        dest = os.path.join(self.tmp, "b.db")
        self.assertEqual(self.run_cli(["store-backup", "--db", self.db, "--dest", dest])[0], 0)
        self.assertEqual(self.run_cli(["store-backup", "--db", self.db, "--dest", dest])[0], 2)
        self.conn = store.open_store(self.db)

    def test_input_errors_exit_2(self):
        self.conn.close()
        missing = os.path.join(self.tmp, "none.json")
        self.assertEqual(self.run_cli(["store-import", "--db", self.db, "--scan", missing])[0], 2)
        self.assertEqual(self.run_cli(["journal-summary", "--db", self.db, "--month", "bad"])[0], 2)
        self.assertEqual(self.run_cli(["journal-event", "--db", self.db, "--entry-id", "9", "--kind", "NOTE",
                                       "--at", "2024-01-01T00:00:00"])[0], 2)
        self.conn = store.open_store(self.db)



class DestructiveSqlReviewRegression(unittest.TestCase):
    def test_hidden_deletes_and_replace_are_destructive(self):
        self.assertTrue(store.destructive_statements(
            "CREATE TRIGGER t AFTER INSERT ON scans BEGIN DELETE FROM candidates; END;"))
        self.assertTrue(store.destructive_statements("INSERT OR REPLACE INTO scans VALUES (1)"))
        for _, _, sql in store.MIGRATIONS:                # the shipped migrations stay additive
            self.assertEqual(store.destructive_statements(sql), [])

if __name__ == "__main__":
    unittest.main()
