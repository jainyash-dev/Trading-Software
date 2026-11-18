# P1 Baseline Audit - Application Hardening

**Date:** 2026-11-17  
**Branch:** `main`  
**HEAD:** `69858d07ccb016b74bc1d518b66b9948656ad6cf`  
**Staged:** none  
**Working tree:** Dirty (pre-existing owner work; ~267 short-status lines). Untouched by this audit.  
**Git actions this audit:** none (no stage/commit/push/reset/clean/stash/revert)

This audit is Batch P1-0. It does not claim P1 complete. Prior P1 docs (`P1_ACCEPTANCE_MATRIX.md`, `P1_CERTIFICATION_REPORT.md`) labelled several workstreams COMPLETE; this audit re-scores against code and tests actually present on this tree.

GTF P1 is not Product Prompt 01 and does not certify P0.

---

## 1. Canonical scope reconciliation

| Source | P1 objective |
|---|---|
| `gtf-autonomous-project-lead` / `GTF_ENGINEERING_FIRST_ROADMAP.md` | Boundary defects, display correctness, session recovery, charges, partial fills, backup/restore, DB recovery, D42 race remediation |
| Existing IDs `P1-A*` … `P1-X*` | Concurrency caps, ED-3, fail-closed UI, navigation, restart, charges, partial fills, backup |
| Residuals named by engineering assessment | T-017 restore automated proof; D57 re-bootstrap; MI-001 / MI-010 readiness honesty; T-006 11th-trigger (claimed elsewhere) |
| Product gaps | MI-001, MI-010, UX-002, DS-018 / T-017 |

No original P1 requirement is removed from scope.

---

## 2. Requirement evidence matrix

Status vocabulary (do not collapse to DONE):  
`NOT_STARTED` | `IMPLEMENTED` | `UNIT_TESTED` | `INTEGRATION_TESTED` | `FAILURE_TESTED` | `CONCURRENCY_TESTED` | `INDEPENDENTLY_REVIEWED` | `ACCEPTANCE_READY` | `ACCEPTED` | `BLOCKED`

Highest status shown is the furthest verified level. Gaps block promotion to `ACCEPTANCE_READY`.

### P1-1 Security and application boundaries

| ID | Requirement | Paths | Tests | Status | Gap / remediation |
|---|---|---|---|---|---|
| P1-SEC-1 | Protected routes require session; unauthenticated fail closed | `security.py`, `app.py` middleware | `test_api_security.test_unauthenticated_*`, health 401 | `FAILURE_TESTED` | Keep; add forged-cookie negative |
| P1-SEC-2 | Host / origin / CSRF marker enforced | `security.authorize` | Host/origin/CSRF 403 tests | `FAILURE_TESTED` | Non-loopback client test still missing |
| P1-SEC-3 | Cookie-only identity; not query/body/Bearer | `require_session` cookie only | OpenAPI asserts no bearer | `IMPLEMENTED` | Add explicit negative tests that query/Bearer cannot authenticate |
| P1-SEC-4 | Errors do not leak tokens/secrets | fixed 500 body; `logsafe.py` | cookie log redaction | `UNIT_TESTED` | 500 body disclosure untested; redaction limited to `gtf_session=` |
| P1-SEC-5 | No accidental production auth shortcuts | `PUBLIC_API` = bootstrap only | OpenAPI security scheme | `INTEGRATION_TESTED` |  -  |
| P1-SEC-6 | Config/secrets not exposed via responses | bootstrap omits token in JSON | security + product-flow | `INTEGRATION_TESTED` |  -  |

### P1-2 Session lifecycle and recovery (D57)

| ID | Requirement | Paths | Tests | Status | Gap / remediation |
|---|---|---|---|---|---|
| P1-F1 | API restart drops session; journal survives; safe retry | `SessionStore` in-memory; product-flow restart | `test_restart_drops_the_cookie_and_keeps_the_journal` | `INTEGRATION_TESTED` | Document exact lifecycle; concurrent bootstrap leaves multiple digests |
| P1-F2 | Stale portfolio/journal cleared after session loss | `WorkflowPages.tsx` | product-flow + UI clear path | `INTEGRATION_TESTED` |  -  |
| P1-F3 | Expired/invalid session rejected; re-bootstrap required | `expire`, bootstrap | `test_expired_session_is_rejected` | `FAILURE_TESTED` | Forged token untested; bootstrap does not revoke prior digest |
| P1-F4 | Session loss must not look like readiness success | health/overview after 401 | UI connection states | `IMPLEMENTED` | Strengthen readiness mapping (see P1-7) |
| P1-F5 | Concurrent refresh must not corrupt identity | `SessionStore.issue` | none | `IMPLEMENTED` | Add concurrency / re-bootstrap revoke behaviour |

### P1-3 Financial records, charges, partial fills

