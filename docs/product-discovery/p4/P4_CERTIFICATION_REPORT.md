# GTF P4 certification report

**Date:** 2026-11-15  
**Phase:** GTF P4 - Trade Planning (maps to Product Prompt 07 / TP-001…TP-012; not Product Prompt 04)  
**Overall status:** **P4_COMPLETE_WITH_LIMITATIONS**

This is not P0 data certification, P7 strategy validation, or production readiness (P11). No orders are authorised. No historical performance is claimed.

## 1. Executive summary

P4 delivers a functional, auditable trade-planning workflow on top of the existing P1 desk and research journal. Plans are created from stored scanner candidates, reviewed with checklist and buffer selection, sized through `risk.plan_trade`, checked against advisory portfolio constraints, and approved into the journal without placing orders. Caps and ED-3 remain journal-authoritative. Canonical eligibility is never recalculated in the platform planning package.

### Implemented

- Migration `005_trade_plan_lifecycle` (columns, events, notes)
- Plan list / draft create / submit / reject / cancel / reopen / rationale / notes / history
- Preview enrichment: geometry, combinations, portfolio_checks, capacity, risk inputs, manual-exec prep
- Approve path preserved: checklist + `journal_add` + `authorises_order: false`
- Planned-versus-actual comparison after journal linkage
- Source-quality labelling with CERTIFIED demoted while P0 incomplete
- Plans UI overview, filters, disclosures, lifecycle actions
- Tests + architecture/repository gates green

### Limitations

1. P0 incomplete: no CERTIFIED planning inputs; exploratory/fixture only.
2. P7 incomplete: no performance-based sizing or success-rate claims.
3. Platform plan state can remain `APPROVED` after a journal-side cancel (P4-IR-04); zone allowance still follows ED-3 in the journal.
4. `EXPIRED` plan state is modeled but not auto-produced (deferred).
5. Full local_data `run_all` and visual screenshot matrix not run.
6. Sector / valuation / drawdown remain UNAVAILABLE (pre-existing).

## 2. Batch report

| Batch | Status | Key outcomes |
|---|---|---|
| 0 | COMPLETE | Reuse map; gaps vs TP-001…012 |
| 1 | COMPLETE | Contract + migration 005; immutable candidate_status |
| 2 | COMPLETE | Create / submit / reject / reopen / cancel / notes |
| 3 | COMPLETE | Geometry from stored candidate; tested overlay BLOCKED |
| 4 | COMPLETE | Transparent sizing via risk.plan_trade; no invented RPT |
| 5 | COMPLETE | portfolio_checks + capacity on preview; hard caps in journal |
| 6 | COMPLETE | Lifecycle + manual execution preparation disclosure |
| 7 | COMPLETE | Planned vs actual; approve cancel refuse when entry exists |
| 8 | COMPLETE | Plans overview UI + filters + warnings |
| 9 | COMPLETE | Platform 58 / web 48 / architecture / repository PASS |
| 10 | COMPLETE | Independent + quant review; remediations closed |

## 3. Dependency report

- **INDEPENDENT completed:** P4-R01…R07
- **INTERFACE_DEPENDENT completed:** P4-R08…R16
- **P0_BLOCKED deferred:** P4-R17, P4-R18
- **P7_BLOCKED deferred:** P4-R19, P4-R20
- **Disallowed preserved:** P4-R21 (`authorises_order` false)

## 4. Architecture and governance

| Concern | Result |
|---|---|
| Canonical eligibility | Stored candidate only; no qualification import in planning package |
| Geometry | Printed entry/stop ranges + G7 proximal; never invented |
| Risk / sizing | `risk.plan_trade`; owner capital/`rpt_pct` required |
| Caps / ED-3 | Journal authority unchanged (P1); preview advisory |
| Manual execution | Explicit disclosure; no broker path |
| Data quality | FIXTURE / EXPLORATORY / UNKNOWN; CERTIFIED demoted |

## 5. Evidence highlights

- Risk calculations: combinations expose entry, stop, target, risk_per_share, loss_if_stopped, quantity, R:R.
- Position / monthly caps: preview `portfolio_checks` + capacity; hard refuse on TRIGGERED / first ENTRY (P1 tests retained).
- ED-3: platform cancel of approved+journalled plan returns 409; journal owns release rules.
- Journal / fills: planned-versus-actual uses owner-recorded prints only.

## 6. Independent review

See `P4_REVIEW_REGISTER.md`.

Critical/High unresolved: **none** after remediation.  
Medium: IR-01/02/03/05 fixed; IR-04 accepted limitation.  
Quant: accept.

## 7. Validation report

Exact commands in `P4_TEST_REPORT.md`.

- Platform unittest: **58 passed**
- P4-focused: **6 passed**
- Web vitest: **48 passed**
- Web build: **PASS**
- Architecture + repository (`--no-data`): **PASS**

## 8. Git report

| Item | Value |
|---|---|
| Branch | `main` |
| HEAD at session start | `69858d07ccb016b74bc1d518b66b9948656ad6cf` |
| Dirty working tree | Yes (pre-existing P0/P1/P2/P3 + P4 edits) |
| Staged | None by this session |
| Commits this session | **none** |
| Push | **none** |

### P4-owned / touched files (this session)

- `docs/product-discovery/p4/*`
- `platform/gtf_platform/planning/*`
- `platform/gtf_platform/db.py` (migration 005)
- `platform/gtf_platform/routes.py` (plan routes)
- `platform/gtf_platform/integration/desk.py` (plan helpers)
- `platform/gtf_platform/openapi.json` (regenerated)
- `platform/web/src/features/workflow/WorkflowPages.tsx`
- `platform/web/src/navigation/query.ts`
- `platform/tests/test_trade_planning.py`
- `platform/tests/test_platform_api.py` (migration list)

## 9. Remaining owner decisions

- None required to use the implemented planning desk on fixture/exploratory stored scans.
- OD-CA-1 / P0 certification remains the blocker for CERTIFIED planning inputs.
- Optional later: sync platform plan state when journal cancels an approved entry (P4-IR-04).

## 10. P5 handoff recommendations

1. Keep portfolio accounting and exposure work on the research journal (`portfolio_at`); do not fork counters into platform.
2. If P5 adds valuation, keep UNAVAILABLE without inventing quotes.
3. Mirror or subscribe platform plan state to journal CANCELLED/EXPIRED if dual-state UX becomes painful.
4. Continue P0 CA completeness so CERTIFIED source_quality can be honest later without re-architecture.
5. Do not add broker connectivity without an explicit owner decision.

## 11. Acceptance checklist

| Criterion | Met? |
|---|---|
| Plans created and reviewed safely | Yes |
| Canonical eligibility preserved | Yes |
| Geometry validated without invention | Yes |
| Risk calculations traceable | Yes |
| Caps enforced by authoritative backend | Yes (journal) |
| ED-3 preserved | Yes |
| Manual fills integrate with journal | Yes |
| No automated order execution | Yes |
| Independent review: no open Critical/High | Yes |
| Required tests pass | Yes |

**Final status: P4_COMPLETE_WITH_LIMITATIONS**
