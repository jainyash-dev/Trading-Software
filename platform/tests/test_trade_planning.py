"""GTF P4 trade-planning tests.

Uses the synthetic research fixture. Not NSE market data. Not performance evidence.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
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
        "alert_note": "Synthetic P4 plan. Not an order.",
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
        calendar_dir=ROOT / "nse" / "data" / "calendar",
        repo_root=ROOT,
    )


class TradePlanningP4(unittest.TestCase):
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
        self.client = TestClient(
            create_app(_settings(self.tmp)),
            base_url="http://127.0.0.1:8765",
            client=("127.0.0.1", 50000),
        )
        self.client.post("/api/v1/session/bootstrap", headers=MARKER)
        self.scan_key = "scan-p4"
        self.zone = self.candidate.zone["zone_id"]
        envelope = {
            "as_of": self.scan["as_of"],
            "trade_type": self.scan["trade_type"],
            "invocation": "manual",
            "dataset_id": "synthetic",
            "completeness": "COMPLETE",
            "full_universe_scan": False,
            "fixture": True,
            "limitations": list(self.scan["limitations"]) + ["FIXTURE_NOT_MARKET_DATA"],
            "symbols_not_opened": [],
            "symbols": self.scan["symbols"],
            "scan": self.scan,
            "authorises_order": False,
            "idempotency_key": self.scan_key,
            "manifest_id": "run-synthetic",
        }
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

    def tearDown(self):
        self.client.close()
        self._tmp.cleanup()

    def _create(self, **extra):
        body = {"scan_key": self.scan_key, "symbol": "SYN", "zone_id": self.zone}
        body.update(extra)
        return self.client.post(
            "/api/v1/plans?include_fixtures=true",
            headers={**MARKER, "Content-Type": "application/json"},
            json=body,
        )

    def _insert_scan(self, scan_key: str, envelope: dict, *, fixture: int = 1) -> None:
        self.client.app.state.db.execute(
            """
            INSERT INTO scan_result (
                scan_key, job_id, as_of, trade_type, invocation, dataset_id, universe_label,
                completeness, full_universe_scan, fixture, limitations_json,
                symbols_not_opened_json, envelope_json, created_at
            ) VALUES (?, NULL, ?, ?, 'manual', ?, 'SYNTHETIC', 'COMPLETE', 0, ?, ?, '[]', ?, ?)
            """,
            (
                scan_key,
                envelope["as_of"],
                envelope["trade_type"],
                envelope.get("dataset_id") or "synthetic",
                fixture,
                json.dumps(envelope.get("limitations") or []),
                json.dumps(envelope),
                "2024-02-02T18:00:00+00:00",
            ),
        )

    def test_create_preview_lists_and_idempotent_draft(self):
        first = self._create(rationale="First look")
        self.assertEqual(first.status_code, 201, first.text)
        data = first.json()["data"]
        self.assertEqual(data["state"], "DRAFT")
        self.assertEqual(data["candidate_status"], models.ACTIONABLE)
        self.assertEqual(data["source_quality"], "FIXTURE")
        self.assertFalse(data["authorises_order"])
        second = self._create()
        self.assertEqual(second.status_code, 201, second.text)
        self.assertEqual(second.json()["data"]["plan_id"], data["plan_id"])
        preview = self.client.get("/api/v1/plans/%s" % data["plan_id"], headers=MARKER)
        self.assertEqual(preview.status_code, 200, preview.text)
        body = preview.json()["data"]
        self.assertIn("portfolio_checks", body)
        self.assertIn("geometry", body)
        self.assertIn("capacity", body)
        self.assertIn("manual_execution", body)
        self.assertFalse(body["authorises_order"])
        self.assertFalse(body["manual_execution"]["authorises_order"])
        self.assertGreater(len(body["combinations"]), 0)
        listed = self.client.get("/api/v1/plans", headers=MARKER)
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertEqual(listed.json()["data"]["counts_by_state"]["DRAFT"], 1)

    def test_submit_reject_reopen_cancel(self):
        plan_id = self._create().json()["data"]["plan_id"]
        submitted = self.client.post(
            "/api/v1/plans/%s/submit" % plan_id,
            headers={**MARKER, "Content-Type": "application/json"},
            json={"note": "Ready for review"},
        )
        self.assertEqual(submitted.status_code, 200, submitted.text)
        self.assertEqual(submitted.json()["data"]["state"], "AWAITING_OWNER")
        rejected = self.client.post(
            "/api/v1/plans/%s/reject" % plan_id,
            headers={**MARKER, "Content-Type": "application/json"},
            json={"reason": "Setup no longer fits"},
        )
        self.assertEqual(rejected.status_code, 200, rejected.text)
        self.assertEqual(rejected.json()["data"]["state"], "REJECTED")
        reopened = self.client.post(
            "/api/v1/plans/%s/reopen" % plan_id,
            headers={**MARKER, "Content-Type": "application/json"},
            json={},
        )
        self.assertEqual(reopened.status_code, 200, reopened.text)
        self.assertEqual(reopened.json()["data"]["state"], "DRAFT")
        cancelled = self.client.post(
            "/api/v1/plans/%s/cancel" % plan_id,
            headers={**MARKER, "Content-Type": "application/json"},
            json={"reason": "Owner cancelled before approval"},
        )
        self.assertEqual(cancelled.status_code, 200, cancelled.text)
        self.assertEqual(cancelled.json()["data"]["state"], "CANCELLED")
        history = self.client.get("/api/v1/plans/%s/history" % plan_id, headers=MARKER)
        self.assertEqual(history.status_code, 200, history.text)
        actions = [event["action"] for event in history.json()["data"]["events"]]
        self.assertIn("CREATED", actions)
        self.assertIn("SUBMITTED", actions)
        self.assertIn("REJECTED", actions)
        self.assertIn("REOPENED", actions)
        self.assertIn("CANCELLED", actions)

    def test_refuse_blocked_candidate_and_notes(self):
        blocked = json.loads(json.dumps(self.scan))
        for symbol in blocked.get("symbols") or []:
            for candidate in symbol.get("candidates") or []:
                candidate["status"] = "BLOCKED"
        self._insert_scan(
            "scan-blocked",
            {
                "as_of": blocked["as_of"],
                "trade_type": blocked["trade_type"],
                "dataset_id": "synthetic",
                "limitations": ["FIXTURE"],
                "fixture": True,
                "scan": blocked,
                "symbols": blocked.get("symbols") or [],
            },
        )
        refused = self.client.post(
            "/api/v1/plans?include_fixtures=true",
            headers={**MARKER, "Content-Type": "application/json"},
            json={"scan_key": "scan-blocked", "symbol": "SYN", "zone_id": self.zone},
        )
        self.assertEqual(refused.status_code, 409, refused.text)
        plan_id = self._create().json()["data"]["plan_id"]
        note = self.client.post(
            "/api/v1/plans/%s/notes" % plan_id,
            headers={**MARKER, "Content-Type": "application/json"},
            json={"body": "Watching opening range. Not methodology."},
        )
        self.assertEqual(note.status_code, 200, note.text)
        listed = self.client.get("/api/v1/plans/%s/notes" % plan_id, headers=MARKER)
        self.assertEqual(len(listed.json()["data"]["notes"]), 1)

    def test_approve_preserves_canonical_status_and_planned_vs_actual(self):
        plan_id = self._create().json()["data"]["plan_id"]
        approved = self.client.post(
            "/api/v1/plans/%s/approve" % plan_id,
            headers={**MARKER, "Content-Type": "application/json"},
            json=_approve_body(recorded_at=self.scan["as_of"]),
        )
        self.assertEqual(approved.status_code, 200, approved.text)
        data = approved.json()["data"]
        self.assertEqual(data["state"], "APPROVED")
        self.assertEqual(data["candidate_status_unchanged"], models.ACTIONABLE)
        self.assertFalse(data["authorises_order"])
        self.assertIsNotNone(data["entry_id"])
        cancel = self.client.post(
            "/api/v1/plans/%s/cancel" % plan_id,
            headers={**MARKER, "Content-Type": "application/json"},
            json={"reason": "Should refuse"},
        )
        self.assertEqual(cancel.status_code, 409, cancel.text)
        preview = self.client.get("/api/v1/plans/%s" % plan_id, headers=MARKER)
        self.assertEqual(preview.status_code, 200, preview.text)
        vs = preview.json()["data"]["planned_versus_actual"]
        self.assertIsNotNone(vs)
        self.assertEqual(vs["state"], "PLANNED_ONLY")
        self.assertFalse(vs["authorises_order"])

    # --- P4-IR-04: journal cancellation must not leave the plan APPROVED -----------------

    def _approved(self) -> tuple[str, int]:
        plan_id = self._create().json()["data"]["plan_id"]
        approved = self.client.post(
            "/api/v1/plans/%s/approve" % plan_id,
            headers={**MARKER, "Content-Type": "application/json"},
            json=_approve_body(recorded_at=self.scan["as_of"]),
        )
        self.assertEqual(approved.status_code, 200, approved.text)
        return plan_id, int(approved.json()["data"]["entry_id"])

    def _journal_event(self, entry_id: int, kind: str, **extra):
        body = {"kind": kind, "at": self.scan["as_of"], "note": "Synthetic P4-IR-04 test"}
        body.update(extra)
        return self.client.post(
            "/api/v1/journal/%d/events" % entry_id,
            headers={**MARKER, "Content-Type": "application/json"},
            json=body,
        )

    def _journal_state(self, entry_id: int) -> str:
        from nse.research import store

        conn = store.open_readonly(str(self.tmp / "research.sqlite"))
        try:
            return store._state(store.journal_events(conn, entry_id))[0]
        finally:
            conn.close()

    def test_ir04_journal_cancel_syncs_plan_on_write_and_read(self):
        plan_id, entry_id = self._approved()
        cancelled = self._journal_event(entry_id, "CANCELLED")
        self.assertEqual(cancelled.status_code, 200, cancelled.text)
        self.assertEqual(cancelled.json()["data"]["plan_sync"]["synced"], [plan_id])
        self.assertEqual(self._journal_state(entry_id), "CANCELLED")
        preview = self.client.get("/api/v1/plans/%s" % plan_id, headers=MARKER).json()["data"]
        self.assertEqual(preview["state"], "CANCELLED")
        self.assertEqual(preview["journal_state"], "CANCELLED")
        self.assertEqual(preview["journal_sync"], "IN_SYNC")
        self.assertEqual(preview["cancelled_by"], "journal-sync")
        self.assertFalse(preview["authorises_order"])
        listed = self.client.get("/api/v1/plans", headers=MARKER).json()["data"]
        row = [item for item in listed["plans"] if item["plan_id"] == plan_id][0]
        self.assertEqual(row["state"], "CANCELLED")
        self.assertEqual(listed["counts_by_state"]["APPROVED"], 0)
        self.assertEqual(listed["counts_by_state"]["CANCELLED"], 1)
        events = self.client.get("/api/v1/plans/%s/history" % plan_id, headers=MARKER).json()["data"]["events"]
        actions = [event["action"] for event in events]
        self.assertEqual(actions.count("JOURNAL_SYNC_CANCELLED"), 1)
        self.assertEqual(actions[:2], ["CREATED", "APPROVED"])  # append-only history kept

    def test_ir04_repeated_cancel_and_platform_cancel_after_journal_cancel(self):
        plan_id, entry_id = self._approved()
        # Platform cancel of an approved plan with a live journal entry is still refused (ED-3).
        refused = self.client.post(
            "/api/v1/plans/%s/cancel" % plan_id,
            headers={**MARKER, "Content-Type": "application/json"},
            json={"reason": "Should refuse while the journal entry is PLANNED"},
        )
        self.assertEqual(refused.status_code, 409, refused.text)
        self.assertEqual(self._journal_state(entry_id), "PLANNED")
        first = self._journal_event(entry_id, "CANCELLED")
        self.assertEqual(first.status_code, 200, first.text)
        replay = self._journal_event(entry_id, "CANCELLED")  # identical body: idempotent replay
        self.assertEqual(replay.status_code, 200, replay.text)
        self.assertEqual(replay.json()["data"]["seq"], first.json()["data"]["seq"])
        again = self._journal_event(entry_id, "CANCELLED", note="a different second cancel")
        self.assertEqual(again.status_code, 409, again.text)  # the journal refuses a second CANCELLED
        platform = self.client.post(
            "/api/v1/plans/%s/cancel" % plan_id,
            headers={**MARKER, "Content-Type": "application/json"},
            json={"reason": "Already cancelled in the journal"},
        )
        self.assertEqual(platform.status_code, 200, platform.text)
        self.assertEqual(platform.json()["data"]["state"], "CANCELLED")
        events = self.client.get("/api/v1/plans/%s/history" % plan_id, headers=MARKER).json()["data"]["events"]
        cancels = [event for event in events if event["to_state"] == "CANCELLED"]
        self.assertEqual(len(cancels), 1)

    def test_ir04_recovery_when_platform_mirror_was_interrupted(self):
        """Journal write committed, platform mirror never ran (crash / outside CLI)."""
        plan_id, entry_id = self._approved()
        from nse.research import store

        conn = store.open_store(str(self.tmp / "research.sqlite"))
        try:
            store.journal_event(conn, entry_id, "CANCELLED", self.scan["as_of"], note="research CLI cancel")
        finally:
            conn.close()
        raw = self.client.app.state.db.execute("SELECT state FROM trade_plan WHERE plan_id = ?", (plan_id,)).fetchone()
        self.assertEqual(raw["state"], "APPROVED")  # the reproduced desynchronisation
        # Restart: a fresh app over the same files repairs the mirror at startup.
        self.client.close()
        self.client = TestClient(create_app(_settings(self.tmp)), base_url="http://127.0.0.1:8765", client=("127.0.0.1", 50000))
        self.client.post("/api/v1/session/bootstrap", headers=MARKER)
        raw = self.client.app.state.db.execute("SELECT state FROM trade_plan WHERE plan_id = ?", (plan_id,)).fetchone()
        self.assertEqual(raw["state"], "CANCELLED")
        preview = self.client.get("/api/v1/plans/%s" % plan_id, headers=MARKER).json()["data"]
        self.assertEqual(preview["journal_sync"], "IN_SYNC")

    def test_ir04_read_repairs_without_restart_and_journal_unavailable_is_disclosed(self):
        plan_id, entry_id = self._approved()
        from nse.research import store

        conn = store.open_store(str(self.tmp / "research.sqlite"))
        try:
            store.journal_event(conn, entry_id, "CANCELLED", self.scan["as_of"], note="outside the platform")
        finally:
            conn.close()
        listed = self.client.get("/api/v1/plans", headers=MARKER).json()["data"]
        row = [item for item in listed["plans"] if item["plan_id"] == plan_id][0]
        self.assertEqual(row["state"], "CANCELLED")
        # Journal unreadable: the plan is not changed and the state is not claimed consistent.
        self.client.app.state.db.execute(
            "UPDATE trade_plan SET state = 'APPROVED', entry_id = 999999 WHERE plan_id = ?", (plan_id,)
        )
        preview = self.client.get("/api/v1/plans/%s" % plan_id, headers=MARKER).json()["data"]
        self.assertEqual(preview["state"], "APPROVED")
        self.assertEqual(preview["journal_sync"], "JOURNAL_ENTRY_MISSING")
        (self.tmp / "research.sqlite").rename(self.tmp / "research.moved")
        preview = self.client.get("/api/v1/plans/%s" % plan_id, headers=MARKER).json()["data"]
        self.assertEqual(preview["journal_sync"], "JOURNAL_UNAVAILABLE")
        self.assertIsNone(preview["journal_state"])
        self.assertEqual(preview["state"], "APPROVED")

    def test_ir04_journal_expired_event_is_mirrored_not_auto_produced(self):
        plan_id, entry_id = self._approved()
        submitted = self.client.post(
            "/api/v1/journal/%d/order" % entry_id,
            headers={**MARKER, "Content-Type": "application/json"},
            json={"submitted_at": self.scan["as_of"], "order_ref": "manual-ref", "note": "owner typed"},
        )
        self.assertEqual(submitted.status_code, 200, submitted.text)
        # No clock: the plan stays APPROVED until the owner records EXPIRED in the journal.
        self.assertEqual(self.client.get("/api/v1/plans/%s" % plan_id, headers=MARKER).json()["data"]["state"], "APPROVED")
        expired = self._journal_event(entry_id, "EXPIRED")
        self.assertEqual(expired.status_code, 200, expired.text)
        preview = self.client.get("/api/v1/plans/%s" % plan_id, headers=MARKER).json()["data"]
        self.assertEqual(preview["state"], "EXPIRED")
        self.assertEqual(preview["journal_state"], "EXPIRED")

    def test_ir04_open_and_closed_journal_entries_keep_plan_approved(self):
        plan_id, entry_id = self._approved()
        selected = self.client.get("/api/v1/plans/%s" % plan_id, headers=MARKER).json()["data"]["selected"]
        triggered = self._journal_event(entry_id, "TRIGGERED", price=selected["entry"])
        self.assertEqual(triggered.status_code, 200, triggered.text)
        preview = self.client.get("/api/v1/plans/%s" % plan_id, headers=MARKER).json()["data"]
        self.assertEqual(preview["state"], "APPROVED")
        self.assertEqual(preview["journal_state"], "OPEN")
        self.assertEqual(preview["journal_sync"], "IN_SYNC")
        closed = self._journal_event(entry_id, "CLOSED_MANUAL", price=selected["entry"])
        self.assertEqual(closed.status_code, 200, closed.text)
        preview = self.client.get("/api/v1/plans/%s" % plan_id, headers=MARKER).json()["data"]
        self.assertEqual(preview["state"], "APPROVED")
        self.assertEqual(preview["journal_state"], "CLOSED")

    def test_ir04_journal_refusal_leaves_plan_unchanged(self):
        plan_id, entry_id = self._approved()
        selected = self.client.get("/api/v1/plans/%s" % plan_id, headers=MARKER).json()["data"]["selected"]
        self.assertEqual(self._journal_event(entry_id, "TRIGGERED", price=selected["entry"]).status_code, 200)
        refused = self._journal_event(entry_id, "CANCELLED", note="cannot cancel an open trade")
        self.assertEqual(refused.status_code, 409, refused.text)
        preview = self.client.get("/api/v1/plans/%s" % plan_id, headers=MARKER).json()["data"]
        self.assertEqual(preview["state"], "APPROVED")
        self.assertEqual(preview["journal_state"], "OPEN")
        self.assertEqual(preview["journal_sync"], "IN_SYNC")

    def test_ir04_plan_mirror_failure_is_reported_then_repaired_on_read(self):
        from unittest import mock

        from gtf_platform.planning import service as planning

        plan_id, entry_id = self._approved()
        with mock.patch.object(planning, "mirror_journal_terminal", side_effect=RuntimeError("disk full")):
            cancelled = self._journal_event(entry_id, "CANCELLED")
        self.assertEqual(cancelled.status_code, 200, cancelled.text)  # the journal write stands
        self.assertEqual(cancelled.json()["data"]["plan_sync"]["status"], "PENDING_REPAIR_ON_READ")
        self.assertEqual(self._journal_state(entry_id), "CANCELLED")
        raw = self.client.app.state.db.execute("SELECT state FROM trade_plan WHERE plan_id = ?", (plan_id,)).fetchone()
        self.assertEqual(raw["state"], "APPROVED")  # rolled back, not half-written
        preview = self.client.get("/api/v1/plans/%s" % plan_id, headers=MARKER).json()["data"]
        self.assertEqual(preview["state"], "CANCELLED")
        self.assertEqual(preview["journal_sync"], "IN_SYNC")

    def test_ir04_concurrent_readers_and_cancellers_mirror_once(self):
        import threading

        from nse.research import store

        plan_id, entry_id = self._approved()
        conn = store.open_store(str(self.tmp / "research.sqlite"))
        try:
            store.journal_event(conn, entry_id, "CANCELLED", self.scan["as_of"], note="outside cancel")
        finally:
            conn.close()
        errors: list[str] = []

        def hit(index: int) -> None:
            if index % 2:
                response = self.client.get("/api/v1/plans", headers=MARKER)
            else:
                response = self.client.post(
                    "/api/v1/plans/%s/cancel" % plan_id,
                    headers={**MARKER, "Content-Type": "application/json"},
                    json={"reason": "concurrent cancel %d" % index},
                )
            if response.status_code != 200:
                errors.append(response.text)

        threads = [threading.Thread(target=hit, args=(index,)) for index in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(errors, [])
        events = self.client.get("/api/v1/plans/%s/history" % plan_id, headers=MARKER).json()["data"]["events"]
        self.assertEqual([event["to_state"] for event in events].count("CANCELLED"), 1)

    # --- FR-5.9 / TP-010: a later scan does not overwrite the plan; the mismatch is shown ----

    def _insert_later(self, scan_key: str, envelope: dict, *, fixture: int = 1, created_at: str = "2024-02-03T18:00:00+00:00",
                      dataset_id: str = "synthetic"):
        self.client.app.state.db.execute(
            """
            INSERT INTO scan_result (
                scan_key, job_id, as_of, trade_type, invocation, dataset_id, universe_label,
                completeness, full_universe_scan, fixture, limitations_json,
                symbols_not_opened_json, envelope_json, created_at
            ) VALUES (?, NULL, ?, ?, 'manual', ?, 'SYNTHETIC', 'COMPLETE', 0, ?, '[]', '[]', ?, ?)
            """,
            (scan_key, envelope["as_of"], envelope["trade_type"], dataset_id, fixture, json.dumps(envelope), created_at),
        )

    def test_tp010_later_scan_change_is_shown_and_plan_version_kept(self):
        plan_id = self._create().json()["data"]["plan_id"]
        first = self.client.get("/api/v1/plans/%s" % plan_id, headers=MARKER).json()["data"]
        self.assertEqual(first["later_scan"]["state"], "NO_LATER_SCAN")
        changed = json.loads(json.dumps(self.scan))
        for symbol in changed["symbols"]:
            for candidate in symbol.get("candidates") or []:
                candidate["status"] = "MANUAL_REVIEW"
                candidate["zone"]["test_count"] = 1
        self._insert_later("scan-later", {"as_of": self.scan["as_of"], "trade_type": self.scan["trade_type"], "symbols": changed["symbols"], "completeness": "COMPLETE"})
        preview = self.client.get("/api/v1/plans/%s" % plan_id, headers=MARKER).json()["data"]
        later = preview["later_scan"]
        self.assertEqual(later["state"], "CHANGED")
        self.assertEqual(later["scan_key"], "scan-later")
        fields = {item["field"]: item for item in later["differences"]}
        self.assertEqual(fields["status"]["plan"], models.ACTIONABLE)
        self.assertEqual(fields["status"]["later_scan"], "MANUAL_REVIEW")
        self.assertIn("test_count", fields)
        # The plan keeps its own version and status.
        self.assertEqual(preview["candidate_status"], models.ACTIONABLE)
        self.assertEqual(preview["plan_version"], first["plan_version"])
        self.assertEqual(preview["scan_key"], self.scan_key)

    def test_tp010_zone_gone_unrelated_and_cross_fixture_scans(self):
        plan_id = self._create().json()["data"]["plan_id"]
        other = [dict(symbol, symbol="OTHER") for symbol in self.scan["symbols"]]
        self._insert_later("scan-other", {"as_of": self.scan["as_of"], "trade_type": self.scan["trade_type"], "symbols": other})
        changed = json.loads(json.dumps(self.scan["symbols"]))
        for symbol in changed:
            for candidate in symbol.get("candidates") or []:
                candidate["status"] = "REJECTED"
        same_symbol = {"as_of": self.scan["as_of"], "trade_type": self.scan["trade_type"], "symbols": changed}
        # Each of these covers the plan's symbol with a changed candidate, but must not be compared:
        self._insert_later("scan-real", same_symbol, fixture=0)  # accepted-data vs fixture plan
        self._insert_later("scan-other-dataset", same_symbol, dataset_id="another-dataset")  # zone ids not stable
        self._insert_later("scan-wit", dict(same_symbol, trade_type="WIT-75"))  # different trade type
        self.assertEqual(
            self.client.get("/api/v1/plans/%s" % plan_id, headers=MARKER).json()["data"]["later_scan"]["state"], "NO_LATER_SCAN"
        )
        gone = [dict(symbol, candidates=[], blocked_zones=[{"zone_id": self.zone, "disposition": "TESTED_ZONE", "overlay_status": "TESTED"}])
                for symbol in self.scan["symbols"]]
        self._insert_later("scan-gone", {"as_of": self.scan["as_of"], "trade_type": self.scan["trade_type"], "symbols": gone},
                           created_at="2024-02-04T18:00:00+00:00")
        later = self.client.get("/api/v1/plans/%s" % plan_id, headers=MARKER).json()["data"]["later_scan"]
        self.assertEqual(later["state"], "ZONE_NOT_A_CANDIDATE")
        self.assertEqual(later["later_overlay_status"], "TESTED")
        # A later DATA_INSUFFICIENT symbol row is an unknown result, not "the zone left the list".
        unknown = [dict(symbol, status="DATA_INSUFFICIENT", candidates=[], blocked_zones=[]) for symbol in self.scan["symbols"]]
        self._insert_later("scan-unknown", {"as_of": self.scan["as_of"], "trade_type": self.scan["trade_type"], "symbols": unknown},
                           created_at="2024-02-05T18:00:00+00:00")
        later = self.client.get("/api/v1/plans/%s" % plan_id, headers=MARKER).json()["data"]["later_scan"]
        self.assertEqual(later["state"], "LATER_RESULT_NOT_EVALUATED")
        self.assertEqual(later["later_symbol_status"], "DATA_INSUFFICIENT")

    # --- review finding 1: a reused or foreign journal entry number is never trusted -----

    def test_ir04_recreated_journal_reusing_entry_ids_is_not_trusted(self):
        plan_a, entry_a = self._approved()
        (self.tmp / "research.sqlite").rename(self.tmp / "research.previous")  # journal recreated / swapped
        plan_b, entry_b = self._approved()
        self.assertEqual(entry_a, entry_b)  # entry numbers restart: the hazard
        view_a = self.client.get("/api/v1/plans/%s" % plan_a, headers=MARKER).json()["data"]
        self.assertEqual(view_a["journal_sync"], "JOURNAL_IDENTITY_MISMATCH")
        self.assertIsNone(view_a["journal_state"])
        self.assertEqual(self._journal_event(entry_b, "CANCELLED").status_code, 200)
        self.assertEqual(self.client.get("/api/v1/plans/%s" % plan_b, headers=MARKER).json()["data"]["state"], "CANCELLED")
        view_a = self.client.get("/api/v1/plans/%s" % plan_a, headers=MARKER).json()["data"]
        self.assertEqual(view_a["state"], "APPROVED")  # the unrelated plan was not written
        self.assertEqual(view_a["journal_sync"], "JOURNAL_IDENTITY_MISMATCH")

    def test_ir04_entry_for_another_zone_is_identity_mismatch(self):
        plan_id, _entry = self._approved()
        self.client.app.state.db.execute("UPDATE trade_plan SET zone_id = 'demand-other' WHERE plan_id = ?", (plan_id,))
        view = self.client.get("/api/v1/plans/%s" % plan_id, headers=MARKER).json()["data"]
        self.assertEqual(view["journal_sync"], "JOURNAL_IDENTITY_MISMATCH")

    def test_journal_zone_invalidated_is_flagged(self):
        plan_id, entry_id = self._approved()
        view = self.client.get("/api/v1/plans/%s" % plan_id, headers=MARKER).json()["data"]
        self.assertFalse(view["journal_zone_invalidated"])
        self.assertEqual(self._journal_event(entry_id, "ZONE_INVALIDATED").status_code, 200)
        view = self.client.get("/api/v1/plans/%s" % plan_id, headers=MARKER).json()["data"]
        self.assertEqual(view["journal_state"], "PLANNED")  # canonical journal state is not renamed
        self.assertTrue(view["journal_zone_invalidated"])

    def test_geometry_blocks_tested_overlay(self):
        from gtf_platform.planning.service import _geometry_summary

        candidate = {
            "levels": {"entry": [100.0, 101.0], "sl": {"normal": [95.0, 96.0]}},
            "gates": [{"gate": "G7", "evidence": {"target": {"proximal": 120.0}}}],
            "zone": {"overlay_status": "TESTED", "test_count": 2},
        }
        combinations = [
            {"entry": 100.0, "stop": 95.0, "target": 120.0, "quantity": 10, "status": "WITHIN_RISK_RULES_MANUAL_CHECKS_PENDING"}
        ]
        summary = _geometry_summary(candidate, combinations)
        self.assertEqual(summary["status"], "BLOCKED")
        self.assertTrue(any("test_count" in reason for reason in summary["reasons"]))

    def test_certified_source_downgraded_to_exploratory(self):
        self._insert_scan(
            "scan-certified-claim",
            {
                "as_of": self.scan["as_of"],
                "trade_type": self.scan["trade_type"],
                "dataset_id": "claimed-certified",
                "source_label": "CERTIFIED",
                "limitations": [],
                "fixture": False,
                "scan": self.scan,
                "symbols": self.scan.get("symbols") or [],
            },
            fixture=0,
        )
        created = self.client.post(
            "/api/v1/plans",
            headers={**MARKER, "Content-Type": "application/json"},
            json={"scan_key": "scan-certified-claim", "symbol": "SYN", "zone_id": self.zone},
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(created.json()["data"]["source_quality"], "EXPLORATORY")


if __name__ == "__main__":
    unittest.main()