| ID | Requirement | Paths | Tests | Status | Gap / remediation |
|---|---|---|---|---|---|
| P1-G1 | Charges only from owner schedule or ACTUAL; absent ≠ zero | `nse/research/charges.py`, store | `test_absent_charges_*` | `UNIT_TESTED` + prior independent review | Official tariff absent (B12) - documented limitation |
| P1-H1 | Partial prints, WAP, remaining qty, one monthly trade | `journal_executions`, `portfolio_at` | `test_partial_prints_*`; P5 suite | `CONCURRENCY_TESTED` (via P5 reuse) | Reuse P5; do not rewrite |
| P1-H2 | Journal UI records prints, not bare TRIGGERED | `WorkflowPages` | product-flow / UI | `INTEGRATION_TESTED` |  -  |
| P1-FIN-ADV | Reject NaN/inf/negative malformed quantities | store / valuation | P5 `test_price_rejects_nan` and store refusals | `UNIT_TESTED` | Confirm coverage in P1 matrix; add only if gap found |

### P1-4 Backup and restoration (primary residual)

| ID | Requirement | Paths | Tests | Status | Gap / remediation |
|---|---|---|---|---|---|
| P1-I1 | Backup via SQLite API; restore-check; live protected | `desk.backup_to`, `desk.restore_copy` | `test_backup_restores_a_copy_*`, `test_interrupted_restore_*` | `FAILURE_TESTED` (partial) | No rich journal record-level proof; restored DB not opened independently |
| P1-I2 | Representative journal survives restore | same | **missing** | `IMPLEMENTED` | Seed plan/order/fill/charges then backup→restore→compare |
| P1-I3 | Missing / corrupt / incomplete backup fail closed | same | missing + corrupt covered; incomplete **missing** | `FAILURE_TESTED` (partial) | Empty / one-of-two-file incomplete cases |
| P1-I4 | Failed restore leaves source intact | same | byte-equal live after 422 | `FAILURE_TESTED` | Keep |
| P1-I5 | Invalid / live destination refused | same | overwrite + live dest 409 | `FAILURE_TESTED` | Keep |
| P1-I6 | Permission / interrupted restore | same | integrity-fail cleanup only | `IMPLEMENTED` | Add permission and incomplete-manifest cases where feasible |
| T-017 | Dedicated automated restore proof | `REMAINING_BLOCKERS.md` | called incomplete | `BLOCKED` until P1-I2 closes | Primary Batch P1-1 work |

### P1-5 Database integrity and recovery

| ID | Requirement | Paths | Tests | Status | Gap / remediation |
|---|---|---|---|---|---|
| P1-DB-1 | Multi-step financial ops atomic (`BEGIN IMMEDIATE`) | `store.py`, `jobs.py` | failed trigger leaves no row; uncommitted invisible | `FAILURE_TESTED` |  -  |
| P1-DB-2 | Busy/locked handled deterministically | SQLite + immediate lock | multi-connection races | `CONCURRENCY_TESTED` |  -  |
| P1-DB-3 | Restart does not expose partial commits | journal on disk; jobs → INTERRUPTED | restart + stale job tests | `INTEGRATION_TESTED` | Document recovery contract |
| P1-DB-4 | Backup compatible with SQLite backup API / WAL | `_sqlite_backup` | backup tests | `INTEGRATION_TESTED` | Document WAL/checkpoint semantics |

### P1-6 Concurrency and race conditions

| ID | Requirement | Paths | Tests | Status | Gap / remediation |
|---|---|---|---|---|---|
| P1-A1 | Monthly IST fill cap atomic | `store._refuse_new_trigger` | tenth-trigger race | `CONCURRENCY_TESTED` | Reuse; do not duplicate |
| P1-A2 | Open-position cap independent | `_open_positions` | open-slot race; eleventh position | `CONCURRENCY_TESTED` | Reuse |
| P1-A3 / A4 | Rollback / idempotent retries | store | store integrity tests | `FAILURE_TESTED` |  -  |
| T-006 / 11th trigger | Both connections refuse 11th | `test_two_connections_cannot_both_commit_an_eleventh_trigger` | present in `tests/test_research_store.py` | `CONCURRENCY_TESTED` | **Reuse P5/store evidence; do not re-label duplicate** |
| P1-B1 | One order per zone under concurrency | ED-3 | zone race test | `CONCURRENCY_TESTED` | Preserve P5 |
| P1-CON-SESS | Concurrent session bootstrap | SessionStore | **missing** | `IMPLEMENTED` | Batch P1-2 |
| P1-CON-BACKUP | Concurrent backup/restore | desk | **none** | `IMPLEMENTED` | Document single-writer expectation or add lock note |

### P1-7 Readiness and application-state honesty

| ID | Requirement | Paths | Tests | Status | Gap / remediation |
|---|---|---|---|---|---|
| MI-001 | Session/scan overview: due / running / partial / complete | `routes.overview`, `desk.overview_facts`, `OverviewPage` | missing≠0; PARTIAL/FAILED labels | `IMPLEMENTED` (partial) | Job only for stored scan `result_ref`; **no scan-due**; under-reports FR-2.1 |
| MI-010 | `DATA_READY` from readiness verdict, not a green test | health, overview, eod_coverage | always false asserted | `IMPLEMENTED` (honest non-claim) | Flag is **hardcoded False**, not derived from authoritative evaluator |
| P1-RDY-1 | No hardcoded `data_ready=true`; missing verdict ≠ ready | app/desk/reference | platform API asserts false | `FAILURE_TESTED` (false path) | Replace hardcode with fail-closed evaluator |
| P1-RDY-2 | Distinguish READY / NOT_READY / RUNNING / FAILED / STALE / UNAVAILABLE | jobs enums + UI | scanner job helpers only | `NOT_STARTED` for overview vocabulary | Map job + readiness onto explicit states |
| P1-RDY-P0 | P0 fail-closed: no CERTIFIED_P0_DATA / false data_ready | opportunity/planning refuse certified | P0/P5 protections | `INTEGRATION_TESTED` | Preserve |

