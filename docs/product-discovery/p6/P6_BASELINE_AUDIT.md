# P6-0 Baseline and Architecture Audit - Trading Journal and Performance Reporting

**Date:** 2026-11-17  
**Governance:** `gtf-autonomous-project-lead`  
**Batch:** P6-0 (read-only audit; no source mutation in this batch)  
**HEAD:** `69858d07ccb016b74bc1d518b66b9948656ad6cf`  
**Branch:** `main` (dirty working tree; staged files: none)

---

## 1. Original P6 scope (reconciled)

**GTF P6** maps to Prompt 08 (journal narrative and exports), not Product Prompt 06.

Canonical objectives (master skill + roadmap + FR-7 / TJ-* / UX-008):

1. Trade lifecycle recording (plan → submission → fills → exit).
2. Partial fills and actual execution records.
3. Charges without inventing missing costs (B12).
4. Notes, screenshots, review observations.
5. Mistake / rule-adherence classification (Rulebook Part 7 Ch 5).
6. Search and filter over stored journal rows.
7. Planned versus actual comparison.
8. Descriptive performance breakdowns (not certified strategy performance).
9. Exports with provenance.
10. UI completion over the existing Journal page.

**Out of scope for this phase (explicit):**

| Item | Authority | Treatment |
|---|---|---|
| TJ-012 / paper book | FR-7.8, AR-7; gap register | Remain `NOT_IMPLEMENTED`; stay in `NOT_IMPLEMENTED` meta (`paper`) |
| Broker / order placement | D10, D17 | `authorises_order=false`; no client |
| R4 / certified expectancy | FR-9, P7 | Journal metrics stay `JOURNAL_DESCRIPTIVE` |
| B12 owner tariff | Remaining blockers | Do not invent a schedule |
| TJ-008 dedicated missed-trade type | Gap register (recommendation; FR-7 schema undefined) | Deferred; not a P6 blocker |
| Full P10 visual redesign | Roadmap | Targeted journal UX only |

---

## 2. Repository safety preflight

| Item | Observation |
|---|---|
| Root | `/Users/yash/day-trader-skill` |
| Branch | `main` |
| HEAD | `69858d07ccb016b74bc1d518b66b9948656ad6cf` |
| Staged | none |
| Working tree | ~267 short-status lines; treat all as owner work |
| P6 docs dir | did not exist before this audit |
| P5 closure | `ACCEPTANCE_READY` (owner ACCEPTED separate) |
| P1 closure | `ACCEPTANCE_READY` (2026-11-17) |
| This batch | Did not stage, commit, push, reset, clean, stash, or revert |

### Test baseline (executed 2026-11-17)

| Suite | Result |
|---|---|
| `PYTHONPATH=.:tests python3 -m unittest tests.test_research_store -q` | **81 PASS** |
| `PYTHONPATH=platform:. python3 -m unittest discover -s platform/tests -p 'test_product_flow.py' -q` | **27 PASS** |
| `PYTHONPATH=platform:. python3 -m unittest discover -s platform/tests -p 'test_portfolio_p5.py' -q` | **17 PASS** |
| Dedicated Journal vitest | **absent** (Portfolio has `portfolio.test.tsx`) |

---

## 3. Canonical authority path (must preserve)

```
nse/research/store.py
  journal_entries + journal_events + journal_orders
  + journal_executions + journal_charges + journal_idempotency
        → position_book / portfolio_at / journal_summary
        → platform desk.journal_rows / record_* / planned_versus_actual
        → GET/POST /api/v1/journal*
        → JournalPage (WorkflowPages.tsx)
```

Platform SQLite has **no** journal ledger and **no** monthly counter (PR-011).  
`paper` remains listed in `NOT_IMPLEMENTED` (`platform/gtf_platform/app.py`).

P5 accounting (WAP, partial fills, D42, ED-3, EOD STALE) is authoritative. P6 must not create a second book.

---

## 4. Lifecycle state model (as implemented)

### 4.1 Entry lifecycle (derived from events)

| State | How reached | Allowed next kinds (`ALLOWED`) |
|---|---|---|
| `PLANNED` | `journal_add` inserts entry + first `PLANNED` event | PLANNED, TRIGGERED, CANCELLED, EXPIRED, ZONE_INVALIDATED, NOTE |
| `OPEN` | first `TRIGGERED` (via `journal_event` or first ENTRY print) | STOP_LOSS_HIT, TARGET_HIT, CLOSED_MANUAL, ZONE_INVALIDATED, NOTE |
| `CLOSED` | any exit kind | NOTE only |
| `CANCELLED` | CANCELLED while planned | NOTE only |
| `EXPIRED` | EXPIRED while planned | NOTE only |

### 4.2 Execution prints (v4)

- `journal_executions`: append-only ENTRY/EXIT prints keyed by `print_key`.
- First ENTRY print creates the single `TRIGGERED` trade (RB 2140: no second TRIGGERED).
- Multiple ENTRY prints accumulate toward planned quantity; overfill refused.
- EXIT prints reduce open quantity; `position_book` computes WAP and realised PnL.
- Legacy path: bare `TRIGGERED` event without prints still means full planned quantity.

