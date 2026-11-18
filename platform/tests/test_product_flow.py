"""Plan, journal, portfolio, backup, and explanation tests.

The prices come from the repository's synthetic research fixture. They are not NSE
market data. Every database is a temporary file.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

PLATFORM = Path(__file__).resolve().parents[1]
ROOT = PLATFORM.parent
sys.path.insert(0, str(PLATFORM))
sys.path.append(str(ROOT))
sys.path.append(str(ROOT / "tests"))

import _research as R  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from gtf_platform.app import create_app  # noqa: E402
from gtf_platform.config import Settings  # noqa: E402
from nse.research import models, reports, scanner  # noqa: E402

MARKER = {"X-GTF-Request": "1", "Origin": "http://127.0.0.1:8765", "Sec-Fetch-Site": "same-origin"}


def _checklist(confirmed: bool = True) -> dict:
    return {code: confirmed for code, _label, _src in models.CHECKLIST}


def _approve_body(**extra) -> dict:
    body = {
        "combination_index": 0,
        "alert_note": "Synthetic plan. Not an order.",
        "checklist": _checklist(True),
    }
    body.update(extra)
    return body


def _settings(tmp: Path) -> Settings:
    return Settings(
        bind_host="127.0.0.1",
        bind_port=8765,
        advertised_port=8765,
        public_origins=(),
        platform_db=tmp / "platform.sqlite",
        research_db=tmp / "research.sqlite",
        cookie_secure=False,
        data_dir=tmp,
        testing=True,
        source_label="FIXTURE",
        price_adjustment="NONE",
        fixture_mode=True,
        csv_dir=tmp / "csv",
        # Submitted fills need a calendar for D42 expiry (fail-closed when absent).
        calendar_dir=ROOT / "nse" / "data" / "calendar",
        repo_root=ROOT,
    )


class PlanJournalPortfolio(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        candles = R.long_mit_candles()
        result = scanner.scan(
            [R.daily_input("SYN", candles)],
            scanner.ScanConfig(
                as_of=candles[-1].end,
                calendar=R.WeekdayCalendar(),
                calendar_label="TEST_WEEKDAYS",
                risk_per_trade=1000.0,
                generated_at="SYNTHETIC-TEST",
                corporate_action_coverage=R.verified_ca("SYN"),
            ),
        )
        cls.scan = reports.to_dict(result)
        cls.candidate = result.candidates()[0]
        if cls.candidate.status != models.ACTIONABLE:
            raise AssertionError("synthetic fixture did not produce an actionable candidate")

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.client = TestClient(create_app(_settings(self.tmp)), base_url="http://127.0.0.1:8765", client=("127.0.0.1", 50000))
        self.client.post("/api/v1/session/bootstrap", headers=MARKER)
        self.scan_key = "scan-synthetic"
        envelope = {
            "as_of": self.scan["as_of"],
            "trade_type": self.scan["trade_type"],
            "invocation": "manual",
            "dataset_id": "synthetic",
            "completeness": "COMPLETE",
            "full_universe_scan": False,
            "limitations": list(self.scan["limitations"]) + ["FIXTURE_NOT_MARKET_DATA"],
            "symbols_not_opened": [],
            "symbols": self.scan["symbols"],
            "scan": self.scan,
            "authorises_order": False,
            "idempotency_key": self.scan_key,
            "manifest_id": "run-synthetic",
        }
        folder = self.tmp / "reports" / self.scan_key
        folder.mkdir(parents=True)
        (folder / "candidates.csv").write_text("symbol,status\nSYN,STORED\n", encoding="utf-8")
        (folder / "run_manifest.json").write_text(json.dumps({"run_id": "run-synthetic"}) + "\n", encoding="utf-8")
        now = "2024-02-02T18:00:00+00:00"
        self.client.app.state.db.execute(
            """
            INSERT INTO scan_result (
                scan_key, job_id, as_of, trade_type, invocation, dataset_id, universe_label,
                completeness, full_universe_scan, fixture, limitations_json,
                symbols_not_opened_json, envelope_json, created_at
            ) VALUES (?, NULL, ?, ?, 'manual', 'synthetic', 'SYNTHETIC', 'COMPLETE', 0, 1, ?, '[]', ?, ?)
            """,
            (
                self.scan_key,
                envelope["as_of"],
                envelope["trade_type"],
                json.dumps(envelope["limitations"]),
                json.dumps(envelope),
                now,
            ),
        )
        saved = self.client.patch(
            "/api/v1/settings",
            headers={**MARKER, "Content-Type": "application/json"},
            json={"capital": 100000, "rpt_pct": 1, "risk_stage": "LEARNING"},
        )
        self.assertEqual(saved.status_code, 200, saved.text)
        # Application backups require the configured research DB file to exist.
        from nse.research import store as research_store

        research_conn = research_store.open_store(str(self.tmp / "research.sqlite"))
        research_conn.close()

    def tearDown(self):
        self.client.close()
        self._tmp.cleanup()

    def test_plan_approval_journal_portfolio_export_and_backup(self):
        zone = self.candidate.zone["zone_id"]
        created = self.client.post(
            "/api/v1/plans?include_fixtures=true",
            headers={**MARKER, "Content-Type": "application/json"},
            json={"scan_key": self.scan_key, "symbol": "SYN", "zone_id": zone},
        )
        self.assertEqual(created.status_code, 201, created.text)
        plan_id = created.json()["data"]["plan_id"]
        self.assertIsNone(created.json()["data"]["quantity"])
        preview = self.client.get("/api/v1/plans/%s" % plan_id, headers=MARKER)
        self.assertEqual(preview.status_code, 200, preview.text)
        self.assertGreater(len(preview.json()["data"]["combinations"]), 0)
        self.assertIsNone(preview.json()["data"]["quantity"])
        recorded = self.scan["as_of"]
        approved = self.client.post(
            "/api/v1/plans/%s/approve" % plan_id,
            headers={**MARKER, "Content-Type": "application/json"},
            json=_approve_body(alert_note="Synthetic plan. Not an order.", recorded_at=recorded),
        )
        self.assertEqual(approved.status_code, 200, approved.text)
        self.assertFalse(approved.json()["data"]["authorises_order"])
        entry_id = approved.json()["data"]["entry_id"]
        again = self.client.post(
            "/api/v1/plans/%s/approve" % plan_id,
            headers={**MARKER, "Content-Type": "application/json"},
            json=_approve_body(alert_note="Synthetic plan. Not an order.", recorded_at=recorded),
        )
        self.assertEqual(again.status_code, 200, again.text)
        self.assertEqual(again.json()["data"]["entry_id"], entry_id)
        research = sqlite3.connect(self.tmp / "research.sqlite")
        self.assertEqual(research.execute("SELECT COUNT(*) FROM journal_entries").fetchone()[0], 1)
        self.assertEqual(research.execute("SELECT COUNT(*) FROM journal_events WHERE kind = 'TRIGGERED'").fetchone()[0], 0)
        research.close()
        submitted = self.client.post(
            "/api/v1/journal/%s/order" % entry_id,
            headers={**MARKER, "Content-Type": "application/json"},
            json={"submitted_at": recorded, "order_ref": "KITE-TEST", "note": "Typed by the owner. Not sent by this app."},
        )
        self.assertEqual(submitted.status_code, 200, submitted.text)
        filled = self.client.post(
            "/api/v1/journal/%s/events" % entry_id,
            headers={**MARKER, "Content-Type": "application/json"},
            json={"kind": "TRIGGERED", "at": recorded, "price": self.candidate.levels["entry"][1]},
        )
        self.assertEqual(filled.status_code, 200, filled.text)
        book = self.client.get("/api/v1/portfolio", headers=MARKER, params={"at": recorded})
        self.assertEqual(book.status_code, 200, book.text)
        body = book.json()["data"]
        self.assertEqual(body["trades_triggered_this_month"], 1)
        self.assertEqual(body["open_positions"], 1)
        self.assertEqual(body["valuation_state"], "UNAVAILABLE")
        self.assertEqual(body["sector_state"], "UNAVAILABLE")
        self.assertFalse(body["authorises_order"])
        live = self.client.get("/api/v1/portfolio", headers=MARKER)
        self.assertEqual(live.status_code, 200, live.text)
        self.assertEqual(live.json()["data"]["open_positions"], 1)
        self.assertEqual(live.json()["data"]["valuation_state"], "UNAVAILABLE")
        from datetime import datetime
        closed_at = (datetime.fromisoformat(recorded) + timedelta(hours=1)).isoformat()
        closed = self.client.post(
            "/api/v1/journal/%s/events" % entry_id,
            headers={**MARKER, "Content-Type": "application/json"},
            json={"kind": "CLOSED_MANUAL", "at": closed_at, "price": self.candidate.levels["entry"][1]},
        )
        self.assertEqual(closed.status_code, 200, closed.text)
        after_close = (datetime.fromisoformat(closed_at) + timedelta(seconds=1)).isoformat()
        after = self.client.get("/api/v1/portfolio", headers=MARKER, params={"at": after_close})
        self.assertEqual(after.json()["data"]["open_positions"], 0)
        self.assertEqual(after.json()["data"]["trades_triggered_this_month"], 1)
        second = self.client.post(
            "/api/v1/plans?include_fixtures=true",
            headers={**MARKER, "Content-Type": "application/json"},
            json={"scan_key": self.scan_key, "symbol": "SYN", "zone_id": zone},
        )
        self.assertEqual(second.status_code, 201, second.text)
        duplicate = self.client.post(
            "/api/v1/plans/%s/approve" % second.json()["data"]["plan_id"],
            headers={**MARKER, "Content-Type": "application/json"},
            json=_approve_body(alert_note="Second plan.", recorded_at=recorded),
        )
        self.assertEqual(duplicate.status_code, 409, duplicate.text)
        self.assertIn("ONE_ORDER_PER_ZONE", duplicate.text)

    def test_restart_drops_the_cookie_and_keeps_the_journal(self):
        zone = self.candidate.zone["zone_id"]
        created = self.client.post(
            "/api/v1/plans?include_fixtures=true",
            headers={**MARKER, "Content-Type": "application/json"},
            json={"scan_key": self.scan_key, "symbol": "SYN", "zone_id": zone},
        )
        plan_id = created.json()["data"]["plan_id"]
        approved = self.client.post(
            "/api/v1/plans/%s/approve" % plan_id,
            headers={**MARKER, "Content-Type": "application/json"},
            json=_approve_body(alert_note="Synthetic plan. Not an order.", recorded_at=self.scan["as_of"]),
        )
        self.assertEqual(approved.status_code, 200, approved.text)
        entry_id = approved.json()["data"]["entry_id"]
        old_cookie = self.client.cookies.get("gtf_session")
        restarted = TestClient(create_app(_settings(self.tmp)), base_url="http://127.0.0.1:8765", client=("127.0.0.1", 50000))
        restarted.cookies.set("gtf_session", old_cookie)
        rejected = restarted.get("/api/v1/journal", headers=MARKER)
        self.assertEqual(rejected.status_code, 401, rejected.text)
        restarted.post("/api/v1/session/bootstrap", headers=MARKER)
        rows = restarted.get("/api/v1/journal", headers=MARKER)
        self.assertEqual(rows.status_code, 200, rows.text)
        self.assertEqual(rows.json()["data"]["entries"][0]["entry_id"], entry_id)
        self.assertEqual(rows.json()["data"]["entries"][0]["book"]["source"], "unfilled")
        printed = restarted.post(
            "/api/v1/journal/%s/executions" % entry_id,
            headers={**MARKER, "Content-Type": "application/json", "Idempotency-Key": "print-restart"},
            json={"side": "ENTRY", "quantity": 1, "price": 100, "at": self.scan["as_of"], "print_key": "print-restart"},
        )
        self.assertEqual(printed.status_code, 200, printed.text)
        self.assertFalse(printed.json()["data"]["authorises_order"])
        repeated = restarted.post(
            "/api/v1/journal/%s/executions" % entry_id,
            headers={**MARKER, "Content-Type": "application/json", "Idempotency-Key": "print-restart"},
            json={"side": "ENTRY", "quantity": 1, "price": 100, "at": self.scan["as_of"], "print_key": "print-restart"},
        )
        self.assertEqual(repeated.status_code, 200, repeated.text)
        self.assertTrue(repeated.json()["data"]["already_present"])
        research = sqlite3.connect(self.tmp / "research.sqlite")
        self.assertEqual(research.execute("SELECT COUNT(*) FROM journal_executions").fetchone()[0], 1)
        self.assertEqual(research.execute("SELECT COUNT(*) FROM journal_events WHERE kind = 'TRIGGERED'").fetchone()[0], 1)
        research.close()

    def test_browser_timestamp_is_converted_to_the_naive_scan_clock(self):
        zone = self.candidate.zone["zone_id"]
        created = self.client.post(
            "/api/v1/plans?include_fixtures=true",
            headers={**MARKER, "Content-Type": "application/json"},
            json={"scan_key": self.scan_key, "symbol": "SYN", "zone_id": zone},
        )
        self.assertEqual(created.status_code, 201, created.text)
        plan_id = created.json()["data"]["plan_id"]
        approved = self.client.post(
            "/api/v1/plans/%s/approve" % plan_id,
            headers={**MARKER, "Content-Type": "application/json"},
            json=_approve_body(alert_note="Aware clock. Not an order.", recorded_at="2024-02-02T10:00:00+00:00"),
        )
        self.assertEqual(approved.status_code, 200, approved.text)
        research = sqlite3.connect(self.tmp / "research.sqlite")
        stored = research.execute("SELECT recorded_at FROM journal_entries").fetchone()[0]
        research.close()
        self.assertNotIn("+", stored)
        self.assertTrue(stored.startswith("2024-02-02T15:30:00"))

    def test_rejected_candidate_cannot_be_planned_and_export_matches_bytes(self):
        refused = json.loads(json.dumps(self.scan))
        refused["symbols"][0]["candidates"][0]["status"] = "REJECTED"
        envelope = {
            "as_of": refused["as_of"],
            "trade_type": refused["trade_type"],
            "invocation": "manual",
            "dataset_id": "synthetic",
            "completeness": "PARTIAL",
            "full_universe_scan": False,
            "limitations": ["FIXTURE_NOT_MARKET_DATA"],
            "symbols": refused["symbols"],
            "scan": refused,
            "authorises_order": False,
        }
        self.client.app.state.db.execute(
            """
            INSERT INTO scan_result (
                scan_key, job_id, as_of, trade_type, invocation, dataset_id, universe_label,
                completeness, full_universe_scan, fixture, limitations_json,
                symbols_not_opened_json, envelope_json, created_at
            ) VALUES ('scan-refused', NULL, ?, ?, 'manual', 'synthetic', 'SYNTHETIC', 'PARTIAL', 0, 1, '[]', '[]', ?, '2024-02-02T18:00:00+00:00')
            """,
            (envelope["as_of"], envelope["trade_type"], json.dumps(envelope)),
        )
        zone = refused["symbols"][0]["candidates"][0]["zone"]["zone_id"]
        refused_plan = self.client.post(
            "/api/v1/plans?include_fixtures=true",
            headers={**MARKER, "Content-Type": "application/json"},
            json={"scan_key": "scan-refused", "symbol": "SYN", "zone_id": zone},
        )
        self.assertEqual(refused_plan.status_code, 409, refused_plan.text)
        stored = (self.tmp / "reports" / self.scan_key / "candidates.csv").read_text(encoding="utf-8")
        exported = self.client.get("/api/v1/scans/%s/reports/candidates.csv" % self.scan_key, headers=MARKER)
        self.assertEqual(exported.status_code, 200, exported.text)
        self.assertEqual(exported.json()["data"]["body"], stored)
        missing = self.client.get("/api/v1/scans/%s/reports/missing.csv" % self.scan_key, headers=MARKER)
        self.assertEqual(missing.status_code, 400)
        partial = self.client.get("/api/v1/scans/scan-refused", headers=MARKER, params={"include_fixtures": True})
        self.assertEqual(partial.json()["data"]["completeness"], "PARTIAL")
        first = self.client.get("/api/v1/symbols/SYN/explain", headers=MARKER, params={"scan_key": self.scan_key, "include_fixtures": True})
        second = self.client.get("/api/v1/symbols/SYN/explain", headers=MARKER, params={"scan_key": self.scan_key, "include_fixtures": True})
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.json()["data"]["answer_lines"], second.json()["data"]["answer_lines"])
        self.assertFalse(first.json()["data"]["changes_status"])
        self.assertIsNone(first.json()["data"]["model"])

    def test_backup_restores_a_copy_and_leaves_the_live_files(self):
        live_platform = (self.tmp / "platform.sqlite").read_bytes()
        backup = self.client.post(
            "/api/v1/backup",
            headers={**MARKER, "Content-Type": "application/json"},
            json={"directory": str(self.tmp / "backup-out")},
        )
        self.assertEqual(backup.status_code, 200, backup.text)
        self.assertIn("platform.sqlite", backup.json()["data"]["files"])
        self.assertTrue((self.tmp / "backup-out" / "platform.sqlite").is_file())
        restored = self.client.post(
            "/api/v1/restore-check",
            headers={**MARKER, "Content-Type": "application/json"},
            json={"directory": str(self.tmp / "backup-out")},
        )
        self.assertEqual(restored.status_code, 200, restored.text)
        self.assertTrue(restored.json()["data"]["live_files_unchanged"])
        self.assertEqual((self.tmp / "platform.sqlite").read_bytes(), live_platform)
        bad = self.client.post(
            "/api/v1/restore-check",
            headers={**MARKER, "Content-Type": "application/json"},
            json={"directory": str(self.tmp / "missing-backup")},
        )
        self.assertEqual(bad.status_code, 404)
        corrupt = self.tmp / "corrupt-backup"
        corrupt.mkdir()
        (corrupt / "platform.sqlite").write_bytes(b"not a database")
        broken = self.client.post(
            "/api/v1/restore-check",
            headers={**MARKER, "Content-Type": "application/json"},
            json={"directory": str(corrupt)},
        )
        self.assertEqual(broken.status_code, 422)
        self.assertEqual((self.tmp / "platform.sqlite").read_bytes(), live_platform)
        mode = (self.tmp / "backup-out" / "platform.sqlite").stat().st_mode & 0o777
        self.assertEqual(mode, 0o600)
        self.assertTrue(restored.json()["data"]["counts_match_backup"])
        self.assertEqual(restored.json()["data"]["status"], "RESTORE_CHECK_PASSED")
        self.assertFalse(restored.json()["data"]["includes_bhavcopy_archive"])
        again = self.client.post(
            "/api/v1/backup",
            headers={**MARKER, "Content-Type": "application/json"},
            json={"directory": str(self.tmp / "backup-out")},
        )
        self.assertEqual(again.status_code, 409, again.text)
        self.assertEqual((self.tmp / "platform.sqlite").read_bytes(), live_platform)
        live_target = self.client.post(
            "/api/v1/backup",
            headers={**MARKER, "Content-Type": "application/json"},
            json={"directory": str(self.tmp)},
        )
        self.assertEqual(live_target.status_code, 409, live_target.text)
        self.assertEqual((self.tmp / "platform.sqlite").read_bytes(), live_platform)
        shutil.rmtree(self.tmp / "backup-out")

    def test_interrupted_restore_cleans_partial_and_protects_live(self):
        zone = self.candidate.zone["zone_id"]
        created = self.client.post(
            "/api/v1/plans?include_fixtures=true",
            headers={**MARKER, "Content-Type": "application/json"},
            json={"scan_key": self.scan_key, "symbol": "SYN", "zone_id": zone},
        )
        self.assertEqual(created.status_code, 201, created.text)
        approved = self.client.post(
            "/api/v1/plans/%s/approve" % created.json()["data"]["plan_id"],
            headers={**MARKER, "Content-Type": "application/json"},
            json=_approve_body(alert_note="Backup fixture. Not an order.", recorded_at=self.scan["as_of"]),
        )
        self.assertEqual(approved.status_code, 200, approved.text)
        live_platform = (self.tmp / "platform.sqlite").read_bytes()
        live_research = (self.tmp / "research.sqlite").read_bytes()
        backup = self.client.post(
            "/api/v1/backup",
            headers={**MARKER, "Content-Type": "application/json"},
            json={"directory": str(self.tmp / "backup-intact")},
        )
        self.assertEqual(backup.status_code, 200, backup.text)
        self.assertIn("research.sqlite", backup.json()["data"]["files"])
        manifest = json.loads((self.tmp / "backup-intact" / "backup_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["backup_format"], 1)
        self.assertIn("created_at", manifest)
        self.assertEqual(manifest["status"], "BACKUP_NOT_VERIFIED")
        checks = self.tmp / "restore-checks"
        checks.mkdir(parents=True, exist_ok=True)
        leftover = checks / "stale.partial"
        leftover.mkdir()
        (leftover / "platform.sqlite").write_bytes(b"partial-bytes")
        corrupt = self.tmp / "backup-broken"
        corrupt.mkdir()
        shutil.copy2(self.tmp / "backup-intact" / "platform.sqlite", corrupt / "platform.sqlite")
        (corrupt / "research.sqlite").write_bytes(b"not-a-database")
        broken = self.client.post(
            "/api/v1/restore-check",
            headers={**MARKER, "Content-Type": "application/json"},
            json={"directory": str(corrupt)},
        )
        self.assertEqual(broken.status_code, 422, broken.text)
        self.assertEqual((self.tmp / "platform.sqlite").read_bytes(), live_platform)
        self.assertEqual((self.tmp / "research.sqlite").read_bytes(), live_research)
        self.assertTrue(leftover.is_dir())
        self.assertFalse(any(path.name.endswith(".partial") and path != leftover for path in checks.iterdir()))
        ok = self.client.post(
            "/api/v1/restore-check",
            headers={**MARKER, "Content-Type": "application/json"},
            json={"directory": str(self.tmp / "backup-intact")},
        )
        self.assertEqual(ok.status_code, 200, ok.text)
        self.assertEqual(ok.json()["data"]["status"], "RESTORE_CHECK_PASSED")
        self.assertEqual((self.tmp / "platform.sqlite").read_bytes(), live_platform)
        self.assertEqual((self.tmp / "research.sqlite").read_bytes(), live_research)
        shutil.rmtree(self.tmp / "backup-intact")
        shutil.rmtree(corrupt)

    def test_backup_restore_preserves_journal_records_and_rejects_incomplete(self):
        """P1-I2/T-017: production backup path, isolated restore, record-level proof."""
        zone = self.candidate.zone["zone_id"]
        created = self.client.post(
            "/api/v1/plans?include_fixtures=true",
            headers={**MARKER, "Content-Type": "application/json"},
            json={"scan_key": self.scan_key, "symbol": "SYN", "zone_id": zone},
        )
        self.assertEqual(created.status_code, 201, created.text)
        plan_id = created.json()["data"]["plan_id"]
        approved = self.client.post(
            "/api/v1/plans/%s/approve" % plan_id,
            headers={**MARKER, "Content-Type": "application/json"},
            json=_approve_body(alert_note="Restore proof. Not an order.", recorded_at=self.scan["as_of"]),
        )
        self.assertEqual(approved.status_code, 200, approved.text)
        entry_id = approved.json()["data"]["entry_id"]
        submitted = self.client.post(
            "/api/v1/journal/%s/order" % entry_id,
            headers={**MARKER, "Content-Type": "application/json", "Idempotency-Key": "restore-order"},
            json={"submitted_at": self.scan["as_of"], "order_ref": "KITE-RESTORE", "note": "Owner submitted in Kite"},
        )
        self.assertEqual(submitted.status_code, 200, submitted.text)
        filled = self.client.post(
            "/api/v1/journal/%s/executions" % entry_id,
            headers={**MARKER, "Content-Type": "application/json", "Idempotency-Key": "restore-print"},
            json={
                "side": "ENTRY",
                "quantity": 1,
                "price": 100,
                "at": self.scan["as_of"],
                "print_key": "restore-print",
            },
        )
        self.assertEqual(filled.status_code, 200, filled.text)
        live_platform = (self.tmp / "platform.sqlite").read_bytes()
        live_research = (self.tmp / "research.sqlite").read_bytes()
        source = sqlite3.connect(self.tmp / "research.sqlite")
        source.row_factory = sqlite3.Row
        source_entries = [dict(row) for row in source.execute("SELECT * FROM journal_entries ORDER BY entry_id")]
        source_events = [dict(row) for row in source.execute("SELECT entry_id, kind, at FROM journal_events ORDER BY rowid")]
        source_execs = [
            dict(row)
            for row in source.execute(
                "SELECT entry_id, side, quantity, price, print_key FROM journal_executions ORDER BY rowid"
            )
        ]
        source_plans = self.client.app.state.db.execute("SELECT COUNT(*) FROM trade_plan").fetchone()[0]
        source.close()

        backup = self.client.post(
            "/api/v1/backup",
            headers={**MARKER, "Content-Type": "application/json"},
            json={},
        )
        self.assertEqual(backup.status_code, 200, backup.text)
        backup_dir = Path(backup.json()["data"]["directory"])
        self.assertTrue(str(backup_dir).startswith(str(self.tmp / "backups")))
        self.assertTrue((backup_dir / "platform.sqlite").is_file())
        self.assertTrue((backup_dir / "research.sqlite").is_file())
        self.assertEqual((backup_dir / "platform.sqlite").stat().st_mode & 0o777, 0o600)
        self.assertEqual(backup_dir.stat().st_mode & 0o777, 0o700)

        restored = self.client.post(
            "/api/v1/restore-check",
            headers={**MARKER, "Content-Type": "application/json"},
            json={"directory": str(backup_dir)},
        )
        self.assertEqual(restored.status_code, 200, restored.text)
        body = restored.json()["data"]
        self.assertEqual(body["status"], "RESTORE_CHECK_PASSED")
        self.assertTrue(body["live_files_unchanged"])
        self.assertTrue(body["counts_match_backup"])
        restored_to = Path(body["restored_to"])
        self.assertTrue(str(restored_to).startswith(str(self.tmp / "restore-checks")))
        self.assertNotEqual(restored_to.resolve(), backup_dir.resolve())
        self.assertNotEqual(restored_to.resolve(), self.tmp.resolve())

        opened = sqlite3.connect(restored_to / "research.sqlite")
        opened.row_factory = sqlite3.Row
        restored_entries = [dict(row) for row in opened.execute("SELECT * FROM journal_entries ORDER BY entry_id")]
        restored_events = [dict(row) for row in opened.execute("SELECT entry_id, kind, at FROM journal_events ORDER BY rowid")]
        restored_execs = [
            dict(row)
            for row in opened.execute(
                "SELECT entry_id, side, quantity, price, print_key FROM journal_executions ORDER BY rowid"
            )
        ]
        opened.close()
        self.assertEqual(restored_entries, source_entries)
        self.assertEqual(restored_events, source_events)
        self.assertEqual(restored_execs, source_execs)
        platform_restored = sqlite3.connect(restored_to / "platform.sqlite")
        self.assertEqual(platform_restored.execute("SELECT COUNT(*) FROM trade_plan").fetchone()[0], source_plans)
        platform_restored.close()
        self.assertEqual((self.tmp / "platform.sqlite").read_bytes(), live_platform)
        self.assertEqual((self.tmp / "research.sqlite").read_bytes(), live_research)

        empty = self.tmp / "empty-backup"
        empty.mkdir()
        empty_check = self.client.post(
            "/api/v1/restore-check",
            headers={**MARKER, "Content-Type": "application/json"},
            json={"directory": str(empty)},
        )
        self.assertEqual(empty_check.status_code, 422, empty_check.text)
        incomplete = self.tmp / "incomplete-backup"
        incomplete.mkdir()
        shutil.copy2(backup_dir / "platform.sqlite", incomplete / "platform.sqlite")
        shutil.copy2(backup_dir / "backup_manifest.json", incomplete / "backup_manifest.json")
        incomplete_check = self.client.post(
            "/api/v1/restore-check",
            headers={**MARKER, "Content-Type": "application/json"},
            json={"directory": str(incomplete)},
        )
        self.assertEqual(incomplete_check.status_code, 422, incomplete_check.text)
        self.assertIn("incomplete", incomplete_check.text.lower())
        self.assertEqual((self.tmp / "platform.sqlite").read_bytes(), live_platform)
        self.assertEqual((self.tmp / "research.sqlite").read_bytes(), live_research)

        readonly = self.tmp / "readonly-dest"
        readonly.mkdir()
        os.chmod(readonly, 0o500)
        try:
            from gtf_platform.integration import desk

            with self.assertRaises(Exception):
                desk.backup_to(self.client.app.state.settings, readonly / "nested-backup")
        finally:
            os.chmod(readonly, 0o700)
        self.assertEqual((self.tmp / "platform.sqlite").read_bytes(), live_platform)
        self.assertEqual((self.tmp / "research.sqlite").read_bytes(), live_research)

        truncated = self.tmp / "truncated-manifest"
        truncated.mkdir()
        shutil.copy2(backup_dir / "platform.sqlite", truncated / "platform.sqlite")
        (truncated / "backup_manifest.json").write_text(
            json.dumps(
                {
                    "backup_format": 1,
                    "files": ["platform.sqlite", "backup_manifest.json"],
                    "status": "BACKUP_NOT_VERIFIED",
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        truncated_check = self.client.post(
            "/api/v1/restore-check",
            headers={**MARKER, "Content-Type": "application/json"},
            json={"directory": str(truncated)},
        )
        self.assertEqual(truncated_check.status_code, 422, truncated_check.text)
        self.assertIn("incomplete", truncated_check.text.lower())

        held_research = self.tmp / "research.sqlite"
        moved = self.tmp / "research.sqlite.held"
        held_research.rename(moved)
        try:
            missing_research = self.client.post(
                "/api/v1/backup",
                headers={**MARKER, "Content-Type": "application/json"},
                json={"directory": str(self.tmp / "backup-missing-research")},
            )
            self.assertEqual(missing_research.status_code, 422, missing_research.text)
            self.assertFalse((self.tmp / "backup-missing-research" / "platform.sqlite").exists())
        finally:
            moved.rename(held_research)
        self.assertEqual((self.tmp / "platform.sqlite").read_bytes(), live_platform)
        self.assertEqual((self.tmp / "research.sqlite").read_bytes(), live_research)

    def test_overview_reports_derived_readiness_and_active_job(self):
        self.client.app.state.db.execute(
            """
            INSERT INTO job (
                job_id, kind, state, idempotency_key, heartbeat, created_at, request_json,
                body_hash, result_ref, research_key, completeness, fixture, progress_done,
                progress_total, progress_unit, updated_at, error_code, error_message
            ) VALUES (
                'job-running', 'SCAN', 'RUNNING', 'idem-running', NULL, '2024-02-02T18:00:00+00:00', '{}',
                'hash', NULL, NULL, NULL, 0, 0, 1, 'symbols', '2024-02-02T18:00:00+00:00', NULL, NULL
            )
            """
        )
        self.client.app.state.db.execute(
            """
            INSERT INTO scan_result (
                scan_key, job_id, as_of, trade_type, invocation, dataset_id, universe_label,
                completeness, full_universe_scan, fixture, limitations_json,
                symbols_not_opened_json, envelope_json, created_at
            ) VALUES (
                'scan-live', NULL, '2024-02-02T15:30:00+00:00', 'MIT', 'manual', 'synthetic', 'SYNTHETIC',
                'COMPLETE', 0, 0, ?, '[]', ?, '2024-02-02T18:05:00+00:00'
            )
            """,
            (
                json.dumps(["FIXTURE_NOT_MARKET_DATA"]),
                json.dumps(
                    {
                        "as_of": "2024-02-02T15:30:00+00:00",
                        "completeness": "COMPLETE",
                        "counts": {"symbols": 1, "candidate_status": {"ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING": 1}},
                        "limitations": ["FIXTURE_NOT_MARKET_DATA"],
                        "full_universe_scan": False,
                        "manifest_id": "run-live",
                    }
                ),
            ),
        )
        self.client.app.state.db.execute(
            """
            INSERT INTO job (
                job_id, kind, state, idempotency_key, heartbeat, created_at, request_json,
                body_hash, result_ref, research_key, completeness, fixture, progress_done,
                progress_total, progress_unit, updated_at, error_code, error_message
            ) VALUES (
                'job-stored', 'SCAN', 'SUCCEEDED_COMPLETE', 'idem-stored', NULL, '2024-02-02T18:05:00+00:00', '{}',
                'hash2', 'scan-live', NULL, 'COMPLETE', 0, 1, 1, 'symbols', '2024-02-02T18:05:00+00:00', NULL, NULL
            )
            """
        )
        overview = self.client.get("/api/v1/overview", headers=MARKER)
        self.assertEqual(overview.status_code, 200, overview.text)
        data = overview.json()["data"]
        self.assertFalse(data["data_ready"])
        self.assertEqual(data["readiness_state"], "NOT_READY")
        self.assertFalse(data["certified_p0_data"])
        self.assertEqual(data["active_job"]["state"], "RUNNING")
        self.assertEqual(data["job_phase"], "RUNNING")
        self.assertEqual(data["job"]["state"], "SUCCEEDED_COMPLETE")
        self.assertEqual(data["scan_due"]["state"], "NOT_READY")
        self.assertIn("Scheduler is not enabled", data["scan_due"]["reason"] or "")
        health = self.client.get("/api/v1/health", headers=MARKER)
        self.assertEqual(health.status_code, 200, health.text)
        self.assertFalse(health.json()["data"]["data_ready"])
        self.assertEqual(health.json()["data"]["readiness_state"], "NOT_READY")
        self.assertFalse(health.json()["data"]["certified_p0_data"])

        # Clear the active runner so stored PARTIAL completeness drives job_phase.
        self.client.app.state.db.execute("DELETE FROM job WHERE job_id = 'job-running'")
        self.client.app.state.db.execute(
            "UPDATE scan_result SET completeness = 'PARTIAL', envelope_json = ? WHERE scan_key = 'scan-live'",
            (
                json.dumps(
                    {
                        "as_of": "2024-02-02T15:30:00+00:00",
                        "completeness": "PARTIAL",
                        "counts": {"symbols": 1, "candidate_status": {"ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING": 1}},
                        "limitations": ["FIXTURE_NOT_MARKET_DATA"],
                        "full_universe_scan": False,
                        "manifest_id": "run-live",
                    }
                ),
            ),
        )
        self.client.app.state.db.execute(
            "UPDATE job SET state = 'SUCCEEDED_PARTIAL', completeness = 'PARTIAL' WHERE job_id = 'job-stored'"
        )
        partial = self.client.get("/api/v1/overview", headers=MARKER)
        self.assertEqual(partial.status_code, 200, partial.text)
        self.assertIsNone(partial.json()["data"]["active_job"])
        self.assertEqual(partial.json()["data"]["job_phase"], "NOT_READY")
        self.assertEqual(partial.json()["data"]["state"], "PARTIAL")

    def test_approve_refuses_a_missing_checklist(self):
        zone = self.candidate.zone["zone_id"]
        created = self.client.post(
            "/api/v1/plans?include_fixtures=true",
            headers={**MARKER, "Content-Type": "application/json"},
            json={"scan_key": self.scan_key, "symbol": "SYN", "zone_id": zone},
        )
        self.assertEqual(created.status_code, 201, created.text)
        refused = self.client.post(
            "/api/v1/plans/%s/approve" % created.json()["data"]["plan_id"],
            headers={**MARKER, "Content-Type": "application/json"},
            json={
                "combination_index": 0,
                "alert_note": "Missing checklist. Not an order.",
                "recorded_at": self.scan["as_of"],
            },
        )
        self.assertEqual(refused.status_code, 400, refused.text)
        self.assertIn("checklist", refused.text.lower())

    def test_broken_calendar_dir_refuses_a_fill(self):
        from gtf_platform.integration import desk

        zone = self.candidate.zone["zone_id"]
        created = self.client.post(
            "/api/v1/plans?include_fixtures=true",
            headers={**MARKER, "Content-Type": "application/json"},
            json={"scan_key": self.scan_key, "symbol": "SYN", "zone_id": zone},
        )
        approved = self.client.post(
            "/api/v1/plans/%s/approve" % created.json()["data"]["plan_id"],
            headers={**MARKER, "Content-Type": "application/json"},
            json=_approve_body(recorded_at=self.scan["as_of"]),
        )
        self.assertEqual(approved.status_code, 200, approved.text)
        entry_id = approved.json()["data"]["entry_id"]
        submitted = self.client.post(
            "/api/v1/journal/%s/order" % entry_id,
            headers={**MARKER, "Content-Type": "application/json", "Idempotency-Key": "sub-cal"},
            json={"submitted_at": self.scan["as_of"], "order_ref": "KITE-CAL", "note": "Owner submitted in Kite"},
        )
        self.assertEqual(submitted.status_code, 200, submitted.text)
        broken = self.tmp / "broken-calendar"
        broken.mkdir()
        (broken / "events.csv").write_text("not,a,calendar\n", encoding="utf-8")
        settings = _settings(self.tmp)
        from dataclasses import replace

        settings = replace(settings, calendar_dir=broken)
        with self.assertRaises(desk.ApiError) as raised:
            desk._calendar(settings)
        self.assertEqual(raised.exception.status, 422)
        self.assertEqual(raised.exception.code, "DATA_INSUFFICIENT")
        self.client.app.state.settings = settings
        fill = self.client.post(
            "/api/v1/journal/%s/events" % entry_id,
            headers={**MARKER, "Content-Type": "application/json", "Idempotency-Key": "fill-cal"},
            json={"kind": "TRIGGERED", "at": self.scan["as_of"], "price": 100},
        )
        self.assertEqual(fill.status_code, 422, fill.text)
        research = sqlite3.connect(self.tmp / "research.sqlite")
        self.assertEqual(
            research.execute("SELECT COUNT(*) FROM journal_events WHERE kind = 'TRIGGERED'").fetchone()[0],
            0,
        )
        research.close()
