# P2–P4 Baseline Audit (Batch 0)

**Date:** 2026-11-17  
**Programme:** GTF P2–P4 Engineering Integrity & Product Completion  
**Governance chair:** `gtf-autonomous-project-lead`  
**Batch:** 0 only - specification and repository audit  
**Implementation code changes this batch:** none  
**Git mutations this batch:** none (no stage, commit, push, reset, clean, stash, or revert)

---

## 1. Executive verdict (Batch 0)

P2, P3, and P4 software already exists in `platform/` with prior phase certification reports dated 2026-11-15 (`COMPLETE_WITH_LIMITATIONS`). Subsequent work (P5 2026-11-16, P6 2026-11-17) closed portfolio and journal product tracks at the same HEAD without rewriting P2–P4 authority boundaries. November 16 roadmap gaps are **mostly still open** as engineering residuals, not silently closed.

This Batch 0 does **not** stamp any phase `ACCEPTANCE_READY`. It produces the acceptance matrix for owner review before Batch 1.

| Phase | Prior stamp (2026-11-15) | Current engineering reading (2026-11-17) |
|---|---|---|
| P2 | `P2_COMPLETE_WITH_LIMITATIONS` | Still limitations: OD-P2-1 deferred; W/M volume not aggregated; no chart SMA-50 overlay; FR-4.9 plan overlay absent; no browser proof; TradingView parity externally blocked |
| P3 | `P3_COMPLETE_WITH_LIMITATIONS` | Still limitations: OI-007 omitted; D6 sector filter unavailable; richer empty-scan productisation weak; no browser click-through; CERTIFIED discovery correctly refused (P0=0) |
| P4 | `P4_COMPLETE_WITH_LIMITATIONS` | Still limitations: P4-IR-04 plan/journal cancel desync; platform `EXPIRED` never produced; charge tariffs by design owner-supplied (B12), not PDF-verified |

---

## 2. Git and working-tree baseline

| Item | Value |
|---|---|
| Branch | `main` |
| HEAD | `69858d07ccb016b74bc1d518b66b9948656ad6cf` |
| HEAD subject | `docs: close remaining GTF governance reconciliation gaps` |
| Staged | none |
| Dirty paths (approx.) | ~269 modified/untracked (owner / prior-session work) |
| Protected | `nse/sources/` and Rulebook PDF not touched this batch |
| P0 outputs | Not modified this batch; on-disk summary still builder `1.5.0`, `certified_symbol_dates: 0` |

**Safety protocol:** Dirty tree treated as owner work. No restore/revert. Documentation written only under `docs/implementation/` plus `AGENT_WORK_LOG.md` update.

---

## 3. Authoritative specifications located

| Document | Role |
|---|---|
| `CLAUDE.md` | Repository operating rules |
| `docs/owner/MASTER_IMPLEMENTATION_PROMPT.md` | Binding master prompt (cited by section) |
| `.claude/skills/gtf-autonomous-project-lead/SKILL.md` | Sole GTF governance chair |
| `docs/product/PRODUCT_REQUIREMENTS.md` | Canonical FR-3 / FR-4 / FR-5 requirement IDs |
| `docs/product-discovery/02_MASTER_CAPABILITY_MAP.md` | Canonical OI-*, TP-*, UX-* IDs |
| `docs/product/FRONTEND_SPECIFICATION.md` | Chart UX specimen (M/W/D, overlays, no SMA line ID) |
| `nse/docs/DECISION_LOG.md` | D6 (sector), D42 (caps/expiry), D43, etc. |
| `docs/product-discovery/p2/*` | P2 architecture, contracts, tracker, certification |
| `docs/product-discovery/p3/*` | P3 plan, matrix P3-R01…R17, certification |
| `docs/product-discovery/p4/*` | P4 plan, matrix P4-R01…R21, review register |
| `docs/product-discovery/P0_P4_COMPLETION_REPORT.md` | 2026-11-15 software snapshot + accepted limitations |
| `GTF_ENGINEERING_FIRST_ROADMAP.md` | 2026-11-16 engineering-first assessment (not a replacement FR register) |
| `docs/implementation/AGENT_WORK_LOG.md` | P5/P6 closure evidence at same HEAD |
| `docs/product-discovery/p5/P5_CLOSURE_REPORT.md` | P5 ACCEPTANCE_READY (owner stamp reserved) |
| `docs/product-discovery/p6/P6_CLOSURE_REPORT.md` | P6 ACCEPTANCE_READY (owner stamp reserved) |

