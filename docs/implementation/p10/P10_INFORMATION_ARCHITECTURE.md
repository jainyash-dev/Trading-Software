# P10-1 Information Architecture and Navigation

Source of truth: `platform/web/src/navigation/routes.ts`. Hash routing (`#/<id>?<allow-listed query>`) is unchanged, so every pre-P10 deep link still resolves. Unknown ids fall back to Market Overview.

## Navigation

| Group | Label | Route id | Capability status | Backed by |
|---|---|---|---|---|
| Overview | Market Overview | `overview` | LIVE | health, overview, datasets, universe, calendar, scans, watchlists, portfolio, plans, journal |
| Overview | Watchlists | `watchlists` | LIVE | watchlists, instruments |
| Research | Stock Analysis | `analysis` | LIVE | scans/{k}, candles, bundle, explain, drawings, plans, instruments |
| Research | Opportunity Scanner | `scanner` | LIVE | scans, jobs, scan-configs, datasets |
| Research | Opportunities | `opportunities` | LIVE | opportunities |
| Research | Scan History | `history` (new) | LIVE | scans (cursor paging) |
| Trading | Trade Plans | `plans` | LIVE | plans (+ history for lifecycle and allowed transitions) |
| Trading | Portfolio | `portfolio` | LIVE | portfolio |
| Trading | Risk Overview | `risk` (new) | LIVE | portfolio, settings |
| Trading | Trading Journal | `journal` | LIVE | journal (+ 7 write routes) |
| Intelligence | Backtesting | `backtest` | PARTIAL | POST backtests; no run list |
| Intelligence | Strategy Analytics | `analytics` | NOT_IMPLEMENTED | none (capability page) |
| Intelligence | Research Reports | `reports` | LIVE | scans/{k}/reports/{name} (8 files) |
| Intelligence | AI Research Assistant | `assistant` | PARTIAL | symbols/{s}/explain (deterministic); no language model |
| Intelligence | Shadow / Paper | `paper` | NOT_IMPLEMENTED | none (TJ-012 owner-deferred) |
| System | Data Health | `data` | LIVE | health, datasets, universe, calendar, overview |
| System | Jobs and Monitoring | `jobs` | PARTIAL | health, overview job fields, scans, jobs/{id}; no job list route |
| System | Settings | `settings` | LIVE | settings, backup, restore-check; theme (browser) |

`Partial` and `Later` tags appear next to the nav label. A `NOT_IMPLEMENTED` route renders a capability page that explains purpose, blockers and what to use instead; it never renders sample results.

## Shell

- Sidebar (232 px, 56 px collapsed; collapses automatically below 1100 px, overlay when opened): brand, five groups with icons, collapse control, persistent safety line ("No broker connection. No orders are placed.").
- Sticky top bar: breadcrumb (group › page), data-context chips (EOD through, last scan, completeness, P0 data certified / not certified), global search, API status, theme switch, IST clock labelled as wall clock.
- Context strip: "Research and decision support · End-of-day NSE data · Nothing on this screen is an order or a live quote", plus the fixture-specimen toggle. When disconnected it becomes the `role="alert"` bar with Retry.
- Full-width `FIXTURE_NOT_MARKET_DATA` banner unchanged.

## Cross-screen links (journeys)

Search result → Analyse (asks for a stored scan; OD-P2-1 kept) or Add to watchlist. Analysis → Draft a plan from candidate, Open trade plan. Plans → Open chart, Journal entry. Portfolio row → Journal entry. Overview → recent plans / journal entries, Data Health. Jobs / History → Scanner inspect. Assistant → Open in Stock Analysis.

## Acceptance (browser evidence, `P10_BROWSER_VALIDATION.md`)

All 18 routes reachable; active state correct; reload keeps the route; back/forward and deep links verified; no dead links; unavailable features explained.
