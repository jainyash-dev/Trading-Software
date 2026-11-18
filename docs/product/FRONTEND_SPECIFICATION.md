# Frontend specification

> Product Prompt 00. What the Mac application shows. Visual quality is part of the
> build, and it is subordinate to status honesty: a dense screen that mislabels a manual
> review is a defect.
>
> Chart library choice and object separation: [system architecture](../architecture/SYSTEM_ARCHITECTURE.md) section 6.
> Payload shapes: [API contracts](../architecture/API_CONTRACTS.md).

## 1. Product shape

One browser window on the local origin (D57). Desktop-width first. Minimum useful size
1100 × 720. From 1100 down to 768 the sidebar collapses and the top bar wraps. A phone
layout is not a product target.

Regions:

- Left navigation, 240 px, grouped. Collapsible to icons.
- Top bar: current dataset id (short), `as_of` or "latest accepted", scan completeness, and a fixture banner when `meta.fixture` is true.
- Main canvas.
- Optional right inspector on analysis, plans, and positions.

The top bar is present on every screen. A fixture banner is a full-width strip reading
`FIXTURE_NOT_MARKET_DATA`, not a footnote.

## 2. Navigation

| Group | Item | Screen |
|---|---|---|
| Work | Overview | Market overview |
| Work | Market Scanner | Scanner |
| Work | Watchlists | Watchlist editor and scan-from-list |
| Work | Stock Analysis | Chart workstation |
| Work | Trade Plans | Plan list and plan detail |
| Work | Portfolio | Positions, caps, capital |
| Work | Trading Journal | Journal |
| Research | Backtesting | Backtest setup and runs |
| Research | Strategy Analytics | Figures for a cited run |
| Research | Shadow / Paper | Simulated book |
| System | AI Research Assistant | Explain, or a disabled state |
| System | Data Centre | Ingest, coverage, calendar, identity |
| System | Reports | Report builder |
| System | Settings | Local configuration |

Keyboard: `/` focuses search on screens that have it. `Esc` closes a dialog.
Table rows accept Up/Down when the table is focused. Prompt 4 implements the keys and
shows them in tooltips. Missing shortcuts are acceptable in a spike; missing status
labels are not.

## 3. Visual system

Institutional and quiet. The interface looks like a research terminal, not a marketing
site and not a brokerage ticket.

| Token | Value | Use |
|---|---|---|
| Canvas | `#f4f6f8` | Window background |
| Surface | `#ffffff` | Cards, tables |
| Line | `#e1e5ea` | Borders and dividers |
| Text | `#1b2128` | Primary |
| Muted | `#5c6773` | Labels, provenance |
| Focus | `#1f4b99` | Focus ring and links |
| Demand zone | `#1d6b3a` at 18% opacity, solid proximal | Engine demand `FRESH` only |
| Supply zone | `#8f2d2d` at 12% opacity | Engine supply |
| Drawing | `#6b4c9a` | User geometry only |
| Plan entry | dashed `#1f4b99` | Plan overlay |
| Plan stop | solid `#8f2d2d` | Plan overlay |
| Plan target | solid `#1d6b3a` | Plan overlay |

Typography: the system UI font on macOS. Prices and quantities use tabular figures.
Sizes: 13 px body, 12 px tables, 11 px meta. Row height 36 px. Spacing steps 4, 8, 12, 16, 24, 32.

| Candidate status | Chip | Label |
|---|---|---|
| `ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING` | background `#fff6e0`, text `#8a5a00` | `Actionable · manual checks pending` |
| `MANUAL_REVIEW` | background `#fff6e0`, text `#8a5a00`, dashed border `#8a5a00` | `Manual review` |
| `DATA_INSUFFICIENT` | background `#eef1f4`, text `#3d4a5c`, dashed border `#3d4a5c` | `Data insufficient` |
| `REJECTED` | background `#fdecec`, text `#8f2d2d` | `Rejected` |
| `BLOCKED` | background `#eef0f3`, text `#3d4450` | `Blocked` |

| Gate outcome | Text |
|---|---|
| `PASS` | `#1d6b3a` |
| `FAIL` | `#8f2d2d` |
| `MANUAL` | `#8a5a00` |
| `DATA_INSUFFICIENT` | `#3d4a5c` |
| `BLOCKED` | `#3d4450` |
| `NOT_EVALUATED` | `#5c6773` |

| Symbol status | Label colour |
|---|---|
| `EVALUATED` | `#1b2128` |
| `NO_FRESH_EXECUTION_ZONE` | `#5c6773` |
| `DATA_INSUFFICIENT` | `#3d4a5c` |
| `BLOCKED` | `#3d4450` |
| `NOT_IN_UNIVERSE_AT_AS_OF` | `#5c6773` |

