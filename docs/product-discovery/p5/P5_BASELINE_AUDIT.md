# P5-0 Baseline and Architecture Audit - Portfolio and Risk Management

**Date:** 2026-11-16  
**Governance:** `gtf-autonomous-project-lead`  
**Batch:** P5-0 (read-only audit; no source mutation in this batch)  
**HEAD:** `69858d07ccb016b74bc1d518b66b9948656ad6cf`  
**Branch:** `main` (dirty working tree; staged files: none)

---

## 1. Original P5 scope (from master prompt)

Accurate portfolio state from journal/executions; weighted average entry; partial entry/exit accounting; realised/unrealised P&L; independent monthly and open-position caps (D42); ED-3 one-order-per-zone; position risk from executed quantity and stop; EOD valuation (PR-007); exposure/sector reporting; API/UI honesty; concurrency safety; auditability. No broker execution. No P0 certification shortcut.

---

## 2. Verified baseline (facts)

### 2.1 Repository safety

| Item | Observation |
|---|---|
| Working tree | ~266 short-status lines; treat all as owner work |
| `nse/research/store.py` | **Already modified** (+~884/−~65 vs HEAD) - P1 journal executions, IMMEDIATE locks, ED-3, `position_book`, `portfolio_at` |
| `tests/test_research_store.py` | **Already modified** - concurrency, partial prints, ED-3, IST month |
| `platform/` desk, UI, product-flow tests | **Untracked** owner platform work |
| Staged | Empty |
| This batch | Did not stage, commit, push, reset, clean, stash, or revert |

### 2.2 Canonical authority path

```
journal_entries + journal_events + journal_executions + journal_orders
        → position_book / portfolio_at / journal_summary
        → platform desk.portfolio_view (read-only open_readonly)
        → GET /api/v1/portfolio
        → PortfolioPage (WorkflowPages.tsx)
```

Platform SQLite (`gtf_platform/db.py`) has **no** journal, fill, or monthly-counter tables. Caps stay in the research journal (PR-011 architecture satisfied).

### 2.3 Owner / engineering constraints that bind P5

| Authority | Binding content |
|---|---|
| D42 / D46 (`USER_STATED`) | 10 TRIGGERED / IST month; 10 open positions; independent; close frees open only |
| ED-3 | One order per zone; submitted order keeps allowance after cancel/expiry/close |
| D6 | Sector not evaluated - must stay `UNAVAILABLE` / not evaluated (never invent) |
| FR-6.3 / PR-007 | Valuation = last accepted daily close on or before valuation date; else `UNAVAILABLE` |
| FR-6.4 | Position risk from recorded stop + filled quantity; missing stop → `UNAVAILABLE` |
| FR-6.7 | Sector concentration `UNAVAILABLE` until a sector source exists |
| D10 / D17 | No broker; `authorises_order` remains false |

---

## 3. Requirement → implementation map

| Req | Status | Evidence | Gap |
|---|---|---|---|
| P5.1 Canonical portfolio state | **IMPLEMENTED** + **UNIT/INTEGRATION_TESTED** (library) | `position_book`, `portfolio_at`; product-flow plan→fill→close | API/UI omit rich position fields |
| P5.2 Weighted average entry | **IMPLEMENTED** + **UNIT_TESTED** | `position_book` WAP; `test_partial_prints_*` | Fees kept separate (`journal_charges`); entry WAP excludes fees - correct |
| P5.3 Partial exits / remaining qty | **IMPLEMENTED** + **UNIT_TESTED** | `journal_execution` EXIT; reject overfill; duplicate `print_key` | - |
| P5.4 D42 monthly cap | **IMPLEMENTED** + **CONCURRENCY_TESTED** | `_refuse_new_trigger`; `test_two_connections_cannot_both_commit_the_tenth_trigger`; IST tests | Add explicit “10 present → both 11th refuse” companion |
| P5.5 Open-position cap | **IMPLEMENTED** + **CONCURRENCY_TESTED** | `_peak_open_from`; `test_two_connections_cannot_both_take_the_last_open_slot` | - |
| P5.6 ED-3 | **IMPLEMENTED** + **CONCURRENCY_TESTED** | `_zone_allowance`; `test_two_connections_cannot_both_reserve_one_zone` | Keep separate from D42 |
| P5.7 Position-level risk | **NOT_IMPLEMENTED** on portfolio path | `risk.plan_trade` is pre-trade sizing only | Remaining-qty × (avg_entry − stop) on portfolio reads |
| P5.8 Stop/target tracking | **PARTIAL** | Planned levels on `journal_entries`; locked stop in events; UI does not show them on Portfolio | Surface planned vs actual on API/UI |
| P5.9 PR-007 EOD valuation | **NOT_IMPLEMENTED** | `portfolio_view` hard-codes `valuation_state=UNAVAILABLE` | Implement last accepted close ≤ valuation date |
| P5.10 Sector / exposure | Sector **correctly UNAVAILABLE** (D6). Exposure **NOT_IMPLEMENTED** | Honest nulls today | Market-value exposure after PR-007; sector stays unavailable |
| P5.11 Limits visibility | **PARTIAL** | Caps shown; risk/valuation thin | Enrich; never show unavailable as zero |
| P5.12 Portfolio API | **PARTIAL** | Caps + zones + UNAVAILABLE labels; `authorises_order=false` | Valuation dates, avg entry, P&L, risk, refusals |
| P5.13 Portfolio UI | **PARTIAL** | Distinct monthly vs open; UNAVAILABLE labels | Position detail, P&L, risk, EOD date |
| P5.14 Auditability | **IMPLEMENTED** (library) | Append-only executions/events; idempotency keys | Corrections stay append-only |