### Specification notes (facts)

1. **GTF phase Pn ≠ Product Prompt n.** P2 charts ≈ Prompt 06 / FR-4; P3 opportunities ≈ Prompt 05 / OI-*; P4 planning ≈ Prompt 07 / TP-*.
2. The November 16 roadmap’s “original objective” language (SMA-50, approaching/fresh/qualified, alerts) is **broader** than numbered FR/OI/TP IDs. Where the roadmap and FR IDs diverge, the matrix keeps FR/OI/TP IDs as authority and records roadmap vernacular separately.
3. No separate “Prompt 05 requirement PDF” beyond `PRODUCT_REQUIREMENTS.md` Module 3 and the capability map was required for ID extraction; those are the canonical ID sources.

---

## 4. Post-November-16 reconciliation

| Event | Effect on P2–P4 |
|---|---|
| P5 portfolio closure (2026-11-16) | Preserved journal as portfolio authority; sector stays `UNAVAILABLE` (D6). Did not close P2/P3/P4 residuals. |
| P6 journal closure (2026-11-17) | Expanded journal UI/API/store. Explicitly left P4-IR-04 as documented dual-state limitation (`P6_BASELINE_AUDIT.md`). |
| P0 certification | Still **0 / 123,778** certified symbol-dates; D66 completeness register absent. Unchanged parallel track. |
| Working tree | Remains dirty; platform code present as untracked/prior work relative to committed HEAD docs at start of programme history. |

**Inference:** Claiming “P1–P4 software complete” from the 2026-11-15 report remains valid only with the listed limitations. It is **not** evidence that Nov-16 gaps were closed afterward.

---

## 5. Current implementation surface (observed)

### P2 - Stock analysis and charting

| Area | Path | Observation |
|---|---|---|
| Candles API | `platform/gtf_platform/integration/candles.py` | M/W/D via `mtf.replay`; daily volume; W/M appends `VOLUME_NOT_AGGREGATED_FOR_HTF` |
| Chart UI | `platform/web/src/chart/CandleChart.tsx`, `model.ts`, `zones.ts` | Lightweight Charts 5.2.1; volume histogram; no SMA series |
| Analysis page | `WorkflowPages.tsx` Analysis | Requires stored scan (FR-4.5); loads candles + `/bundle` + `/explain`; OD-P2-1 empty-state copy present |
| Zones | `zonesFromStored` | Display-only from stored candidates/fresh/blocked; unknown ≠ fresh |
| Drawings | routes + store | GET/POST/PATCH/DELETE; platform SQLite |
| Plan overlay FR-4.9 | chart | **Not found** (`createPriceLine` / plan line overlay absent) |
| SMA-50 chart overlay | chart | **Not found**; research SMA-50 clock lives in `nse/research/trend.py` (G2) |
| TradingView | `nse/research/refcheck.py`, P0 TV-1 | External exports still pending; no parity claim from fixtures |

### P3 - Opportunity intelligence

| Area | Path | Observation |
|---|---|---|
| Ingest | `opportunity/ingest.py` | Stored scan envelope only; never invents CERTIFIED |
| Lifecycle | `opportunity/lifecycle.py` | Desk states: DISCOVERED, UNDER_REVIEW, SHORTLISTED, REJECTED, EXPIRED, BLOCKED, ARCHIVED - **not** “approaching/qualified/fresh” product nouns |
| Priority | `opportunity/priority.py` | Explicitly non-authoritative |
| UI | `features/opportunities/` | Dashboard, filters, deep-link to analysis/plans |
| Watchlists | store + `WatchlistsPage.tsx` | CRUD + delete; ≠ eligibility |
| Scanner / history | `ScannerPage.tsx`, scan APIs | Stored statuses, history, evidence |
| OI-007 | - | **No matcher implementation** under `platform/` |
| Sector filter D6 | valuation / portfolio | `sector_state=UNAVAILABLE`; no opportunity sector filter |
| Alerts | `nse/research/alerts.py` | Scan-diff local alerts; EX-007/EX-008 live session alerts still out of scope / blocked |

### P4 - Trade planning

