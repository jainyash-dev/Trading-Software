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
                             risk_per_trade=1000.0, generated_at=generated_at,
                             corporate_action_coverage=R.verified_ca("SYN"))
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
        bad = store.MIGRATIONS + ((len(store.MIGRATIONS) + 1, "v_next_bad", "DROP TABLE alerts;"),)
        with self.assertRaisesRegex(store.MigrationDriftError, "not additive"):     # QA 2026-11-08
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

    def add_other(self, n):
        """An entry on a different instrument (the same synthetic scan under symbol SYNn), so
        one-order-per-zone does not stand in for the ceilings under test."""
        sym = "SYN%02d" % n
        d = json.loads(json.dumps(self.d1).replace('"SYN"', '"%s"' % sym))
        _, key = store.import_scan(self.conn, d)
        return store.journal_add(self.conn, self.entry(key, symbol=sym))

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
        ids = [self.add_other(n) for n in range(store.MONTHLY_TRADE_CEILING + 1)]
        e = self.entry(self.key)
        risk = e["planned_entry"] - e["planned_stop"]
        for i, eid in enumerate(ids[:-1]):
            store.journal_event(self.conn, eid, store.TRIGGERED, "2024-02-%02dT10:00:00" % (5 + i),
                                price=e["planned_entry"])
        store.journal_event(self.conn, ids[0], store.TARGET_HIT, "2024-02-20T10:00:00",
                            price=e["planned_entry"] + 2 * risk)
        store.journal_event(self.conn, ids[1], store.STOP_LOSS_HIT, "2024-02-21T10:00:00", price=e["planned_stop"])
        # 8 open positions, so only the monthly ceiling can refuse the 11th trade (RB 2392, 2408)
        with self.assertRaisesRegex(store.JournalRefused, "monthly maximum"):
            store.journal_event(self.conn, ids[-1], store.TRIGGERED, "2024-02-28T10:00:00", price=e["planned_entry"])
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

    def test_two_connections_cannot_both_commit_the_tenth_trigger(self):
        """Nine fills already taken; two connections race for the tenth monthly slot."""
        import threading
        ids = [self.add_other(n) for n in range(store.MONTHLY_TRADE_CEILING + 1)]
        price = 161.0
        for eid in ids[:store.MONTHLY_TRADE_CEILING - 1]:
            store.journal_event(self.conn, eid, store.TRIGGERED, "2024-02-%02dT10:00:00" % (5 + ids.index(eid)),
                                price=price)
        barrier = threading.Barrier(2)
        results = []

        def attempt(eid):
            conn = store.open_store(self.db)
            try:
                barrier.wait(timeout=10)
                seq = store.journal_event(conn, eid, store.TRIGGERED, "2024-02-20T10:00:00", price=price)
                results.append(("ok", seq))
            except store.JournalRefused as exc:
                results.append(("refused", str(exc)))
            finally:
                conn.close()

        threads = [threading.Thread(target=attempt, args=(eid,)) for eid in ids[-2:]]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(sorted(kind for kind, _ in results), ["ok", "refused"])
        self.assertIn("monthly maximum", [text for kind, text in results if kind == "refused"][0])
        self.assertEqual(store.journal_summary(self.conn, "2024-02")["trades_taken"], store.MONTHLY_TRADE_CEILING)

    def test_two_connections_cannot_both_commit_an_eleventh_trigger(self):
        """Ten fills already taken; two independent connections both attempt an 11th TRIGGERED.

        Expected: both refuse with JournalRefused; the monthly cap is never exceeded.
        Companion to the race for the tenth slot (which expects one success and one refusal).
        """
        import threading
        ids = [self.add_other(n) for n in range(store.MONTHLY_TRADE_CEILING + 2)]
        price = 161.0
        for i, eid in enumerate(ids[:store.MONTHLY_TRADE_CEILING]):
            store.journal_event(self.conn, eid, store.TRIGGERED, "2024-02-%02dT10:00:00" % (5 + i),
                                price=price)
        self.assertEqual(store.journal_summary(self.conn, "2024-02")["trades_taken"], store.MONTHLY_TRADE_CEILING)
        barrier = threading.Barrier(2)
        results = []

        def attempt(eid):
            conn = store.open_store(self.db)
            try:
                barrier.wait(timeout=10)
                store.journal_event(conn, eid, store.TRIGGERED, "2024-02-28T10:00:00", price=price)
                results.append(("ok", eid))
            except store.JournalRefused as exc:
                results.append(("refused", str(exc)))
            finally:
                conn.close()

        threads = [threading.Thread(target=attempt, args=(eid,)) for eid in ids[-2:]]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual([kind for kind, _ in results], ["refused", "refused"])
        self.assertTrue(all("monthly maximum" in text for kind, text in results if kind == "refused"))
        self.assertEqual(store.journal_summary(self.conn, "2024-02")["trades_taken"], store.MONTHLY_TRADE_CEILING)
        self.assertEqual(
            store.portfolio_at(self.conn, "2024-02-28T12:00:00")["trades_triggered_this_month"],
            store.MONTHLY_TRADE_CEILING,
        )

    def test_fill_after_ten_verified_sessions_is_refused_and_expired_still_records(self):
        eid = self.add()
        store.journal_order_submitted(self.conn, eid, "2024-02-05T10:00:00", order_ref="KITE-1")
        with self.assertRaisesRegex(store.JournalRefused, "ORDER_EXPIRED"):
            store.journal_event(self.conn, eid, store.TRIGGERED, "2024-03-15T10:00:00", price=161.0,
                                calendar=R.WeekdayCalendar())
        store.journal_event(self.conn, eid, store.EXPIRED, "2024-03-15T10:00:00", note="left to expire")
        self.assertEqual(store.journal_events(self.conn, eid)[-1]["kind"], store.EXPIRED)

    def test_ten_trades_is_not_over_the_ceiling(self):
        for i in range(store.MONTHLY_TRADE_CEILING):
            store.journal_event(self.conn, self.add_other(i), store.TRIGGERED, "2024-02-%02dT10:00:00" % (5 + i),
                                price=161.0)
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