### 4.3 Mutable vs immutable

| Kind | Mutability |
|---|---|
| `journal_entries` planned levels, quantity, checklist, alert_note | **Immutable** (append-only table) |
| `journal_events` / `journal_orders` / `journal_executions` / `journal_charges` | **Immutable** (append-only + one-row order guard) |
| Idempotency replay | Returns prior result; does not rewrite history |
| Review notes / classifications / attachments | **Missing product tables**; must be append-only when added |
| Plan row in platform DB | Separate lifecycle; P4-IR-04 cancel desync remains documented |

---

## 5. Requirement evidence matrix

Status legend (not interchangeable):  
`NOT_STARTED` · `IMPLEMENTED` · `UNIT_TESTED` · `INTEGRATION_TESTED` · `FAILURE_TESTED` · `INDEPENDENTLY_REVIEWED` · `ACCEPTANCE_READY` · `ACCEPTED` · `BLOCKED` · `NOT_IMPLEMENTED`

| Requirement | Existing implementation | Tests | Gap | Planned batch | Status |
|---|---|---|---|---|---|
| TJ-001 Plan snapshot (FR-7.1) | `journal_entries` stores symbol, zone, levels, checklist, planned prices | store + product-flow approve | Rich trade-detail UI still thin | P6-8 | `INTEGRATION_TESTED` (library+API); UI partial |
| TJ-002 Order record (FR-7.2 / EX-001) | `journal_orders`; desk `submit_order` | store + product-flow | UI records submission | P6-8 polish | `INTEGRATION_TESTED` |
| TJ-003 Entry record / fills (FR-7.3 / EX-003) | `journal_executions` + TRIGGERED | store partial prints; product-flow | UI entry print only; no EXIT print control | P6-1 / P6-8 | `UNIT_TESTED` / `INTEGRATION_TESTED` |
| TJ-004 Exit record (EX-009) | Exit event kinds + EXIT prints | store + product-flow close | Prefer EXIT prints over bare close when quantity partial | P6-1 | `UNIT_TESTED` |
| TJ-005 Screenshots | none (alert_note text only) | none | Attachment store + API + UI | P6-2 | `NOT_IMPLEMENTED` |
| TJ-006 Mistake / rule adherence | free-text `note` / `alert_note` only | none for taxonomy | Controlled taxonomy + append-only classifications | P6-3 | `NOT_IMPLEMENTED` (structured) |
| TJ-007 Behavioural notes | NOTE events + alert_note | limited | Typed review notes + chronology UI | P6-2 | `IMPLEMENTED` partial |
| TJ-008 Missed / rejected opportunity | scan history only | n/a | Dedicated type undefined in FR-7 | Deferred | `NOT_IMPLEMENTED` (deferred) |
| TJ-009 Post-trade review | none as workflow | none | review_status + history | P6-2 / P6-3 | `NOT_IMPLEMENTED` |
| TJ-010 Search / filter (FR-7.6) | `GET /journal` returns all rows | none for filters | Server-side filters + UI | P6-4 | `NOT_IMPLEMENTED` |
| TJ-011 Audit history | append-only research tables; platform audit for other objects | store append-only | Ensure review/attachment writes are audited | P6-2 | `IMPLEMENTED` partial |
| TJ-012 Paper separated | `paper` in `NOT_IMPLEMENTED` | meta tests | Keep unimplemented | none | `NOT_IMPLEMENTED` (correct) |
| Partial fills / WAP / remaining qty | `position_book` (P5) | store + portfolio | Journal UI already shows book fields | P6-1 reuse | `UNIT_TESTED` / `INTEGRATION_TESTED` |
| Charges honesty (B12) | `journal_charges`, ABSENT/ACTUAL/ESTIMATED/MIXED; `charges.py` | store charge tests | Charge entry UI; export completeness | P6-6 / P6-7 | `UNIT_TESTED`; UI missing |
| Planned vs actual | `desk.planned_versus_actual` on plan preview | trade_planning | Journal detail endpoint + richer deltas | P6-5 | `IMPLEMENTED` partial |
| Performance by setup | `journal_summary` month arithmetic; no setup breakdown for journal | store summary | Descriptive journal metrics + trade_type / review dims | P6-6 | `IMPLEMENTED` partial (CLI month only) |
| Journal export | Scan report export only | product-flow scan CSV | Period/filtered journal CSV/JSON | P6-7 | `NOT_IMPLEMENTED` |
| UX-008 Journal screen | JournalPage: list, order, ENTRY print, close | no dedicated vitest | Detail, search, review, export, charges, EXIT | P6-8 | `IMPLEMENTED` partial |
| FR-7.5 P&L / R | summary + position_book; blank when incomplete | store | Surface completeness labels in UI/export | P6-6 | `UNIT_TESTED` |
| FR-7.7 Manual entry still capped | `journal_add` / trigger refuse | store | Preserve | P6-1 | `UNIT_TESTED` |
| Idempotency / duplicate fills | `journal_idempotency`, print_key, charge_key | store + restart product-flow | Keep; add journal filter failure cases | P6-1 / P6-9 | `FAILURE_TESTED` partial |
| authorises_order=false | desk + routes | security + portfolio | Preserve everywhere | all | `INTEGRATION_TESTED` |

