# P10 Closure Report and Owner Demonstration

**Date:** 2026-11-17 | **Branch / HEAD:** `main` / `69858d07ccb016b74bc1d518b66b9948656ad6cf` (unchanged; nothing staged, committed or pushed)
**Verdict (engineering):** `P10_ACCEPTANCE_READY`, subject to the open items below. Owner `ACCEPTED` is separate. This is UI readiness on FIXTURE data; it is not data certification, external validation or evidence of profitability.

## How to launch

```
cd platform/web && npm run build          # writes platform/web/dist
cd ../.. && python3 platform/run_api.py   # prints the local URL; serves the UI and the API
```
For a fixture demonstration, follow `docs/implementation/evidence/p10-browser/` (setup script, `rebind_dataset.py`, `GTF_FIXTURE=1`).

## 1. What GTF looks like now

An institutional research terminal: grouped sidebar (Overview, Research, Trading, Intelligence, System), sticky top bar with data context (EOD date, last scan, completeness, P0 not certified), search, API status, theme switch and IST clock, and a permanent "no orders" line. Screens use panels, KPI tiles, right-aligned tabular figures in ₹, status chips with text and glyphs, and provenance badges.

| Screen | Dark | Light |
|---|---|---|
| Market Overview | ![](../evidence/p10-browser/shots/dark-overview.png) | ![](../evidence/p10-browser/shots/light-overview.png) |
| Stock Analysis (D) | ![](../evidence/p10-browser/shots/dark-analysis-D.png) | ![](../evidence/p10-browser/shots/light-analysis-D.png) |
| Opportunity Scanner | ![](../evidence/p10-browser/shots/dark-scanner.png) | ![](../evidence/p10-browser/shots/light-scanner.png) |
| Trade Plans | ![](../evidence/p10-browser/shots/dark-plans.png) | ![](../evidence/p10-browser/shots/light-plans.png) |
| Portfolio | ![](../evidence/p10-browser/shots/dark-portfolio.png) | ![](../evidence/p10-browser/shots/light-portfolio.png) |
| Risk Overview | ![](../evidence/p10-browser/shots/dark-risk.png) | ![](../evidence/p10-browser/shots/light-risk.png) |
| Trading Journal | ![](../evidence/p10-browser/shots/dark-journal.png) | ![](../evidence/p10-browser/shots/light-journal.png) |
| Backtesting | ![](../evidence/p10-browser/shots/dark-backtest.png) | ![](../evidence/p10-browser/shots/light-backtest.png) |
| AI Research Assistant | ![](../evidence/p10-browser/shots/dark-assistant.png) | ![](../evidence/p10-browser/shots/light-assistant.png) |
| Data Health | ![](../evidence/p10-browser/shots/dark-data.png) | ![](../evidence/p10-browser/shots/light-data.png) |
| Jobs and Monitoring | ![](../evidence/p10-browser/shots/dark-jobs.png) | ![](../evidence/p10-browser/shots/light-jobs.png) |
| Settings | ![](../evidence/p10-browser/shots/dark-settings.png) | ![](../evidence/p10-browser/shots/light-settings.png) |

All 40 route captures plus journeys and responsive shots: `docs/implementation/evidence/p10-browser/shots/`.

## 2. What the owner can do on each screen

- **Market Overview:** see latest EOD date and certification state, latest scan, monthly trades and open positions against the caps, readiness; candidate counts; recent scans, plans and journal entries; jump to any area.
- **Watchlists:** create, rename, reorder and delete lists; add instruments from search.
- **Stock Analysis:** open a symbol from a stored scan (or pick one from the chooser); switch M/W/D; toggle zones and plan lines; zoom/pan/crosshair; read evidence status, G0-G8 gate table, zones, plan overlay, explanation, data quality; save drawings; draft a plan from the candidate.
- **Opportunity Scanner / Scan History / Opportunities:** run a scan, follow the job, read outcomes and per-symbol evidence; page through stored scans; organise candidates.
- **Trade Plans:** create a draft from a stored candidate, choose a printed buffer, answer the 11-item checklist, submit, approve (with confirmation), reject or cancel with a reason; only backend-allowed transitions are offered; lifecycle and plan/journal sync are shown.
- **Portfolio / Risk Overview:** caps, EOD valuation and its date, STALE marks, per-position risk to recorded stops, owner risk inputs; sector and drawdown shown as unavailable.
- **Trading Journal:** filter, open a trade, read planned versus actual, executions, events, notes, attachments; record order reference, prints, close, CANCELLED (confirmed), charges, notes, reviews, screenshots; export.
- **Backtesting / Reports:** run a labelled study on owner costs; export any of the 8 stored report files.
- **AI Research Assistant:** ask "why this status" for a symbol in a stored scan; get the deterministic explanation with cited gates, rule references and zones.
- **Data Health / Jobs / Settings:** data coverage, limitations, datasets, calendar, identity; scheduler, latest and active jobs, recent outcomes, job lookup; theme, risk inputs, scheduler, backup and restore check, status vocabulary.

