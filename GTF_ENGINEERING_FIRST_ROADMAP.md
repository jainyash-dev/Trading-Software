# GTF Engineering-First Roadmap

**Assessment date:** 2026-11-16  
**Governance chair:** `gtf-autonomous-project-lead`  
**Scope:** Repository assessment only. No implementation. No git mutation. No P0 production rebuild.  
**Strategic decision recorded here:** Complete GTF software engineering before formal historical dataset certification. This changes **execution priority**, not acceptance criteria. D66 and all existing P0 acceptance requirements remain unchanged.

---

## 0. How to read this report

| Label | Meaning |
|---|---|
| **Fact** | Observed in this checkout (files, code paths, preserved validation artefacts, git metadata) |
| **Assumption** | Reasonable inference not re-proven in this session |
| **Unresolved** | Open question that still needs evidence or an owner decision |

Passing tests prove software behaviour under the cases they cover. They are **not** historical-data certification, TradingView parity, strategy validation, or profitability evidence.

---

## 1. Repository baseline (verified)

### 1.1 Git state

| Item | Value | Class |
|---|---|---|
| Branch | `main` | Fact |
| HEAD | `69858d07ccb016b74bc1d518b66b9948656ad6cf` | Fact |
| HEAD subject | `docs: close remaining GTF governance reconciliation gaps` | Fact |
| HEAD date | 2026-11-12 09:23:15 +0530 | Fact |
| Working tree | Dirty: **86 modified**, **179 untracked** (265 short-status lines) | Fact |
| This assessment | Did not stage, commit, push, reset, clean, stash, or revert | Fact |

Working-tree composition (approximate by path prefix of short status):

| Area | Approx. short-status lines | Note |
|---|---|---|
| `docs/` | ~139 | Mostly untracked product-discovery / P0 evidence packs |
| `nse/` | ~67 | Modified research/data/docs under active work |
| `tests/` | ~38 | Modified and untracked test modules |
| `.claude/` | ~16 | Agents, hooks, vendored skills, scripts |
| Root / other | remainder | `PRODUCT_MASTER_STATUS.md`, `.env.example`, `pyproject.toml`, etc. |

**Unresolved:** Which of the 265 dirty paths are intentional owner work versus abandoned drafts. Rule: treat all as owner work; do not clean or overwrite without inspection.

### 1.2 Project documentation and phase plans (present)

| Document | Role |
|---|---|
| `CLAUDE.md` + `docs/owner/MASTER_IMPLEMENTATION_PROMPT.md` | Binding operating rules |
| `.claude/skills/gtf-autonomous-project-lead/SKILL.md` | GTF phases P0–P11 and crosswalk |
| `PRODUCT_MASTER_STATUS.md` | Capability inventory (last fully dated 2026-11-02; later notes appended) |
| `docs/MILESTONE_STATUS.md` | MP0 / MP1 / Product Prompt 00 authority for milestone state |
| `docs/PRODUCT_ROADMAP.md` | Repository milestones vs Product Prompts 00–14 |
| `docs/product/MASTER_PROMPT_ROADMAP.md` | Desktop product catalogue (referenced) |
| `docs/product-discovery/*` | Capability map, implementation audit, gap register, readiness scorecard |
| `docs/product-discovery/P0_P4_COMPLETION_REPORT.md` | Claims P1–P4 software `COMPLETE_WITH_EXPLICIT_LIMITATIONS` (2026-11-15) |
| `docs/product-discovery/p0/*` | P0 certification evidence, D66 gaps, blockers, validation logs |
| `docs/VALIDATION_SCORECARD.md` | Historical `run_all` counts (MP0/MP1 era) |
| `nse/docs/IMPLEMENTATION_BLOCKERS.md` | Long-lived evidence blockers B6–B18 |
| `nse/docs/DECISION_LOG.md` | Owner decisions (authoritative) |
| `docs/TECHNICAL_DEBT.md` | TD-1…TD-18 |

### 1.3 Implementation surface (fact)