| Zone overlay | Fill | Stroke |
|---|---|---|
| Demand `FRESH` | `#1d6b3a` at 18% opacity | `#1d6b3a` |
| Demand `TESTED` | `#5c6773` at 12% opacity | `#5c6773` dashed |
| Demand `INVALIDATED` | none | `#8f2d2d` dashed |
| Demand `UNKNOWN` | `#3d4a5c` at 10% opacity | `#3d4a5c` dotted |
| Supply, any status | `#8f2d2d` at 12% opacity | `#8f2d2d`, and never the fresh-demand fill |

Plan entry is a dashed line `#1f4b99`. Plan stop is solid `#8f2d2d`. Plan target is solid `#1d6b3a`. User drawings are `#6b4c9a`. Tested, invalidated, and unknown zones never use the fresh-demand fill.

Colour is a status language. It is not a buy button. Gate `PASS` never fills the row as "go". `UNAVAILABLE` and `NOT_SUPPLIED` are an em dash plus the word, in `#5c6773`, never `0`. `UNIVERSE_UNVERIFIED` is persistent text. `SIMULATED` is in the title of the paper book. An error shows the message, the `error.code`, and a retry when the action is safe to retry. Loading uses skeleton rows that are not shaped like numbers. An empty state says what is empty, why, and the next action.

Every screen in section 5 has three states in addition to its specific notes: an empty sentence, a loading skeleton, and an error line with `error.code` and a retry when the request is safe to repeat. The scanner includes `FAILED` and `INTERRUPTED`. Analysis includes a bundle that is loading, missing, or has no candles. Watchlists include a list with no symbols. Overview includes health still loading.

Charts sit on a slightly darker panel so candles are readable. The rest of the app stays
light. A dark theme is a Prompt 4 option only if the same status chips remain distinguishable.
Reduced motion: zone and page transitions respect the system setting. The vendored
design skills are advisory for motion polish; they do not override this status language.

## 4. Components

- Tables: sticky header, sortable only by columns that are fields. No secret rank column. Status sort uses the engine's restrictiveness order.
- Filters: status, limitation code, watchlist. Active filters are visible chips and can be cleared.
- Search: symbol, name, ISIN. Results show the identity verified flag.
- Cards: one idea, a title, a primary fact, and provenance in muted type.
- Tooltips: define a code (`G5`, `NOT_SUPPLIED`). They do not hide the only copy of a warning.
- Notifications: scan finished, scan failed, job interrupted. They include completeness. They disappear into the job record.
- Buttons that record an order say "Record Kite order". They do not say "Buy" or "Send".

## 5. Screen specifications

### 5.1 Overview

Purpose: decide whether to trust today's research.
Data: health, calendar, last dataset, last scan counts, cap usage from the live journal.
Layout: four status cards (data, scan, caps, health), then the candidate counts by status, then the latest limitations list.
Actions: open the scan, open Data Centre, start a manual scan.
States: no dataset yet; scan partial; calendar unresolved; health fail.
Must not: show sector or index performance as zero when the series is absent.

### 5.2 Market scanner

Purpose: read every symbol result for one run.
Data: envelope symbols, paged.
Layout: filter bar, table (symbol, symbol status, candidate status, execution zone freshness, deciding gate, limitations), footer with completeness.
Actions: open analysis, save the visible symbols as a watchlist, export the existing CSV.
States: running with progress; partial; unverified universe; empty because the date is a holiday.
Must not: rank by an invented score. `pre_entry_score`, if a column is shown, is labelled display-only.

### 5.3 Watchlists

Purpose: private lists.
Data: watchlist rows and whether each symbol is in the universe at the selected date.
Actions: add, remove, reorder, scan this list.
Must not: imply that a watchlist is the Nifty 100.

### 5.4 Stock analysis

Purpose: inspect structure at an `as_of`.
Layout: timeframe switcher `M` / `W` / `D`, chart, drawing toolbar, inspector with overlay status, opposing supply, G0–G8, findings, provenance.
Actions: draw, save drawing, open the plan if a candidate exists, change `as_of`.
States: `replay: NOT_RUN` with the engine reason; unknown freshness styled differently from fresh; no zone.
Must not: let a drawing tool edit a zone's proximal or distal. Engine geometry is read-only. Zone and plan primitives have no hit target and no drag handles. Saving a drawing writes one platform drawing record and leaves the decision bundle and the scan files unchanged. The create-plan action is enabled only from the stored candidate status, not from fresh-zone styling.

Drawing toolbar: select, horizontal line, trend line, rectangle, text, delete selection.
Selected user objects show a `#6b4c9a` outline. Engine zones use the overlay table in section 3, including tested, invalidated, and unknown. A chart opened from a scan renders the stored bundle.

### 5.5 Trade plans

