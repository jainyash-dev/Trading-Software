# P0 final certification report (V3 cycle)

**Date:** 2026-11-15
**Programme status: `P0_CERTIFICATION_BLOCKED`**
**Certified member-dates: 0 of 123,778.** No partial certification: no subset meets D66.

## Separation of claims

| Dimension | Status | Evidence |
|---|---|---|
| Software implementation | Builder 1.6.0 with ED-57 (exact rational ratios) | `nse/research/corporate_actions.py`, ED-57 |
| Software tests | Acceptance mode PASS: 1,481 run, 0 failures, 0 errors, 0 skipped, 27/27 checks (after all code changes) | `evidence/validation_2026-11-15/v3/run_all_acceptance_v3_report.json` |
| Real historical data availability | EOD: 123,395 EQ member-dates held; calendar 123,778 `TRADING_DAY` | build F |
| Owner-approved membership | 231 rows ACCEPTED (D65 + D67); 173/185 periods verified; 121,156 member-dates VERIFIED | `P0_91_MEMBERSHIP_DECISION_AUDIT.md` |
| Verified security identity | 121,323 RESOLVED; 2,455 UNKNOWN (kept unjoined by owner decision; dummy seats) | `P0_IDENTITY_FINAL_REVIEW.md` |
| Corporate-action evidence | 61 events recorded by NSE only; 13 held official documents; no independent pair | `P0_D66_SOURCE_DISCOVERY_REPORT.md` |
| Approved completeness windows | **0** | `completeness.csv` absent; 0 markers |
| Certified member-dates | **0** | build F |
| Excluded member-dates | 123,778: EXCLUDED_CORPORATE_ACTION 121,156; EXCLUDED_MEMBERSHIP 2,622 | build F |
| Historical coverage | Window 2020-12-31..2025-12-31; 164 symbols; 185 periods | `P0_MEMBERSHIP_FINAL_STATUS.csv` |
| Remaining external blockers | D66 source path (BSE paid or a CDSL coverage test); owner rules Q7-Q10 | `P0_OWNER_DECISION_QUEUE_V4.md` |
| Known limitations | 2016 circulars re-served by NSE in 2019 (R-7); release ISINs from bhavcopies; CDSL record-date independence unknown; ED-57 expectations 2-3 await owner sign-off | reports above |

## Why not "partially complete"

Every member-date fails the corporate-action gate: no window has two independent, reconciled, owner-approved sources (D66). Membership and identity progress does not change that, and passing tests are not historical certification.

## Deliverables index (V3)

`P0_V3_BASELINE_AUDIT.md`; `P0_91_MEMBERSHIP_DECISION_AUDIT.md/.csv`; `P0_D66_SOURCE_DISCOVERY_REPORT.md`; `P0_D66_SOURCE_QUALIFICATION_MATRIX.csv`; `P0_D66_REMAINING_GAPS.csv`; `P0_CA_EVENT_REGISTER_V3.csv`; `P0_CA_RECONCILIATION_V3.csv`; `P0_D66_WINDOW_APPROVAL_QUEUE.csv`; `P0_IDENTITY_FINAL_REVIEW.md`; `P0_IDENTITY_BLOCKERS_V3.csv`; `P0_PRICE_INTEGRITY_REPORT_V3.md`; `P0_PRICE_EXCEPTION_REGISTER_V3.csv`; `P0_EQ_SERIES_FINAL_MATRIX.csv`; `P0_MEMBERSHIP_FINAL_STATUS.csv`; `P0_OWNER_DECISION_QUEUE_V4.md`; `P0_CERTIFICATION_READINESS_REPORT.md`; `P0_INDEPENDENT_AUDIT_REPORT.md` (Phase 11 blocked); `P0_SOURCE_TO_OUTPUT_TRACEABILITY.csv`; `P0_AUDIT_EXCEPTIONS.csv`; `P0_FINAL_BLOCKER_REGISTER.md`; `evidence/validation_2026-11-15/v3/`; `P0_CA_SOURCE_LEDGER.csv` (13 documents). Phase 10 (final certification build) was not run because its prerequisites are not met.