class JournalAuditRegressions20261106(Base):
    """Journal holes confirmed by the 2026-11-06 audit (Agent 4 CE-J1/J2/J3/J5)."""

    def setUp(self):
        super().setUp()
        _, self.k1 = store.import_scan(self.conn, self.d1)
        self.t1 = datetime.datetime.fromisoformat(self.d1["as_of"])

    def add(self, key=None, **kw):
        kw.setdefault("recorded_at", self.t1.isoformat())
        return store.journal_add(self.conn, self.entry(key or self.k1, **kw))

    def add_other(self, n):
        sym = "SYN%02d" % n
        d = json.loads(json.dumps(self.d1).replace('"SYN"', '"%s"' % sym))
        _, key = store.import_scan(self.conn, d)
        return self.add(key, symbol=sym)

    def test_one_order_per_zone_until_the_first_is_cancelled_or_expired(self):
        first = self.add()
        with self.assertRaisesRegex(store.JournalRefused, "ONE_ORDER_PER_ZONE"):
            self.add()
        store.journal_event(self.conn, first, store.TRIGGERED, (self.t1 + datetime.timedelta(hours=18)).isoformat(),
                            price=161.0)
        with self.assertRaisesRegex(store.JournalRefused, "ONE_ORDER_PER_ZONE"):    # a traded zone is not fresh
            self.add()

    # ED-3 (revised by the owner brief 2026-11-08): a plan never submitted as an order does not
    # use the zone's one-order allowance; once an order is submitted, nothing releases it
    def at(self, hours):
        return (self.t1 + datetime.timedelta(hours=hours)).isoformat()

    def test_ed3_a_cancelled_plan_never_submitted_frees_the_zone(self):
        first = self.add()
        store.journal_event(self.conn, first, store.CANCELLED, self.at(1), note="never placed")
        self.assertIsInstance(self.add(), int)

    def test_ed3_a_submitted_order_keeps_the_allowance_after_cancel_or_expiry(self):
        for kind in (store.CANCELLED, store.EXPIRED):
            first = self.add()
            store.journal_order_submitted(self.conn, first, self.at(1), order_ref="GTT-TEST-1")
            store.journal_event(self.conn, first, kind, self.at(2))
            with self.assertRaisesRegex(store.JournalRefused, "ONE_ORDER_PER_ZONE.*order was submitted", msg=kind):
                self.add()
            self.conn.close()                                  # a fresh store for the next kind
            os.remove(self.db)
            self.conn = store.open_store(self.db)
            _, self.k1 = store.import_scan(self.conn, self.d1)

    def test_ed3_an_expired_entry_without_a_submission_record_still_holds_the_zone(self):
        # expiry belongs to a live order (and older journals have no submission rows): conservative
        first = self.add()
        store.journal_event(self.conn, first, store.EXPIRED, self.at(1))
        with self.assertRaisesRegex(store.JournalRefused, "EXPIRED"):
            self.add()

    def test_ed3_a_pending_plan_blocks_a_second_plan(self):
        self.add()
        with self.assertRaisesRegex(store.JournalRefused, "plan is still pending"):
            self.add()

    def test_ed3_order_submission_rules(self):
        eid = self.add()
        with self.assertRaises(store.JournalRefused):                   # before the plan was recorded
            store.journal_order_submitted(self.conn, eid, (self.t1 - datetime.timedelta(hours=1)).isoformat())
        store.journal_order_submitted(self.conn, eid, self.at(1), order_ref="GTT-TEST-2", note="manual Kite GTT")
        self.assertEqual(store.order_submission(self.conn, eid)["order_ref"], "GTT-TEST-2")
        with self.assertRaisesRegex(store.JournalRefused, "already has a submitted order"):
            store.journal_order_submitted(self.conn, eid, self.at(2))
        with self.assertRaises(sqlite3.DatabaseError):                  # append-only
            self.conn.execute("DELETE FROM journal_orders WHERE entry_id = ?", (eid,))
        other = self.add_other(1)
        store.journal_event(self.conn, other, store.CANCELLED, self.at(1))
        with self.assertRaisesRegex(store.JournalRefused, "only be submitted while the entry is PLANNED"):
            store.journal_order_submitted(self.conn, other, self.at(2))
        with self.assertRaises(store.StoreError):
            store.journal_order_submitted(self.conn, 9999, self.at(2))

    def test_ed3_insert_or_replace_cannot_overwrite_a_submission(self):
        eid = self.add()
        store.journal_order_submitted(self.conn, eid, self.at(1), order_ref="GTT-TEST-3")
        with self.assertRaises(sqlite3.DatabaseError):
            self.conn.execute("INSERT OR REPLACE INTO journal_orders VALUES (?, ?, ?, ?)", (eid, self.at(5), "X", None))
        self.assertEqual(store.order_submission(self.conn, eid)["order_ref"], "GTT-TEST-3")

    def test_ed3_an_event_before_the_submission_time_is_refused(self):
        eid = self.add()
        store.journal_order_submitted(self.conn, eid, self.at(3))
        with self.assertRaisesRegex(store.JournalRefused, "before the order's submission"):
            store.journal_event(self.conn, eid, store.CANCELLED, self.at(2))

    def test_ed3_a_cancelled_entry_from_a_pre_v2_journal_still_holds_its_zone(self):
        # QA 2026-11-08: a v1 journal has no submission rows, so its CANCELLED entries may have
        # been submitted orders; after the upgrade they keep the zone used
        self.conn.close()
        os.remove(self.db)
        conn = store.open_store(self.db, migrations=store.MIGRATIONS[:1])
        _, key = store.import_scan(conn, self.d1)
        with conn:                                   # v1 rows written directly (v1 had no submissions)
            cur = conn.execute(
                "INSERT INTO journal_entries (scan_key, symbol, zone_id, trade_type, direction, candidate_status, "
                "manual_review_resolution, candidate_levels, planned_entry, planned_stop, planned_target, quantity, "
                "alert_note, checklist, recorded_at) SELECT scan_key, symbol, zone_id, ?, 'LONG', status, NULL, '{}', "
                "1.0, 0.5, 3.0, 1, 'SYNTHETIC', '{}', ? FROM candidates WHERE scan_key = ? AND zone_id = ?",
                (self.d1["trade_type"], self.t1.isoformat(), key, self.cand.zone["zone_id"]))
            eid = cur.lastrowid
            conn.execute("INSERT INTO journal_events VALUES (?, 1, 'PLANNED', ?, NULL, NULL, NULL)",
                         (eid, self.t1.isoformat()))
            conn.execute("INSERT INTO journal_events VALUES (?, 2, 'CANCELLED', ?, NULL, NULL, NULL)",
                         (eid, self.at(1)))
        conn.close()
        self.conn = store.open_store(self.db)
        self.k1 = key
        with self.assertRaisesRegex(store.JournalRefused, "pre-v2 journal"):
            self.add()

    def test_ed3_a_v1_store_upgrades_to_v2(self):
        self.conn.close()
        os.remove(self.db)
        conn = store.open_store(self.db, migrations=store.MIGRATIONS[:1])
        conn.close()
        conn = store.open_store(self.db)
        try:
            self.assertEqual([r[0] for r in conn.execute("SELECT version FROM schema_migrations ORDER BY version")],
                             [version for version, _name, _sql in store.MIGRATIONS])
        finally:
            conn.close()
        self.conn = store.open_store(self.db)

    def test_trigger_after_a_later_scan_shows_the_zone_tested_is_refused(self):
        eid = self.add()                                   # planned while the zone was still a candidate
        store.import_scan(self.conn, self.d2)              # a later scan: the PL was touched
        t2 = datetime.datetime.fromisoformat(self.d2["as_of"])
        with self.assertRaisesRegex(store.JournalRefused, "ZONE_NO_LONGER_CANDIDATE"):
            store.journal_event(self.conn, eid, store.TRIGGERED, (t2 + datetime.timedelta(hours=18)).isoformat(),
                                price=161.0)
        # a fill on the scan's own date is not judged by it, even logged after that day's EOD scan:
        # that scan already sees the fill's own touch (Agent 6 review M3)
        self.assertIsInstance(store.journal_event(self.conn, eid, store.TRIGGERED,
                                                  (t2 + datetime.timedelta(minutes=30)).isoformat(), price=161.0), int)

    def test_eleventh_simultaneous_position_is_refused_in_a_fresh_month(self):
        ids = [self.add_other(n) for n in range(m.OWNER_MAX_OPEN_POSITIONS + 1)]
        for i, eid in enumerate(ids[:-1]):
            store.journal_event(self.conn, eid, store.TRIGGERED, "2024-02-%02dT10:00:00" % (10 + i), price=161.0)
        # March: no trade taken this month, so only the position limit can refuse (D42)
        with self.assertRaisesRegex(store.JournalRefused, "MAX_OPEN_POSITIONS"):
            store.journal_event(self.conn, ids[-1], store.TRIGGERED, "2024-03-04T10:00:00", price=161.0)
        store.journal_event(self.conn, ids[0], store.STOP_LOSS_HIT, "2024-03-01T10:00:00", price=155.0)
        self.assertIsInstance(store.journal_event(self.conn, ids[-1], store.TRIGGERED, "2024-03-04T10:00:00",
                                                  price=161.0), int)


