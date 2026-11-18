"""P6 journal product API: search, review, attachments, performance, export."""

from __future__ import annotations

import base64
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
PNG_1X1 = base64.b64encode(
    bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
        "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
    )
).decode("ascii")


def _checklist() -> dict:
    return {code: True for code, _label, _src in models.CHECKLIST}


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


class JournalP6(unittest.TestCase):
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
        self.scan_key = "scan-synthetic-p6"
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
            "manifest_id": "run-synthetic-p6",
        }
        folder = self.tmp / "reports" / self.scan_key
        folder.mkdir(parents=True)
        (folder / "candidates.csv").write_text("symbol,status\nSYN,STORED\n", encoding="utf-8")
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
        self.client.patch(
            "/api/v1/settings",
            headers={**MARKER, "Content-Type": "application/json"},
            json={"capital": 100000, "rpt_pct": 1, "risk_stage": "LEARNING"},
        )
        from nse.research import store as research_store

        research_store.open_store(str(self.tmp / "research.sqlite")).close()

    def tearDown(self):
        self.client.close()
        self._tmp.cleanup()

    def _approve(self) -> int:
        zone = self.candidate.zone["zone_id"]
        created = self.client.post(
            "/api/v1/plans?include_fixtures=true",
            headers={**MARKER, "Content-Type": "application/json", "Idempotency-Key": "p6-plan"},
            json={"scan_key": self.scan_key, "symbol": "SYN", "zone_id": zone},
        )
        self.assertEqual(created.status_code, 201, created.text)
        plan_id = created.json()["data"]["plan_id"]
        approved = self.client.post(
            "/api/v1/plans/%s/approve" % plan_id,
            headers={**MARKER, "Content-Type": "application/json", "Idempotency-Key": "p6-approve"},
            json={
                "combination_index": 0,
                "alert_note": "P6 synthetic plan. Not an order.",
                "checklist": _checklist(),
                "recorded_at": self.scan["as_of"],
            },
        )
        self.assertEqual(approved.status_code, 200, approved.text)
        return int(approved.json()["data"]["entry_id"])

    def test_search_detail_review_attachment_performance_export(self):
        entry_id = self._approve()
        listed = self.client.get("/api/v1/journal?symbol=SYN", headers=MARKER)
        self.assertEqual(listed.status_code, 200, listed.text)
        self.assertEqual(listed.json()["data"]["total"], 1)
        self.assertFalse(listed.json()["data"]["authorises_order"])

        empty = self.client.get("/api/v1/journal?symbol=NOPE", headers=MARKER)
        self.assertEqual(empty.status_code, 200, empty.text)
        self.assertEqual(empty.json()["data"]["total"], 0)

        bad = self.client.get("/api/v1/journal?limit=abc", headers=MARKER)
        self.assertEqual(bad.status_code, 400)

        order = self.client.post(
            "/api/v1/journal/%s/order" % entry_id,
            headers={**MARKER, "Content-Type": "application/json", "Idempotency-Key": "p6-order"},
            json={"submitted_at": "2024-02-03T10:00:00+00:00", "order_ref": "KITE-P6", "note": "submitted"},
        )
        self.assertEqual(order.status_code, 200, order.text)
        fill = self.client.post(
            "/api/v1/journal/%s/executions" % entry_id,
            headers={**MARKER, "Content-Type": "application/json", "Idempotency-Key": "p6-fill"},
            json={
                "side": "ENTRY",
                "quantity": 10,
                "price": 161.0,
                "at": "2024-02-03T11:00:00+00:00",
                "print_key": "p6-entry",
            },
        )
        self.assertEqual(fill.status_code, 200, fill.text)

        note = self.client.post(
            "/api/v1/journal/%s/notes" % entry_id,
            headers={**MARKER, "Content-Type": "application/json", "Idempotency-Key": "p6-note"},
            json={
                "note_key": "n1",
                "at": "2024-02-03T12:00:00+00:00",
                "kind": "POST_TRADE_REVIEW",
                "body": "Synthetic review note.",
            },
        )
        self.assertEqual(note.status_code, 200, note.text)

        review = self.client.post(
            "/api/v1/journal/%s/reviews" % entry_id,
            headers={**MARKER, "Content-Type": "application/json", "Idempotency-Key": "p6-review"},
            json={
                "review_key": "r1",
                "at": "2024-02-03T12:30:00+00:00",
                "review_status": "REVIEWED",
                "outcome_class": "NOT_CLASSIFIED",
                "mistake_category": "NONE",
                "setup_label": "MIT-TEST",
                "note": "Open position still under review process quality.",
            },
        )
        self.assertEqual(review.status_code, 200, review.text)

        attach = self.client.post(
            "/api/v1/journal/%s/attachments" % entry_id,
            headers={**MARKER, "Content-Type": "application/json", "Idempotency-Key": "p6-att"},
            json={
                "attachment_id": "shot1",
                "at": "2024-02-03T13:00:00+00:00",
                "filename": "chart.png",
                "content_type": "image/png",
                "content_base64": PNG_1X1,
            },
        )
        self.assertEqual(attach.status_code, 200, attach.text)

        unsafe = self.client.post(
            "/api/v1/journal/%s/attachments" % entry_id,
            headers={**MARKER, "Content-Type": "application/json", "Idempotency-Key": "p6-bad"},
            json={
                "attachment_id": "exe1",
                "at": "2024-02-03T13:05:00+00:00",
                "filename": "evil.exe",
                "content_type": "image/png",
                "content_base64": base64.b64encode(b"MZFAKE").decode("ascii"),
            },
        )
        self.assertEqual(unsafe.status_code, 400)
        spoofed = self.client.post(
            "/api/v1/journal/%s/attachments" % entry_id,
            headers={**MARKER, "Content-Type": "application/json", "Idempotency-Key": "p6-spoof"},
            json={
                "attachment_id": "spoof1",
                "at": "2024-02-03T13:06:00+00:00",
                "filename": "fake.png",
                "content_type": "image/png",
                "content_base64": base64.b64encode(b"not-an-image-content").decode("ascii"),
            },
        )
        self.assertEqual(spoofed.status_code, 400)

        detail = self.client.get("/api/v1/journal/%s" % entry_id, headers=MARKER)
        self.assertEqual(detail.status_code, 200, detail.text)
        body = detail.json()["data"]
        self.assertEqual(body["review"]["setup_label"], "MIT-TEST")
        self.assertEqual(body["planned_versus_actual"]["state"], "COMPARED")
        self.assertEqual(len(body["attachments"]), 1)
        self.assertFalse(body["authorises_order"])

        got = self.client.get("/api/v1/journal/%s/attachments/shot1" % entry_id, headers=MARKER)
        self.assertEqual(got.status_code, 200, got.text)
        self.assertEqual(got.json()["data"]["content_type"], "image/png")

        perf = self.client.get("/api/v1/journal/performance", headers=MARKER)
        self.assertEqual(perf.status_code, 200, perf.text)
        self.assertEqual(perf.json()["data"]["evidence_class"], "JOURNAL_DESCRIPTIVE")
        self.assertIn("Not certified strategy performance.", perf.json()["data"]["limitations"])

        exported = self.client.get("/api/v1/journal/export?symbol=SYN", headers=MARKER)
        self.assertEqual(exported.status_code, 200, exported.text)
        payload = exported.json()["data"]
        self.assertEqual(payload["format"], "gtf-journal-export-v1")
        self.assertEqual(payload["total"], 1)
        self.assertFalse(payload["attachments_embedded"])

        # Paper remains unimplemented.
        meta = self.client.get("/api/v1/meta", headers=MARKER)
        self.assertEqual(meta.status_code, 200)
        self.assertIn("paper", meta.json()["data"]["routes_not_implemented"])

    def test_journeys_partial_close_missing_costs_and_auth(self):
        """Journeys B/F/G fragments: partial fills, missing costs, auth failure."""
        entry_id = self._approve()
        recorded = self.scan["as_of"]
        self.client.post(
            "/api/v1/journal/%s/order" % entry_id,
            headers={**MARKER, "Content-Type": "application/json", "Idempotency-Key": "p6-j-order"},
            json={"submitted_at": recorded, "order_ref": "KITE-J", "note": "submitted"},
        )
        first = self.client.post(
            "/api/v1/journal/%s/executions" % entry_id,
            headers={**MARKER, "Content-Type": "application/json", "Idempotency-Key": "p6-j-e1"},
            json={"side": "ENTRY", "quantity": 4, "price": 160.0, "at": recorded, "print_key": "e1"},
        )
        self.assertEqual(first.status_code, 200, first.text)
        second = self.client.post(
            "/api/v1/journal/%s/executions" % entry_id,
            headers={**MARKER, "Content-Type": "application/json", "Idempotency-Key": "p6-j-e2"},
            json={"side": "ENTRY", "quantity": 6, "price": 162.0, "at": recorded, "print_key": "e2"},
        )
        self.assertEqual(second.status_code, 200, second.text)
        detail = self.client.get("/api/v1/journal/%s" % entry_id, headers=MARKER).json()["data"]
        self.assertEqual(detail["book"]["executed_entry_quantity"], 10)
        self.assertAlmostEqual(detail["book"]["average_entry_price"], (4 * 160.0 + 6 * 162.0) / 10)
        partial = self.client.post(
            "/api/v1/journal/%s/executions" % entry_id,
            headers={**MARKER, "Content-Type": "application/json", "Idempotency-Key": "p6-j-x1"},
            json={"side": "EXIT", "quantity": 3, "price": 170.0, "at": recorded, "print_key": "x1"},
        )
        self.assertEqual(partial.status_code, 200, partial.text)
        after = self.client.get("/api/v1/journal/%s" % entry_id, headers=MARKER).json()["data"]
        self.assertEqual(after["book"]["open_quantity"], 7)
        dup = self.client.post(
            "/api/v1/journal/%s/executions" % entry_id,
            headers={**MARKER, "Content-Type": "application/json", "Idempotency-Key": "p6-j-e1"},
            json={"side": "ENTRY", "quantity": 4, "price": 160.0, "at": recorded, "print_key": "e1"},
        )
        self.assertEqual(dup.status_code, 200, dup.text)
        self.assertTrue(dup.json()["data"]["already_present"])
        final = self.client.post(
            "/api/v1/journal/%s/executions" % entry_id,
            headers={**MARKER, "Content-Type": "application/json", "Idempotency-Key": "p6-j-x2"},
            json={"side": "EXIT", "quantity": 7, "price": 171.0, "at": recorded, "print_key": "x2"},
        )
        self.assertEqual(final.status_code, 200, final.text)
        self.client.post(
            "/api/v1/journal/%s/events" % entry_id,
            headers={**MARKER, "Content-Type": "application/json", "Idempotency-Key": "p6-j-close"},
            json={"kind": "CLOSED_MANUAL", "at": recorded, "price": 171.0, "note": "closed"},
        )
        perf = self.client.get("/api/v1/journal/performance", headers=MARKER).json()["data"]
        self.assertEqual(perf["totals"]["closed_trades"], 1)
        self.assertEqual(perf["totals"]["net_state"], "INCOMPLETE_COSTS")
        self.assertIsNone(perf["totals"]["net_realised_pnl"])
        self.assertNotIn("costs are not recorded", str(perf.get("note", "")).lower())
        unauth = TestClient(self.client.app, base_url="http://127.0.0.1:8765", client=("127.0.0.1", 50001))
        denied = unauth.get("/api/v1/journal", headers=MARKER)
        self.assertEqual(denied.status_code, 401)


if __name__ == "__main__":
    unittest.main()
