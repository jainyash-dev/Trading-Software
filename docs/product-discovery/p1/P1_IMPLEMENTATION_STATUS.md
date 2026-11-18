# P1 Implementation Status

**Date:** 2026-11-17  
**HEAD at start:** `69858d07ccb016b74bc1d518b66b9948656ad6cf`  
**Git mutations:** none  
**Baseline:** `P1_BASELINE_AUDIT.md`

## Batch progress

| Batch | Scope | Status |
|---|---|---|
| P1-0 | Baseline audit + evidence matrix | Complete |
| P1-1 | Backup/restore automated proof + policy | Complete |
| P1-2 | Session + database recovery | Complete |
| P1-3 | Financial + concurrency evidence (reuse P5) | Complete (reuse) |
| P1-4 | Readiness / overview honesty (MI-001 / MI-010) | Complete |
| P1-5 | Security boundary negatives | Complete |
| P1-6 | Regression + independent review + closure | In progress |

## Requirement status (post-implementation)

| ID | Status | Evidence |
|---|---|---|
| P1-SEC-* | `FAILURE_TESTED` | `test_api_security` forged cookie, Bearer/query, 500 body, re-bootstrap revoke |
| P1-F1..F5 | `FAILURE_TESTED` / `INTEGRATION_TESTED` | restart product-flow; `replace_all` bootstrap; recovery policy |
| P1-G1 / P1-H* | `CONCURRENCY_TESTED` (reuse P5/store) | `test_absent_charges_*`, `test_partial_prints_*`, P5 suite |
| P1-I1..I6 / T-017 | `INTEGRATION_TESTED` + `FAILURE_TESTED` | `test_backup_restore_preserves_journal_records_and_rejects_incomplete` |
| P1-DB-* | `FAILURE_TESTED` / `CONCURRENCY_TESTED` | store + platform startup interrupt |
| P1-A* / T-006 / P1-B1 | `CONCURRENCY_TESTED` | store tenth/eleventh races; P5 closure |
| MI-001 / MI-010 / P1-RDY-* | `INTEGRATION_TESTED` | `evaluate_data_ready`; overview active_job / scan_due / job_phase; UI tests |
| P1-X1 | `INTEGRATION_TESTED` | `authorises_order=false` preserved |

Statuses above are engineering evidence levels. Owner `ACCEPTED` is not claimed.

## Code touched this closure

- `platform/gtf_platform/integration/desk.py`  -  readiness evaluator, overview job/due/phase, incomplete restore enforcement
- `platform/gtf_platform/integration/reference.py`  -  datasets use derived readiness
- `platform/gtf_platform/app.py`  -  health readiness fields; bootstrap replace_all
- `platform/gtf_platform/security.py`  -  locked SessionStore; `replace_all`
- `platform/gtf_platform/routes.py`  -  pass settings into overview_facts
- `platform/tests/test_product_flow.py`  -  restore record-level + overview readiness tests
- `platform/tests/test_api_security.py`  -  security negatives
- `platform/web/src/features/overview/*`, `types/contracts.ts`  -  honest overview fields
- `docs/product-discovery/p1/*`  -  audit, policies, status

## Residuals (non-blocking limitations)

- B12: no owner charge tariff in-repo
- `NO_BACKUP_SCHEDULE`
- Bhavcopies excluded from app backup
- Log redaction still cookie-focused
- Browser click-through journey not re-run as a release artefact
- P0 certification remain fail-closed / parallel track