class JournalIstMonth20261108(Base):
    """D42, D46: the monthly ceiling counts TRIGGERED times by IST calendar month (00:00 IST
    on day 1); a closed position frees a concurrent slot, never a monthly one."""
    add, add_other = Journal.add, Journal.add_other

    def setUp(self):
        Base.setUp(self)
        _, self.key = store.import_scan(self.conn, self.d1)

    def test_month_boundary_is_midnight_ist(self):
        ids = [self.add_other(n) for n in range(12)]
        for i, eid in enumerate(ids[:10]):
            store.journal_event(self.conn, eid, store.TRIGGERED, "2024-02-%02dT10:00:00" % (5 + i), price=161.0)
        store.journal_event(self.conn, ids[0], store.STOP_LOSS_HIT, "2024-02-29T23:58:00", price=155.0)
        # a slot is free, but February's ten trades are taken: 23:59 IST on 29 Feb is still February
        with self.assertRaisesRegex(store.JournalRefused, "IST month 2024-02"):
            store.journal_event(self.conn, ids[10], store.TRIGGERED, "2024-02-29T23:59:00", price=161.0)
        self.assertIsInstance(store.journal_event(self.conn, ids[10], store.TRIGGERED, "2024-03-01T00:00:00",
                                                  price=161.0), int)
        self.assertEqual(store.journal_summary(self.conn, "2024-03")["trades_taken"], 1)
        self.assertEqual(store.journal_summary(self.conn, "2024-02")["trades_taken"], 10)

    def test_a_timezone_aware_time_mixed_with_naive_ist_times_is_refused(self):
        eid = self.add()
        with self.assertRaises(store.StoreError):
            store.journal_event(self.conn, eid, store.TRIGGERED, "2024-02-05T04:30:00+00:00", price=161.0)


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