---

## 6. What already works (reuse)

1. Append-only research journal schema v1–v4.
2. Lifecycle transitions and refusals (`JournalRefused`).
3. Partial ENTRY/EXIT prints, WAP, remaining quantity (P5).
4. Cap / ED-3 concurrency protections (P5).
5. Charge components and schedule quoting without built-in tariffs.
6. `journal_summary` gross vs net honesty when charges incomplete.
7. Platform journal write routes (order, event, execution, charges).
8. Plan → journal approval path (P4) and portfolio reads (P5).
9. `planned_versus_actual` read model (plan preview).
10. Backup/restore preserves journal records (P1).

---

## 7. What is incomplete

1. Journal list has no search/filter/pagination.
2. No trade detail view with timeline, comparison, review sections.
3. No EXIT print UI (close uses bare `CLOSED_MANUAL` event).
4. Charge recording API unused by Journal UI.
5. Planned-versus-actual not on journal detail.
6. Notes are unstructured; no review status.
7. No performance summary screen backed by journal (Reports page is scan export).
8. No journal-period export.
9. No dedicated Journal frontend tests.

---

## 8. What is missing entirely

1. Screenshot / evidence attachment storage and serving.
2. Controlled mistake taxonomy (RB 3746–3758 classes).
3. Server-side journal query API.
4. Journal performance breakdown API (by trade_type / classification / month).
5. Metric-definition document for journal-descriptive figures.
6. Export schema for journal rows.

---

## 9. Schema change assessment

| Need | Schema change? | Approach |
|---|---|---|
| Search/filter | No | Filter in `desk.journal_rows` / new query helper over existing columns + derived state |
| Planned vs actual on journal | No | Reuse `planned_versus_actual` |
| Performance summary | No for trade_type/month; optional for classification after taxonomy | Wrap `journal_summary` + group-bys |
| Export | No | Read model → CSV/JSON |
| Typed notes / review status / taxonomy | **Yes (additive)** | Append-only `journal_reviews` (or review events) with controlled codes |
| Screenshots | **Yes (additive)** | Append-only `journal_attachments` metadata in research DB + files under app data dir (not embedded blobs) |
| Paper book | No (out of scope) | Leave unimplemented |
| Setup class | Prefer derive `trade_type` + candidate_levels pattern/core; optional owner `setup_label` on review row | Avoid mutating `journal_entries` |

Migration rules: additive only; preserve append-only triggers; test fresh DB + migrate existing; no owner-data mutation beyond schema apply.

---

## 10. Dependencies

| Phase | Dependency on P6 |
|---|---|
| P1 | Session, backup/restore, idempotent retries must remain intact |
| P4 | Plan approval creates journal rows; planned snapshot is plan-time; do not silently “fix” P4-IR-04 cancel desync without audit |
| P5 | Portfolio accounting and caps are inputs; do not fork |
| P0 | Parallel; no certification claims from journal stats |
| B12 | Charges stay ABSENT until owner enters lines or dated schedule |

---

## 11. Genuine owner decisions (do not invent)

1. **B12** dated broker tariff file (optional for estimated charges).
2. **TJ-012** whether/when to build a paper book (explicitly deferred).
3. **TJ-008** whether a dedicated missed-trade journal type is required.
4. Optional maximum age for STALE portfolio marks (P5 leftover; not P6).
5. Final **ACCEPTED** stamp for P6 (owner only).

Engineering may define a **controlled review taxonomy** aligned to RB 3746–3758 without inventing trading rules (Level C).

---

## 12. Proposed batch order (adjusted)

| Batch | Focus |
|---|---|
| P6-0 | This audit + acceptance matrix |
| P6-1 | Lifecycle/execution integrity checks + EXIT path honesty in API/UI wiring |
| P6-2 | Notes, review history, attachments |
| P6-3 | Mistake taxonomy (RB-aligned) |
| P6-4 | Search / filter / pagination |
| P6-5 | Planned-versus-actual journal detail |
| P6-6 | Charges completeness + descriptive performance |
| P6-7 | Exports |
| P6-8 | Journal UI completion + dedicated tests |
| P6-9 | End-to-end journeys A–G |
| P6-10 | Independent review + closure |

---

## 13. P6-0 exit condition checklist

| # | Question | Answer |
|---|---|---|
| 1 | What already works? | Section 6 |
| 2 | What is incomplete? | Section 7 |
| 3 | What is missing entirely? | Section 8 |
| 4 | What should be reused? | Store v4, desk routes, P5 book, plan comparison |
| 5 | What needs schema change? | Reviews + attachments (additive) |
| 6 | What needs no schema change? | Search, export, performance wrap, comparison surface |
| 7 | Dependencies? | Section 10 |
| 8 | Owner decisions? | Section 11 |

**P6-0 complete.** Implementation begins only after this document and `P6_ACCEPTANCE_MATRIX.md` exist.
