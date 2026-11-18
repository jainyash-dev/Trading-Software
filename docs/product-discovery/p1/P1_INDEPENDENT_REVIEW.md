# P1 Independent Review

**Date:** 2026-11-17  
**Reviewer role:** independent-reviewer (did not author the implementation batches)  
**Initial review agent:** `6aa0dfd6-78c0-4f31-9f26-34668f69ee27` (verdict FAIL  -  C1/I1)  
**Re-review agent:** `340b95c8-8b19-495b-bb3d-6109bf501eed` (verdict PASS_WITH_LIMITATIONS  -  R1 Important)  
**Post-R1 remediation:** engineering closed R1/R2 in-tree; dual-DB always required for backup/restore; PARTIAL→`NOT_READY` regression added.

## Verdict

**PASS** after remediations of Critical C1, Important I1, Important R1, and Minor M1/M2.

No unresolved Critical or Important findings remain against the acceptance paths below.

## Findings and disposition

| ID | Severity | Finding | Disposition |
|---|---|---|---|
| C1 | Critical | Truncated/incomplete backup could get `RESTORE_CHECK_PASSED` without `research.sqlite` | **Fixed.** Required set always includes both application DBs; missing research refuses backup and scrubs partial copies; truncated manifest cannot drop research. Tests cover truncated manifest + missing-research backup. |
| I1 | Important | Dead `evaluate_data_ready` success branch could invent `certified_p0_data=True` | **Fixed.** Fail-closed only; never returns `data_ready`/`certified_p0_data` true. |
| R1 | Important | `research_db is None` fallback still allowed platform-only restore-check | **Fixed.** `_required_backup_sqlite` always requires both DBs (desk journal uses `research_path` fallback). |
| M1 | Minor | PARTIAL mapped to READY in `job_phase` | **Fixed.** PARTIAL / `SUCCEEDED_PARTIAL` → `NOT_READY`. Regression in overview product-flow test. |
| M2 | Minor | Weak `scan_due` assertion | **Fixed.** Asserts scheduler-off → `NOT_READY` with reason. |

### Residual (non-blocking)

| ID | Severity | Note |
|---|---|---|
| N1 | Informational | `scan_due` true-due-day path not exercised in tests (scheduler-off path is) |
| N2 | Informational | Browser click-through not re-run as a release artefact |
| N3 | Informational | Log redaction remains cookie-focused |

## Confirmations

- Live files preserved on backup/restore failure and success paths tested
- Session bootstrap `replace_all` under lock; restart drops cookie; journal survives
- P5 / T-006 / D42 / ED-3 not weakened; no second monthly counter
- `authorises_order` remains false
- P0 fail-closed: `data_ready` false; `certified_p0_data` false
- `nse/sources/` untouched

## Owner authority

This review does not stamp `ACCEPTED`. Engineering recommendation may be `ACCEPTANCE_READY` only when full regression evidence is attached in the closure report.