class P1JournalIntegrity(JournalAuditRegressions20261106):
    """P1: the monthly cap, the open-position cap and the zone reservation share one write lock."""

    def ist_month(self, hours):
        year, month = m.ist_month(self.t1 + datetime.timedelta(hours=hours))
        return "%04d-%02d" % (year, month)

    def test_two_connections_cannot_both_reserve_one_zone(self):
        import threading
        barrier = threading.Barrier(2)
        results = []

        def attempt():
            conn = store.open_store(self.db)
            try:
                barrier.wait(timeout=10)
                results.append(("ok", store.journal_add(conn, self.entry(self.k1))))
            except store.JournalRefused as exc:
                results.append(("refused", str(exc)))
            finally:
                conn.close()

        threads = [threading.Thread(target=attempt) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(sorted(kind for kind, _ in results), ["ok", "refused"])
        self.assertIn("ONE_ORDER_PER_ZONE", [text for kind, text in results if kind == "refused"][0])
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM journal_entries").fetchone()[0], 1)

    def test_a_retried_plan_key_does_not_create_a_second_entry(self):
        entry = self.entry(self.k1)
        first = store.journal_add(self.conn, entry, request_key="plan-1")
        second = store.journal_add(self.conn, entry, request_key="plan-1")
        self.assertEqual(first, second)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM journal_entries").fetchone()[0], 1)

    def test_two_connections_cannot_both_take_the_last_open_slot(self):
        import threading
        ids = [self.add_other(n) for n in range(m.OWNER_MAX_OPEN_POSITIONS + 1)]
        for i, eid in enumerate(ids[:-2]):
            store.journal_event(self.conn, eid, store.TRIGGERED, "2024-02-%02dT10:00:00" % (10 + i), price=161.0)
        barrier = threading.Barrier(2)
        results = []

        def attempt(eid):
            conn = store.open_store(self.db)
            try:
                barrier.wait(timeout=10)
                seq = store.journal_event(conn, eid, store.TRIGGERED, "2024-03-04T10:00:00", price=161.0)
                results.append(("ok", seq))
            except store.JournalRefused as exc:
                results.append(("refused", str(exc)))
            finally:
                conn.close()

        threads = [threading.Thread(target=attempt, args=(eid,)) for eid in ids[-2:]]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(sorted(kind for kind, _ in results), ["ok", "refused"])
        self.assertIn("MAX_OPEN_POSITIONS", [text for kind, text in results if kind == "refused"][0])
        self.assertEqual(store.journal_summary(self.conn, "2024-03")["trades_taken"], 1)
        self.assertEqual(store.portfolio_at(self.conn, "2024-03-04T10:00:00")["open_positions"], 10)

    def test_a_backdated_fill_cannot_exceed_the_open_position_cap(self):
        ids = [self.add_other(n) for n in range(m.OWNER_MAX_OPEN_POSITIONS + 1)]
        for i, eid in enumerate(ids[:-1]):
            store.journal_event(self.conn, eid, store.TRIGGERED, "2024-03-10T10:00:00", price=161.0)
        self.assertEqual(store.portfolio_at(self.conn, "2024-03-10T10:00:00")["open_positions"], 10)
        with self.assertRaisesRegex(store.JournalRefused, "MAX_OPEN_POSITIONS"):
            store.journal_event(self.conn, ids[-1], store.TRIGGERED, "2024-02-05T10:00:00", price=161.0)
        self.assertEqual(store.portfolio_at(self.conn, "2024-03-10T10:00:00")["open_positions"], 10)
        self.assertEqual(store.journal_summary(self.conn, "2024-02")["trades_taken"], 0)

    def test_a_submitted_fill_without_a_calendar_is_refused(self):
        eid = self.add()
        store.journal_order_submitted(self.conn, eid, self.at(1), order_ref="KITE-NO-CAL")
        with self.assertRaisesRegex(store.JournalRefused, "ORDER_EXPIRY_UNRESOLVED"):
            store.journal_event(self.conn, eid, store.TRIGGERED, self.at(2), price=161.0, calendar=None)
        self.assertEqual(
            self.conn.execute("SELECT COUNT(*) FROM journal_events WHERE kind = ?", (store.TRIGGERED,)).fetchone()[0],
            0)

    def test_a_failed_trigger_insert_leaves_no_row_and_the_connection_recovers(self):
        eid = self.add()
        self.conn.execute(
            "CREATE TRIGGER abort_fill BEFORE INSERT ON journal_events "
            "WHEN NEW.note = 'abort-this' BEGIN SELECT RAISE(ABORT, 'forced'); END;")
        before = self.conn.execute("SELECT COUNT(*) FROM journal_events").fetchone()[0]
        with self.assertRaises(sqlite3.DatabaseError):
            store.journal_event(self.conn, eid, store.TRIGGERED, self.at(2), price=161.0, note="abort-this")
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM journal_events").fetchone()[0], before)
        self.assertEqual(store.journal_event(self.conn, eid, store.TRIGGERED, self.at(2), price=161.0), 2)

    def test_an_uncommitted_trigger_is_invisible_after_the_connection_closes(self):
        eid = self.add()
        other = store.open_store(self.db)
        other.execute("BEGIN IMMEDIATE")
        other.execute(
            "INSERT INTO journal_events VALUES (?, 2, 'TRIGGERED', ?, 161.0, NULL, 'uncommitted')",
            (eid, self.at(2)))
        other.close()
        self.assertEqual([event["kind"] for event in store.journal_events(self.conn, eid)], [store.PLANNED])

    def test_an_identical_trigger_retry_does_not_insert_a_second_fill(self):
        eid = self.add()
        at = self.at(2)
        first = store.journal_event(self.conn, eid, store.TRIGGERED, at, price=161.0)
        second = store.journal_event(self.conn, eid, store.TRIGGERED, at, price=161.0, request_key="fill-1")
        third = store.journal_event(self.conn, eid, store.TRIGGERED, at, price=161.0, request_key="fill-1")
        self.assertEqual((first, second, third), (2, 2, 2))
        self.assertEqual(store.journal_summary(self.conn, self.ist_month(2))["trades_taken"], 1)
        with self.assertRaisesRegex(store.JournalRefused, "already TRIGGERED"):
            store.journal_event(self.conn, eid, store.TRIGGERED, self.at(3), price=161.0)

    def test_partial_prints_are_one_trade_and_do_not_count_the_unfilled_quantity(self):
        eid = self.add()
        first = store.journal_execution(self.conn, eid, "ENTRY", 40, 160.0, self.at(2), "print-1")
        self.assertEqual(first["book"]["executed_entry_quantity"], 40)
        self.assertEqual(first["book"]["unfilled_quantity"], 60)
        self.assertEqual(store.journal_summary(self.conn, self.ist_month(2))["trades_taken"], 1)
        self.assertEqual(store._open_positions(self.conn, store._dt(self.at(3), "at")), 1)
        second = store.journal_execution(self.conn, eid, "ENTRY", 20, 162.0, self.at(3), "print-2")
        self.assertEqual(second["book"]["average_entry_price"], round((40 * 160.0 + 20 * 162.0) / 60, 4))
        retry = store.journal_execution(self.conn, eid, "ENTRY", 40, 160.0, self.at(2), "print-1")
        self.assertTrue(retry["already_present"])
        self.assertEqual(len(store._execution_rows(self.conn, eid)), 2)
        with self.assertRaisesRegex(store.JournalRefused, "QUANTITY_EXCEEDS_ORDER"):
            store.journal_execution(self.conn, eid, "ENTRY", 50, 161.0, self.at(4), "print-3")
        store.journal_execution(self.conn, eid, "EXIT", 25, 170.0, self.at(5), "exit-1")
        book = store.position_book(self.conn, eid, 100, store.journal_events(self.conn, eid), None)
        self.assertEqual((book["open_quantity"], book["executed_exit_quantity"]), (35, 25))
        self.assertEqual(book["realised_pnl"], round(25 * 170.0 - (40 * 160.0 + 20 * 162.0) / 60 * 25, 2))
        self.assertEqual(book["unrealised"], "UNAVAILABLE")
        self.assertEqual(store.journal_summary(self.conn, self.ist_month(2))["trades_taken"], 1)
        self.assertEqual(store.portfolio_at(self.conn, self.at(6))["open_positions"], 1)
        mid = store.portfolio_at(self.conn, self.at(6))
        open_held = [z for z in mid["zones_holding_allowance"] if z["counts_as_open"]][0]
        self.assertEqual(open_held["average_entry_price"], round((40 * 160.0 + 20 * 162.0) / 60, 4))
        self.assertEqual(open_held["open_quantity"], 35)
        self.assertEqual(open_held["executed_exit_quantity"], 25)
        self.assertIsNotNone(open_held["planned_stop"])
        self.assertIsNotNone(open_held["locked_stop"])
        store.journal_event(self.conn, eid, store.CLOSED_MANUAL, self.at(6), price=171.0)
        after = store.portfolio_at(self.conn, self.at(7))
        self.assertEqual(after["open_positions"], 0)
        self.assertEqual(after["trades_triggered_this_month"], 1)
        held = after["zones_holding_allowance"][0]
        self.assertEqual(held["state"], "CLOSED")
        self.assertFalse(held["counts_as_open"])
        closed_book = store.position_book(self.conn, eid, 100, store.journal_events(self.conn, eid), None)
        self.assertEqual(held["realised_pnl"], closed_book["realised_pnl"])
        self.assertEqual(held["open_quantity"], 0)
        self.assertNotEqual(held["realised_pnl"], book["realised_pnl"])

    def test_stop_and_close_do_not_release_a_submitted_zone(self):
        eid = self.add()
        store.journal_order_submitted(self.conn, eid, self.at(1), order_ref="KITE-P1")
        store.journal_event(self.conn, eid, store.TRIGGERED, self.at(2), price=161.0,
                            calendar=R.WeekdayCalendar())
        store.journal_event(self.conn, eid, store.STOP_LOSS_HIT, self.at(3), price=155.0)
        with self.assertRaisesRegex(store.JournalRefused, "ONE_ORDER_PER_ZONE"):
            self.add()

    def test_absent_charges_are_not_invented_and_a_schedule_stays_estimated(self):
        eid = self.add()
        store.journal_event(self.conn, eid, store.TRIGGERED, self.at(2), price=161.0)
        store.journal_event(self.conn, eid, store.TARGET_HIT, self.at(4), price=171.0)
        bare = store.journal_summary(self.conn, self.ist_month(2))
        self.assertEqual(bare["charges_state"], "ABSENT")
        self.assertIsNone(bare["charges_paise"])
        self.assertIsNone(bare["actual_net_pnl"])
        self.assertIsNone(bare["estimated_net_pnl"])
        with self.assertRaises(store.StoreError):
            store.journal_apply_schedule(
                self.conn, eid, None, side="BUY", quantity=100, price=161.0, at=self.at(2), print_key="fill")
        estimated = store.journal_apply_schedule(
            self.conn, eid, _synthetic_schedule(), side="BUY", quantity=100, price=100.0,
            at=self.at(2), print_key="fill")
        self.assertFalse(estimated["already_present"])
        again = store.journal_apply_schedule(
            self.conn, eid, _synthetic_schedule(), side="BUY", quantity=100, price=100.0,
            at=self.at(2), print_key="fill")
        self.assertTrue(again["already_present"])
        summary = store.journal_summary(self.conn, self.ist_month(2))
        self.assertEqual(summary["charges_state"], "ESTIMATED")
        self.assertIsNone(summary["actual_net_pnl"])
        self.assertIsNotNone(summary["estimated_net_pnl"])
        self.assertEqual(summary["gross_pnl"], bare["gross_pnl"])
        sell = store.journal_apply_schedule(
            self.conn, eid, _synthetic_schedule(), side="SELL", quantity=100, price=100.0,
            at=self.at(4), print_key="exit")
        self.assertFalse(sell["already_present"])
        rows = store._charge_rows(self.conn, eid)
        buy_stamp = [row for row in rows if row["component"] == "STAMP" and row["side"] == "BUY"][0]
        sell_stamp = [row for row in rows if row["component"] == "STAMP" and row["side"] == "SELL"][0]
        self.assertGreater(buy_stamp["amount_paise"], 0)
        self.assertEqual(sell_stamp["amount_paise"], 0)


def _synthetic_schedule():
    side = {
        "BROKERAGE": {"BUY": {"model": "FLAT_RUPEES", "rupees": 20}, "SELL": {"model": "NONE"}},
        "STT": {"BUY": {"model": "BPS_OF_VALUE", "bps": 10}, "SELL": {"model": "BPS_OF_VALUE", "bps": 10}},
        "EXCHANGE": {"BUY": {"model": "BPS_OF_VALUE", "bps": 0}, "SELL": {"model": "BPS_OF_VALUE", "bps": 0}},
        "SEBI": {"BUY": {"model": "BPS_OF_VALUE", "bps": 0}, "SELL": {"model": "BPS_OF_VALUE", "bps": 0}},
        "STAMP": {"BUY": {"model": "FLAT_RUPEES", "rupees": 1}, "SELL": {"model": "NONE"}},
        "OTHER": {"BUY": {"model": "NONE"}, "SELL": {"model": "NONE"}},
    }
    components = [{"code": code, **rules} for code, rules in side.items()]
    components.append({"code": "GST", "model": "PERCENT_OF_COMPONENTS", "percent": 18,
                       "of": ["BROKERAGE", "EXCHANGE", "SEBI"]})
    return {
        "source": "SYNTHETIC schedule for the test. Not a statutory or broker tariff.",
        "effective_from": "2024-01-01",
        "effective_to": "2024-12-31",
        "components": components,
    }


class P6JournalProduct(P1JournalIntegrity):
    """P6 notes, taxonomy, search, planned-vs-actual, performance, export."""

    def test_notes_reviews_attachments_do_not_rewrite_execution(self):
        eid = self.add()
        store.journal_execution(self.conn, eid, "ENTRY", 50, 160.0, self.at(2), "p6-e1")
        before = store._execution_rows(self.conn, eid)
        store.journal_add_note(
            self.conn, eid, note_key="n1", at=self.at(3), kind="POST_TRADE_REVIEW",
            body="Owner review note.")
        store.journal_add_review(
            self.conn, eid, review_key="r1", at=self.at(4), review_status="REVIEWED",
            outcome_class="PROBABILITY_LOSS", mistake_category="NONE",
            note="No mistake. Cost of probability.", setup_label="MIT-LOC")
        store.journal_register_attachment(
            self.conn, eid, attachment_id="a1", at=self.at(5), filename="chart.png",
            content_type="image/png", size_bytes=12, sha256="a" * 64, storage_name="a1_chart.png")
        after = store._execution_rows(self.conn, eid)
        self.assertEqual(before, after)
        detail = store.journal_entry_detail(self.conn, eid)
        self.assertEqual(detail["review"]["outcome_class"], "PROBABILITY_LOSS")
        self.assertEqual(detail["notes"][0]["kind"], "POST_TRADE_REVIEW")
        self.assertEqual(detail["attachments"][0]["filename"], "chart.png")
        self.assertEqual(detail["setup"]["setup_label"], "MIT-LOC")

    def test_review_taxonomy_refuses_lucky_win_without_mistake(self):
        eid = self.add()
        with self.assertRaises(store.StoreError):
            store.journal_add_review(
                self.conn, eid, review_key="bad", at=self.at(2), review_status="REVIEWED",
                outcome_class="LUCKY_WIN", mistake_category="NONE")

    def test_query_filters_and_pagination_are_stable(self):
        first = self.add()
        second = self.add_other(1)
        store.journal_execution(self.conn, first, "ENTRY", 10, 160.0, self.at(2), "q1")
        store.journal_event(self.conn, first, store.CLOSED_MANUAL, self.at(3), price=170.0)
        store.journal_add_review(
            self.conn, first, review_key="rev", at=self.at(4), review_status="REVIEWED",
            outcome_class="DISCIPLINE_WIN", mistake_category="NONE")
        by_symbol = store.journal_query(self.conn, {"symbol": "SYN", "limit": 10, "offset": 0})
        self.assertGreaterEqual(by_symbol["total"], 1)
        self.assertTrue(all("SYN" in row["symbol"] for row in by_symbol["entries"]))
        reviewed = store.journal_query(self.conn, {"review_status": "REVIEWED"})
        self.assertEqual(reviewed["total"], 1)
        self.assertEqual(reviewed["entries"][0]["entry_id"], first)
        page = store.journal_query(self.conn, {"limit": 1, "offset": 0, "sort": "entry_id", "order": "asc"})
        self.assertEqual(page["total"], 2)
        self.assertEqual(len(page["entries"]), 1)
        empty = store.journal_query(self.conn, {"symbol": "NOPE"})
        self.assertEqual(empty["total"], 0)
        self.assertEqual(empty["entries"], [])
        with self.assertRaises(store.StoreError):
            store.journal_query(self.conn, {"not_a_field": "x"})
        self.assertEqual(second, second)

    def test_planned_versus_actual_preserves_plan_and_marks_unfilled(self):
        eid = self.add()
        planned = store.journal_planned_versus_actual(self.conn, eid)
        self.assertEqual(planned["state"], "PLANNED_ONLY")
        entry = self.conn.execute("SELECT planned_entry FROM journal_entries WHERE entry_id = ?", (eid,)).fetchone()
        store.journal_execution(self.conn, eid, "ENTRY", 40, float(entry["planned_entry"]) + 1.0,
                                self.at(2), "pv1")
        compared = store.journal_planned_versus_actual(self.conn, eid)
        self.assertEqual(compared["state"], "COMPARED")
        self.assertEqual(compared["planned"]["entry"], entry["planned_entry"])
        self.assertAlmostEqual(compared["deltas"]["entry_price"], 1.0)
        self.assertEqual(compared["actual"]["unfilled_quantity"], 60)

    def test_performance_and_export_stay_descriptive_and_cost_honest(self):
        eid = self.add()
        store.journal_execution(self.conn, eid, "ENTRY", 100, 160.0, self.at(2), "perf-e")
        store.journal_execution(self.conn, eid, "EXIT", 100, 170.0, self.at(3), "perf-x")
        store.journal_event(self.conn, eid, store.CLOSED_MANUAL, self.at(4), price=170.0)
        perf = store.journal_performance(self.conn, {})
        self.assertEqual(perf["evidence_class"], "JOURNAL_DESCRIPTIVE")
        self.assertEqual(perf["totals"]["closed_trades"], 1)
        self.assertEqual(perf["totals"]["net_state"], "INCOMPLETE_COSTS")
        self.assertIsNone(perf["totals"]["net_realised_pnl"])
        exported = store.journal_export(self.conn, {})
        self.assertEqual(exported["format"], "gtf-journal-export-v1")
        self.assertFalse(exported["attachments_embedded"])
        self.assertEqual(exported["total"], 1)
        self.assertEqual(exported["rows"][0]["charges_state"], "ABSENT")

    def test_unfilled_plan_is_not_a_completed_trade_in_performance(self):
        self.add()
        perf = store.journal_performance(self.conn, {})
        self.assertEqual(perf["totals"]["recorded_trades"], 1)
        self.assertEqual(perf["totals"]["closed_trades"], 0)
        self.assertEqual(perf["totals"]["wins"], 0)
        self.assertEqual(perf["totals"]["losses"], 0)

    def test_journal_note_does_not_claim_costs_are_absent_when_actual(self):
        eid = self.add()
        store.journal_execution(self.conn, eid, "ENTRY", 100, 160.0, self.at(2), "note-e")
        store.journal_execution(self.conn, eid, "EXIT", 100, 170.0, self.at(3), "note-x")
        store.journal_event(self.conn, eid, store.CLOSED_MANUAL, self.at(4), price=170.0)
        store.journal_record_charges(
            self.conn, eid,
            [{"charge_key": "c1", "component": "OTHER", "side": "BUY", "amount_paise": 100,
              "basis": "owner"}],
            at=self.at(5), source="OWNER_ENTERED", estimated=False)
        perf = store.journal_performance(self.conn, {})
        self.assertEqual(perf["totals"]["net_state"], "ACTUAL")
        self.assertIsNotNone(perf["totals"]["net_realised_pnl"])
        self.assertNotIn("costs are not recorded", perf["note"].lower())
        self.assertIn("never treated as zero", perf["note"].lower())
        self.assertFalse(perf["truncated"])


if __name__ == "__main__":
    unittest.main()