| Area | Path | Observation |
|---|---|---|
| Planning package | `platform/gtf_platform/planning/` | Lifecycle, preview, geometry, sizing via `risk.plan_trade` |
| States | `planning/states.py` | Includes `EXPIRED` in map; **no producer** sets `EXPIRED` |
| Cancel | `cancel_plan` | APPROVED+`entry_id` → 409; journal cancel path not syncing platform plan (P4-IR-04) |
| UI | Plans section in `WorkflowPages.tsx` | Approval/reject/cancel; `authorises_order` disclosure |
| Charges / tariffs | `nse/research/charges.py` + journal | Owner schedule / actual lines; **no** built-in Zerodha/NSE PDF tariff (B12 / FR-8.5) |
| Caps / ED-3 | research journal (P1/P5/P6) | Preserved; preview advisory only |

---

## 6. Vocabulary reconciliation (mission vs canonical)

| Mission wording | Canonical meaning in this repo |
|---|---|
| Qualified / approaching / fresh candidates | Stored `candidate_status` + overlay `FRESH`/`TESTED`/…; desk workflow is separate (`SHORTLISTED`, etc.). There is **no** approved lifecycle state named APPROACHING. |
| Alerts (P3) | Product alerts EX-007/EX-008 are blocked without quote provider. Scan-diff alerts exist in research CLI. Do not invent push/email delivery. |
| SMA-50 (P2) | Rulebook trend clock in `trend.py` (G2). **Not** an FR-4 chart overlay ID. Roadmap listed it as objective; FR-4 does not. |
| Automatic EXPIRED (P4) | D42/FR-6.9 expiry is **journal pending-order** (10 verified sessions). Platform plan `EXPIRED` edge exists without a producer; auto plan-expiry was deferred, not specified as a second clock. |

---

## 7. November 16 known gaps - recheck

| Gap (Nov 16) | Current evidence | Status |
|---|---|---|
| OD-P2-1 standalone chart without scan | Empty state cites OD-P2-1; FR-4.5 scan-linked path only | **Still deferred / owner decision** |
| Weekly/Monthly volume aggregation | `VOLUME_NOT_AGGREGATED_FOR_HTF` still emitted; tests assert it | **Still missing** |
| Browser proof analysis = stored bundle only | Vitest stubs fetch; no screenshot matrix | **Still missing** |
| TradingView external parity | TV-1 / B8/B10 pending exports | **Externally blocked** |
| OI-007 historical analogue | No platform matcher; capability map: omit unless validated PIT matcher | **Still missing / out of initial scope (P7-gated)** |
| Sector filter (D6) | UNAVAILABLE by approved decision | **Blocked on sector source; must not fabricate** |
| “Why nothing qualified” productisation | Scanner shows statuses; dedicated empty-universe explanation UX thin | **Partial** |
| P3 browser click-through | Not run this programme | **Still missing** |
| P4-IR-04 plan/journal cancel desync | Still 409 on platform cancel; P6 audit still lists desync | **Still open integrity item** |
| Auto `EXPIRED` on plans | No producer in planning package | **Still missing / needs rule clarification** |
| Charge tariffs vs official PDFs | By design no in-repo tariff (B12) | **Document as owner/external dependency, not invent rates** |

---

## 8. Baseline tests (this Batch 0)

| Command | Result |
|---|---|
| `python3 -m unittest discover -s platform/tests` | **82 passed** (includes P5/P6 suites) |
| `cd platform/web && npm test -- --run` | **63 passed** (14 files) |
| `python3 -m pytest -q -p no:cacheprovider platform/tests/test_opportunity.py platform/tests/test_trade_planning.py platform/tests/test_platform_api.py` | **29 passed** |
| `python3 -m nse.validation.architecture` | **PASS** (55 modules, 0 violations) |
| `python3 -m nse.validation.docs_health` | **PASS** (0 findings) |
| `python3 -m nse.validation.run_all --no-data` | **PASS** - **1512 ran / 0 failures / 0 errors / 0 skipped** (local_data and reference_comparison not run) |
| Full `run_all` with local_data | **Not re-run this batch** |
| Browser / screenshot matrix | **Not run** |

Prior same-HEAD evidence (do not treat as this-batch re-execution): P6 closure `run_all` **1512 PASS**; P5 closure **1482 PASS**.

---

## 9. Dependencies and blockers

### External / owner

