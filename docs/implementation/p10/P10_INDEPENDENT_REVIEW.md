# P10 Independent Review

**Reviewer:** the repository's `independent-reviewer` agent (read-only; did not write the change). **Date:** 2026-11-17.
**Scope:** P10 changes in `platform/web/` (shell, design system, every redesigned or new screen, tests).
**Baseline limit:** `platform/web/` is untracked in git, so the reviewer could not diff against the pre-P10 screens; findings are defects in the current code, and whether each predates P10 is unknown.

## Findings and disposition

| # | Class | Finding | Disposition |
|---|---|---|---|
| I-1 | Important | Journal "Record close event" sent `Number("")` = 0 for a blank price; backend accepts any finite number, so a ₹0 close could enter the canonical journal | FIXED: close and print require a positive price before any request or dialog; regression test `I-1` |
| I-2 | Important | Backtest blank cost/slippage became 0 and bypassed the owner-supplied-cost check | FIXED: blank is sent as `null`, backend refuses with 422; test `I-2` |
| I-3 | Important | Checklist answers, buffer index, note and reason carried over when switching plans | FIXED: reset when a different plan loads; test `I-3` |
| I-4 | Important | Assistant showed CONNECTED while the API was down; stale answer survived a symbol change | FIXED: badge follows connection; answer cleared on symbol change; test `I-4` |
| I-5 | Important | Settings Save enabled after a failed read, would write nulls over stored risk inputs | FIXED: load error shown, Save disabled; test `I-5` |
| M-1 | Minor | Plans hard-coded `authorises_order` "false", cap fallback 10, missing count shown 0 | FIXED: reads `plan.authorises_order` (true would be flagged as a defect), "unavailable" or a dash for missing |
| M-2 | Minor | Analysis notices closed by default | FIXED: open by default (still collapsible) |
| M-3 | Minor | `useApi` screens did not raise the global fixture banner | FIXED: per-hook fixture reporting. Residual: the banner follows `meta.fixture`; routes that return fixture rows with `meta.fixture: false` (plans, journal, portfolio) rely on their in-page FIXTURE labels |
| M-4 | Minor | Journal entry id not URL-encoded; Jobs said "No job is running" after an overview error; `orders_placed` missing shown as false | FIXED |
| M-5 | Minor | Dialog had no focus trap | FIXED: Tab/Shift+Tab cycle inside the dialog |
| M-6 | Minor | Risk table chose `locked_stop ?? planned_stop` | FIXED: shows both, chooses neither |
| M-7 | Minor | Collapse button changes label and `aria-pressed`; `aria-selected` on plain table rows; `TextInput` ids derived from labels can collide; Journal shows `ABSENT`/`NOT_REVIEWED` defaults for missing fields (pre-existing wording) | OPEN (Minor) |
| M-8 | Minor | One intermittent vitest failure ("navigates to every destination") seen once while the 16-minute `run_all` was running concurrently | Not reproduced: 5 consecutive full runs 104/104; test takes ~1.1 s alone. Recorded as load-related flake, not hidden |
| C-1 | Cosmetic | `.panel` unlayered beat utilities | FIXED: moved to `@layer components`; `!` workaround removed |
| C-2 | Cosmetic | Drawing colour fixed `#6b4c9a` in both themes | OPEN (specification colour) |

## Checked clean by the reviewer

No `dangerouslySetInnerHTML`; attachments render only `image/*` data URLs in `<img>`; localStorage holds only `gtf-theme` and `gtf-sidebar`; no order or broker controls; OD-P2-1 holds (no fetch without a scan); CERTIFIED appears only when `certified_p0_data === true` or `data_quality.certified` (always false on the candle route) plus the Settings specimens; approval blocks unanswered checklist; reject/cancel need a reason; transitions come from the backend; the journal stays canonical.

## Verdict

All Critical (none) and Important (5) findings are fixed and covered by regression tests. Open items are Minor/Cosmetic. **Review: PASS after remediation.** The remediation was verified by the implementer (tests and browser rerun), not re-reviewed by the agent.
