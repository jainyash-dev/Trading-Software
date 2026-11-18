"""P5 portfolio valuation, single-counter invariant, and honest unavailable states.

Synthetic CSV closes only. Not NSE market data and not P0 certification evidence.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta
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
from gtf_platform.db import connect as platform_connect  # noqa: E402
from gtf_platform.integration import valuation  # noqa: E402
from nse.research import models, reports, scanner, store  # noqa: E402

MARKER = {"X-GTF-Request": "1", "Origin": "http://127.0.0.1:8765", "Sec-Fetch-Site": "same-origin"}


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


def _write_csv(path: Path, rows: list[tuple[str, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["date,open,high,low,close"]
    for day, close in rows:
        lines.append("%s,%.2f,%.2f,%.2f,%.2f" % (day, close, close + 1, close - 1, close))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class ValuationUnit(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.settings = _settings(self.tmp)

    def tearDown(self):
        self._tmp.cleanup()

    def test_close_on_valuation_date(self):
        _write_csv(self.tmp / "csv" / "SYN.csv", [("2024-02-01", 100.0), ("2024-02-02", 110.0)])
        quote = valuation.close_on_or_before(self.settings, "SYN", date(2024, 2, 2))
        self.assertEqual(quote["state"], valuation.AVAILABLE)
        self.assertEqual(quote["close"], 110.0)
        self.assertEqual(quote["price_date"], "2024-02-02")
        self.assertEqual(quote["valuation_date"], "2024-02-02")

    def test_previous_accepted_close_when_valuation_date_missing(self):
        _write_csv(self.tmp / "csv" / "SYN.csv", [("2024-02-01", 100.0), ("2024-02-02", 110.0)])
        quote = valuation.close_on_or_before(self.settings, "SYN", date(2024, 2, 3))
        self.assertEqual(quote["state"], valuation.STALE)
        self.assertEqual(quote["close"], 110.0)
        self.assertEqual(quote["price_date"], "2024-02-02")
        self.assertEqual(quote["valuation_date"], "2024-02-03")

    def test_portfolio_aggregate_stays_stale_when_marks_are_stale(self):
        _write_csv(self.tmp / "csv" / "SYN.csv", [("2024-02-01", 100.0)])
        marked = valuation.mark_positions(
            self.settings,
            [{
                "symbol": "SYN",
                "counts_as_open": True,
                "open_quantity": 10,
                "average_entry_price": 90.0,
                "locked_stop": 80.0,
            }],
            date(2024, 2, 3),
        )
        self.assertEqual(marked["valuation_state"], valuation.STALE)
        self.assertEqual(marked["exposure_state"], valuation.STALE)
        self.assertEqual(marked["valuation"], 1000.0)
        self.assertEqual(marked["positions"][0]["valuation_state"], valuation.STALE)
        self.assertIn("2024-02-01", marked["valuation_reason"] or "")

    def test_future_close_excluded(self):
        _write_csv(self.tmp / "csv" / "SYN.csv", [("2024-02-01", 100.0), ("2024-02-05", 150.0)])
        quote = valuation.close_on_or_before(self.settings, "SYN", date(2024, 2, 2))
        self.assertEqual(quote["state"], valuation.STALE)
        self.assertEqual(quote["close"], 100.0)
        self.assertEqual(quote["price_date"], "2024-02-01")

    def test_missing_all_closes(self):
        (self.tmp / "csv").mkdir(parents=True, exist_ok=True)
        quote = valuation.close_on_or_before(self.settings, "SYN", date(2024, 2, 2))
        self.assertEqual(quote["state"], valuation.UNAVAILABLE)
        self.assertIsNone(quote["close"])

    def test_later_error_does_not_discard_earlier_accepted_close(self):
        # Corrupt second row triggers a CSV ERROR dated on that session; the prior
        # accepted close must remain usable as STALE (PR-007 last accepted close).
        path = self.tmp / "csv" / "SYN.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "date,open,high,low,close\n"
            "2024-02-01,100,101,99,100\n"
            "2024-02-02,110,111,109,not-a-price\n",
            encoding="utf-8",
        )
        quote = valuation.close_on_or_before(self.settings, "SYN", date(2024, 2, 2))
        self.assertEqual(quote["state"], valuation.STALE)
        self.assertEqual(quote["close"], 100.0)
        self.assertEqual(quote["price_date"], "2024-02-01")

    def test_price_rejects_nan(self):
        self.assertIsNone(valuation._price("nan"))
        self.assertIsNone(valuation._price(float("nan")))

    def test_no_market_data_configured(self):
        bare = Settings(
            bind_host="127.0.0.1",
            bind_port=8765,
            advertised_port=8765,
            public_origins=(),
            platform_db=self.tmp / "platform.sqlite",
            research_db=self.tmp / "research.sqlite",
            cookie_secure=False,
            data_dir=self.tmp,
            testing=True,
            source_label="FIXTURE",
            price_adjustment="NONE",
            fixture_mode=True,
            csv_dir=None,
            bhavcopy_dir=None,
            calendar_dir=ROOT / "nse" / "data" / "calendar",
            repo_root=ROOT,
        )
        quote = valuation.close_on_or_before(bare, "SYN", date(2024, 2, 2))
        self.assertEqual(quote["state"], valuation.UNAVAILABLE)

    def test_partial_quantity_market_value(self):
        _write_csv(self.tmp / "csv" / "SYN.csv", [("2024-02-02", 200.0)])
        marked = valuation.mark_positions(
            self.settings,
            [{
                "symbol": "SYN",
                "counts_as_open": True,
                "open_quantity": 25,
                "average_entry_price": 160.0,
            }],
            date(2024, 2, 2),
        )
        self.assertEqual(marked["valuation_state"], valuation.AVAILABLE)
        self.assertEqual(marked["valuation"], 5000.0)
        self.assertEqual(marked["unrealised_pnl"], 1000.0)
        self.assertEqual(marked["positions"][0]["price_date"], "2024-02-02")

    def test_closed_position_excluded_from_exposure(self):
        _write_csv(self.tmp / "csv" / "SYN.csv", [("2024-02-02", 200.0)])
        marked = valuation.mark_positions(
            self.settings,
            [{
                "symbol": "SYN",
                "counts_as_open": False,
                "open_quantity": 0,
                "average_entry_price": 160.0,
            }],
            date(2024, 2, 2),
        )
        self.assertEqual(marked["valuation_state"], valuation.UNAVAILABLE)
        self.assertIsNone(marked["valuation"])
        self.assertEqual(marked["positions"][0]["valuation_state"], valuation.UNAVAILABLE)
        self.assertEqual(marked["sector_state"], valuation.UNAVAILABLE)
        self.assertEqual(marked["exposure_state"], valuation.UNAVAILABLE)

    def test_position_remaining_risk_uses_open_quantity(self):
        risk = valuation.position_remaining_risk({
            "counts_as_open": True,
            "open_quantity": 40,
            "average_entry_price": 160.0,
            "locked_stop": 150.0,
            "requested_quantity": 100,
        })
        self.assertEqual(risk["position_risk_state"], valuation.AVAILABLE)
        self.assertEqual(risk["position_risk"], 400.0)
        self.assertEqual(risk["risk_quantity"], 40)

    def test_invalid_or_missing_stop_risk_is_unavailable(self):
        missing = valuation.position_remaining_risk({
            "counts_as_open": True,
            "open_quantity": 10,
            "average_entry_price": 160.0,
        })
        self.assertEqual(missing["position_risk_state"], valuation.UNAVAILABLE)
        bad = valuation.position_remaining_risk({
            "counts_as_open": True,
            "open_quantity": 10,
            "average_entry_price": 160.0,
            "planned_stop": 170.0,
        })
        self.assertEqual(bad["position_risk_state"], valuation.UNAVAILABLE)

    def test_multiple_symbols_mixed_price_dates(self):
        _write_csv(self.tmp / "csv" / "AAA.csv", [("2024-02-01", 10.0)])
        _write_csv(self.tmp / "csv" / "BBB.csv", [("2024-02-02", 20.0)])
        marked = valuation.mark_positions(
            self.settings,
            [
                {"symbol": "AAA", "counts_as_open": True, "open_quantity": 2, "average_entry_price": 9.0},
                {"symbol": "BBB", "counts_as_open": True, "open_quantity": 3, "average_entry_price": 19.0},
            ],
            date(2024, 2, 2),
        )
        self.assertEqual(marked["valuation_state"], valuation.STALE)
        self.assertEqual(marked["exposure_state"], valuation.STALE)
        self.assertEqual(marked["positions"][0]["price_date"], "2024-02-01")
        self.assertEqual(marked["positions"][0]["valuation_state"], valuation.STALE)
        self.assertEqual(marked["positions"][1]["price_date"], "2024-02-02")
        self.assertEqual(marked["positions"][1]["valuation_state"], valuation.AVAILABLE)
        self.assertEqual(marked["valuation"], 2 * 10.0 + 3 * 20.0)


class PortfolioApiP5(unittest.TestCase):
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
        cls.as_of_day = datetime.fromisoformat(cls.scan["as_of"]).date()
        if cls.candidate.status != models.ACTIONABLE:
            raise AssertionError("synthetic fixture did not produce an actionable candidate")

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.settings = _settings(self.tmp)
        day = self.as_of_day
        _write_csv(
            self.tmp / "csv" / "SYN.csv",
            [
                ((day - timedelta(days=3)).isoformat(), 90.0),
                (day.isoformat(), 125.5),
                ((day + timedelta(days=5)).isoformat(), 999.0),
            ],
        )
        self.client = TestClient(create_app(self.settings), base_url="http://127.0.0.1:8765", client=("127.0.0.1", 50000))
        self.client.post("/api/v1/session/bootstrap", headers=MARKER)
        self.scan_key = "scan-synthetic-p5"
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
            "manifest_id": "run-synthetic-p5",
        }
        folder = self.tmp / "reports" / self.scan_key
        folder.mkdir(parents=True)
        (folder / "candidates.csv").write_text("symbol,status\nSYN,STORED\n", encoding="utf-8")
        (folder / "run_manifest.json").write_text(json.dumps({"run_id": "run-synthetic-p5"}) + "\n", encoding="utf-8")
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

    def _approve_and_trigger(self):
        zone = self.candidate.zone["zone_id"]
        created = self.client.post(
            "/api/v1/plans?include_fixtures=true",
            headers={**MARKER, "Content-Type": "application/json"},
            json={"scan_key": self.scan_key, "symbol": "SYN", "zone_id": zone},
        )
        self.assertEqual(created.status_code, 201, created.text)
        plan_id = created.json()["data"]["plan_id"]
        recorded = self.scan["as_of"]
        approved = self.client.post(
            "/api/v1/plans/%s/approve" % plan_id,
            headers={**MARKER, "Content-Type": "application/json"},
            json={
                "combination_index": 0,
                "alert_note": "Synthetic plan. Not an order.",
                "checklist": _checklist(),
                "recorded_at": recorded,
            },
        )
        self.assertEqual(approved.status_code, 200, approved.text)
        entry_id = approved.json()["data"]["entry_id"]
        submitted = self.client.post(
            "/api/v1/journal/%s/order" % entry_id,
            headers={**MARKER, "Content-Type": "application/json"},
            json={"submitted_at": recorded, "order_ref": "KITE-P5", "note": "Owner typed. Not sent."},
        )
        self.assertEqual(submitted.status_code, 200, submitted.text)
        filled = self.client.post(
            "/api/v1/journal/%s/events" % entry_id,
            headers={**MARKER, "Content-Type": "application/json"},
            json={"kind": "TRIGGERED", "at": recorded, "price": self.candidate.levels["entry"][1]},
        )
        self.assertEqual(filled.status_code, 200, filled.text)
        return entry_id, recorded

    def test_portfolio_valuation_uses_accepted_close_and_exposes_price_date(self):
        self._approve_and_trigger()
        book = self.client.get("/api/v1/portfolio", headers=MARKER, params={"at": self.scan["as_of"]})
        self.assertEqual(book.status_code, 200, book.text)
        body = book.json()["data"]
        self.assertFalse(body["authorises_order"])
        self.assertEqual(body["sector_state"], "UNAVAILABLE")
        self.assertEqual(body["drawdown_state"], "UNAVAILABLE")
        self.assertEqual(body["valuation_state"], "AVAILABLE")
        self.assertEqual(body["zones"][0]["price_date"], self.as_of_day.isoformat())
        self.assertEqual(body["zones"][0]["valuation"], 125.5)
        self.assertIsNotNone(body["zones"][0]["average_entry_price"])
        self.assertNotEqual(body["zones"][0]["valuation"], 999.0)
        self.assertEqual(body["research_use"], "FIXTURE_NOT_MARKET_DATA")

    def test_portfolio_counts_match_store_portfolio_at(self):
        self._approve_and_trigger()
        api = self.client.get("/api/v1/portfolio", headers=MARKER, params={"at": self.scan["as_of"]})
        self.assertEqual(api.status_code, 200, api.text)
        body = api.json()["data"]
        conn = store.open_readonly(str(self.tmp / "research.sqlite"))
        try:
            canonical = store.portfolio_at(conn, self.scan["as_of"])
        finally:
            conn.close()
        self.assertEqual(body["trades_triggered_this_month"], canonical["trades_triggered_this_month"])
        self.assertEqual(body["open_positions"], canonical["open_positions"])
        self.assertEqual(body["monthly_cap"], canonical["monthly_cap"])
        self.assertEqual(body["open_position_cap"], canonical["open_position_cap"])

    def test_platform_schema_has_no_second_monthly_counter(self):
        conn = platform_connect(self.tmp / "platform.sqlite")
        try:
            names = {
                row["name"]
                for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
            }
        finally:
            conn.close()
        forbidden = {
            "journal_entries",
            "journal_events",
            "journal_executions",
            "fills",
            "monthly_trades",
            "portfolio_positions",
        }
        self.assertFalse(names & forbidden)

    def test_zone_refusal_is_visible_and_does_not_change_counts(self):
        self._approve_and_trigger()
        zone = self.candidate.zone["zone_id"]
        second = self.client.post(
            "/api/v1/plans?include_fixtures=true",
            headers={**MARKER, "Content-Type": "application/json"},
            json={"scan_key": self.scan_key, "symbol": "SYN", "zone_id": zone},
        )
        self.assertEqual(second.status_code, 201, second.text)
        refused = self.client.post(
            "/api/v1/plans/%s/approve" % second.json()["data"]["plan_id"],
            headers={**MARKER, "Content-Type": "application/json"},
            json={
                "combination_index": 0,
                "alert_note": "Second plan must be refused.",
                "checklist": _checklist(),
                "recorded_at": self.scan["as_of"],
            },
        )
        self.assertEqual(refused.status_code, 409, refused.text)
        self.assertIn("ONE_ORDER_PER_ZONE", refused.text)
        book = self.client.get("/api/v1/portfolio", headers=MARKER, params={"at": self.scan["as_of"]})
        self.assertEqual(book.status_code, 200, book.text)
        body = book.json()["data"]
        self.assertEqual(body["trades_triggered_this_month"], 1)
        self.assertEqual(body["open_positions"], 1)
        self.assertFalse(body["authorises_order"])


if __name__ == "__main__":
    unittest.main()