| Layer | Observed |
|---|---|
| Research library | `nse/research/` (~40 Python modules): acquisition, marketdata, universe/membership, instruments, corporate_actions, qualification, scanner, pipeline, reports, backtest, store/journal, dashboard, p0_certification, etc. |
| Engines | `nse/zone-engine/zone_engine.py`, `nse/mtf-freshness/mtf_freshness.py` |
| EOD / calendar | `nse/eod/`, `nse/calendar/` |
| Validation | `nse/validation/run_all.py` with 24 test groups + repository/local_data/reference/lint checks |
| Platform API | `platform/gtf_platform/` (FastAPI): scans, opportunities, planning, journal/portfolio desk, backup |
| Platform UI | `platform/web/src/`: overview, scanner, watchlists, opportunities, workflow pages (plans, journal, portfolio, backtest, reports, settings), chart |
| Explicitly unimplemented API surface | `fills`, `assistant`, `paper` (`platform/gtf_platform/app.py` `NOT_IMPLEMENTED`) |
| Broker | No broker client under `nse/`; `authorises_order` remains false by design |

### 1.4 Test and validation status

**Preserved artefact (fact):** `docs/product-discovery/p0/evidence/validation_2026-11-15/run_all_full_local_data_report.json`

| Field | Value |
|---|---|
| Verdict | `PASS` |
| Totals | ran **1,475**, failures 0, errors 0, skipped 0 |
| Mode | full local data (not `--no-data`); `acceptance_mode` false |
| Context | HEAD `69858d0` plus a dirty working tree on 2026-11-15 |

**This session (fact):** listed `run_all` groups; counted **54** root `tests/test_*.py` modules and **6** `platform/tests/test_*.py` modules (~58 platform test methods). Did **not** re-execute the full ~15-minute `run_all` (would not change the engineering-first conclusion; prior evidence is recent and preserved).

**Assumption:** Current dirty tree still largely passes the same suites; uncommitted edits since 2026-11-15 may have introduced or fixed defects. Re-run before claiming a new engineering batch complete.

### 1.5 Known unfinished work and blockers (summary)

| Track | State | Class |
|---|---|---|
| P0 historical certification | **0 / 123,778** member-dates certified; `completeness.csv` absent; D66 blocks every window | Fact (`P0_CERTIFICATION_SUMMARY.json` on disk still reports builder **1.5.0**; code `BUILD_VERSION` is **1.6.0**) |
| Membership owner backlog | 131 blank decision cells; 24 evidence-sufficient groups await owner ACCEPTED/REJECTED | Fact (handoff docs) |
| Identity OD-ID-1/2 | BAJFINANCE / GRASIM ISIN-change effective session unresolved | Fact |
| TradingView parity (B8/B10/TV-1) | Pending external exports | Fact |
| B11-P | No certified membership before 2020-12-31 | Fact |
| WIT | BLOCKED by design (M4b / B6 / B15) | Fact |
| Release gates R1–R5 | Open / blocked / not started as product certification | Fact (scorecard + milestone docs) |
| Browser journey proof | Not executed as a release artefact | Fact |
| Working tree | Large uncommitted P0/docs/engineering delta | Fact |

---

## 2. GTF phases P0–P11 - assessed status

GTF phase numbering follows `gtf-autonomous-project-lead` (P*n* ≠ Product Prompt *n*).

Legend for “proceed without certified historical data”:

- **Yes** = implement and test with fixtures / available local files / labelled non-certified runs  
- **Partial** = build now, but production claims or full-universe research need certified data later  
- **No** = cannot finish the phase’s acceptance bar without certified evidence

### P0 - Historical data foundation

| Aspect | Assessment |
|---|---|
| Original objective | Membership, identity, CA, calendar, EOD integrity, price continuity, provenance, certified research universe, exclusions |
| Implemented | Certification **builder** (`p0_certification.py` 1.6.0), six D63 gates, D66 dual-source completeness enforcement in code, EOD 2016–2025 archives held, calendar reconciled (D58), identity/CA loaders, exclusion/matrix writers, extensive tests (`test_research_p0_*`, corporate-action adversarial tests) |
| Missing | Dual independent CA completeness evidence; `completeness.csv`; owner membership decisions; OD-ID/PX closures; TradingView exports; any certified member-date |
| Tests | Engineering gates covered in the 2026-11-15 PASS run; synthetic e2e build fixture exists |
| Dependencies / blockers | OD-CA-1 / D66 (critical path); OD-MEM-1; OD-ID-1/2; B11-P; TV-1; optional OD-PX-* |
| Without certified data? | Engineering of gates: **Yes**. Certification itself: **No** |
| Requires certified data? | **Yes** for any `CERTIFIED_P0_DATA` claim or R1 |

