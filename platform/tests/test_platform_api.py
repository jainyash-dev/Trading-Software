"""Research, candle, job, and platform-state tests for the local API.

Prices in this file are fixtures. They are not NSE market data.
"""

from __future__ import annotations

import json
import logging
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

PLATFORM = Path(__file__).resolve().parents[1]
ROOT = PLATFORM.parent
sys.path.insert(0, str(PLATFORM))
sys.path.append(str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from gtf_platform.app import create_app  # noqa: E402
from gtf_platform.config import Settings  # noqa: E402
from gtf_platform.db import connect  # noqa: E402
from gtf_platform.jobs import interrupt_stale  # noqa: E402

CALENDAR = ROOT / "nse" / "data" / "calendar"
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


def write_csv(folder: Path, symbol: str, rows: list[tuple]) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    lines = ["date,open,high,low,close,volume"]
    for day, open_, high, low, close, volume in rows:
        lines.append("%s,%s,%s,%s,%s,%s" % (day, open_, high, low, close, volume))
    (folder / ("%s.csv" % symbol)).write_text("\n".join(lines) + "\n", encoding="utf-8")


def weekdays(start: str, count: int) -> list[str]:
    day = datetime.fromisoformat(start).date()
    found = []
    while len(found) < count:
        if day.weekday() < 5:
            found.append(day.isoformat())
        day += timedelta(days=1)
    return found


def rising(symbol: str, days: list[str], start: int = 100) -> list[tuple]:
    rows = []
    for index, day in enumerate(days):
        price = start + index
        rows.append((day, price, price + 2, price - 1, price + 1, 1000 + index))
    return rows


class ApiCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.client = None

    def tearDown(self) -> None:
        if self.client is not None:
            self.client.close()
        self._tmp.cleanup()

    def open(self, **overrides) -> TestClient:
        application = create_app(settings(self.tmp, **overrides))
        self.client = TestClient(application, base_url="http://127.0.0.1:8765", client=("127.0.0.1", 50000))
        self.client.post("/api/v1/session/bootstrap", headers=MARKER)
        return self.client

    def dataset_id(self) -> str:
        response = self.client.get("/api/v1/datasets", headers=MARKER)
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertTrue(body["meta"]["fixture"])
        self.assertEqual(body["meta"]["fixture_label"], "FIXTURE_NOT_MARKET_DATA")
        self.assertFalse(body["data"]["datasets"][0]["data_ready"])
        self.assertFalse(body["data"]["datasets"][0]["research_validation"])
        return body["data"]["datasets"][0]["dataset_id"]


class ResearchApi(ApiCase):
    def test_wit_scan_is_blocked_and_idempotent(self) -> None:
        days = weekdays("2024-06-03", 4)
        write_csv(self.tmp / "csv", "FIX", rising("FIX", days))
        client = self.open()
        dataset = self.dataset_id()
        body = {
            "mode": "MANUAL",
            "as_of": days[-1],
            "trade_type": "WIT-75",
            "universe": ["FIX"],
            "dataset_id": dataset,
        }
        missing = client.post("/api/v1/scans", headers=MARKER, json=body)
        self.assertEqual(missing.status_code, 400, missing.text)
        self.assertEqual(missing.json()["error"]["code"], "REQUEST_INVALID")
        headers = dict(MARKER)
        headers["Idempotency-Key"] = "wit-1"
        first = client.post("/api/v1/scans", headers=headers, json=body)
        self.assertEqual(first.status_code, 202, first.text)
        self.assertTrue(first.json()["meta"]["fixture"])
        job_id = first.json()["data"]["job_id"]
        again = client.post("/api/v1/scans", headers=headers, json=body)
        self.assertEqual(again.json()["data"]["job_id"], job_id)
        changed = dict(body)
        changed["trade_type"] = "WIT-125"
        conflict = client.post("/api/v1/scans", headers=headers, json=changed)
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["error"]["code"], "CONFLICT")
        client.app.state.runner.drain()
        job = client.get("/api/v1/jobs/%s" % job_id, headers=MARKER)
        self.assertEqual(job.status_code, 200, job.text)
        self.assertEqual(job.json()["data"]["state"], "SUCCEEDED_COMPLETE")
        scan_key = job.json()["data"]["result_ref"]
        hidden = client.get("/api/v1/scans/%s" % scan_key, headers=MARKER)
        self.assertEqual(hidden.status_code, 404)
        stored = client.get("/api/v1/scans/%s" % scan_key, headers=MARKER, params={"include_fixtures": True})
        self.assertEqual(stored.status_code, 200, stored.text)
        envelope = stored.json()
        self.assertTrue(envelope["meta"]["fixture"])
        self.assertEqual(envelope["meta"]["engine_schema"], "research-pipeline/1")
        self.assertEqual(envelope["data"]["schema"], "research-pipeline/1")
        self.assertFalse(envelope["data"]["authorises_order"])
        self.assertEqual(envelope["data"]["completeness"], "COMPLETE")
        self.assertFalse(envelope["data"]["full_universe_scan"])
        self.assertEqual(envelope["data"]["symbols"][0]["symbol_status"], "BLOCKED")
        self.assertIn("FIXTURE_NOT_MARKET_DATA", envelope["data"]["limitations"])
        health = client.get("/api/v1/health", headers=MARKER).json()["data"]
        self.assertIsNone(health["last_scan"])
        self.assertEqual(health["last_scan_state"], "UNAVAILABLE")
        self.assertFalse(health["data_ready"])
        self.assertNotEqual(health["outcome"], "OK")
        second_key = dict(MARKER)
        second_key["Idempotency-Key"] = "wit-2"
        repeat = client.post("/api/v1/scans", headers=second_key, json=body)
        self.assertEqual(repeat.status_code, 202, repeat.text)
        self.assertEqual(repeat.json()["data"]["result_ref"], scan_key)
        self.assertEqual(repeat.json()["data"]["job_id"], job_id)

    def test_mit_scan_stores_the_pipeline_envelope_and_bundle(self) -> None:
        days = weekdays("2024-06-03", 12)
        write_csv(self.tmp / "csv", "FIX", rising("FIX", days))
        universe = self.tmp / "universe.csv"
        universe.write_text(
            "symbol,series,isin,index_name,effective_from,effective_to,source,source_file,source_sha256,recorded_on,notes\n"
            "FIX,EQ,,NIFTY 100,2020-01-01,,unverified,,,2024-01-01,\n",
            encoding="utf-8",
        )
        client = self.open(calendar_dir=CALENDAR, universe_path=universe)
        dataset = self.dataset_id()
        body = {
            "mode": "MANUAL",
            "as_of": days[-1],
            "trade_type": "MIT",
            "universe": "SUPPORTED",
            "dataset_id": dataset,
        }
        headers = dict(MARKER)
        headers["Idempotency-Key"] = "mit-1"
        created = client.post("/api/v1/scans", headers=headers, json=body)
        self.assertEqual(created.status_code, 202, created.text)
        client.app.state.runner.drain()
        job = client.get("/api/v1/jobs/%s" % created.json()["data"]["job_id"], headers=MARKER).json()["data"]
        self.assertEqual(job["state"], "SUCCEEDED_COMPLETE", job)
        self.assertEqual(job["completeness"], "COMPLETE")
        scan_key = job["result_ref"]
        stored = client.get("/api/v1/scans/%s" % scan_key, headers=MARKER, params={"include_fixtures": True})
        envelope = stored.json()["data"]
        self.assertFalse(envelope["full_universe_scan"])
        self.assertIn("UNIVERSE_UNVERIFIED", envelope["limitations"])
        self.assertFalse(envelope["authorises_order"])
        self.assertIsNone(envelope["trade_plans"][0]["selected_quantity"] if envelope["trade_plans"] else None)
        for plan in envelope["trade_plans"]:
            self.assertFalse(plan["authorises_order"])
            self.assertIsNone(plan["selected_quantity"])
        symbols = client.get(
            "/api/v1/scans/%s/symbols" % scan_key,
            headers=MARKER,
            params={"include_fixtures": True},
        )
        self.assertEqual(symbols.status_code, 200, symbols.text)
        self.assertEqual(symbols.json()["data"]["symbols"][0]["symbol"], "FIX")
        bundle = client.get(
            "/api/v1/symbols/FIX/bundle",
            headers=MARKER,
            params={"scan_key": scan_key, "include_fixtures": True, "dataset_id": dataset, "as_of": days[-1]},
        )
        self.assertEqual(bundle.status_code, 200, bundle.text)
        stored_symbol = bundle.json()["data"]["stored"]
        self.assertEqual(stored_symbol["symbol"], "FIX")
        self.assertEqual(bundle.json()["data"]["authorises_order"], False)
        report = self.tmp / "reports" / scan_key / "candidates.csv"
        manifest = self.tmp / "reports" / scan_key / "run_manifest.json"
        self.assertTrue(report.is_file(), "the scan job did not write the existing candidates report")
        self.assertTrue(manifest.is_file(), "the scan job did not write a run manifest")
        exported = client.get("/api/v1/scans/%s/reports/candidates.csv" % scan_key, headers=MARKER)
        self.assertEqual(exported.status_code, 200, exported.text)
        self.assertEqual(exported.json()["data"]["body"], report.read_text(encoding="utf-8"))
        self.assertIn("mtf", stored_symbol)
        self.assertIn("identity", stored_symbol)
        self.assertEqual(stored_symbol["symbol_status"], "NO_FRESH_EXECUTION_ZONE")
        missing_key = client.get("/api/v1/symbols/FIX/bundle", headers=MARKER)
        self.assertEqual(missing_key.status_code, 400)
        wrong = client.get(
            "/api/v1/symbols/NOPE/bundle",
            headers=MARKER,
            params={"scan_key": scan_key, "include_fixtures": True},
        )
        self.assertEqual(wrong.status_code, 404)
        overview = client.get("/api/v1/overview", headers=MARKER, params={"as_of": days[-1]})
        self.assertEqual(overview.status_code, 200, overview.text)
        self.assertIsNone(overview.json()["data"]["counts"])
        universe_body = client.get("/api/v1/universe", headers=MARKER, params={"as_of": days[-1]})
        self.assertEqual(universe_body.status_code, 200, universe_body.text)
        self.assertIn("UNIVERSE_UNVERIFIED", universe_body.json()["data"]["limitations"])
        self.assertFalse(universe_body.json()["data"]["certified"])
        self.assertFalse(universe_body.json()["data"]["full_universe_scan"])
        repeat = client.post(
            "/api/v1/scans",
            headers={**MARKER, "Idempotency-Key": "mit-2"},
            json=body,
        )
        self.assertEqual(repeat.status_code, 202, repeat.text)
        self.assertEqual(repeat.json()["data"]["result_ref"], scan_key)
        self.assertEqual(repeat.json()["data"]["job_id"], job["job_id"])

    def test_replay_does_not_read_a_later_candle_and_cancel_is_not_success(self) -> None:
        days = weekdays("2024-06-03", 8)
        write_csv(self.tmp / "csv", "FIX", rising("FIX", days))
        client = self.open(calendar_dir=CALENDAR)
        dataset = self.dataset_id()
        early = {
            "mode": "REPLAY",
            "as_of": days[3],
            "trade_type": "MIT",
            "universe": ["FIX"],
            "dataset_id": dataset,
        }
        later = dict(early)
        later["as_of"] = days[-1]
        headers = dict(MARKER)
        headers["Idempotency-Key"] = "replay-early"
        first = client.post("/api/v1/scans", headers=headers, json=early)
        self.assertEqual(first.status_code, 202, first.text)
        client.app.state.runner.drain()
        early_job = client.get("/api/v1/jobs/%s" % first.json()["data"]["job_id"], headers=MARKER).json()["data"]
        early_env = client.get(
            "/api/v1/scans/%s" % early_job["result_ref"],
            headers=MARKER,
            params={"include_fixtures": True},
        ).json()["data"]
        self.assertTrue(str(early_env["as_of"]).startswith(days[3]))
        headers["Idempotency-Key"] = "replay-later"
        second = client.post("/api/v1/scans", headers=headers, json=later)
        client.app.state.runner.drain()
        later_job = client.get("/api/v1/jobs/%s" % second.json()["data"]["job_id"], headers=MARKER).json()["data"]
        self.assertNotEqual(early_job["result_ref"], later_job["result_ref"])
        again = client.get(
            "/api/v1/scans/%s" % early_job["result_ref"],
            headers=MARKER,
            params={"include_fixtures": True},
        ).json()["data"]
        self.assertEqual(again, early_env)
        headers["Idempotency-Key"] = "cancel-1"
        pending = {
            "mode": "MANUAL",
            "as_of": days[-1],
            "trade_type": "MIT",
            "universe": ["FIX"],
            "dataset_id": dataset,
        }
        created = client.post("/api/v1/scans", headers=headers, json=pending)
        scan_ref = created.json()["data"]["job_id"]
        cancelled = client.post(
            "/api/v1/scans/%s/cancel" % scan_ref,
            headers={**MARKER, "Idempotency-Key": "cancel-do"},
        )
        self.assertEqual(cancelled.status_code, 202, cancelled.text)
        self.assertEqual(cancelled.json()["data"]["state"], "CANCELLED")
        client.app.state.runner.drain()
        final = client.get("/api/v1/jobs/%s" % scan_ref, headers=MARKER).json()["data"]
        self.assertEqual(final["state"], "CANCELLED")
        self.assertNotIn(final["state"], {"SUCCEEDED_COMPLETE", "SUCCEEDED_PARTIAL"})

    def test_stored_partial_scan_is_not_recomputed(self) -> None:
        client = self.open()
        now = datetime.now(timezone.utc).isoformat()
        envelope = {
            "schema": "research-pipeline/1",
            "as_of": "2024-06-07T15:30:00",
            "trade_type": "MIT",
            "invocation": "manual",
            "dataset_id": "stored-dataset",
            "completeness": "PARTIAL",
            "symbols_not_opened": ["MISSING"],
            "full_universe_scan": False,
            "authorises_order": False,
            "limitations": ["UNIVERSE_UNVERIFIED"],
            "symbols": [
                {
                    "symbol": "FIX",
                    "symbol_status": "DATA_INSUFFICIENT",
                    "candidates": [],
                    "gates": [],
                }
            ],
            "counts": {"symbol_status": {"DATA_INSUFFICIENT": 1}, "candidate_status": {}},
        }
        connection = client.app.state.db
        connection.execute(
            """
            INSERT INTO scan_result (
                scan_key, job_id, as_of, trade_type, invocation, dataset_id, universe_label,
                completeness, full_universe_scan, fixture, limitations_json,
                symbols_not_opened_json, envelope_json, created_at
            ) VALUES (?, NULL, ?, 'MIT', 'manual', 'stored-dataset', 'ADHOC',
                      'PARTIAL', 0, 0, ?, ?, ?, ?)
            """,
            (
                "scan-stored",
                "2024-06-07T15:30:00",
                json.dumps(["UNIVERSE_UNVERIFIED"]),
                json.dumps(["MISSING"]),
                json.dumps(envelope),
                now,
            ),
        )
        response = client.get("/api/v1/scans/scan-stored", headers=MARKER)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["data"], envelope)
        self.assertEqual(response.json()["data"]["symbols_not_opened"], ["MISSING"])
        self.assertEqual(response.json()["data"]["completeness"], "PARTIAL")
        self.assertFalse(response.json()["meta"]["fixture"])


