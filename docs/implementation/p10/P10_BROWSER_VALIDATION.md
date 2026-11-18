# P10 Browser Validation

**Date:** 2026-11-17. **Browser:** Google Chrome headless via `puppeteer-core` (existing dev dependency).
**Server:** the real platform launcher (`python3 platform/run_api.py`, which calls `gtf_platform.__main__`) on `127.0.0.1:8899` serving the production build `platform/web/dist`, with `GTF_FIXTURE=1` and a temporary data directory.
**Data:** FIXTURE only (`setup_fixture_env.py`, copied from the P2-P4 evidence: synthetic long-MIT series `SYN` and random walk `WALK`). Not NSE market data. Nothing here is certification, external validation or a performance claim.

Evidence: `docs/implementation/evidence/p10-browser/`: `run_p10_browser.mjs` (driver), `setup_fixture_env.py`, `rebind_dataset.py`, `results.json`, `shots/` (48 screenshots).

## Procedure

1. Build fixture env, start server, `rebind_dataset.py` (binds the fixture scan to the dataset id the server computes; without it the UI correctly shows Candles `STALE`, as in P2 run 1).
2. Seed through real API routes from the browser session: settings; plan draft from the stored candidate; approval with all 11 checklist answers (journal entry 1, `authorises_order` false); journal order reference, ENTRY print (181 @ 160.44), review note; second draft; a real-pipeline MIT scan (`WALK`, missing `NOPE`: VALIDATING → RUNNING → SUCCEEDED_COMPLETE); opportunity ingest; a watchlist.
3. Every route in dark, then light (theme set, page reloaded), with an in-page audit per screen.
4. Journeys and behaviours below, then responsive widths.

## Runs

| Run | Result | Action |
|---|---|---|
| 1 | 54/56; daily chart missing; Weekly showed Candles `STALE` (dataset id mismatch) | Correct fail-closed UI. Added `rebind_dataset.py`. Also found: content scrolled inside a fixed viewport (full-page capture cut off) → document scrolling with sticky nav/header. Driver bugs (backdated journal events, missing idempotency key) fixed. |
| 2 | 56/56; light pass not actually light (hash-only navigation did not reload) | Driver fixed (reload after theme set). Found 390 px overflow from always-mounted benchmark host → mounted only with `?bench`. |
| 3 | 56/56; overview fixed; analysis still overflowed at 390 px | Light-theme review found unreadable selected/primary buttons (unlayered CSS reset) → resets moved to `@layer base`; candidate zone id read from `zone.zone_id`; plan actions gated on backend `allowed_transitions`; long codes wrap. |
| 4 | **56/56 pass**; every route in the requested theme; 0 unnamed buttons, 0 unlabelled inputs, 0 horizontal page overflow at 1440/1024/768/390 px; `CERTIFIED` badge only on Settings specimens | none |
| 5 (final, after independent-review fixes, current build) | **56/56 pass**; same audit results: both themes on every route, 0 accessibility-audit failures, no page overflow at any width, CERTIFIED only on Settings specimens | none |

Global fixture banner: it follows `meta.fixture`. Plans, Journal, Portfolio and Risk receive fixture rows with `meta.fixture: false`, so those screens show their own FIXTURE labels (source quality, research use) instead of the global banner. Recorded as a limitation; API semantics were not changed.

Console errors in the final run: HTTP 401 (pre-bootstrap session probe) and 404 (journey A opens SYN in the WALK scan, which does not contain SYN; the page reports it). Both expected.

## Screens captured (dark and light, `shots/<theme>-<name>.png`)

overview, watchlists, analysis-D, analysis-W, analysis-noscan, scanner, opportunities, history, plans, portfolio, risk, journal, backtest, analytics, reports, assistant, paper, data, jobs, settings. Plus `journey-a-opened-from-chooser`, `journey-c-approve-confirmation`, `responsive-{laptop,tablet,mobile}-{overview,analysis}`.

## Journeys (P10 section 16)

| Journey | Observed |
|---|---|
| A Stock research | Global search returned 11 instruments; "Analyse" → Stock Analysis lists stored scans (OD-P2-1 kept); choosing a scan opened the chart page with evidence. Timeframe M/W/D, zones, gate table, notices on D and W. |
| B Opportunity discovery | Scanner shows the stored fixture scan outcome; real-pipeline scan job reached SUCCEEDED_COMPLETE (API from the browser session, as in P2-P4); Opportunities list populated by ingest. Scan form submit itself is covered by vitest, not this run. |
| C Trade planning | Plan detail shows combinations table, cap checks, manual execution card, planned versus actual, lifecycle. On a DRAFT, Approve opens a confirmation dialog (Escape closes it, nothing recorded). Approved plan shows only backend-allowed transitions. |
| D Portfolio | Caps 1 of 10 / 1 of 10, EOD valuation, `STALE` mark with date 2024-02-02, sector/drawdown UNAVAILABLE; row "Journal" → `#/journal?entry=1` with detail. |
| E Journal | Entries table, detail with planned versus actual, executions, events, notes; grouped record forms; CANCELLED and close require confirmation. Filtering covered by vitest. |
| F Data transparency | Data Health: latest EOD 2024-07-12, Not certified, data_ready false, readiness NOT_READY, datasets with provenance, limitations list; no screen shows CERTIFIED. |
| G Theme and navigation | Header switch → light; after reload `data-theme=light` already at DOMContentLoaded and after mount. Deep link, back, back, forward, reload all keep route and h1; active nav correct. |

## Not covered in the browser

Disconnected/unauthenticated states (vitest); attachment upload and preview; backtest run (needs calendar and owner costs; refusal path is API-tested); report "Save file" download; keyboard-only traversal of every screen (spot checks only); screen-reader output (not tested with an actual screen reader).
