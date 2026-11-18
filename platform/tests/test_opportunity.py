"""P3 opportunity intelligence API tests. Fixtures are not market data."""

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

from fastapi.testclient import TestClient  # noqa: E402

from gtf_platform.app import create_app  # noqa: E402
from gtf_platform.config import Settings  # noqa: E402
from gtf_platform.db import connect  # noqa: E402
from gtf_platform.opportunity.ingest import classify_source_quality, initial_workflow  # noqa: E402
from gtf_platform.opportunity.lifecycle import allowed_transitions, apply_transition  # noqa: E402
from gtf_platform.opportunity.priority import organizational_priority  # noqa: E402
from gtf_platform.opportunity.repository import insert_opportunity, list_opportunities  # noqa: E402
from gtf_platform.store import insert_watchlist  # noqa: E402

MARKER = {
    "X-GTF-Request": "1",
    "Origin": "http://127.0.0.1:8765",
    "Sec-Fetch-Site": "same-origin",
}


def settings(tmp: Path, **overrides) -> Settings:
    values = dict(
        bind_host="127.0.0.1",
        bind_port=8765,
        advertised_port=8765,
        public_origins=(),
        platform_db=tmp / "platform.sqlite",
        research_db=None,
        cookie_secure=False,
        data_dir=tmp,
        testing=True,
        csv_dir=tmp / "csv",
        bhavcopy_dir=None,
        eod_manifest=None,
        calendar_dir=None,
        universe_path=None,
        instruments_path=None,
        corporate_actions_path=None,
        equity_names_path=None,
        source_label="FIXTURE",
        price_adjustment="NONE",
        fixture_mode=True,
        scheduler_enabled=False,
    )
    values.update(overrides)
    return Settings(**values)


def seed_scan(connection, *, scan_key: str = "scan-1", fixture: bool = True) -> None:
    envelope = {
        "authorises_order": False,
        "as_of": "2024-01-02",
        "dataset_id": "ds-fixture",
        "limitations": ["FIXTURE_NOT_MARKET_DATA"],
        "symbols": [
            {
                "symbol": "AAA",
                "status": "ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING",
                "candidates": [
                    {
                        "status": "ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING",
                        "zone_id": "z-1",
                        "timeframe": "D",
                        "zone": {"zone_id": "z-1", "timeframe": "D"},
                        "manual_checks": ["checklist"],
                    }
                ],
            },
            {
                "symbol": "BBB",
                "status": "BLOCKED",
                "candidates": [],
            },
            {
                "symbol": "CCC",
                "status": "REJECTED",
                "candidates": [
                    {"status": "REJECTED", "zone_id": "z-2", "timeframe": "W"},
                ],
            },
        ],
    }
    connection.execute(
        """
        INSERT INTO scan_result (
            scan_key, job_id, as_of, trade_type, invocation, dataset_id, universe_label,
            completeness, full_universe_scan, fixture, limitations_json, symbols_not_opened_json,
            envelope_json, created_at
        ) VALUES (?, NULL, ?, 'MIT', 'manual', ?, 'fixture', 'PARTIAL', 0, ?, ?, '[]', ?, ?)
        """,
        (
            scan_key,
            "2024-01-02",
            "ds-fixture",
            1 if fixture else 0,
            json.dumps(["FIXTURE_NOT_MARKET_DATA"] if fixture else ["EXPLORATORY"]),
            json.dumps(envelope),
            "2024-01-02T00:00:00+00:00",
        ),
    )


