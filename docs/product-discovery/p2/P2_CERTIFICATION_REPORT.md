# GTF P2 certification report

**Date:** 2026-11-15  
**Phase:** GTF P2 - Charts and Stock Analysis  
**Overall status:** **P2_COMPLETE_WITH_LIMITATIONS**

This is not P0 data certification, P1 hardening, strategy validation (P7), or production readiness (P11). No orders are authorised. No historical performance is claimed.

## 1. Executive summary

P2 extends the existing `platform/` chart and Stock Analysis stack (Lightweight Charts 5.2.1). Candle integrity, volume honesty, data-quality disclosure, URL timeframe state, multi-timeframe stored zone overlays, drawing persistence, and analysis UX were implemented and tested.

Essential chart and integrity criteria pass. Material limitations remain: standalone inspection without a scan is reserved (OD-P2-1 / FR-4.5); W/M volume is not aggregated; full `run_all` with local_data and automated visual screenshot suite were not completed; P0 remains uncertified and charts label non-fixture local data as exploratory.

## 2. Architecture

- Chart-data service: `platform/gtf_platform/integration/candles.py`
- Renderer: TradingView Lightweight Charts 5.2.1 (AR-4)
- Zones: display-only mapping from stored scan payload (`zonesFromStored`)
- Qualification: stored scan bundle / explain only
- Drawings: platform SQLite via GET/POST/PATCH/DELETE
- Eligibility path unchanged in `nse/`

## 3. Batch delivery

| Batch | Status | Notes |
|---|---|---|
| 0 | COMPLETE | Prior discovery |
| 1 | COMPLETE | Volume null vs zero; quality metadata; invalid candles surfaced |
| 2 | COMPLETE | Volume panel when PRESENT/PARTIAL; legend; zoom controls |
| 3 | COMPLETE | Hash `timeframe`; MTF via `mtf.replay` |
| 4 | COMPLETE | candidates + fresh_zones + blocked_zones; visibility; selection detail |
| 5 | COMPLETE | PLATFORM_DB persistence; PATCH geometry |
| 6 | COMPLETE_WITH_LIMITATIONS | Scan-linked analysis; OD-P2-1 deferred |
| 7 | COMPLETE_WITH_LIMITATIONS | a11y labels / denser layout; no screenshot automation |
| 8 | COMPLETE_WITH_LIMITATIONS | Platform + web + selected `run_all` groups green |

## 4. Data integrity evidence

- Fixture CSV path: blank volume -> `null`; `"0"` -> `"0"`; `volume_state=PARTIAL`; tests in `CandleApi`.
- `data_quality.certified` always false; fixtures `FIXTURE_NOT_MARKET_DATA`.
- Bhavcopy quantity via `nse.research.deps` (`BHAVCOPY_TOTTRDQTY`); no direct `nse.eod` import.
- W/M: `VOLUME_NOT_AGGREGATED_FOR_HTF`; volumes null.
- Frontend `prepareSeries` accepts null volume; rejects negative volume.

## 5. Test results

| Suite | Counts |
|---|---|
| Platform unittest discover | 44 passed |
| Platform product_flow | 8 passed |
| Web vitest | 46 passed |
| Web production build | PASS |
| `run_all --no-data` groups architecture, repository, hooks, validation_framework, zone_engine, mtf_freshness | 180 ran, 0 failures |
| `docs_health` | PASS after removing broken P1 markdown link (pre-existing defect) |
| Full `run_all` with local_data | NOT RUN (limitation) |
| Automated visual screenshot pass | NOT RUN (limitation) |

## 6. Independent review

Independent reviewer: **accept-with-limitations**.

| ID | Severity | Disposition |
|---|---|---|
| P2-IR-1 | MEDIUM | Accepted with documentation: `fresh_zones` list is D3-fresh-only; FRESH fallback is list contract, not geometry inference |
| P2-IR-2 | MEDIUM | Fixed: as_of/dataset resolved from the named scan envelope only; health `last_scan` no longer used |
| P2-IR-3 | LOW | Fixed: invalid/undrawable candle rows surfaced in Analysis UI |
| P2-IR-4 | LOW | Fixed: non-fixture exploratory quality API test |
| P2-IR-5 | INFO | Drawing type-only geometry validation; no eligibility coupling |
| P2-IR-6 | INFO | Evidence limits documented (full local_data run_all / live TOTTRDQTY) |

No unresolved CRITICAL or HIGH findings. MEDIUM items closed or documented.

## 7. P0 / P1 compatibility

- P0 certification rules and membership CSVs were not modified for chart features.
- P1 desk/risk contracts were not weakened. One docs-health fix in `P1_CERTIFICATION_REPORT.md` (broken relative link text) only.
- `authorises_order` remains false. `DATA_READY` remains false on candle quality.

## 8. Changed files (P2-owned)

- `platform/gtf_platform/integration/candles.py`
- `platform/gtf_platform/routes.py`
- `platform/gtf_platform/store.py`
- `platform/gtf_platform/openapi.json`
- `platform/tests/test_platform_api.py`
- `platform/web/src/chart/*` (including `zones.ts`, `zones.test.ts`)
- `platform/web/src/features/workflow/WorkflowPages.tsx`
- `platform/web/src/types/contracts.ts`
- `platform/web/src/navigation/query.ts`, `routes.test.ts`
- `platform/web/docs/CHARTING.md`, `LIMITATIONS.md`, `FIXTURES_AND_API.md`
- `docs/product-discovery/p2/*`
- `docs/product-discovery/p1/P1_CERTIFICATION_REPORT.md` (docs-health link only)

Unrelated dirty/untracked files outside this list remain owner/other-session work.

## 9. Git status

- Branch: `main`
- HEAD: `69858d07ccb016b74bc1d518b66b9948656ad6cf`
- Ahead of origin: 17 commits (pre-existing)
- Staged: none
- Commits this session: **none**
- Push: **none**
- Working tree: still heavily dirty from pre-existing work plus P2 edits (uncommitted)

## 10. Limitations (accepted)

1. OD-P2-1: no standalone chart without stored scan.
2. W/M volume not aggregated.
3. Candle route never claims P0 CERTIFIED.
4. Full local_data `run_all` not executed in Batch 8.
5. No automated visual screenshot matrix.
6. Live official-archive TOTTRDQTY path implemented but not integration-tested against owner bhavcopies in this session.

## 11. Next-phase handoff (P3)

P3 may consume: durable candle contract with quality labels, Analysis URL state (`symbol`, `scan`, `timeframe`, `as_of`, `dataset_id`), stored zone overlay vocabulary, and drawing persistence. P3 must not treat chart overlays as opportunity ranking authority.