## 3-7. Connection and data status

| | Screens |
|---|---|
| Fully connected to existing APIs | Overview, Watchlists, Stock Analysis, Scanner, Opportunities, Scan History, Trade Plans, Portfolio, Risk Overview, Journal, Research Reports, Data Health, Settings |
| Partly connected (capability gap is in the backend) | Backtesting (no run list or manifests), AI Assistant (deterministic only; no language model), Jobs (no job list route) |
| Frontend capability page only (no backend) | Strategy Analytics, Shadow / Paper |
| Blocked by P0 | Any CERTIFIED label; analytics and quotable backtests. `certified_p0_data` is false and every screen says "not certified" |
| Fixture data in screenshots | All. Evidence uses synthetic `SYN`/`WALK` series (FIXTURE_NOT_MARKET_DATA) |
| Certified data | None. No screen claims certification |

## 8. Browser-tested workflows

Journeys A (stock research), C (plan approval confirmation, transitions), D (portfolio to journal), F (data transparency), G (theme, deep links, back/forward, reload) in the browser; B and E partly (scanner outcome, real pipeline job, opportunities ingest, journal detail; form submission and filtering by vitest). Detail: `P10_BROWSER_VALIDATION.md`.

## Test results (exact)

| Command | Result |
|---|---|
| `npx tsc -p tsconfig.json --noEmit` (platform/web) | pass |
| `npx vitest run` (platform/web) | 17 files, **104/104 pass**, 5 consecutive runs (baseline 89; +15 P10 tests; 1 assertion's expected h1 renamed to "Market Overview") |
| `npm run build` | pass (561 kB chunk-size warning, pre-existing) |
| `python3 -m pytest -q -p no:cacheprovider tests` (platform) | **100 passed** |
| Browser run (final) | **56/56** steps |
| `python3 -m nse.validation.run_all` | Run 3 on the final tree: 1512 ran, 1 failure (docs-health H4 on a command quoted in the new work-log entry); every other group PASS. After a one-line wording fix: `docs_health` PASS (0 findings), `--group architecture` 28/28 PASS, `--group repository` 15/15 PASS. The full 16-minute run was not repeated after that one-line doc edit. `git diff --check` clean; nothing staged |

## 9. Remaining issues

- Minor review items M-7 and C-2 (`P10_INDEPENDENT_REVIEW.md`).
- The global fixture banner follows `meta.fixture` only; plans/journal/portfolio fixture rows rely on in-page labels.
- No screen-reader session or full automated contrast scan.
- One intermittent vitest failure seen once under concurrent load; not reproduced in 5 runs.
- 561 kB JS bundle (no code splitting).
- The P2-P4 browser driver (`evidence/p2-p4-browser/run_browser_validation.mjs`) matches pre-P10 page text (e.g. "Plan state\nDRAFT", unconfirmed Approve) and was not rerun; its screenshots are historical. The P10 driver covers the same flows through the API plus the new UI.

## 10. Recommended next

1. Owner review of the screens above and `ACCEPTED` decision.
2. Backend routes the UI is ready for: job list, backtest run list and manifest store (then Strategy Analytics), platform-wide activity feed.
3. Mark fixture rows with `meta.fixture` on plans/journal/portfolio so the global banner covers them (API change; needs approval of the contract change).
4. Owner decisions still pending from earlier phases: OD-P2-1 (standalone chart), P2-SMA-CHART, plan expiry rule, TJ-012 paper book, AI-002 provider.
5. Continue P0 certification; no UI change is needed for certified data to appear, the badges follow `certified_p0_data`.

## Governance record

Facts: no backend, contract, Rulebook, Pine, D66 or P0 file changed; protected hashes verified by `run_all` repository checks; no broker or order code; `authorises_order` never set. Assumptions: Ant Design and "P9" references in the P10 prompt did not match the repository (none added). Recommendations above are not owner decisions.