**Verdict:** Engineering of the certification **machinery** is advanced. Historical **certification** is not achieved (0 certified). Do not weaken D66.

### P1 - Application hardening

| Aspect | Assessment |
|---|---|
| Original objective | Boundary defects, display correctness, session recovery, charges, partial fills, backup/restore, DB recovery, D42 race remediation |
| Implemented | Platform security/session boundaries, journal `BEGIN IMMEDIATE`, backup/restore copy paths in `desk.py`, structured charge hooks in research store, API security tests |
| Missing / residual | Dedicated two-connection 11th-`TRIGGERED` race test still called out as T-006; restore automated test called incomplete in `docs/implementation/REMAINING_BLOCKERS.md`; in-memory sessions (D57) need re-bootstrap; overview still can hardcode/under-report job state (audit MI-001/MI-010) |
| Tests | `platform/tests/test_api_security.py`, product-flow and platform API suites present |
| Without certified data? | **Yes** |
| Requires certified data? | **No** for hardening; real scans stay labelled uncertified while P0 open |

**Verdict:** Substantial progress; not “closed” if T-006 / restore proof / honest readiness wiring remain open. Treat residuals as first-class engineering work under the new priority.

### P2 - Stock analysis and charting

| Aspect | Assessment |
|---|---|
| Original objective | Interactive M/W/D charts, zone overlays from engine, SMA-50, explanations, missing-evidence warnings |
| Implemented | Candle chart components, zone helpers, drawings API path, symbol bundle route, fixture labelling patterns |
| Missing | OD-P2-1 (standalone chart without stored scan deferred); Weekly/Monthly volume aggregation; browser proof that analysis reads stored bundle only; TradingView external parity |
| Tests | Vitest chart/zone tests; platform fixture scan paths |
| Without certified data? | **Yes** (labelled fixtures / uncertified local EOD) |
| Requires certified data? | **No** for UI; **Yes** for “production chart matches certified history” claims |

**Verdict:** Usable engineering skeleton; product honesty depends on fixture banners and stored-envelope authority.

### P3 - Opportunity intelligence

| Aspect | Assessment |
|---|---|
| Original objective | Qualified/approaching/fresh candidates, MTF alignment, rejection reasons, watchlists, scan history/alerts |
| Implemented | Opportunities feature + ingest/lifecycle/priority modules; scanner page; watchlists; scan history APIs; CERTIFIED discovery refused while certified count is 0 (per P0–P4 report) |
| Missing | OI-007 historical analogue matcher (not implemented); sector filter (D6); richer “why nothing qualified” productisation; browser click-through |
| Tests | `test_opportunity.py`, opportunities vitest |
| Without certified data? | **Yes** for organisational workflows over stored envelopes |
| Requires certified data? | **Yes** for any “certified opportunity” product mode |

**Verdict:** Software path exists and is constrained not to recompute qualification. Treat as engineering-complete-with-limitations, not market-validated.

### P4 - Trade planning

| Aspect | Assessment |
|---|---|
| Original objective | Entry/stop/targets, R:R, sizing, stage risk, expiry, approval/rejection, geometry explanation |
| Implemented | `platform/gtf_platform/planning/`, plans UI in workflow pages, risk plan attachment from research pipeline, `authorises_order` false enforced |
| Missing / accepted limits | P4-IR-04 plan/journal cancel desync; auto `EXPIRED` not produced; charge tariffs not verified against official PDFs |
| Tests | `test_trade_planning.py` |
| Without certified data? | **Yes** |
| Requires certified data? | **No** for planning UX; plans on uncertified scans must stay labelled |

**Verdict:** Core planning loop exists. Residual integrity items remain engineering work.

