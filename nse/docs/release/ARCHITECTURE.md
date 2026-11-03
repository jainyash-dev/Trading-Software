# Architecture (as implemented, 2026-11-02)

A modular monolith in standard-library Python. One deterministic decision pathway; every
other module reads its outputs. No network, broker or order code anywhere under `nse/`.

## Dependency graph

```
 local files only (D31)
 nse/data/eod/raw (bhavcopies) --- nse/eod/nse_bhavcopy.py (strict loader, manifest SHA-256)
 user CSVs ----------------------- nse/research/marketdata.py (DailyInput, dated findings)
 nse/data/calendar --------------- nse/calendar/nse_calendar.py (official circulars, hashed)
 inbox -> research/acquisition.py (plan, ingest, quarantine, ledger, daily update)
 universe CSV -> research/universe.py      instrument records -> research/instruments.py
 corporate actions -> research/corporate_actions.py
                 |
                 v
 nse/mtf-freshness/mtf_freshness.py  replay(daily base, D W M Q HY Y, as_of, calendar)
   uses nse/zone-engine/zone_engine.py on every completed series
   MtfSnapshot.eligible_after_overlay / manual_review_after_overlay   <- ONLY candidate source
                 |
                 v
 research/qualification.py  G0..G8  (structure.py curve/conflict/coinciding, trend.py, levels.py,
                                     topdown.py; confluence.py X/14 display, read by no gate)
   models.derive_status: BLOCKED > REJECTED > DATA_INSUFFICIENT > MANUAL_REVIEW > ACTIONABLE (checks pending)
                 |
                 v
 research/scanner.py  scan / scan_symbol / scan_history (point in time)
                 |
   +-------------+---------------+-----------------+----------------+-----------------+
   v             v               v                 v                v                 v
 reports.py   decision_replay   backtest.py      risk.py          explain.py        store.py
 JSON / CSV   (bundles)         (owner model,    (sizing plan,    alerts.py         (SQLite, journal)
              dashboard.py      walk-forward,    never a status)  narrative.py
              (static HTML)     sensitivity)                      (read scan.json only)
                 |
 scenarios.py + nse/scenarios/ (regression cases through scanner.scan)
 health.py, readiness.py, nse/validation/run_all.py (one validation command)
 .claude/ skills, agents, guard and post-edit hooks
```

## Module responsibilities

| Layer | Module | Responsibility |
|---|---|---|
| Data | `nse/eod/nse_bhavcopy.py`, `nse_replay.py`, `nse_reference.py` | Strict legacy loader with provenance; replay; OHLC reference comparison |
| Data | `research/marketdata.py` | Normalised daily inputs, dated data-quality findings |
| Data | `research/acquisition.py` | Offline acquisition: backfill plan, ingestion, duplicates, revisions, quarantine, JSONL ledger, daily update |
| Data | `research/inventory.py`, `manifest_tool.py` | Coverage and history needed per as-of; manifest rows |
| Reference data | `research/universe.py`, `instruments.py`, `corporate_actions.py` | Effective-dated membership, identity, corporate-action records (no data shipped) |
| Calendar | `nse/calendar/nse_calendar.py` | Official circular tables 2021-2025 |
| Zones | `nse/zone-engine/zone_engine.py` | Detection, core 7/7, freshness, invalidation |
| Freshness | `nse/mtf-freshness/mtf_freshness.py` | HTF candles, touches from the finest base, gaps, overlay eligibility |
| Analysis | `research/structure.py`, `trend.py`, `levels.py`, `topdown.py`, `confluence.py` | Curve, conflict, coinciding, SMA-50 clock, level ranges, TDA, X/14 display |
| Qualification | `research/qualification.py`, `models.py` | G0-G8, alignment matrix, statuses |
| Scanner | `research/scanner.py`, `cli.py` | Universe scans; point-in-time history |
| Outputs | `reports.py`, `narrative.py`, `dashboard.py`, `decision_replay.py` | JSON/CSV, markdown, static HTML, decision bundles |
| Assistant | `explain.py`, `alerts.py` | Evidence-cited answers and self-audit; watchlist alerts (stdout/JSONL) |
| Research | `backtest.py`, `scenarios.py`, `store.py`, `risk.py` | Simulation under owner assumptions; scenario regression; storage and journal; sizing |
| Operations | `health.py`, `readiness.py`, `nse/validation/` | Health, readiness, validation runner, protected hashes |

## Contracts

- `scan.json` (`reports.to_dict`) is the contract every downstream module reads. Each
  consumer re-checks that a status equals `derive_status` of its gates before acting on it
  (store import, risk plan, alerts, explain audit).
- CLI modules register through `add_commands(subparsers)`; `cli.COMMAND_MODULES` lists them,
  and an import error stops the CLI (no silently missing command).
- Every new test module must be in a `run_all` group (the repository check fails otherwise).
