# Agent work log

## P10 UI/UX programme - Institutional terminal, dark and light themes (2026-11-17)

| Item | Record |
|---|---|
| Branch / HEAD | `main` / `69858d07ccb016b74bc1d518b66b9948656ad6cf` (before and after) |
| Staged | none (before and after) |
| Working tree | Dirty; 269 porcelain paths before and after. P10 changes landed inside already-untracked `platform/web/` and `docs/implementation/` (new `p10/`, `evidence/p10-browser/`, this log) |
| Baseline | vitest 89/89; `npm run build` pass |
| Work | P10-0 audit docs; IA (5 groups, 18 routes, new `history`, `risk`, `data`, `jobs` screens, capability pages); design tokens for both themes, pre-paint theme script, theme switch; shared components and formatting; redesigned Overview, Stock Analysis, Trade Plans, Portfolio, Journal, Backtesting, Reports, Settings; AI Assistant on deterministic explain; chart follows theme |
| Defects fixed | Unlayered CSS resets overriding button colours; always-mounted benchmark host overflowing phones; content scrolling inside fixed viewport; candidate zone id path; long-code overflow; actions not gated on backend transitions; placeholder contrast; 5 Important independent-review findings (blank close price, blank backtest cost, checklist carry-over, assistant connection badge, settings save after failed read) |
| Tests | vitest **104/104** (5 consecutive runs; +15 P10 tests; overview h1 expectation renamed to "Market Overview"); `tsc` pass; build pass; platform pytest **100 passed**; browser **56/56** (final, after review fixes) |
| run_all | Run 1: 1512 ran, 1 failure (em dashes in new P10 docs). Run 2: 2 failures (em dashes in review/closure docs; docs-health H4 for a module command that only works from `platform/`). Both fixed. Run 3: 1 failure (docs-health on this entry's wording), fixed; then `docs_health`, `architecture` and `repository` groups PASS (full run not repeated after the one-line doc edit) |
| Independent review | `independent-reviewer` agent: 0 Critical, 5 Important (all fixed, regression-tested), Minor/Cosmetic dispositioned in `P10_INDEPENDENT_REVIEW.md` |
| Unchanged | No backend, contract, Rulebook, Pine, D66 or P0 file; no broker or order code; `authorises_order` never set |
| Git | No stage, commit, push, reset, clean, stash or revert |

## P2-P4 programme execution - Analysis, Opportunities, Planning (2026-11-17)

| Item | Record |
|---|---|
| Branch | `main` |
| HEAD | `69858d07ccb016b74bc1d518b66b9948656ad6cf` (before and after) |
| Staged | none (before and after) |
| Working tree | Dirty; 269 porcelain paths before and after (86 M, 183 ??); changes landed inside already-untracked `platform/` and `docs/implementation/`, plus three modified tracked-area docs under `docs/product-discovery/` (untracked tree) |
| Stage 0 | Git state matched Batch 0. Baseline platform 82 PASS, vitest 63 PASS; `run_all --no-data` 1512 ran with 1 failure (em-dashes in the Batch 0 docs, fixed) |
| Work | W/M volume aggregation; FR-4.9 plan overlay; evidence-status panel; scan-outcome ("why nothing qualified") panel; P4-IR-04 identity-bound journal-to-plan mirror (write, read, startup); FR-5.9 later-scan mismatch; Journal "Record CANCELLED"; two canonical-key defects fixed (Scanner statuses, opportunity timeframe) |
| Validation (final) | Platform unittest **100 PASS**; opportunity+planning+API pytest **47 PASS**; web vitest **16 files / 89 PASS**; architecture PASS (55 modules); docs_health PASS; `run_all --no-data` **1512/0/0/0 PASS**; `git diff --check` clean; local_data and reference_comparison not run (`--no-data`) |
| Browser | Real headless Chrome against the running platform, FIXTURE data: 22/22 journey steps + supplemental drawings, watchlist rename, zoom/pan/crosshair; 23 screenshots in `docs/implementation/evidence/p2-p4-browser/` |
| Independent review | Initial FAIL (3 Important, 3 Minor); all remediated; re-review PASS; no unresolved Critical/Important |
| Recommendation | **P2_P3_P4_ACCEPTANCE_READY** (P2, P3, P4 each ACCEPTANCE_READY); owner retains ACCEPTED |
| Deferred / blocked | OD-P2-1, SMA-50 overlay, OI-007, automatic EXPIRED (owner); TV-1, D6 sector, B12 tariffs, live alerts, P0/D66 certified claims (external) |
| Git | No stage, commit, push, reset, clean, stash, or revert |
| Protected | `nse/sources/` and Rulebook PDF untouched (`git status nse/sources` empty; Pine hash matches pin); P0 outputs untouched; P5/P6 suites pass; `authorises_order` false; no route added |
| Notes | One intermittent vitest timing failure seen once under load (`stock scanner > submits a MIT scan ...`), passed in every later run. Batch 0 matrix total 64 was a miscount; 65 rows |

## P2–P4 Batch 0 - Baseline audit (2026-11-17)

| Item | Record |
|---|---|
| Branch | `main` |
| HEAD | `69858d07ccb016b74bc1d518b66b9948656ad6cf` |
| Staged | none |
| Working tree | Dirty (~269 paths); treated as owner work; not restored |
| Scope | Batch 0 only: governance read, spec location, implementation recheck vs Nov-16 gaps, baseline tests, acceptance matrix |
| Code changes | **none** (docs only under `docs/implementation/`) |
| Deliverables | `P2_P4_BASELINE_AUDIT.md`, `P2_P4_ACCEPTANCE_MATRIX.md` |
| Baseline tests | Platform unittest **82 PASS**; vitest **63 PASS**; opportunity+planning+API pytest **29 PASS**; architecture **PASS**; docs_health **PASS** |
| Full `run_all` | This batch: `python3 -m nse.validation.run_all --no-data` → **1512/0/0/0 PASS** (~16m); local_data not run |
| Browser / TV | Not run; TV-1 still external blocker |
| P0 impact | Unchanged: `certified_symbol_dates: 0`; D66 untouched |
| P5/P6 | Preserved; P4-IR-04 still open per P6 baseline |
| Stop | Owner review required before Batch 1 implementation |
| Git | No stage, commit, push, reset, clean, stash, or revert |

## P6 closure - Trading journal and performance reporting (2026-11-17)

| Item | Record |
|---|---|
| Branch | `main` |
| HEAD | `69858d07ccb016b74bc1d518b66b9948656ad6cf` |
| Staged | none |
| Working tree | Dirty; treated as owner work |
| Closure work | P6-0 audit through UI/API/store v5; remediations for independent-review Important findings; architecture layer map for `journal_taxonomy` |
| Validation | Store 111 PASS; journal API 2 PASS; vitest 63 PASS; `run_all` **1512/0/0/0 PASS** |
| Independent review | Initial FAIL then remediations; re-review PASS; no unresolved Critical/Important |
| Recommendation | **P6_ACCEPTANCE_READY** (owner retains ACCEPTED stamp) |
| Git | No stage, commit, push, reset, clean, stash, or revert |
| Protected | `nse/sources/` and Rulebook PDF untouched; P0 certification outputs untouched; P5 caps/accounting preserved; paper book remains NOT_IMPLEMENTED |

## P1 closure - Application hardening (2026-11-17)

| Item | Record |
|---|---|
| Branch | `main` |
| HEAD | `69858d07ccb016b74bc1d518b66b9948656ad6cf` |
| Staged | none |
| Working tree | Dirty; treated as owner work |
| Closure work | Baseline audit; backup/restore record-level proof; dual-DB incomplete refusal; session replace_all; readiness evaluator; overview job/due/phase honesty; security negatives; independent review remediations (C1/I1/R1/M1/M2) |
| Validation | Platform 80 PASS; vitest 59 PASS; store 81 PASS; repository PASS after em-dash hygiene; full `run_all` **1482/0/0/0 PASS** |
| Independent review | Initial FAIL then remediations; no unresolved Critical/Important |
| Recommendation | **ACCEPTANCE_READY** (owner retains ACCEPTED stamp) |
| Git | No stage, commit, push, reset, clean, stash, or revert |
| Protected | `nse/sources/` and Rulebook PDF untouched; P0 certification outputs untouched |

## P5 closure - Portfolio and risk (2026-11-16)

| Item | Record |
|---|---|
| Branch | `main` |
| HEAD | `69858d07ccb016b74bc1d518b66b9948656ad6cf` |
| Staged | none |
| Working tree | Dirty; treated as owner work |
| Closure work | EOD STALE policy; dedicated Portfolio vitest; reel + em-dash hygiene for `GTF_ENGINEERING_FIRST_ROADMAP.md`; aggregate STALE honesty; docs-health link fix |
| Validation | `run_all` **1482/0/0/0 PASS**; Portfolio vitest 10 PASS; store+repo 96 PASS; portfolio API 17 PASS |
| Independent review | Closure review Important (aggregate STALE) fixed; no unresolved critical/important |
| Recommendation | **ACCEPTANCE_READY** (owner retains ACCEPTED stamp) |
| Git | No stage, commit, push, reset, clean, stash, or revert |
| Protected | `nse/sources/` and Rulebook PDF untouched; P0 certification outputs untouched |

## P5 implementation batches (same day)

| Item | Record |
|---|---|
| Batches | P5-0 audit through P5-6 validation; then P5-closure |
| Deliverables | `docs/product-discovery/p5/*` including baseline, status, independent review, EOD policy, closure report |
| Code surface | `valuation.py`, `desk.py` portfolio_view, additive `store.portfolio_at` fields, Portfolio UI, `test_portfolio_p5.py`, store concurrency companion |

## Wave 0, 2026-11-10

| Item | Record |
|---|---|
| Branch | `main` |
| HEAD | `9e302df1a81c2b13696d8fab61f05d377481be2e` |
| Staged | none |
| Working tree | Already dirty with owner work, including untracked `platform/` and `docs/` |
| Ownership | One writer. The orchestrator kept `platform/gtf_platform/`, `platform/web/`, `nse/research/store.py`, and `nse/research/backtest.py`. No second agent edited those files |
| Protected files | `nse/sources/` and the Rulebook PDF were not edited |