### P5 - Portfolio and risk

| Aspect | Assessment |
|---|---|
| Original objective | Positions, exposure, average entry, SL/target tracking, P&L, caps (10 monthly / 10 open), allocation |
| Implemented (library) | `nse/research/store.py`: `portfolio_at`, monthly + open-position caps, journal lifecycle, zone allowance |
| Implemented (product) | Portfolio page reads `/api/v1/portfolio`; shows caps; sector/drawdown/valuation often `UNAVAILABLE` |
| Missing | Mark-to-market from last accepted close with explicit session date (PR-007 product completeness); richer open-position presentation; race-test evidence for concurrent writers; no live quotes (correct; EX-007 blocked) |
| Tests | Research store tests; platform portfolio reads exist but are thinner than research journal tests |
| Without certified data? | **Yes** (synthetic journal + fixture EOD closes) |
| Requires certified data? | **No** for cap accounting; **Yes** only if valuing a certified historical book |

**Verdict:** **Recommended next engineering phase.** Library authority exists; product hardening and regression depth are the gap.

### P6 - Trading journal and performance reporting

| Aspect | Assessment |
|---|---|
| Original objective | Lifecycle, partial fills, charges, notes, planned vs actual, exports, performance breakdowns |
| Implemented | Research journal API surface + platform Journal page (submission, entry print, close); charges hooks; append-only design |
| Missing | Richer review UX (screenshots, mistake taxonomy, search/filter productisation); performance-by-setup screens beyond CLI; paper book separation (TJ-012 / `paper` not implemented - correct until decided) |
| Without certified data? | **Yes** |
| Requires certified data? | **No** for recording owner trades; **Yes** for strategy-performance claims |

### P7 - Backtesting and quantitative validation

| Aspect | Assessment |
|---|---|
| Original objective | Leakage-safe backtests, walk-forward, costs, sensitivity, certified studies, acceptance criteria |
| Implemented | `backtest.py`, `execution_policy.py`, walk-forward/sensitivity commands, labelled platform backtest page, run manifests for primary backtest path |
| Missing | TD-4 (walk-forward/sensitivity manifests); owner cost schedule file (B12); pre-registered acceptance hurdles in decision log; **any certified historical strategy evaluation** |
| Without certified data? | **Yes** for infrastructure, fixtures, labelled non-performance studies |
| Requires certified data? | **Yes** for R4 / strategy validation sentences |

### P8 - Monitoring and automation

| Aspect | Assessment |
|---|---|
| Original objective | Scheduled EOD prepare/validate/scan, notifications, backup, health |
| Implemented | Job runner, post-15:45 consider path that refuses public download, health route, backup copy |
| Missing | Scheduler setting fully wired to runner (audit SD-006); unattended monitoring ops proof; missing-data alert productisation |
| Without certified data? | **Yes** |
| Requires certified data? | **No** |

### P9 - AI research assistant

| Aspect | Assessment |
|---|---|
| Original objective | Evidence-grounded explanations over stored records |
| Implemented | Deterministic `explain` in research CLI; platform assistant route in `NOT_IMPLEMENTED`; AI cannot write gates (tested invariant) |
| Missing | Provider enablement (OQ-2); product assistant UI |
| Without certified data? | **Yes** for deterministic explain |
| Requires certified data? | **No** for explain; citations still need real stored envelopes |

### P10 - Professional UI/UX

| Aspect | Assessment |
|---|---|
| Original objective | Design system, navigation, empty/loading/error, consistency, a11y |
| Implemented | Shell, design components, status language helpers, multiple screens; vendored design skills present (some untracked) |
| Missing | Visual polish pass; automated screenshot matrix not run; browser UAT |
| Without certified data? | **Yes** |
| Requires certified data? | **No** |

### P11 - Final production certification

| Aspect | Assessment |
|---|---|
| Original objective | R1–R5, security, backups, UAT, operational readiness |
| Implemented | Partial ingredients only |
| Missing | All release gates closed with evidence |
| Without certified data? | **No** |
| Requires certified data? | **Yes** (R1) plus strategy evidence (R4) and operational proof (R5) |

