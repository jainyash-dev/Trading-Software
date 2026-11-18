# P2-P4 Closure Report

**Date:** 2026-11-17 | **Branch / HEAD:** `main` / `69858d07ccb016b74bc1d518b66b9948656ad6cf` (unchanged)

## Verdicts (engineering; owner retains `ACCEPTED`)

| Scope | Verdict |
|---|---|
| Programme | `P2_P3_P4_ACCEPTANCE_READY` |
| P2 Stock analysis and charting | `P2_ACCEPTANCE_READY` |
| P3 Opportunity intelligence | `P3_ACCEPTANCE_READY` |
| P4 Trade planning | `P4_ACCEPTANCE_READY` |

Each phase's in-scope rows are implemented, tested and either browser-validated or covered by passing
automated tests on unchanged code. The independent review passed after remediation. Owner-deferred and
externally blocked rows stay deferred or blocked and are not counted as implemented. This is engineering
readiness on FIXTURE data. It is not certification, external validation, or evidence of profitability.

## Status breakdown (65 rows; Batch 0 said 64, a miscount)

| Phase | Rows | INDEPENDENT_REVIEWED | VALIDATED | TESTED | DEFERRED_OWNER | BLOCKED |
|---|---:|---:|---:|---:|---:|---:|
| P2 | 18 | 14 | 1 | 0 | 2 | 1 |
| P3 | 27 | 13 | 4 | 5 | 2 | 3 |
| P4 | 20 | 11 | 1 | 5 | 1 | 2 |

Owner-deferred: OD-P2-1, P2-SMA-CHART, OI-007, P3-R15, P4-EXPIRED.
Blocked: TV-1 (TradingView exports), P3-R12/R13 and P4-R17/R18 (P0/D66 certification), D6 sector source,
live alerts (quote provider / owner), B12 tariff verification.

## What changed

**Backend** (`platform/gtf_platform/`): `integration/candles.py` (W/M volume), `planning/service.py`
(journal mirror transition, idempotent cancel), `integration/desk.py` (identity-bound plan/journal sync,
later-scan comparison), `routes.py` (sync on plan reads/cancel/approve and after journal events), `app.py`
(startup repair), `opportunity/ingest.py` (canonical timeframe keys).

**Frontend** (`platform/web/src/`): new `chart/plans.ts`, `chart/evidence.ts`; `chart/CandleChart.tsx` (plan
price lines); `features/workflow/WorkflowPages.tsx` (evidence and plan panels, plan journal state/sync,
later-scan mismatch, expiry note, Journal "Record CANCELLED"); `features/scanner/model.ts` and
`ScannerPage.tsx` (scan outcome panel, canonical status keys); `types/contracts.ts`.

**Tests:** `platform/tests/test_platform_api.py` (+3, 1 assertion updated for the new volume behaviour),
`test_trade_planning.py` (+14), `test_opportunity.py` (+1); vitest `chart/plans.test.ts` (new, 7),
`chart/evidence.test.ts` (new, 10), `scanner/model.test.ts` (+9), `scanner/scanner.test.tsx` (query scoped
to the results table because the outcome panel repeats the gate text; plus outcome assertions).

**Docs:** this folder (matrix, audit appendix, three status files, integration, browser, review, closure,
work log), `docs/implementation/evidence/p2-p4-browser/`, `platform/web/docs/LIMITATIONS.md`,
`docs/product-discovery/p2/P2_ARCHITECTURE.md`, `P2_DATA_CONTRACTS.md`, `p4/P4_REVIEW_REGISTER.md`.

**Build output:** `platform/web/dist` rebuilt (gitignored).

**Architecture:** no new layer, store, journal, qualification path or route. The plan row mirrors the
journal; the journal stays the only execution record.

## Test results (exact, final)

See `AGENT_WORK_LOG.md` entry of 2026-11-17 for the final command list and totals.

## Remaining limitations

- Plan/journal consistency is recoverable (repair on write, read and startup), not atomic.
- Plan GET routes write idempotent mirrors and hold `db_lock` while reading the journal.
- Browser evidence is FIXTURE data; the daily fixture truncates at missing NSE special sessions.
- Several unchanged requirements (FR-3.2, 3.6, 3.8, OI-006, TP-006/007/008/012, FR-5.10) have automated tests
  only in this run.
- One intermittent vitest timing failure was seen once under full-suite load (`stock scanner > submits a MIT
  scan ...`); it passed in every subsequent full and isolated run.
- `run_all` does not include the `platform/` suites; they were run separately.

## Owner decisions still required

1. Automatic plan expiry: an authoritative rule (condition, clock, sessions, timezone) if it is wanted.
2. Whether the Journal UI should also offer an explicit EXPIRED control (today API/CLI only).
3. Confirm that confirmed-excluded (special) sessions stay out of W/M volume, as they are out of W/M OHLC.
4. Unchanged external items: TradingView exports (TV-1), sector source (D6), tariff schedule (B12), P0/D66.
5. `ACCEPTED` stamps for P2, P3 and P4.