| ID | Dependency |
|---|---|
| D66 / OD-CA-1 | Dual-independent CA completeness windows - blocks CERTIFIED discovery/planning claims |
| TV-1 / B8 / B10 | TradingView exports - blocks external chart/SMA/zone parity |
| OD-P2-1 | Owner decision whether standalone chart without stored scan is authorised |
| Sector source | Required before any sector filter; D6 forbids proxy scoring |
| B12 tariff file | Optional owner-dated charge schedule; do not hardcode broker PDFs |
| OI-007 method | No approved similarity algorithm - implementing one would invent methodology |

### Internal (engineering, uncertified data OK)

| Item | Notes |
|---|---|
| W/M volume aggregation | Needs constituent-session volume sum with honest nulls |
| FR-4.9 plan overlay | Chart third overlay labelled as plan |
| P4-IR-04 sync | Recoverable plan↔journal cancel consistency |
| Plan EXPIRED producer | Only if original rule maps platform plans to D42 sessions - clarify before inventing |
| Browser validation | Required for ACCEPTANCE_READY per programme |
| Empty-scan explanation UX | Productise FR-3.4 / OI-002 for zero-qualified scans |

### Must preserve

- P0 certification criteria and D66 fail-closed tests  
- `authorises_order=false`  
- Single qualification path; no second journal/ledger  
- P5 caps / P6 store authority  

---

## 10. Proposed Batch 1–3 scope (for owner approval; not started)

1. **Batch 1 (P2):** W/M volume aggregation per canonical HTF rules; FR-4.9 plan overlay if confirmed in scope; clarify SMA-50 as trend evidence vs optional chart line (do not invent FR); browser validation; leave OD-P2-1 and TV-1 as owner/external unless owner decides.  
2. **Batch 2 (P3):** Empty/partial/failed scan explanation productisation; keep OI-007 deferred unless owner supplies approved matcher; sector filter stays UNAVAILABLE; browser click-through.  
3. **Batch 3 (P4):** Reproduce and remediate P4-IR-04; clarify/implement EXPIRED only per D42/FR mapping; charge-source evidence register (no invented rates); adversarial `authorises_order` already largely covered - extend if gaps.  

---

## 11. Owner decisions required before or during implementation

1. **OD-P2-1:** Authorise standalone chart without stored scan, or keep FR-4.5-only?  
2. **SMA-50 on chart:** Treat as non-FR display enhancement, or require chart overlay matching `trend.py`?  
3. **OI-007:** Confirm remains out of initial release / P7-gated (recommended), or supply approved matcher specification.  
4. **P4-IR-04:** Prefer journal-authoritative sync of platform plan to CANCELLED after journal cancel, vs keep accepted dual-state with stronger UI disclosure?  
5. **Platform plan EXPIRED:** Confirm whether platform plans should auto-expire on D42’s 10 verified sessions after journal order submission, or only journal `EXPIRED` events apply.  
6. **D66 timing:** Confirm P2–P4 engineering proceeds on fixtures/exploratory labels without waiting for certification (programme default: yes).

---

## 12. Stop point

Batch 0 complete pending owner review of:

- `docs/implementation/P2_P4_BASELINE_AUDIT.md` (this file)  
- `docs/implementation/P2_P4_ACCEPTANCE_MATRIX.md`  

**Do not begin Batch 1 implementation until the owner has reviewed the audit and matrix.**

---

## 13. Stage 0 revalidation (programme execution, 2026-11-17)

Recorded before any implementation change in the execution programme.

| Item | Batch 0 | Stage 0 recheck |
|---|---|---|
| Branch / HEAD | `main` / `69858d07...` | Same |
| Staged | none | none |
| Dirty paths | ~269 | 269 (86 modified, 183 untracked); treated as owner work |
| Platform unittest | 82 PASS | 82 PASS |
| Web vitest | 63 PASS | 63 PASS |
| `run_all --no-data` | 1512 PASS (reported) | 1512 ran, **1 failure**: `test_repo.Repo.test_no_em_dashes_and_no_personal_email`. Cause: the two Batch 0 documents in this folder (this file and the matrix) contained em-dashes and were written after the Batch 0 run. Fixed by replacing that punctuation only; the next run was 1512/0/0/0. |

Owner decisions 1-6 of the programme prompt were applied: OD-P2-1 deferred, SMA-50 chart overlay out of
scope, OI-007 omitted, P4-IR-04 authorised for remediation, automatic EXPIRED deferred pending
specification, uncertified engineering approved. No conflict between the matrix and the canonical
FR/OI/TP/UX requirements was found. The Batch 0 matrix total of 64 rows is a miscount (P3 lists 27 rows);
see the updated matrix.