---

## 3. Complete software scope - remaining engineering work

Mapped to repository architecture (research library + platform). Items are **not** all the same GTF phase.

### 3.1 Data ingestion and normalization

| Remaining | Class |
|---|---|
| Offline acquire/ingest/quarantine already implemented; continue format/regression hardening | A |
| Optional parse cache (TD-17) | A |
| UDiFF continuity samples / format evidence expansion | B |
| Claiming full historical readiness | C |

### 3.2 Historical stock universe and membership

| Remaining | Class |
|---|---|
| Membership converter + review gate + unverified fail-closed behaviour | A (done; keep tests) |
| Owner ACCEPTED/REJECTED on backlog groups | C (owner + evidence) |
| Pre-2020-12-31 membership (B11-P) | C |
| Member-ISIN vs bhavcopy ISIN compare (TD-16) once reviewed data exists | B |

### 3.3 Corporate-action processing interfaces

| Remaining | Class |
|---|---|
| Event store, coverage, G0 MANUAL on gaps, D66 dual-source loaders/tests | A (engineering done) |
| Completeness register population with independent sources | C (D66 unchanged) |
| Parser extensions for unparsed/fractional ratios (ENG-1 etc.) | A/B |

### 3.4 Data-quality and validation infrastructure

| Remaining | Class |
|---|---|
| `run_all`, architecture, docs_health, local_data, reference_comparison | A |
| Run `run_all --acceptance` before any certification claim (ENG-5) | B/C boundary |
| TradingView reference intake schema (TD-14) | A now; B when samples arrive |

### 3.5 Zone Engine / 3.6 Multi-timeframe analysis

| Remaining | Class |
|---|---|
| Core engines + overlay + G0–G8 MIT path | A (implemented; keep regression) |
| Wick-to-wick / unevaluated confluence pieces | A (leave manual; do not invent) |
| TradingView parity | B/C (needs exports) |

### 3.7 Stock scanner / 3.8 Strategy and signal evaluation

| Remaining | Class |
|---|---|
| Canonical `pipeline → scanner → qualification` | A |
| Honest UI labelling of partial/uncertified scans | A |
| Full-universe certified scans | C |

### 3.9 Risk management

| Remaining | Class |
|---|---|
| Caps, sizing library, portfolio_at | A |
| Product portfolio completeness + concurrency proof | A (**next**) |
| Live intraday risk monitor | Blocked (quote source OQ-1) |

### 3.10 Reporting and visualization

| Remaining | Class |
|---|---|
| CLI reports + static dashboard + platform screens | A |
| Browser UAT + screenshot matrix | A |
| Certified-universe report packs | C |

### 3.11 Auditability and reproducibility

| Remaining | Class |
|---|---|
| Run manifests for scan/backtest; decision replay | A |
| Walk-forward/sensitivity manifests (TD-4) | A |
| P0 rebuild determinism already demonstrated in isolated builds | A (engineering); certification still C |

### 3.12 Backtesting infrastructure

| Remaining | Class |
|---|---|
| Engine, labelled UI, fixture studies | A |
| Owner cost schedule + sensitivity grids | B |
| Certified historical strategy evaluation / R4 | C |

### 3.13 Future broker integration boundaries

| Remaining | Class |
|---|---|
| Keep `authorises_order=false`, no order routes, journal-as-record-only | A (preserve) |
| Any real broker client | Out of scope until explicit owner authorisation (not in engineering-first batch) |

---

## 4. Engineering vs certification classification

### A - Implement and test now (fixtures / available local data)

1. P5 portfolio/risk product hardening (valuation from accepted EOD close, caps UI, refusal surfacing).  
2. P1 residuals: two-connection cap race test; backup restore automated test; readiness flag driven by verdict (still default false).  
3. Honest overview / scan-header completeness (universe limitation, coverage, job state) without flipping `data_ready`.  
4. TD-4 walk-forward/sensitivity manifests.  
5. Journal UX depth that still writes only through research store.  
6. Scheduler setting ↔ runner wiring (still no download).  
7. Chart/analysis paths that consume stored bundles only; fixture banners.  
8. Reference-comparison schema prep (TD-14) without fabricating exports.  
9. Platform/browser journey tests on isolated DBs.  
10. Preserve D66 fail-closed unit/adversarial tests; never soften them for green builds.

