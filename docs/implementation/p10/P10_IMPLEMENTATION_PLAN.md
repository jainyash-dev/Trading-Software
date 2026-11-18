# P10 Implementation Plan

Scope: `platform/web/src` and `index.html`, plus P10 documentation. No backend, store, contract, Rulebook or P0 change. No new npm dependency.

| Batch | Plan |
|---|---|
| P10-1 | Five navigation groups (Overview, Research, Trading, Intelligence, System). Route ids kept for deep-link compatibility; new ids `history`, `risk`, `jobs`. Each route carries a capability status (`LIVE`, `PARTIAL`, `NOT_IMPLEMENTED`). Full-height sidebar with icons, breadcrumb page header, data-context strip, theme switch, safety line. |
| P10-2 | Token set for both themes (surfaces, text tiers, accent, positive/negative/warning/info, focus); restyled shared components; new `Panel`, `Metric`, `Meter`, `ProvenanceBadge`, `Callout`, `Notices`, `KeyValue`, `Segmented`, `CapabilityPage`. No-flash theme script in `index.html`. |
| P10-3 | Overview: KPI strip (data, scan, caps, health) using `/portfolio`; recent plans and journal activity. |
| P10-4 | Stock Analysis: stock header with last EOD close and date, segmented timeframe control, grouped notices, gate table, structured inspector. OD-P2-1 respected: no standalone chart. |
| P10-5 | Scanner restyle through shared components; new Scan History page with paging. |
| P10-6 | Trade Plans: plan table, structured detail, combinations table, checklist grid, action bar. Same API calls and validation. |
| P10-7 | Portfolio: cap meters, positions table. New Risk Overview (portfolio + settings). |
| P10-8 | Journal: list table, readable detail (executions, events, notes, attachments, planned versus actual), grouped record forms. |
| P10-9 | Backtesting form card; Strategy Analytics capability page; AI Assistant connected to deterministic explain; Paper capability page. |
| P10-10 | Data Health from health/datasets/universe/calendar; Jobs and Monitoring; Settings sections incl. appearance and status-vocabulary specimens. |
| P10-11 | vitest, build, browser run with fixture env (both themes, every route), docs. |

Test policy: existing assertions keep their meaning. Where a page title is renamed by the IA, the expected title string is updated, never removed.
