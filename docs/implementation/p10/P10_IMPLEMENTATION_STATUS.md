# P10 Implementation Status

Statuses per P10 section 20. `VALIDATED` = browser-validated on FIXTURE data in both themes (`P10_BROWSER_VALIDATION.md`). `INDEPENDENT_REVIEWED` is set only after `P10_INDEPENDENT_REVIEW.md` passes. `ACCEPTED` is the owner's.

| Batch | Scope | Status | Evidence |
|---|---|---|---|
| P10-0 | Baseline audit, inventory, API matrix, plan | IMPLEMENTED (docs) | `P10_BASELINE_AUDIT.md`, `P10_SCREEN_INVENTORY.md`, `P10_API_TO_SCREEN_MATRIX.md`, `P10_IMPLEMENTATION_PLAN.md` |
| P10-1 | IA, shell, navigation, search, theme switch | VALIDATED | `p10.test.tsx` (IA, theme), `app.test.tsx`; browser G |
| P10-2 | Tokens, components, formatting, pre-paint theme, chart theming | VALIDATED | `P10_DESIGN_SYSTEM.md`; Settings specimens; `p10.test.tsx` formatting |
| P10-3 | Market Overview: KPI strip, recent plans/journal, regrouped sections | VALIDATED | `overview.test.tsx` (7); shots `*-overview` |
| P10-4 | Stock Analysis: header (identity, close at as-of, provenance), toolbar, notices, gate table, zones, plan overlay, scan chooser (OD-P2-1) | VALIDATED | evidence/zones/plans tests; shots `*-analysis-*`, journey A |
| P10-5 | Scanner restyle; Scan History page | VALIDATED | `scanner.test.tsx` (7); shots `*-scanner`, `*-history` |
| P10-6 | Trade Plans: table, detail, combinations, lifecycle, actions from `allowed_transitions`, approval confirmation | VALIDATED | `plans-navigation.test.tsx`, `p10.test.tsx`; journey C |
| P10-7 | Portfolio table and cap meters; Risk Overview | VALIDATED | `portfolio.test.tsx` (10), `p10.test.tsx` risk; journey D |
| P10-8 | Journal: table, readable detail, grouped forms, confirmations, attachment preview | VALIDATED (attachment preview TESTED by type check only) | `journal.test.tsx` (4); shots `*-journal` |
| P10-9 | Backtesting form/result, Research Reports (8 files), AI Assistant (deterministic explain), Analytics and Paper capability pages | VALIDATED | `p10.test.tsx`; shots |
| P10-10 | Data Health, Jobs and Monitoring, Settings sections | VALIDATED | `p10.test.tsx`; shots |
| P10-11 | Integration journeys A-G, responsive, accessibility audit | VALIDATED | `P10_BROWSER_VALIDATION.md`, `P10_ACCESSIBILITY_REVIEW.md` |

Not implemented (no backend; shown honestly): job list, global activity feed, backtest run history and analytics, language-model assistant, paper book, live quotes, sector and index data. Owner-deferred items unchanged: OD-P2-1, P2-SMA-CHART, automatic plan expiry, TJ-012, AI-002.

## Defects found and fixed during P10

1. Global CSS resets were unlayered and overrode every button text colour (unreadable primary/selected buttons in light theme).
2. Always-mounted benchmark host caused horizontal scroll on phones.
3. Main content scrolled inside a fixed viewport (cut-off printing/captures).
4. Candidate zone id read only from `zone_id`, so plan drafting from Analysis was hidden when the id is in `zone.zone_id`.
5. Long status codes forced page overflow at 390 px.
6. Approved plans offered Submit/Approve/Reject that the backend refuses.
7. Placeholder text contrast below 4.5:1.
