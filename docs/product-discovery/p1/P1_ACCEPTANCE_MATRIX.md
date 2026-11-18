# GTF P1 acceptance matrix

GTF P1 is application hardening. It is not Product Prompt 01 and it does not certify P0.
Statuses below are evidence-backed for this working tree after the 2026-11-17 closure pass.
A green unit suite alone is not completion. Owner `ACCEPTED` is not claimed here.

| ID | Requirement | Status | Evidence |
|---|---|---|---|
| P1-A1 | Monthly actual-fill cap atomic (IST) | `CONCURRENCY_TESTED` | `store._Immediate` + `_refuse_new_trigger`; `test_two_connections_cannot_both_commit_the_tenth_trigger`; IST month tests |
| P1-A2 | Open-position cap atomic, independent of monthly | `CONCURRENCY_TESTED` | `_open_positions`; open-slot race; eleventh simultaneous position |
| P1-A3 | Rejected / rolled-back writes leave no partial rows | `FAILURE_TESTED` | failed trigger / uncommitted visibility tests |
| P1-A4 | Idempotent retries do not double fills | `FAILURE_TESTED` | identical trigger retry; journal `request_key` |
| P1-A5 | Configured calendar load failure refuses fills | `FAILURE_TESTED` | `test_broken_calendar_dir_refuses_a_fill` |
| P1-A6 | Backdated fill cannot exceed open-position cap | `FAILURE_TESTED` | `_peak_open_from` test |
| P1-A7 | Submitted fill without calendar is refused | `FAILURE_TESTED` | `ORDER_EXPIRY_UNRESOLVED` test |
| P1-H2 | Journal UI records prints, not bare full-plan TRIGGERED | `INTEGRATION_TESTED` | WorkflowPages + product-flow |
| P1-B1 | One order per zone under concurrency | `CONCURRENCY_TESTED` | zone race; ED-3 / ED-54 |
| P1-B2 | Cancel before submission releases; after submission never | `FAILURE_TESTED` | `test_ed3_*` |
| P1-C1 | Unknown / unverified qualification stays fail-closed in UI | `UNIT_TESTED` | `presentStatus`; status tests |
| P1-D1 | Close frees concurrency, not monthly, not submitted zone | `INTEGRATION_TESTED` | partial prints + portfolio |
| P1-E1 | Hash query navigation restores and refreshes | `UNIT_TESTED` | query/navigation tests |
| P1-F1 | API restart drops session; journal survives; safe retry | `INTEGRATION_TESTED` | restart product-flow; bootstrap `replace_all` |
| P1-F2 | Stale portfolio/journal not shown after session loss | `INTEGRATION_TESTED` | WorkflowPages clear path |
| P1-F3 | Re-bootstrap revokes prior digests | `FAILURE_TESTED` | `test_rebootstrap_revokes_prior_sessions` |
| P1-G1 | Charges only from owner schedule or actual lines; absent stays absent | `UNIT_TESTED` (limitation: no tariff) | `test_absent_charges_*` |
| P1-H1 | Partial prints, average price, unfilled qty, one monthly trade | `CONCURRENCY_TESTED` | `test_partial_prints_*`; P5 suite |
| P1-I1 | Backup via SQLite API; restore-check; live protected | `INTEGRATION_TESTED` | backup + interrupted restore tests |
| P1-I2 / T-017 | Representative journal survives restore; record-level proof | `INTEGRATION_TESTED` | `test_backup_restore_preserves_journal_records_and_rejects_incomplete` |
| P1-I3 | Incomplete / empty backup refused | `FAILURE_TESTED` | same test |
| MI-001 | Overview due / running / partial / complete honesty | `INTEGRATION_TESTED` | active_job, scan_due, job_phase; overview API + UI tests |
| MI-010 | DATA_READY derived fail-closed; never invented true | `INTEGRATION_TESTED` | `evaluate_data_ready`; health/overview/datasets |
| T-006 | Both connections refuse 11th trigger | `CONCURRENCY_TESTED` | `test_two_connections_cannot_both_commit_an_eleventh_trigger` (reuse) |
| P1-X1 | `authorises_order` remains false | `INTEGRATION_TESTED` | desk + P5 |
| P1-X2 | Protected Rulebook / Pine untouched | `INTEGRATION_TESTED` | no changes under `nse/sources` |
| P1-X3 | Plan checklist answers are explicit | `FAILURE_TESTED` | missing checklist refused |

## Overall engineering recommendation

**ACCEPTANCE_READY** pending independent review with no unresolved Critical/Important findings and owner decision. Not `ACCEPTED`.