### B - Implement now; real-data / external validation later

1. Scanner and chart behaviour on real local EOD (labelled `UNIVERSE_UNVERIFIED` / non-certified).  
2. Backtest studies on real history with owner cost file - results labelled **not** R4 evidence.  
3. TradingView `refcheck` once owner supplies exports.  
4. Identity join decisions after OD-ID evidence.  
5. CA parser improvements validated against known events once independent sources exist.

### C - Cannot complete or certify without missing historical evidence

1. P0 certified research universe (`CERTIFIED_P0_DATA` > 0) under D66.  
2. `completeness.csv` proved windows (dual independent official sources + reconciliation + owner acceptance markers).  
3. Full-index survivorship-free claims; B11-P pre-window membership.  
4. R1 Data ready; R4 Strategy validated; P11 production certification.  
5. Any profitability / expectancy / win-rate claim as strategy evidence.  
6. WIT enablement (also blocked on intraday source decisions).

**D66 status (fact):** Gaps G-ZERO…G-ALL remain; no qualified completeness window; paid/independent source path still owner-gated. **Do not change D66.**

---

## 5. Execution roadmap (engineering-first)

### 5.1 Principle

Unlock the **owner’s closed-loop desktop workflow** (scan → analyse → plan → journal → portfolio) with fail-closed labels, while P0 certification continues as a **parallel parked track** that does not gate software batches.

Do **not**:

- flip `data_ready` / claim R1–R5  
- weaken D66 or membership review gates  
- enable WIT, paper book, assistant provider, or broker  
- quote strategy performance from uncertified runs  

### 5.2 Recommended sequence

| Order | Phase | Why this order |
|---|---|---|
| 0 | Working-tree hygiene policy | Inventory dirty paths before any batch; never discard owner work |
| 1 | **P5 Portfolio & risk (next)** | Caps/portfolio are the live safety boundary for journaled trades; library exists; product gaps are pure engineering |
| 2 | P1 residual hardening | Race test + restore proof protect P5/P6 |
| 3 | P6 journal product completion | Depends on trustworthy caps/portfolio reads |
| 4 | P3/P2/P4 honesty pass | Overview/chart/plan labelling so uncertified data cannot be misread |
| 5 | P8 scheduler/ops polish | After manual loop works |
| 6 | P7 infrastructure (not certification) | Manifests, labelled studies, cost-file plumbing |
| 7 | P10 UI consistency | After workflows stable |
| 8 | P9 deterministic explain in UI | Optional; model assistant still owner-gated |
| ∞ | P0 certification track | Continues when evidence/owner decisions arrive; mandatory before R1/R4/P11 |
| final | P11 | Only after R1–R5 evidence |

### 5.3 Next engineering phase - exact definition

**Phase:** GTF **P5 - Portfolio and risk** (product completion over existing journal authority).

**Exact next task (batch P5-1):**

1. Add an automated **two-connection** regression that attempts an 11th `TRIGGERED` and expects exactly one success and one `JournalRefused` (T-006 / D42).  
2. Drive portfolio valuation from the **last accepted EOD close on or before the valuation date**, printing that date; keep `UNAVAILABLE` when no close exists (PR-007).  
3. Ensure platform portfolio/journal paths cannot maintain a second monthly counter (PR-011 invariant tests).  
4. Surface journal refusals in the UI without converting them to passes (PR-012).  
5. Keep sector and live drawdown `UNAVAILABLE` unless an approved source exists.

**Dependencies:**

- Research `store.portfolio_at` / journal writers (already present).  
- Local or fixture EOD closes for valuation tests.  
- **Not** dependent on D66 completeness or certified membership.

**Acceptance criteria:**

- Caps remain independent (monthly vs open positions).  
- Closing a position frees a seat, not a monthly fill.  
- `authorises_order` stays false on all portfolio/journal responses.  
- Valuation never invents a quote.  
- Targeted tests + `python3 -m nse.validation.run_all` (or documented group set) PASS on the batch.  
- No P0 production outputs rewritten; D66 tests still fail-closed.