class OpportunityUnit(unittest.TestCase):
    def test_source_quality_never_invents_certified(self) -> None:
        self.assertEqual(classify_source_quality(fixture=True, limitations=[]), "FIXTURE")
        self.assertEqual(classify_source_quality(fixture=False, limitations=["EXPLORATORY"]), "EXPLORATORY")

    def test_fixture_starts_blocked_workflow(self) -> None:
        self.assertEqual(
            initial_workflow("ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING", source_quality="FIXTURE"),
            "BLOCKED",
        )
        self.assertEqual(
            initial_workflow("ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING", source_quality="EXPLORATORY"),
            "DISCOVERED",
        )

    def test_priority_is_non_authoritative(self) -> None:
        score = organizational_priority(
            {
                "canonical_status": "ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING",
                "workflow_state": "SHORTLISTED",
                "source_quality": "EXPLORATORY",
                "fixture": False,
            }
        )
        self.assertFalse(score["authoritative"])
        self.assertIn("does not predict returns", score["disclosure"])

    def test_certified_label_downgraded_on_insert(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            connection = connect(Path(raw) / "db.sqlite")
            view, created = insert_opportunity(
                connection,
                scan_key="s",
                symbol="AAA",
                zone_id="z",
                timeframe="D",
                as_of="2024-01-02",
                dataset_id="ds",
                canonical_status="MANUAL_REVIEW",
                source_quality="CERTIFIED",
                fixture=False,
                source_snapshot={},
            )
            self.assertTrue(created)
            self.assertEqual(view["source_quality"], "EXPLORATORY")
            self.assertFalse(view["authorises_order"])
            connection.close()


class OpportunityApi(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        app = create_app(settings(self.tmp))
        self.client = TestClient(app, base_url="http://127.0.0.1:8765", client=("127.0.0.1", 50000))
        boot = self.client.post("/api/v1/session/bootstrap", headers=MARKER)
        self.assertEqual(boot.status_code, 200, boot.text)

    def tearDown(self) -> None:
        self.client.close()
        self._tmp.cleanup()

    def test_ingest_reads_canonical_keys_from_real_scanner_output(self) -> None:
        """Regression (2026-11-17): ingest read `timeframe`; canonical keys are execution_tf / zone.tf."""
        sys.path.append(str(ROOT / "tests"))
        import _research as R
        from nse.research import reports, scanner

        candles = R.long_mit_candles()
        result = scanner.scan(
            [R.daily_input("SYN", candles)],
            scanner.ScanConfig(as_of=candles[-1].end, calendar=R.WeekdayCalendar(), calendar_label="TEST_WEEKDAYS",
                               risk_per_trade=1000.0, generated_at="SYNTHETIC-TEST",
                               corporate_action_coverage=R.verified_ca("SYN")),
        )
        scan = reports.to_dict(result)
        candidate = scan["symbols"][0]["candidates"][0]
        self.assertNotIn("timeframe", candidate)  # the shape real envelopes carry
        envelope = {"authorises_order": False, "as_of": scan["as_of"], "dataset_id": "ds-real-shape",
                    "limitations": ["FIXTURE_NOT_MARKET_DATA"], "symbols": scan["symbols"], "fixture": True}
        connection = connect(self.tmp / "platform.sqlite")
        connection.execute(
            """INSERT INTO scan_result (scan_key, job_id, as_of, trade_type, invocation, dataset_id, universe_label,
               completeness, full_universe_scan, fixture, limitations_json, symbols_not_opened_json, envelope_json, created_at)
               VALUES ('scan-real-shape', NULL, ?, 'MIT', 'manual', 'ds-real-shape', 'X', 'COMPLETE', 0, 1, '[]', '[]', ?, '2024-01-03')""",
            (scan["as_of"], json.dumps(envelope)),
        )
        connection.commit()
        connection.close()
        ingested = self.client.post(
            "/api/v1/opportunities/ingest",
            headers={**MARKER, "Idempotency-Key": "ingest-real-shape"},
            json={"scan_key": "scan-real-shape"},
        )
        self.assertEqual(ingested.status_code, 201, ingested.text)
        row = ingested.json()["data"]["created"][0]
        self.assertEqual(row["timeframe"], candidate["execution_tf"])
        self.assertEqual(row["canonical_status"], candidate["status"])
        self.assertEqual(row["zone_id"], candidate["zone"]["zone_id"])

    def test_migration_004_applied(self) -> None:
        connection = connect(self.tmp / "platform.sqlite")
        applied = {row["id"] for row in connection.execute("SELECT id FROM schema_migration")}
        self.assertIn("004_opportunity_intelligence", applied)
        tables = {row["name"] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertIn("opportunity", tables)
        self.assertIn("opportunity_transition", tables)
        connection.close()

    def test_ingest_duplicate_and_lifecycle(self) -> None:
        connection = connect(self.tmp / "platform.sqlite")
        seed_scan(connection, scan_key="scan-fix", fixture=True)
        connection.close()

        first = self.client.post(
            "/api/v1/opportunities/ingest",
            headers={**MARKER, "Idempotency-Key": "ingest-1"},
            json={"scan_key": "scan-fix"},
        )
        self.assertEqual(first.status_code, 201, first.text)
        body = first.json()["data"]
        self.assertEqual(body["source_quality"], "FIXTURE")
        self.assertTrue(body["fixture"])
        self.assertGreaterEqual(body["created_count"], 2)
        self.assertFalse(body["authorises_order"])
        self.assertFalse(body["p0_certified_discovery"])

        second = self.client.post(
            "/api/v1/opportunities/ingest",
            headers={**MARKER, "Idempotency-Key": "ingest-2"},
            json={"scan_key": "scan-fix"},
        )
        self.assertEqual(second.status_code, 201, second.text)
        self.assertEqual(second.json()["data"]["created_count"], 0)
        self.assertGreaterEqual(second.json()["data"]["existing_count"], 2)

        listed = self.client.get("/api/v1/opportunities", headers=MARKER, params={"include_fixtures": True})
        self.assertEqual(listed.status_code, 200)
        rows = listed.json()["data"]["opportunities"]
        self.assertTrue(rows)
        target = next(row for row in rows if row["symbol"] == "AAA")
        self.assertEqual(target["workflow_state"], "BLOCKED")
        self.assertEqual(target["canonical_status"], "ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING")
        self.assertFalse(target["authorises_order"])

        # Fixture BLOCKED -> UNDER_REVIEW is allowed; canonical status stays.
        moved = self.client.post(
            "/api/v1/opportunities/%s/transition" % target["opportunity_id"],
            headers=MARKER,
            json={"to_state": "UNDER_REVIEW", "reason": "owner reviewing fixture"},
        )
        self.assertEqual(moved.status_code, 200, moved.text)
        self.assertEqual(moved.json()["data"]["workflow_state"], "UNDER_REVIEW")
        self.assertEqual(
            moved.json()["data"]["canonical_status"],
            "ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING",
        )

        bad = self.client.post(
            "/api/v1/opportunities/%s/transition" % target["opportunity_id"],
            headers=MARKER,
            json={"to_state": "SHORTLISTED"},
        )
        # UNDER_REVIEW -> SHORTLISTED is allowed without reason
        self.assertEqual(bad.status_code, 200, bad.text)

        reject = self.client.post(
            "/api/v1/opportunities/%s/transition" % target["opportunity_id"],
            headers=MARKER,
            json={"to_state": "REJECTED"},
        )
        self.assertEqual(reject.status_code, 400)

        reject_ok = self.client.post(
            "/api/v1/opportunities/%s/transition" % target["opportunity_id"],
            headers=MARKER,
            json={"to_state": "REJECTED", "reason": "not suitable"},
        )
        self.assertEqual(reject_ok.status_code, 200, reject_ok.text)
        self.assertEqual(
            reject_ok.json()["data"]["canonical_status"],
            "ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING",
        )

        note = self.client.post(
            "/api/v1/opportunities/%s/notes" % target["opportunity_id"],
            headers=MARKER,
            json={"body": "Research note only"},
        )
        self.assertEqual(note.status_code, 201, note.text)
        history = self.client.get(
            "/api/v1/opportunities/%s/history" % target["opportunity_id"],
            headers=MARKER,
        )
        self.assertEqual(history.status_code, 200)
        self.assertGreaterEqual(len(history.json()["data"]["history"]), 2)

    def test_filters_and_watchlist_delete(self) -> None:
        connection = connect(self.tmp / "platform.sqlite")
        seed_scan(connection, scan_key="scan-filter", fixture=False)
        # Force exploratory non-fixture seed
        connection.execute("UPDATE scan_result SET fixture = 0 WHERE scan_key = ?", ("scan-filter",))
        envelope = json.loads(
            connection.execute(
                "SELECT envelope_json FROM scan_result WHERE scan_key = ?",
                ("scan-filter",),
            ).fetchone()["envelope_json"]
        )
        envelope["limitations"] = ["EXPLORATORY_ONLY_NOT_CERTIFIED"]
        connection.execute(
            "UPDATE scan_result SET envelope_json = ?, limitations_json = ? WHERE scan_key = ?",
            (json.dumps(envelope), json.dumps(["EXPLORATORY_ONLY_NOT_CERTIFIED"]), "scan-filter"),
        )
        wl = insert_watchlist(
            connection,
            "Desk",
            ["AAA"],
            items=[{"symbol": "AAA", "reason": "monitor daily demand", "note": "not a signal"}],
        )
        connection.close()

        ingest = self.client.post(
            "/api/v1/opportunities/ingest",
            headers=MARKER,
            json={"scan_key": "scan-filter"},
        )
        self.assertEqual(ingest.status_code, 201, ingest.text)
        self.assertEqual(ingest.json()["data"]["source_quality"], "EXPLORATORY")

        filtered = self.client.get(
            "/api/v1/opportunities",
            headers=MARKER,
            params={"symbol": "AAA", "watchlist_id": wl["watchlist_id"], "sort": "priority"},
        )
        self.assertEqual(filtered.status_code, 200)
        data = filtered.json()["data"]
        self.assertTrue(data["opportunities"])
        self.assertIn("does not predict returns", data["priority_disclosure"])
        self.assertFalse(data["p0_certified_discovery"])

        lists = self.client.get("/api/v1/watchlists", headers=MARKER)
        self.assertEqual(lists.status_code, 200)
        item = lists.json()["data"]["watchlists"][0]["items"][0]
        self.assertEqual(item["reason"], "monitor daily demand")
        self.assertIsNotNone(item["added_at"])

        before_delete = self.client.get(
            "/api/v1/opportunities",
            headers=MARKER,
            params={"symbol": "AAA"},
        )
        self.assertEqual(before_delete.status_code, 200)
        before_rows = before_delete.json()["data"]["opportunities"]
        self.assertTrue(before_rows)
        before_status = before_rows[0]["canonical_status"]
        before_workflow = before_rows[0]["workflow_state"]

        deleted = self.client.delete("/api/v1/watchlists/%s" % wl["watchlist_id"], headers=MARKER)
        self.assertEqual(deleted.status_code, 200, deleted.text)
        again = self.client.get("/api/v1/watchlists", headers=MARKER)
        self.assertEqual(again.json()["data"]["watchlists"], [])

        after_delete = self.client.get(
            "/api/v1/opportunities",
            headers=MARKER,
            params={"symbol": "AAA"},
        )
        self.assertEqual(after_delete.status_code, 200)
        after_rows = after_delete.json()["data"]["opportunities"]
        self.assertEqual(len(after_rows), len(before_rows))
        self.assertEqual(after_rows[0]["canonical_status"], before_status)
        self.assertEqual(after_rows[0]["workflow_state"], before_workflow)

    def test_missing_scan_and_invalid_transition(self) -> None:
        missing = self.client.post(
            "/api/v1/opportunities/ingest",
            headers=MARKER,
            json={"scan_key": "missing"},
        )
        self.assertEqual(missing.status_code, 404)
        with tempfile.TemporaryDirectory() as raw:
            connection = connect(Path(raw) / "db.sqlite")
            view, _ = insert_opportunity(
                connection,
                scan_key="s",
                symbol="ZZZ",
                zone_id=None,
                timeframe=None,
                as_of="2024-01-02",
                dataset_id="ds",
                canonical_status="MANUAL_REVIEW",
                source_quality="EXPLORATORY",
                fixture=False,
                source_snapshot={},
            )
            from gtf_platform.errors import ApiError

            with self.assertRaises(ApiError):
                apply_transition(
                    connection,
                    view["opportunity_id"],
                    to_state="ARCHIVED",
                    actor="owner",
                    reason=None,
                )
            # REJECTED cannot go directly to SHORTLISTED
            apply_transition(
                connection,
                view["opportunity_id"],
                to_state="REJECTED",
                actor="owner",
                reason="desk pass",
            )
            with self.assertRaises(ApiError):
                apply_transition(
                    connection,
                    view["opportunity_id"],
                    to_state="SHORTLISTED",
                    actor="owner",
                    reason="no",
                )
            blocked, _ = insert_opportunity(
                connection,
                scan_key="s2",
                symbol="BLK",
                zone_id=None,
                timeframe=None,
                as_of="2024-01-02",
                dataset_id="ds",
                canonical_status="BLOCKED",
                source_quality="EXPLORATORY",
                fixture=False,
                source_snapshot={},
                workflow_state="UNDER_REVIEW",
            )
            self.assertNotIn("SHORTLISTED", allowed_transitions("UNDER_REVIEW", canonical_status="BLOCKED"))
            with self.assertRaises(ApiError):
                apply_transition(
                    connection,
                    blocked["opportunity_id"],
                    to_state="SHORTLISTED",
                    actor="owner",
                    reason="should fail",
                )
            self.assertIn("UNDER_REVIEW", allowed_transitions("DISCOVERED"))
            listed = list_opportunities(connection, include_fixtures=False)
            self.assertEqual(listed["total"], 2)
            connection.close()


if __name__ == "__main__":
    unittest.main()
