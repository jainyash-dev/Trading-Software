"""Build a FIXTURE environment for browser validation. Synthetic prices; not NSE market data."""
import json, sys, shutil
from pathlib import Path

ROOT = Path("/Users/yash/day-trader-skill")
sys.path.insert(0, str(ROOT / "platform")); sys.path.append(str(ROOT)); sys.path.append(str(ROOT / "tests"))
import _research as R
from nse.research import reports, scanner
from gtf_platform.config import Settings
from gtf_platform.integration import sources
from gtf_platform.db import connect

env = Path(sys.argv[1]); shutil.rmtree(env, ignore_errors=True)
(env / "csv").mkdir(parents=True)
candles = R.long_mit_candles()
lines = ["date,open,high,low,close,volume"]
for i, c in enumerate(candles):
    vol = "" if i == len(candles) - 30 else str(100000 + (i * 7919) % 50000)   # one unstated volume day
    lines.append("%s,%s,%s,%s,%s,%s" % (c.start.date().isoformat(), c.open, c.high, c.low, c.close, vol))
(env / "csv" / "SYN.csv").write_text("\n".join(lines) + "\n")
# A second symbol with a gentle random walk: gives the UI scan a non-qualifying symbol.
walk = R.random_walk(7, 400)
lines = ["date,open,high,low,close,volume"] + ["%s,%s,%s,%s,%s,%d" % (c.start.date().isoformat(), c.open, c.high, c.low, c.close, 50000 + i) for i, c in enumerate(walk)]
(env / "csv" / "WALK.csv").write_text("\n".join(lines) + "\n")

settings = Settings(bind_host="127.0.0.1", bind_port=8765, advertised_port=8765, public_origins=(),
    platform_db=env / "platform.sqlite", research_db=env / "research.sqlite", cookie_secure=False,
    data_dir=env, testing=True, source_label="FIXTURE", price_adjustment="NONE", fixture_mode=True,
    csv_dir=env / "csv", repo_root=ROOT)
identity = sources.dataset_identity(settings)
result = scanner.scan([R.daily_input("SYN", candles)], scanner.ScanConfig(
    as_of=candles[-1].end, calendar=R.WeekdayCalendar(), calendar_label="TEST_WEEKDAYS", risk_per_trade=1000.0,
    generated_at="SYNTHETIC-BROWSER", corporate_action_coverage=R.verified_ca("SYN")))
scan = reports.to_dict(result)
assert result.candidates()[0].status == "ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING"
key = "scan-browser-syn"
envelope = {"schema": "research-pipeline/1", "as_of": scan["as_of"], "trade_type": scan["trade_type"], "invocation": "manual",
    "dataset_id": identity["dataset_id"], "completeness": "COMPLETE", "full_universe_scan": False, "fixture": True,
    "limitations": list(scan["limitations"]) + ["FIXTURE_NOT_MARKET_DATA"], "symbols_not_opened": [],
    "symbols": scan["symbols"], "counts": scan.get("counts"), "scan": scan, "authorises_order": False,
    "idempotency_key": key, "manifest_id": "run-browser"}
conn = connect(settings.platform_db)
conn.execute("""INSERT INTO scan_result (scan_key, job_id, as_of, trade_type, invocation, dataset_id, universe_label,
    completeness, full_universe_scan, fixture, limitations_json, symbols_not_opened_json, envelope_json, created_at)
    VALUES (?, NULL, ?, ?, 'manual', ?, 'SYNTHETIC', 'COMPLETE', 0, 1, ?, '[]', ?, '2026-11-17T10:00:00+00:00')""",
    (key, envelope["as_of"], envelope["trade_type"], identity["dataset_id"], json.dumps(envelope["limitations"]), json.dumps(envelope)))
conn.commit(); conn.close()
print(json.dumps({"scan_key": key, "dataset_id": identity["dataset_id"], "as_of": scan["as_of"],
    "zone_id": result.candidates()[0].zone["zone_id"], "last": candles[-1].start.date().isoformat(), "first": candles[0].start.date().isoformat()}))
