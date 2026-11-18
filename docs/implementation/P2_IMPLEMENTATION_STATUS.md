# P2 Implementation Status - Stock Analysis and Charting

**Date:** 2026-11-17 | **HEAD:** `69858d0` (unchanged) | **Verdict:** `P2_ACCEPTANCE_READY` (owner retains `ACCEPTED`)

Row-level detail: `P2_P4_ACCEPTANCE_MATRIX.md` section A (18 rows: 14 INDEPENDENT_REVIEWED, 1 VALIDATED,
2 DEFERRED_OWNER, 1 BLOCKED).

## Work done

| Item | Change | Evidence |
|---|---|---|
| P2-VOL-WM | `platform/gtf_platform/integration/candles.py`: `_aggregate_volume` sums the constituent daily sessions of each W/M candle (the visible, non-excluded sessions in the candle's `period_key`, count checked against `HtfCandle.sessions_present`). Null with `HTF_VOLUME_INCOMPLETE` when any session lacks a stated volume, null with `HTF_VOLUME_SESSION_MISMATCH` on a count mismatch. New per-row `volume_sessions`. Duplicate CSV dates give null volume. `VOLUME_NOT_AGGREGATED_FOR_HTF` is no longer emitted. | API tests: holiday week (2024-08-15) sums 4 sessions; partial first month; month boundary equals the daily sum; stated zero stays "0"; `-5` / `abc` give null; a gap truncates the series and is never filled; duplicate source date refused (422) and nulled in the volume table. Browser BR-03/04 `PRESENT`. |
| FR-4.9 | New `platform/web/src/chart/plans.ts` presentation model; `CandleChart.tsx` draws dashed price lines titled `PLAN <id> entry/stop/target (journal <state>)`, included in autoscale; Analysis page fetches `/api/v1/plans?symbol&scan_key` and shows a "Plan overlay (FR-4.9)" panel; "Plan lines" toggle. Lines only from the recorded `selected` levels of an APPROVED plan whose journal entry is identity-checked, IN_SYNC, and PLANNED or OPEN, and not ZONE_INVALIDATED. No calculation. | vitest `plans.test.ts` (7). BR-11 three labelled lines; BR-14 after journal cancel: 0 lines, "CANCELLED. Inactive plans are not drawn." |
| FR-4.7 / UX-013 / P2-F | New `platform/web/src/chart/evidence.ts`: per-source evidence state (Candles, Volume, Stored bundle, Qualification, Explanation, Plans, Data certification) from the real API outcome. A failed or foreign bundle makes Qualification UNAVAILABLE; DATA_INSUFFICIENT is MISSING; nothing unavailable becomes a finding. | vitest `evidence.test.ts` (10). BR-05 wrong symbol -> bundle MISSING, qualification UNAVAILABLE; BR-06 unknown scan; BR-07 wrong dataset / wrong session -> STALE. |
| P2-A | Canonical stored-bundle authority re-verified: chart consumes `/candles` + `/symbols/{s}/bundle?scan_key`; no frontend zone or qualification computation; mismatched symbol, dataset, or session is surfaced, not substituted. | BR-05/06/07; reviewer found no hidden recompute. |

## Unchanged and re-verified

FR-4.1, 4.2 (BR-21: zoom, pan after zoom, Fit, crosshair OHLC+V legend), 4.3 (BR-22: drawing saved, persists
after reload, delete persists), 4.4, 4.5, 4.6, 4.8, UX-005/006/014.

## Owner-deferred / blocked (not implemented, by decision)

- **OD-P2-1** standalone chart: `DEFERRED_OWNER` (Decision 1). Empty state still cites it (BR-01).
- **SMA-50 chart overlay**: `DEFERRED_OWNER` / out of scope (Decision 2). `nse/research/trend.py` untouched.
- **TV-1 TradingView parity**: `BLOCKED` (external). Worksheet 34/34 rows blank; the filled INFY file is a
  Yahoo Finance screenshot transcription, not a TradingView export. No parity is claimed.

## Limitations

- All browser evidence is FIXTURE data. The synthetic weekday fixture lacks NSE Saturday special sessions
  (2020-02-01, 2024-01-20), so the daily chart truncates at 2020-01-31 with `SERIES_TRUNCATED` and Candles
  `INCOMPLETE`. This is the required fail-closed behaviour, and it means the 2024 zone and plan prices sit
  below the visible candle range in BR-11.
- Confirmed-excluded sessions are left out of HTF volume, consistent with the HTF OHLC (reviewer assumption
  noted; owner may want this stated in the data contract).
- Evidence states are display classifications, not a canonical status vocabulary.
