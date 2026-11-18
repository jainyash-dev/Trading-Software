# P10-0 Screen Inventory (baseline, before P10 changes)

Data kind: every screen reads the live local API. Fixture data appears only when the API marks `meta.fixture` (or `?fixtures=1`). No screen used hard-coded market data at baseline.

| Route | Component | APIs | Functionality | Missing | Tests | Browser evidence | Defects |
|---|---|---|---|---|---|---|---|
| `#/overview` | `OverviewPage` | health, overview, datasets, universe, calendar, scans, watchlists | Platform status, readiness, universe, latest scan, counts, activity, watchlists | Caps, plan/journal activity, summary cards | overview.test (7), model.test | none dedicated | Long single column, no KPI strip |
| `#/scanner` | `ScannerPage` | datasets, scan-configs, watchlists, scans, jobs, scans/{k}, symbols, bundle, candles | Submit, poll, cancel, history, stored results, outcome panel, symbol evidence | Separate history page | scanner.test (7), model.test | 16, 17, 20 | Dense but structured |
| `#/opportunities` | `OpportunitiesPage` | opportunities, ingest, transition, scans, watchlists | Ingest stored scan, filters, workflow transitions | none | opportunities.test | 18 | OK |
| `#/watchlists` | `WatchlistsPage` | watchlists, instruments | CRUD, reorder, search | none | watchlists.test | 19, 23 | OK |
| `#/analysis` | `AnalysisPage` | scans/{k}, candles, bundle, explain, drawings, plans | M/W/D chart, zones, plan lines, drawings, evidence | Stock header, gate table, last close | evidence/zones/plans tests | 01-07, 11, 14, 21, 22 | Warning stack, text-only gates |
| `#/plans` | `PlansPage` | plans (list, detail, create, submit, approve, reject, cancel, reopen, rationale) | Full lifecycle | Table, detail layout | plans-navigation.test; API tests | 08-10, 13, 15 | Unstructured |
| `#/portfolio` | `PortfolioPage` | portfolio | Caps, valuation, positions | Table, meters | portfolio.test (10) | none | Paragraph rows |
| `#/journal` | `JournalPage` | journal list/detail/performance/export + 7 write routes | Full journal | Readable detail | journal.test | 12 | Raw JSON, one-column actions |
| `#/backtest` | `BacktestPage` | backtests | Labelled run | Run list (no API) | none | none | Bare form |
| `#/analytics` | `BacktestPage` | backtests | Same as backtest | Backend | none | none | Duplicate screen |
| `#/paper` | static | none | Placeholder | Simulator (TJ-012) | app.test | none | none |
| `#/assistant` | static | none | Placeholder | explain UI | app.test | none | Ignores existing explain route |
| `#/data` | static | none | Placeholder | All | app.test | none | Ignores existing APIs |
| `#/reports` | `ReportsPage` | scans/{k}/reports/candidates.csv | Export one file | Scan picker, other files | none | none | Free-text scan key |
| `#/settings` | `SettingsPage` | settings, backup, restore-check | Capital, risk, scheduler, backup | Theme | app.test | none | No sections |