Purpose: turn one candidate into an owner-approved plan.
Layout: list of plans, then detail with level ranges, buffer note (no buffer is chosen by the software), stop choice, target provenance, risk result, portfolio checks, manual checklist.
Actions: create from candidate, save a version, approve, go to record-order.
States: risk `MANUAL_REVIEW`; missing target; status that cannot be journaled.
Must not: display a quantity the risk module did not return. Must not show `authorises_order` as true.

### 5.6 Portfolio

Purpose: caps and actual exposure.
Data: capital, stage, open positions, pending recorded orders, month fill count, valuation dates.
Layout: cap meters "7 of 10" style, using the two caps independently, then a position table.
Actions: record a fill, record an exit, edit capital.
States: valuation unavailable; stage not set (risk stays manual).
Must not: mark to a live tick. Must not fold simulated positions into the live meters.

### 5.7 Trading journal

Purpose: the story of each actual trade.
Layout: filterable table and a detail page with plan snapshot, order, fills, notes, R when computable.
Actions: edit notes, add a mistake class, attach the chart `as_of`.
States: R blank because the stop or the exit price is missing.
Must not: overwrite the plan snapshot when notes change.

### 5.8 Backtesting

Purpose: configure and read a simulation.
Layout: model form (the engine's required fields), run list, ledger, equity curve.
Actions: start, open manifest, open analytics.
States: refused config with the 422 code; run labelled so it is not performance evidence.
Must not: offer a cap above 10. Must not offer WIT as a trade type that runs.

### 5.9 Strategy analytics

Purpose: statistics for cited manifests.
Layout: sample size and evidence label first, then the figures that exist, then the caution for small samples.
States: walk-forward result without a manifest (TD-4) shown as incomplete; fixture banner if the source is a fixture.
Must not: fill missing months with zero returns.

### 5.10 Shadow / paper

Purpose: a simulated book after the close.
Layout: run assumptions, simulated orders, comparison link to a backtest manifest.
Actions: start a paper run, step it forward on a new session.
Must not: present simulated fills in the live journal typography. The `SIMULATED` label is in the title.

### 5.11 AI research assistant

Purpose: cited explanation.
Layout: question box, scope chips (which scan or journal), answer with citations.
Disabled state: a short explanation that the application works without this screen, and a settings link.
Must not: include a control that sets a gate or a status. Must not answer from a fixture while looking like NSE research.

### 5.12 Data centre

Purpose: see what the files are.
Layout: coverage summary, calendar exceptions, identity findings, corporate-action coverage, ingest inbox, fetch switch.
Actions: ingest inbox, open a quarantine reason, toggle official fetch.
States: any `UNRESOLVED` calendar date listed as unresolved (none since D58); B11-R listed as review pending.
Must not: offer an "adjust prices" action.

### 5.13 Reports

Purpose: export a stored artefact.
Layout: type, source run, format.
Actions: write CSV or HTML, print.
Must not: export a fixture without the fixture label in the document body.

### 5.14 Settings

Purpose: local configuration.
Fields: data directory, backup directory, capital, risk stage, scheduler, fetch, assistant and payload policy, log retention.
Actions: save (audited), backup now.
Must not: collect a broker password. An assistant key, if ever required, uses the platform secret store and is not echoed.

## 6. User journeys

1. Open the platform. The shell starts the API. Overview shows health and the latest dataset, or an empty state that leads to Data Centre.
2. Review market status. Read calendar, completeness, and limitations. Treat unverified universe text as blocking a "full verified scan" claim.
3. Review the daily scanner. Open the latest complete or partial run. Read counts by status.
4. Open a candidate from a row.
5. Inspect charts and zones on Daily, then Weekly, then Monthly. Confirm unknown zones are not styled as fresh.
6. Read MTF and G0–G8 in the inspector. Read the manual checklist.
7. Create a trade plan. Leave quantity empty until a buffer and a risk result exist. Approve the version.
8. Review risk and both caps on the plan and on Portfolio.
9. Place the order in Kite, outside this application.
10. Return and record the order reference, then the fill.
11. Monitor the position. Valuation shows the close date it used.
12. Record the exit. The concurrent slot frees. The monthly count stays.
13. Open the journal and, when a real backtest exists, the analytics screen. Paper results stay on their own screen.

## 7. Fixture policy

Any overview, scan, candle, or bundle payload with `meta.fixture: true` keeps the
full-width `FIXTURE_NOT_MARKET_DATA` banner, uses a non-market symbol such as `EXAMPLE`,
and does not carry a real `dataset_id`. The overview's last scan ignores fixture jobs.
A fixture may be opened only from an explicit fixture control. Sample candles are not
given real NSE symbols. A screenshot of a fixture is not evidence about a listed stock.

## 8. Prompt 4 design acceptance

- Every status in section 3 has a component specimen.
- Overview, scanner, and analysis are laid out with fixture data and the banner.
- Keyboard focus is visible.
- A 1100 px window does not clip the status chip text.
- The chart attribution required by the chosen library is visible on the analysis specimen.
