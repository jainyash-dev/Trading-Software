# P10-0 Baseline Audit

**Date:** 2026-11-17 | **Branch / HEAD:** `main` / `69858d07ccb016b74bc1d518b66b9948656ad6cf` (verified live)
**Working tree:** 269 modified/untracked paths before P10, all treated as owner work. P10-0 was read-only.

## 1. Frontend architecture (facts from `platform/web`)

| Item | Finding |
|---|---|
| Framework | React 19.2, TypeScript 5.9 (`strict`, `noUnused*`), Vite 7.2 |
| Styling | Tailwind CSS 4 (`@tailwindcss/vite`), CSS variables in `src/styles/global.css`, mapped through `@theme inline` |
| Ant Design | **Not present.** The P10 prompt assumes it; nothing to integrate. No component library is used. |
| Routing | Hand-written hash router: `src/navigation/routes.ts` (`ROUTES`, `parseHash`) and `src/navigation/query.ts` (allow-listed query tokens). Deep links and back/forward work through `hashchange`. |
| Navigation | `src/layout/Shell.tsx`: 15 routes in three groups (Work, Research, System); `Later` tag on 3 unavailable routes; compact mode below 1100 px |
| State | One React context (`src/state/store.tsx`): theme, sidebar, connection, health, route, toast, fixture toggles, `request()` |
| API client | `src/services/api.ts`: envelope validation (`gtf-platform/1`), `X-GTF-Request` header, one bootstrap retry on 401, fixture-label check |
| Auth boundary | HttpOnly cookie session (D57); `connection` state `loading/connected/disconnected/unauthenticated/unavailable` |
| Theme | Dark and light token sets exist; preference persisted in `localStorage` (`gtf-theme`). **No UI control switches the theme**, and the theme is applied only after React mounts (a flash is possible). |
| Charts | `lightweight-charts` 5 (`src/chart/CandleChart.tsx`): candles, volume, engine zones, plan price lines, drawings, zoom/pan/crosshair |
| Tables | `DataTable` in `src/design/components.tsx` (sort by field, keyboard row cursor); several pages use ad-hoc tables or paragraphs instead |
| Shared components | `Page`, `StatusBadge`, `EmptyState`, `Skeleton`, `TextInput`, `SelectInput`, `Switch`, `Dialog`, `Button`; `features/shared/ui.tsx`: `Section`, `Fact`, `FactGrid`, `Warning`, `ErrorLine`, `JobState`, `Completeness` |
| Status vocabulary | `src/design/status.ts`: candidate, gate, symbol and limitation codes; unknown codes render `Unknown status: <code>` |

## 2. Baseline validation (before any P10 change)

| Command | Result |
|---|---|
| `npx vitest run` (platform/web) | 16 files, **89/89 pass** |
| `npm run build` | pass (`tsc --noEmit` + vite); 561 kB JS chunk warning |

## 3. Visual and UX defects observed (P2-P4 browser evidence and source)

1. Header crowds title, disclaimer, data dates, search, status and clock into one wrapping row; there is no page hierarchy.
2. Sidebar background stops at content height (visible in `p2-p4-browser/02`, `10`).
3. Stock Analysis stacks six or more full-width warning banners above the chart; gate results are run-on paragraphs.
4. Trade Plans lists plans as one-line buttons; plan detail, combinations and checklist are unstructured text.
5. Journal renders events, executions, notes and attachments as raw `JSON.stringify` output; 15 action controls sit in a single column.
6. Portfolio positions are paragraphs, not a table; caps are not visualised.
7. Backtesting and Strategy Analytics render the same form; analytics has no backend.
8. Data Centre, Assistant and Paper are static placeholders; Data Centre ignores real health/dataset/universe/calendar APIs.
9. No theme switch; the light theme is never reachable from the UI.
10. Numbers are not right-aligned; currency and units are not formatted.

## 4. Classification summary

| Class | Items |
|---|---|
| Existing and working | Overview, Scanner (run, poll, cancel, history, symbol evidence), Opportunities, Watchlists, Stock Analysis chart (stored scan only), Trade Plans lifecycle, Portfolio, Journal (all write actions), Reports export, Settings, backup / restore check |
| Existing but incomplete | Backtesting UI (form only, no run list), Data Centre (static), theme (no switch), Reports (one file type) |
| Missing frontend (backend exists) | Data Health from `/health`, `/datasets`, `/universe`, `/calendar`; Jobs view from `/overview` job fields and `/jobs/{id}`; deterministic explain screen from `/symbols/{s}/explain`; Risk Overview from `/portfolio` + `/settings`; Scan History page from `/scans` paging |
| Missing backend | Job list, global activity feed (audit needs `object_id`), backtest run list and manifests, strategy analytics, language-model assistant, live quotes, sector data, index/breadth series |
| Blocked by external dependency | TradingView references (TV-1), sector source (D6), tariff schedule (B12), live alerts |
| Blocked by P0 certification | Any `CERTIFIED` label: `certified_p0_data` is false and the candle route always returns `certified: false` |
| Owner-deferred | OD-P2-1 standalone chart, P2-SMA-CHART, automatic plan expiry (P4-EXPIRED), TJ-012 paper book, TJ-008, AI-002 provider (OQ-2) |

## 5. Assumptions

- The P10 prompt's "Ant Design" and "P9 assistant" references do not match this repository. No Ant Design dependency is added (no new dependency is needed). No `P9` record exists; the assistant status is taken from AI-001..AI-004 in `docs/product-discovery/02_MASTER_CAPABILITY_MAP.md`.
- P10 changes only `platform/web` and documentation. No backend route, store or contract is changed.