**Required tests:**

- New/extended store concurrency test (two connections).  
- Portfolio valuation unit tests (present close / missing close / future date cut).  
- Platform API test: portfolio read reflects journal state after a fixture fill/close.  
- Existing adversarial / store cap tests remain green (no weakening).

**Expected deliverables:**

- Code + tests under `nse/research/store.py`, `platform/gtf_platform/integration/desk.py`, portfolio UI as needed.  
- Short batch note in `docs/implementation/AGENT_WORK_LOG.md` (facts vs limitations).  
- No certification claim.

**Validation approach:**

- Synthetic journal fixtures first.  
- Optional labelled real-EOD valuation check (Class B), still not R1.  
- Full `run_all` before calling the batch done.  
- Independent/contrarian review if the batch touches cap arithmetic.

### 5.4 Immediate follow-on tasks (same engineering track)

| ID | Task | Phase |
|---|---|---|
| P5-2 | Open-position detail: average entry, stop/target tracking, realised vs unrealised rules with EOD marks only | P5 |
| P1-R1 | Backup restore automated test on a temp copy | P1 |
| P1-R2 | Overview/job/readiness honesty (never invent `data_ready=true`) | P1/P3 |
| P6-1 | Journal search/filter + planned-vs-actual display from stored rows | P6 |
| P7-I1 | Walk-forward/sensitivity run manifests (TD-4) | P7 infra |
| P0-PARK | Continue D66 source acquisition / owner membership cards **without** blocking P5–P7 infra | P0 |

---

## 6. Parallel P0 certification track (unchanged bar)

Keep running when evidence exists, but **not** as the critical path for software:

1. Owner decisions on 24 evidence-sufficient membership groups.  
2. D66 dual-source acquisition authorisation and per-window acceptance markers.  
3. OD-ID-1/2 effective-session rulings (or continued fail-closed splits).  
4. TradingView export intake (TV-1).  
5. Isolated builder rebuild only when inputs change; expect certified count to remain 0 until completeness windows exist.  
6. `run_all --acceptance` before any certification claim.

Until then: exploratory/uncertified labels only; **0 certified symbol-dates** remains the honest status.

---

## 7. Assumptions and unresolved questions

### Assumptions

1. The 2026-11-15 `run_all` PASS still represents the dominant behaviour of HEAD + similar working tree; uncommitted edits since then are not fully revalidated in this session.  
2. `docs/product-discovery/P0_P4_COMPLETION_REPORT.md` is a useful software snapshot but **not** proof that every P1–P4 limitation is closed; residuals listed above are treated as open engineering.  
3. Engineering-first means P5+ may proceed while P0 certification stays at 0, provided labels and gates remain fail-closed.

### Unresolved questions (do not block P5-1)

1. Which dirty-tree files are authoritative vs draft (especially P0 CSVs and untracked scripts)?  
2. Owner timing for D66 source purchase/enquiry vs pure engineering batches.  
3. Whether OD-PX-3/4 exception mechanisms will ever be wanted (owner choice).  
4. CI adoption (TD-9).  
5. R-5 Rulebook-vs-owner-decision wording conflict remains unresolved in engineering decisions; continue Rulebook-strict until owner resolves.

---

## 8. Bottom line

| Question | Answer |
|---|---|
| Is the software “done”? | **No.** Core MIT research library and much of P1–P4 platform exist with limitations; P5–P11 product completion and all certification gates remain. |
| Is P0 certified? | **No.** **0 / 123,778** member-dates. D66 unchanged. |
| Can engineering proceed now? | **Yes.** Prefer **P5-1** (cap race + honest portfolio valuation) as the next batch. |
| Can strategy evaluation be completed now? | **No** as certification/R4. Infrastructure and labelled studies only. |
| Exact next task | **P5-1:** two-connection 11th-trigger refusal test + EOD-based portfolio valuation + single-counter invariant, without touching P0 certification outputs. |

**Implementation has not started.** This document is the assessment deliverable for owner review before any engineering batch begins.