class CandleApi(ApiCase):
    def test_daily_weekly_monthly_keep_prices_and_omit_the_future(self) -> None:
        days = weekdays("2024-06-03", 12)
        rows = rising("FIX", days)
        rows.append(("2099-01-05", 999, 1000, 998, 999, 5))
        write_csv(self.tmp / "csv", "FIX", rows)
        gapped = days[:5] + days[6:]
        write_csv(self.tmp / "csv", "GAP", rising("GAP", gapped, start=200))
        client = self.open(calendar_dir=CALENDAR)
        dataset = self.dataset_id()
        daily = client.get(
            "/api/v1/candles",
            headers=MARKER,
            params={"symbol": "FIX", "timeframe": "D", "as_of": days[-1], "dataset_id": dataset},
        )
        self.assertEqual(daily.status_code, 200, daily.text)
        body = daily.json()
        self.assertTrue(body["meta"]["fixture"])
        self.assertEqual(body["meta"]["fixture_label"], "FIXTURE_NOT_MARKET_DATA")
        self.assertFalse(body["data"]["adjusted"])
        dates = [row["session_date"] for row in body["data"]["candles"]]
        self.assertNotIn("2099-01-05", dates)
        self.assertNotIn("2024-06-17", dates)
        self.assertIn(days[0], dates)
        self.assertIn(days[-1], dates)
        first = body["data"]["candles"][0]
        self.assertEqual(first["open"], "100")
        self.assertEqual(first["close"], "101")
        self.assertEqual(first["volume"], "1000")
        self.assertEqual(body["data"]["dataset_id"], dataset)
        weekly = client.get(
            "/api/v1/candles",
            headers=MARKER,
            params={"symbol": "FIX", "timeframe": "W", "as_of": days[-1], "dataset_id": dataset},
        )
        self.assertEqual(weekly.status_code, 200, weekly.text)
        self.assertGreaterEqual(len(weekly.json()["data"]["candles"]), 1)
        monthly = client.get(
            "/api/v1/candles",
            headers=MARKER,
            params={"symbol": "FIX", "timeframe": "M", "as_of": days[-1], "dataset_id": dataset},
        )
        self.assertEqual(monthly.status_code, 200, monthly.text)
        self.assertNotIn("999", json.dumps(monthly.json()["data"]["candles"]))
        gapped = client.get(
            "/api/v1/candles",
            headers=MARKER,
            params={"symbol": "GAP", "timeframe": "D", "as_of": days[-1], "dataset_id": dataset},
        )
        self.assertEqual(gapped.status_code, 200, gapped.text)
        gapped_dates = [row["session_date"] for row in gapped.json()["data"]["candles"]]
        self.assertNotIn(days[5], gapped_dates)
        bad = client.get(
            "/api/v1/candles",
            headers=MARKER,
            params={"symbol": "nope", "timeframe": "Q", "as_of": days[-1], "dataset_id": dataset},
        )
        self.assertEqual(bad.status_code, 400)

    def test_real_data_failure_does_not_return_fixture_candles(self) -> None:
        empty = self.tmp / "empty-bhav"
        empty.mkdir()
        client = self.open(
            csv_dir=None,
            bhavcopy_dir=empty,
            source_label="USER_CSV",
            fixture_mode=False,
            price_adjustment="NONE",
        )
        response = client.get(
            "/api/v1/candles",
            headers=MARKER,
            params={"symbol": "RELIANCE", "timeframe": "D", "as_of": "2024-06-14", "dataset_id": "missing"},
        )
        self.assertIn(response.status_code, {409, 422}, response.text)
        self.assertNotIn("FIXTURE_NOT_MARKET_DATA", response.text)
        self.assertNotIn("fixture", response.text)
        self.assertNotEqual(response.json().get("meta", {}).get("fixture"), True)
        scan = client.post(
            "/api/v1/scans",
            headers={**MARKER, "Idempotency-Key": "no-data"},
            json={
                "mode": "MANUAL",
                "as_of": "2024-06-14",
                "trade_type": "MIT",
                "universe": ["RELIANCE"],
                "dataset_id": "missing",
            },
        )
        self.assertEqual(scan.status_code, 422, scan.text)
        self.assertEqual(scan.json()["error"]["code"], "DATA_INSUFFICIENT")
        self.assertNotIn("FIXTURE_NOT_MARKET_DATA", scan.text)

    def test_missing_volume_is_null_and_zero_volume_stays_zero(self) -> None:
        days = weekdays("2024-06-03", 5)
        folder = self.tmp / "csv"
        folder.mkdir(parents=True)
        lines = ["date,open,high,low,close,volume"]
        lines.append("%s,100,102,99,101,0" % days[0])
        lines.append("%s,101,103,100,102," % days[1])  # blank => unavailable
        lines.append("%s,102,104,101,103,1500" % days[2])
        lines.append("%s,103,105,102,104,1600" % days[3])
        lines.append("%s,104,106,103,105,1700" % days[4])
        (folder / "VOL.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
        client = self.open()
        dataset = self.dataset_id()
        response = client.get(
            "/api/v1/candles",
            headers=MARKER,
            params={"symbol": "VOL", "timeframe": "D", "as_of": days[-1], "dataset_id": dataset},
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()["data"]
        by_day = {row["session_date"]: row for row in body["candles"]}
        self.assertEqual(by_day[days[0]]["volume"], "0")
        self.assertIsNone(by_day[days[1]]["volume"])
        self.assertEqual(by_day[days[2]]["volume"], "1500")
        self.assertEqual(body["volume_state"], "PARTIAL")
        self.assertEqual(body["volume_unit"], "TRADED_QUANTITY")
        self.assertEqual(body["volume_source"], "CSV_VOLUME")
        quality = body["data_quality"]
        self.assertFalse(quality["certified"])
        self.assertEqual(quality["research_use"], "FIXTURE_NOT_MARKET_DATA")
        self.assertFalse(quality["data_ready"])
        self.assertFalse(body["adjusted"])
        weekly = client.get(
            "/api/v1/candles",
            headers=MARKER,
            params={"symbol": "VOL", "timeframe": "W", "as_of": days[-1], "dataset_id": dataset},
        )
        self.assertEqual(weekly.status_code, 200, weekly.text)
        weekly_body = weekly.json()["data"]
        self.assertNotIn("VOLUME_NOT_AGGREGATED_FOR_HTF", weekly_body["limitations"])
        # Without a calendar the only week is still in progress (no later evidence),
        # so no weekly candle and no weekly volume is drawn. Aggregation with a
        # calendar is covered by test_weekly_monthly_volume_is_the_sum_of_constituent_sessions.
        self.assertEqual(weekly_body["candles"], [])
        self.assertEqual(weekly_body["volume_state"], "UNAVAILABLE")

    def _candles(self, client, symbol: str, timeframe: str, as_of: str, dataset: str) -> dict:
        response = client.get(
            "/api/v1/candles",
            headers=MARKER,
            params={"symbol": symbol, "timeframe": timeframe, "as_of": as_of, "dataset_id": dataset},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["data"]

    def test_weekly_monthly_volume_is_the_sum_of_constituent_sessions(self) -> None:
        # 2024-08-15 is an NSE holiday (Independence Day) in the real calendar.
        days = [day for day in weekdays("2024-07-29", 30) if day != "2024-08-15"]
        rows = [(day, 100, 102, 99, 101, 10 + index) for index, day in enumerate(days)]
        write_csv(self.tmp / "csv", "SUM", rows)
        by_day = {day: 10 + index for index, day in enumerate(days)}
        client = self.open(calendar_dir=CALENDAR)
        dataset = self.dataset_id()
        weekly = self._candles(client, "SUM", "W", days[-1], dataset)
        self.assertEqual(weekly["volume_state"], "PRESENT")
        self.assertNotIn("HTF_VOLUME_INCOMPLETE", weekly["limitations"])
        weeks = {row["session_date"]: row for row in weekly["candles"]}
        # Holiday week: four sessions, the holiday contributes nothing.
        holiday_week = [d for d in days if "2024-08-12" <= d <= "2024-08-16"]
        self.assertEqual(len(holiday_week), 4)
        self.assertEqual(weeks["2024-08-16"]["volume"], str(sum(by_day[d] for d in holiday_week)))
        self.assertEqual(weeks["2024-08-16"]["volume_sessions"], 4)
        full_week = [d for d in days if "2024-08-05" <= d <= "2024-08-09"]
        self.assertEqual(weeks["2024-08-09"]["volume"], str(sum(by_day[d] for d in full_week)))
        monthly = self._candles(client, "SUM", "M", days[-1], dataset)
        months = {row["session_date"]: row for row in monthly["candles"]}
        # Partial first month (history starts 2024-07-29): only held sessions are summed.
        july = [d for d in days if d.startswith("2024-07")]
        self.assertEqual(months["2024-07-31"]["volume"], str(sum(by_day[d] for d in july)))
        self.assertEqual(months["2024-07-31"]["volume_sessions"], len(july))
        august = [d for d in days if d.startswith("2024-08")]
        self.assertEqual(months["2024-08-30"]["volume"], str(sum(by_day[d] for d in august)))
        # Month boundary: no September session leaks into August.
        self.assertEqual(months["2024-08-30"]["volume_sessions"], len(august))
        daily_total = sum(int(row["volume"]) for row in self._candles(client, "SUM", "D", days[-1], dataset)["candles"]
                          if row["session_date"].startswith("2024-08"))
        self.assertEqual(int(months["2024-08-30"]["volume"]), daily_total)

    def test_htf_volume_zero_invalid_and_missing_sessions_are_not_invented(self) -> None:
        days = weekdays("2024-06-03", 15)  # three complete weeks
        folder = self.tmp / "csv"
        folder.mkdir(parents=True)
        lines = ["date,open,high,low,close,volume"]
        for index, day in enumerate(days):
            if index < 5:
                volume = "0"  # week 1: stated zero
            elif index == 7:
                volume = "-5"  # week 2: invalid volume
            elif index == 12:
                volume = "abc"  # week 3: invalid text
            else:
                volume = "100"
            lines.append("%s,100,102,99,101,%s" % (day, volume))
        (folder / "ZV.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
        client = self.open(calendar_dir=CALENDAR)
        dataset = self.dataset_id()
        weekly = self._candles(client, "ZV", "W", days[-1], dataset)
        volumes = [row["volume"] for row in weekly["candles"]]
        self.assertEqual(volumes, ["0", None, None])
        self.assertIn("HTF_VOLUME_INCOMPLETE", weekly["limitations"])
        self.assertEqual(weekly["volume_state"], "PARTIAL")
        # A missing session (gap) truncates the HTF series; it is never filled.
        gapped = days[:7] + days[8:]
        write_csv(folder, "GAPV", rising("GAPV", gapped))
        client.close()
        client = self.open(calendar_dir=CALENDAR)
        dataset = self.dataset_id()
        gap_weekly = self._candles(client, "GAPV", "W", days[-1], dataset)
        self.assertIn(days[7], gap_weekly["missing_sessions"])
        for row in gap_weekly["candles"]:
            self.assertLess(row["session_date"], days[7])
            self.assertEqual(row["volume_sessions"], 5)

    def test_duplicate_source_session_is_refused_not_double_counted(self) -> None:
        days = weekdays("2024-06-03", 5)
        folder = self.tmp / "csv"
        folder.mkdir(parents=True)
        lines = ["date,open,high,low,close,volume"] + ["%s,100,102,99,101,5" % day for day in days]
        lines.append("%s,100,102,99,101,7" % days[2])
        (folder / "DUP.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")
        client = self.open(calendar_dir=CALENDAR)
        dataset = self.dataset_id()
        response = client.get(
            "/api/v1/candles",
            headers=MARKER,
            params={"symbol": "DUP", "timeframe": "W", "as_of": days[-1], "dataset_id": dataset},
        )
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(response.json()["error"]["code"], "DATA_INSUFFICIENT")
        from gtf_platform.integration import candles as candles_mod

        table = candles_mod._csv_volumes(settings(self.tmp), "DUP")
        self.assertIsNone(table["by_session"][days[2]])
        self.assertEqual(table["by_session"][days[1]], "5")

    def test_candle_quality_never_claims_certified_for_fixtures(self) -> None:
        days = weekdays("2024-06-03", 3)
        write_csv(self.tmp / "csv", "FIX", rising("FIX", days))
        client = self.open()
        dataset = self.dataset_id()
        response = client.get(
            "/api/v1/candles",
            headers=MARKER,
            params={"symbol": "FIX", "timeframe": "D", "as_of": days[-1], "dataset_id": dataset},
        )
        self.assertEqual(response.status_code, 200, response.text)
        quality = response.json()["data"]["data_quality"]
        self.assertIs(quality["certified"], False)
        self.assertNotEqual(quality["research_use"], "CERTIFIED_P0_DATA")

    def test_non_fixture_candles_are_exploratory_not_certified(self) -> None:
        days = weekdays("2024-06-03", 3)
        write_csv(self.tmp / "csv", "EXP", rising("EXP", days))
        client = self.open(source_label="USER_CSV", fixture_mode=False)
        datasets = client.get("/api/v1/datasets", headers=MARKER)
        self.assertEqual(datasets.status_code, 200, datasets.text)
        self.assertFalse(datasets.json()["meta"]["fixture"])
        dataset = datasets.json()["data"]["datasets"][0]["dataset_id"]
        response = client.get(
            "/api/v1/candles",
            headers=MARKER,
            params={"symbol": "EXP", "timeframe": "D", "as_of": days[-1], "dataset_id": dataset},
        )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertFalse(body["meta"]["fixture"])
        quality = body["data"]["data_quality"]
        self.assertIs(quality["certified"], False)
        self.assertEqual(quality["research_use"], "EXPLORATORY_ONLY_NOT_CERTIFIED")
        self.assertFalse(quality["fixture"])
        self.assertFalse(quality["data_ready"])


class PlatformState(ApiCase):
    def test_watchlist_settings_drawings_and_audit(self) -> None:
        client = self.open()
        created = client.post(
            "/api/v1/watchlists",
            headers={**MARKER, "Idempotency-Key": "wl-1"},
            json={"name": "Ideas", "symbols": ["fix", "tcs", "fix"]},
        )
        self.assertEqual(created.status_code, 201, created.text)
        watchlist_id = created.json()["data"]["watchlist_id"]
        self.assertEqual(created.json()["data"]["symbols"], ["FIX", "TCS"])
        self.assertIsNone(created.json()["data"]["eligibility"])
        repeat = client.post(
            "/api/v1/watchlists",
            headers={**MARKER, "Idempotency-Key": "wl-1"},
            json={"name": "Ideas", "symbols": ["fix", "tcs", "fix"]},
        )
        self.assertEqual(repeat.status_code, 200, repeat.text)
        self.assertEqual(repeat.json()["data"]["watchlist_id"], watchlist_id)
        renamed = client.patch(
            "/api/v1/watchlists/%s" % watchlist_id,
            headers=MARKER,
            json={"name": "Later", "symbols": ["TCS", "INFY"]},
        )
        self.assertEqual(renamed.status_code, 200, renamed.text)
        self.assertEqual(renamed.json()["data"]["symbols"], ["TCS", "INFY"])
        unknown = client.patch("/api/v1/settings", headers=MARKER, json={"methodology": "changed"})
        self.assertEqual(unknown.status_code, 400)
        patched = client.patch(
            "/api/v1/settings",
            headers=MARKER,
            json={"scheduler_enabled": False, "risk_stage": "LEARNING", "assistant_enabled": False},
        )
        self.assertEqual(patched.status_code, 200, patched.text)
        self.assertEqual(patched.json()["data"]["risk_stage"], "LEARNING")
        audit = client.get("/api/v1/audit", headers=MARKER, params={"object_id": "settings"})
        self.assertEqual(audit.status_code, 200, audit.text)
        self.assertEqual(audit.json()["data"]["events"][0]["action"], "settings.patch")
        self.assertIsNotNone(audit.json()["data"]["events"][0]["after_digest"])
        drawing = client.post(
            "/api/v1/drawings",
            headers={**MARKER, "Idempotency-Key": "draw-1"},
            json={"symbol": "FIX", "timeframe": "D", "geometry": {"type": "horizontal", "price": "101.5", "time": "2024-06-03"}},
        )
        self.assertEqual(drawing.status_code, 201, drawing.text)
        listed = client.get("/api/v1/drawings", headers=MARKER, params={"symbol": "FIX", "timeframe": "D"})
        self.assertEqual(len(listed.json()["data"]["drawings"]), 1)
        drawing_id = drawing.json()["data"]["drawing_id"]
        patched = client.patch(
            "/api/v1/drawings/%s" % drawing_id,
            headers=MARKER,
            json={"geometry": {"type": "horizontal", "points": [{"time": "2024-06-14", "price": 101.5}], "text": "moved"}},
        )
        self.assertEqual(patched.status_code, 200, patched.text)
        self.assertEqual(patched.json()["data"]["geometry"]["points"][0]["price"], 101.5)
        self.assertEqual(patched.json()["data"]["version"], 2)
        removed = client.delete("/api/v1/drawings/%s" % drawing_id, headers=MARKER)
        self.assertEqual(removed.status_code, 200, removed.text)
        config = client.post(
            "/api/v1/scan-configs",
            headers={**MARKER, "Idempotency-Key": "cfg-1"},
            json={"name": "Manual", "parameters": {"trade_type": "MIT", "password": "no"}},
        )
        self.assertEqual(config.status_code, 422)

    def test_startup_interrupts_a_running_job_and_migrations_replay(self) -> None:
        path = self.tmp / "platform.sqlite"
        connection = connect(path)
        old = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        connection.execute(
            """
            INSERT INTO job (
                job_id, kind, state, idempotency_key, heartbeat, created_at, fixture, cancel_requested
            ) VALUES ('left', 'SCAN', 'RUNNING', 'left-key', ?, ?, 0, 0)
            """,
            (old, old),
        )
        connection.close()
        client = self.open()
        row = client.app.state.db.execute("SELECT state FROM job WHERE job_id = 'left'").fetchone()
        self.assertEqual(row["state"], "INTERRUPTED")
        again = connect(path)
        ids = [item["id"] for item in again.execute("SELECT id FROM schema_migration ORDER BY id")]
        self.assertEqual(
            ids,
            [
                "001_jobs",
                "002_platform_state",
                "003_trade_plan",
                "004_opportunity_intelligence",
                "005_trade_plan_lifecycle",
            ],
        )
        again.close()
        changed = interrupt_stale(connect(path), datetime.now(timezone.utc), timedelta(seconds=30))
        self.assertEqual(changed, 0)

    def test_logs_do_not_keep_a_session_cookie(self) -> None:
        client = self.open()
        logger = logging.getLogger("gtf_platform")
        records = []

        class Capture(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                records.append(record.getMessage())

        handler = Capture()
        logger.addHandler(handler)
        try:
            logger.info("cookie gtf_session=super-secret-value")
            client.get("/api/v1/health", headers=MARKER)
        finally:
            logger.removeHandler(handler)
        text = "\n".join(records)
        self.assertNotIn("super-secret-value", text)
        self.assertIn("[redacted]", text)

    def test_expired_session_is_rejected(self) -> None:
        client = self.open()
        token = client.cookies.get("gtf_session")
        client.app.state.sessions.expire(token)
        response = client.get("/api/v1/health", headers=MARKER)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "UNAUTHENTICATED")
        self.assertNotIn(token, response.text)


class Scheduler(ApiCase):
    def test_duplicate_schedule_reuses_the_job_and_does_not_download(self) -> None:
        days = weekdays("2024-06-03", 6)
        write_csv(self.tmp / "csv", "FIX", rising("FIX", days))
        universe = self.tmp / "universe.csv"
        universe.write_text(
            "symbol,series,isin,index_name,effective_from,effective_to,source,source_file,source_sha256,recorded_on,notes\n"
            "FIX,EQ,,NIFTY 100,2020-01-01,,unverified,,,2024-01-01,\n",
            encoding="utf-8",
        )
        client = self.open(calendar_dir=CALENDAR, universe_path=universe, scheduler_enabled=True)
        from datetime import datetime as dt
        from zoneinfo import ZoneInfo

        from gtf_platform.integration.schedule import consider

        moment = dt.fromisoformat(days[-1] + "T16:00:00").replace(tzinfo=ZoneInfo("Asia/Kolkata"))
        first = consider(client.app.state.settings, client.app.state.db, client.app.state.db_lock, moment)
        second = consider(client.app.state.settings, client.app.state.db, client.app.state.db_lock, moment)
        self.assertIsNotNone(first)
        self.assertEqual(first["job_id"], second["job_id"])
        self.assertIn(first["state"], {"VALIDATING", "PENDING_DATA", "SUCCEEDED_COMPLETE", "SKIPPED_HOLIDAY"})
        provider = (PLATFORM / "providers" / "__init__.py").read_text(encoding="utf-8")
        self.assertIn("PUBLIC_NSE_DOWNLOAD_DISABLED", provider)
        self.assertNotIn("urlopen", provider)
        self.assertNotIn("nseindia", provider)

    def test_saved_scheduler_setting_wins_and_a_non_boolean_does_not_enable(self) -> None:
        days = weekdays("2024-06-03", 6)
        write_csv(self.tmp / "csv", "FIX", rising("FIX", days))
        universe = self.tmp / "universe.csv"
        universe.write_text(
            "symbol,series,isin,index_name,effective_from,effective_to,source,source_file,source_sha256,recorded_on,notes\n"
            "FIX,EQ,,NIFTY 100,2020-01-01,,unverified,,,2024-01-01,\n",
            encoding="utf-8",
        )
        client = self.open(calendar_dir=CALENDAR, universe_path=universe, scheduler_enabled=True)
        from datetime import datetime as dt
        from zoneinfo import ZoneInfo

        from gtf_platform.integration.schedule import consider
        from gtf_platform.store import patch_settings

        moment = dt.fromisoformat(days[-1] + "T16:00:00").replace(tzinfo=ZoneInfo("Asia/Kolkata"))
        with client.app.state.db_lock:
            patch_settings(client.app.state.db, {"scheduler_enabled": False})
            client.app.state.db.commit()
        self.assertIsNone(consider(client.app.state.settings, client.app.state.db, client.app.state.db_lock, moment))
        with client.app.state.db_lock:
            patch_settings(client.app.state.db, {"scheduler_enabled": "yes"})
            client.app.state.db.commit()
        self.assertIsNone(consider(client.app.state.settings, client.app.state.db, client.app.state.db_lock, moment))
        with client.app.state.db_lock:
            client.app.state.db.execute("DELETE FROM app_setting WHERE key = 'scheduler_enabled'")
            client.app.state.db.commit()
        restarted = consider(client.app.state.settings, client.app.state.db, client.app.state.db_lock, moment)
        self.assertIsNotNone(restarted)


if __name__ == "__main__":
    unittest.main()