### Status legend (not interchangeable)

IMPLEMENTED · UNIT_TESTED · INTEGRATION_TESTED · CONCURRENCY_TESTED · INDEPENDENTLY_REVIEWED · ACCEPTED · BLOCKED · NOT_IMPLEMENTED

---

## 4. Existing capabilities retained (do not rewrite)

- `BEGIN IMMEDIATE` journal writers and busy_timeout
- `position_book` print vs legacy full-fill semantics
- Monthly vs open independence (close frees open only)
- ED-3 submission lifecycle
- Platform desk as read-through of `portfolio_at`
- Sector / live drawdown remaining `UNAVAILABLE`
- `authorises_order=false` on portfolio/journal envelopes

---

## 5. Genuine gaps (implementation focus)

1. **PR-007 valuation** - last accepted EOD close on/before valuation date; expose `price_date`; never invent; future closes excluded.
2. **Position risk on portfolio path** - remaining quantity × valid stop geometry; else `UNAVAILABLE`.
3. **API/UI completeness** - average entry, planned vs executed, realised/unrealised, capacity remaining, refusal text.
4. **Market-value exposure** - after valuation works; sector stays `UNAVAILABLE` (D6).
5. **Concurrency companion test** - with 10 TRIGGERED already present, concurrent 11th attempts both refuse.
6. **PR-011 / PR-012 regression tests** - assert no platform counter tables; portfolio counts match store; refusals preserved.

### Unresolved / owner-gated (do not invent)

| Topic | Record |
|---|---|
| Max staleness for EOD marks | FR-6.3 requires printing the actual close date; no approved “too stale → refuse” window. Show date; do not invent a cutoff. |
| Sector classification source | D6 / FR-6.7 - keep `UNAVAILABLE`. |
| Live quotes | EX-007 blocked; not in P5. |
| Stale-data certification labels | Valuation must not claim P0 certified; use fixture / exploratory labels already used by candles. |

---

## 6. Batch plan

| Batch | Focus | Likely change surface |
|---|---|---|
| **P5-1** | 11th-trigger concurrency companion; PR-007 EOD valuation; PR-011 single-counter invariants; PR-012 refusal honesty; sector/drawdown stay UNAVAILABLE | `platform/gtf_platform/integration/valuation.py` (new), `desk.py`, `store.portfolio_at` enrich (additive), `tests/test_research_store.py`, `platform/tests/*`, Portfolio UI labels |
| **P5-2** | Confirm WAP / partials / P&L; enrich API fields; planned vs actual | `store.py` (additive fields), desk, tests - **no rewrite of print accounting** |
| **P5-3** | Position remaining risk; stop/target on portfolio; concurrent seat/zone already present - add missing risk tests | `desk.py` / small risk helper, tests |
| **P5-4** | Portfolio market-value exposure; sector stays UNAVAILABLE; data-quality warnings | desk, tests, UI |
| **P5-5** | Portfolio API contract completeness; UI completeness; journal integration polish | `WorkflowPages.tsx`, routes if needed, UI tests |
| **P5-6** | Transaction failure / restart; full `run_all` + platform + frontend; independent review; final report | docs only + test evidence |

---

## 7. Risks and dependencies

| Risk | Mitigation |
|---|---|
| Overwriting dirty `store.py` / platform untracked files | Extend only; inspect before each edit; no revert/stash |
| Valuation coupling store ↔ market data | Keep close lookup in platform integration; store stays journal-authoritative for quantities |
| Claiming certified marks | Label fixture / exploratory; never CERTIFIED_P0 |
| Weakening D42/ED-3 tests | Additive tests only |
| P0/D66 | Out of scope; do not touch certification outputs |

---

## 8. Decision classification (council)

| Item | Level | Action |
|---|---|---|
| Keep D42/ED-3/D6/FR-6.x | A / USER_STATED | Preserve |
| EOD valuation helper placement (platform integration) | C | AUTO_APPROVED engineering |
| Stale close still usable with printed date | C under FR-6.3 | Implement; no max-age invention |
| Sector scoring | A (D6) | Leave UNAVAILABLE |

---

## 9. P5-0 verdict

**P5 is not complete.** Core journal portfolio accounting and cap concurrency are largely present in the dirty tree and must be retained. Product completeness is blocked primarily by **PR-007 valuation**, **position-risk visibility**, and **API/UI enrichment**. Sector exposure is intentionally unavailable.

**Next executable batch:** P5-1.
