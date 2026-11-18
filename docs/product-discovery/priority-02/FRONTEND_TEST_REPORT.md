# Frontend test report

Working directory: `platform/web`.

| Command | Result |
|---|---|
| `npx tsc -p tsconfig.json --noEmit` | Passed (no output, exit 0, and the following commands ran only because it passed). |
| `npx vitest run` | 9 files, 40 tests passed. |
| `npx vite build` | Passed. Bundle `dist/assets/index-TlqYR40A.js` is 500.24 kB (gzip 153.89 kB). Vite warns that the chunk exceeds 500 kB. |

Vitest files: overview model, scanner model, API client, routes, status badges, overview page, watchlists, application shell, scanner page.

No new Vitest file covers `WorkflowPages.tsx`. The analysis, plan, journal, portfolio, and settings changes were checked in the browser report. The shell test still expects Stock Analysis to render and Shadow / Paper to stay unavailable.

## UI behaviour verified beyond the unit tests

- Fixture banner `FIXTURE_NOT_MARKET_DATA` is on the analysis page when the candle envelope says the series is a fixture.
- Daily Lightweight Charts plot matches the candle route's last close (112).
- Monthly empty series does not keep the daily plot.
- A failed scan request does not keep the previous explanation.
- Plan approval text says no order was sent and `authorises_order` is false.
- Portfolio prints `UNAVAILABLE` for valuation, sector, and drawdown.
- Settings backup copy states that live databases were not replaced.

## Known display gap

On the scanner, symbol status `NO_FRESH_EXECUTION_ZONE` is rendered with `StatusBadge`, whose known codes are candidate decisions. The badge therefore reads "Unknown status: NO_FRESH_EXECUTION_ZONE". The engine reason is still shown beside it. The badge was not given a fake PASS/FAIL mapping.