### P1-8 API and UI consistency

| ID | Requirement | Paths | Tests | Status | Gap / remediation |
|---|---|---|---|---|---|
| P1-C1 | Unknown qualification stays fail-closed in UI | `status.ts` | `status.test.ts` | `UNIT_TESTED` |  -  |
| P1-E1 | Hash query navigation | `query.ts` | plans-navigation / routes tests | `UNIT_TESTED` |  -  |
| P1-X1 | `authorises_order` remains false | desk portfolio/journal | product-flow + P5 | `INTEGRATION_TESTED` | Preserve |
| P1-UI-RDY | Overview shows authoritative job/readiness | OverviewPage | overview vitest partial | `IMPLEMENTED` | Extend after backend wiring |

### P1-9 Operational failure handling

| ID | Requirement | Paths | Tests | Status | Gap / remediation |
|---|---|---|---|---|---|
| P1-OPS-1 | Stale RUNNING jobs → INTERRUPTED on start | `app.py`, `jobs.interrupt_stale` | security test | `FAILURE_TESTED` |  -  |
| P1-OPS-2 | Recovery procedures documented | `P1_RECOVERY_PROCEDURES.md` |  -  | `IMPLEMENTED` | Split backup vs session recovery policies; update after code changes |
| P1-OPS-3 | Logs diagnose without secrets | `logsafe.py` | cookie redaction | `UNIT_TESTED` | Expand coverage modestly if cheap |

---

## 3. Confirmed blockers and residuals (pre-implementation)

| Residual | Severity | Disposition for this P1 closure |
|---|---|---|
| T-017 / P1-I2 record-level restore proof | Critical for P1 acceptance | Batch P1-1 |
| MI-010 hardcoded `data_ready=False` (not verdict-derived) | Important | Batch P1-4 |
| MI-001 under-reported due/running | Important | Batch P1-4 |
| D57 concurrent bootstrap / prior digest retention | Important | Batch P1-2 |
| Security negative-test gaps (forged cookie, Bearer/query) | Important | Batch P1-5 |
| B12 no owner charge schedule | Limitation | Keep `COMPLETE_WITH_LIMITATIONS`; do not invent tariff |
| NO_BACKUP_SCHEDULE / no bhavcopy in app backup | Limitation | Document only |
| P0 certification incomplete | Out of P1 scope | Fail-closed; parallel track |
| Browser journey proof | Limitation | Not required to invent browser automation for P1 if API/UI unit coverage closes honesty |

T-006 eleventh-trigger: **already present** (`tests/test_research_store.py`). Roadmap residual text is stale relative to code. Reuse; do not duplicate.

---

## 4. Implementation plan (preserving IDs)

| Batch | Scope | Deliverables |
|---|---|---|
| P1-0 | This audit | `P1_BASELINE_AUDIT.md` |
| P1-1 | Backup/restore | Strong isolated restore tests; `P1_BACKUP_RESTORE_POLICY.md`; update recovery docs |
| P1-2 | Session + DB recovery | Re-bootstrap revoke; session/DB tests; `P1_RECOVERY_POLICY.md` |
| P1-3 | Financial + concurrency evidence | Matrix updates; reuse P5; fill only true gaps |
| P1-4 | Readiness / overview | Fail-closed evaluator; job/due honesty; MI-001/MI-010 disposition; UI/API tests |
| P1-5 | Security boundaries | Negative tests; boundary fixes only if defect proven |
| P1-6 | Regression + independent review | Status matrix, closure report, independent review; recommend `ACCEPTANCE_READY` only if criteria met |

---

## 5. Facts vs prior claims

| Prior claim | Audit finding |
|---|---|
| P1 COMPLETE_WITH_LIMITATIONS (2026-11-13 cert report) | Overstated for restore record-level proof and readiness derivation |
| T-017 IMPLEMENTED_UNVERIFIED (`TASK_COMPLETION_MATRIX`) | Still accurate until Batch P1-1 |
| T-006 outstanding (roadmap) | **Incorrect** - test exists; reuse P5/store evidence |
| MI-001 job hardcoded unavailable (old audit) | Partially outdated - API queries job by `result_ref`; still under-reports due/active job |
| `data_ready` always false | Factually true and honest; not verdict-wired |

---

## 6. Owner decisions required from this audit

None for starting Batches P1-1 through P1-5. Existing limitations that remain owner-gated (charge tariff B12, backup schedule, P0 membership) stay limitations, not engineering blockers for hardening.
