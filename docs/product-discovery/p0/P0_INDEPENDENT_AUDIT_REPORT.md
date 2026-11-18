# P0 independent audit report (V3)

**Date:** 2026-11-15.

## 1. Certification source-to-output audit (Phase 11): NOT PERFORMED, BLOCKED

There is no certified population: the certified count is 0, and no final certification build is permitted while the D66 gates are blocked (`P0_CERTIFICATION_READINESS_REPORT.md`). An audit of zero certified rows would prove nothing ("a zero-certified-row PASS is not proof of historical certification"). This phase stays open (`P0_AUDIT_EXCEPTIONS.csv` AX-15).

## 2. What was independently audited this cycle

A separate read-only reviewer agent (it did not write the changes) reviewed twice:

| Scope | Review 1 | Review 2 (after fixes) |
|---|---|---|
| D67: 91 ledger rows | PASS_WITH_FINDINGS (2 major, 1 minor, 1 note) | PASS_WITH_FINDINGS (majors closed; 1 minor fixed; 2 notes) |
| ED-57: exact face-value ratios | **FAIL** (blocker: 2 undisclosed test regressions) | PASS_WITH_FINDINGS (blocker closed; owner sign-off pending) |

The reviewer's own checks included:
- diffing the before and after ledgers;
- verifying all 91 source hashes;
- reading 10 release PDFs (77 rows), all 5 renames and all 9 ISIN-change bodies;
- running the old and the new parser on every part of every subject in all 202 raw bodies (2,326 entries; exactly one difference, VBL 2024-09-12);
- re-deriving all 2,064 `actions.csv` rows;
- checking the regenerated universe (185 periods; only hash and notes changed on 88);
- confirming that the membership-test updates tightened rather than loosened the tests;
- running targeted test modules (corporate actions 10, membership 62, D50 store 6 then 16 tests).

All findings and their dispositions are in `P0_AUDIT_EXCEPTIONS.csv`.

## 3. Traceability available now

`P0_SOURCE_TO_OUTPUT_TRACEABILITY.csv` traces every one of the 123,778 member-dates (from isolated build F/E, identical data) to exactly one of 185 membership periods. For each period it gives the membership source file and SHA-256, the per-gate outcome counts, the corporate-action source file and hash, and the final eligibility. This shows the exclusion decisions are traceable. It is not a certification audit.

## 4. Adversarial checks relevant to future certification (from this cycle)

| Risk | Check | Result |
|---|---|---|
| Wrong ratios | Old vs new parser over all held subjects | Only VBL changed (now exact 2:5) |
| Silent repair | `actions.csv` diff | One line, documented |
| Incorrect ISIN joins | `instrument_records.csv` hash | Unchanged |
| BE/BZ substitution | EQ gate counts | 260 BE-only stay excluded |
| Dummy-seat leakage | Identity and EQ gates | 123 excluded |
| Unjustified zero-event claims | completeness register | Absent; 0 markers |
| Incorrectly included member-dates | certified count | 0 |
