# Implementation report (2026-11-02)

## Starting state (verified, not taken from earlier reports)

Uncommitted work already held: Zone Engine, MTF overlay, calendar, legacy bhavcopy loader,
replay, G0-G8 with R1-R6, scanner, JSON/CSV reports, readiness, a backtest scaffold, the
validation runner, 20 project skills, 5 agents and guard hooks. 714 tests, 2 failing.

## Added this session

| Module | What it does | Tests |
|---|---|---|
| `research/acquisition.py` | Offline acquisition: provider interface (`LocalInboxProvider` only), format detection (UDiFF quarantined, B18), resumable plan per calendar session, ingestion with SHA-256, duplicate and revised-file quarantine, never moves or deletes sources, append-only JSONL ledger, scheduler-ready daily update with retries and alerts | 32 |
| `research/instruments.py` | Effective-dated symbol / ISIN / delisting / merger records (none built in), point-in-time resolution, consistency findings against bhavcopies | 22+ |
| `research/risk.py` | Rulebook C1/C2/Ch.3/Ch.6 risk plan per actionable candidate: exact quantity, loss <= RPT, stage band, 10-trade ceiling, capital insufficient MANUAL (never resized), cash equity only, never average down; never changes a status | 30+ |
| `research/confluence.py` | Spec 5.3 X/14 display: core evaluated; HTF EMA20, crossover, gap PROVISIONAL; sector, RSI/Stoch NOT_EVALUATED; read by no gate | 11 |
| `research/backtest.py` (extended) | Extended metrics, setup breakdowns recorded at signal time, assumption events, optional monthly cap and concurrency (recorded when unset), walk-forward with explicit folds, sensitivity without ranking | 46 total |
| `research/scenarios.py`, `nse/scenarios/` | Scenario laboratory: strict schema, SYNTHETIC / HISTORICAL_REAL / OWNER_CHART kinds, 19 seed scenarios, provenance manifest, generator with `--check` | 31 |
| `research/decision_replay.py` | Point-in-time decision bundles (candles, zones with overlay status, the scanner's own decision) | in 24 |
| `research/dashboard.py` | Static offline HTML: overview, scanner table (every status), per-stock gate pages, SVG charts | in 24 |
| `research/explain.py`, `alerts.py`, `narrative.py` | Evidence-cited answers and self-audit; watchlist alerts (stdout, JSONL); daily, stock and comparison markdown | 44 |
| `research/store.py` | Optional SQLite store: additive checksummed migrations, append-only tables, idempotent import, zone history, backup; paper-trade journal with Rulebook constraints | 41 |
| `research/health.py` | Checkout health (protected files, imports, calendar, EOD, readiness claims) | 7 |
| CLI | 24 subcommands registered through `cli.COMMAND_MODULES` | via module tests |
| Agent framework | Skills: nse-data-engineering, nse-scenario-library, frontend-dashboard, database-engineering, security-reliability; guard and protected-hash coverage of the Rulebook PDF | hooks, council |

## Modules requested but not built

- News, fundamentals and sector context (no approved source; sector is D6 "not evaluated").
- External notification delivery (email, webhook): needs owner configuration and approval.
- Paper-trading simulator loop (the journal records owner decisions; no automated loop).
- UDiFF parser (no real sample, B18; D31 requires the format reported first).
- Network downloaders and licensed-API adapters (D31: no network-fetching code).
- A database server (SQLite file store only; nothing needed PostgreSQL).
- WIT intraday output (BLOCKED, M4b).

## Requested skills mapped to existing ones (not duplicated)

quant-research -> trading-council / backtest-review; nse-methodology-compliance ->
rulebook-compliance; backtesting-engineering -> backtest-review; tradingview-parity ->
reference-data-validation; test-automation -> integration-testing, adversarial-testing,
test-engineer agent; technical-documentation -> release-readiness.
