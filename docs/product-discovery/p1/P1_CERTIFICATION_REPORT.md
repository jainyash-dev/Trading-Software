# GTF P1 certification report

**Date:** 2026-11-13  
**Phase:** GTF P1  -  Core Application Hardening  
**Overall status:** **P1 COMPLETE_WITH_LIMITATIONS**

This is not Product Prompt 01. P0 data certification is independent and remains open where previously recorded. No historical strategy performance is claimed.

## A. Executive summary

The application is safer and more reliable for local journal, portfolio and recovery use. Monthly and open-position caps share one SQLite write lock across connections. ED-3 zone reservation is concurrency-safe with cancellation-before-submission release. Unknown qualification stays unknown in the UI. Partial fills, itemised charges (owner schedule only), session honesty after restart, hash navigation, and non-destructive backup/restore-check are implemented and tested.

Critical independent-review finding C1 (broken calendar silently skipped D42 expiry on the desk path) was fixed and re-verified. Checklist answers are no longer invented as `False`.

Follow-up High findings from the Independent Quality Review (agent transcript 201adf76-d411-4f80-971d-978d5facee8d) were closed: backdated fills can no longer exceed the open-position cap; a submitted fill without a calendar is refused; the journal UI records entry prints instead of a bare full-plan `TRIGGERED`.

## B. Workstream results

| Workstream | Status | Notes |
|---|---|---|
| P1-A D42 caps | COMPLETE | Atomic IST monthly + open caps; multi-connection tests |
| P1-B ED-3 zone | COMPLETE | Race-safe reservation; ED-3 release rules preserved |
| P1-C Fail-closed qualification | COMPLETE | Display only; methodology unchanged |
| P1-D Closed-trade allowance | COMPLETE | Frees open slot only |
| P1-E Navigation | COMPLETE | Hash query allowlist + refresh |
| P1-F Restart / session | COMPLETE | Cookie dropped; journal kept; UI clears stale book |
| P1-G Charges | COMPLETE_WITH_LIMITATIONS | No in-repo official tariff |
| P1-H Partial fills | COMPLETE | `journal_executions`; one monthly trade per order |
| P1-I Backup / restore | COMPLETE_WITH_LIMITATIONS | Restore-check proven; no schedule; no bhavcopy archive |

## C. Architecture decisions

Documented as **ED-54** (was a colliding draft id; ED-51 remains P0 gates):

- `BEGIN IMMEDIATE` before reservation / monthly / open counts.
- No permanent unique zone index (preserves cancel-before-submit release).
- Charges only from owner schedule or ACTUAL lines.
- Backup via SQLite backup API; restore-check never swaps live files.
- Desk `_calendar`: configured-but-broken calendar → `DATA_INSUFFICIENT`, not silent skip.
- Desk `_checklist`: every CHECKLIST code must be an explicit bool.

## D. Implementation (this completion pass)

Touched for gap closure and review remediation:

- `platform/gtf_platform/integration/desk.py`  -  calendar fail-closed; checklist explicit; backup manifest `backup_format` / `created_at`
- `platform/web/src/features/workflow/WorkflowPages.tsx`  -  session clear; plan checklist UI
- `platform/tests/test_product_flow.py`  -  interrupted restore; missing checklist; broken calendar
- `tests/test_research_store.py`  -  tenth-fill race test name
- `nse/docs/ENGINEERING_DECISIONS.md`  -  ED-54
- `docs/product-discovery/p1/*`  -  tracker, matrix, recovery, this report
- `docs/product-discovery/priority-02/REMAINING_DEFECTS.md`  -  aligned with P1 closure

Pre-existing working-tree P1 body in `nse/research/store.py`, `nse/research/charges.py`, and the platform package was reviewed and retained (not discarded).

## E. Testing

| Suite | Result |
|---|---|
| `tests/test_research_store.py` | 78 passed |
| `platform/tests/` | 41 passed |
| `platform/web` vitest | 42 passed |
| `nse.validation.architecture` | PASS (54 modules, 0 violations) |
| `nse.validation.docs_health` | PASS |
| Targeted `run_all` groups (store, architecture, repository, hooks, adversarial, validation_framework, `--no-data`) | see validation log from this session |

Skipped / residual:

- Full `run_all` including local_data may report UNAVAILABLE without owner bhavcopies; that is not a P1 defect.
- Official charge-rate verification against exchange/broker PDFs is NOT VERIFIED in-repo (by design: no hardcoded tariff).

## F. Independent review

Reviewer: independent-reviewer agent.

| ID | Severity | Resolution |
|---|---|---|
| C1 broken calendar fail-open on desk fills | Critical | Fixed; regression test passed; re-confirmed closed |
| H1 duplicate ED-51 | High | Renumbered journal decision to ED-54 |
| H2 cross-DB approve window | High | Accepted limitation; retry `approve:<plan_id>` |
| H3 checklist invents False | High | Fixed; API + UI + test |
| Backdated fill exceeds open cap | High | `_peak_open_from`; `test_a_backdated_fill_cannot_exceed_the_open_position_cap` |
| Missing calendar after submission | High | `ORDER_EXPIRY_UNRESOLVED`; `test_a_submitted_fill_without_a_calendar_is_refused` |
| Journal UI bare TRIGGERED full fill | High | UI posts `/executions` ENTRY prints with quantity |

No remaining Critical. No remaining High except H2 as documented limitation.

## G. P0 compatibility

P0 membership CSVs, certification criteria and research-universe decisions were not modified for P1 acceptance. P1 uses fixtures / labelled test data. `DATA_READY` remains false. `authorises_order` remains false.

## H. Git status

- Branch: `main` (ahead of origin; no push)
- Commits: **none** (no owner authorisation for commit in this conversation)
- Proposed commit boundary (when authorised): platform desk/UI/tests + ED-54 + P1 docs only; do not mix P0 data files

## I. Outstanding limitations (accepted)

1. No backup schedule (`NO_BACKUP_SCHEDULE`).
2. App backup excludes `nse/data/eod/raw/`.
3. In-memory sessions (D57); restart requires re-bootstrap.
4. Expiry after submission requires a calendar; unset `calendar_dir` refuses submitted fills (`ORDER_EXPIRY_UNRESOLVED`) rather than skipping the check.
5. Approve spans research + platform SQLite; crash window documented; idempotent retry heals.
6. No official charge rates in repository.
7. Bare legacy `TRIGGERED` without prints counts as a full planned fill.
8. Pre-v2 cancelled journal rows may still hold a zone (documented ED-3 migration behaviour).

## J. Next roadmap

Safe to begin GTF P2 (stock analysis / charting) and continue P0 certification in parallel. Do not claim production readiness (P11) or strategy acceptance (P7) from this report.
