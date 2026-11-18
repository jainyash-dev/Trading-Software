# P2-P4 Independent Review

**Date:** 2026-11-17. **Reviewer:** `independent-reviewer` agent (read-only, did not write the change).
It inspected the code on disk, ran the platform and web test suites, and was asked to attack every area
listed in programme Stage 5.

**Initial verdict:** FAIL (3 Important, 3 Minor). **Re-review after remediation:** PASS. No unresolved
Critical or Important finding.

| # | Severity | Finding | Remediation | Re-review |
|---|---|---|---|---|
| 1 | Important | Plan/journal mirror trusted `entry_id` alone; a recreated or swapped journal reuses entry numbers, so an unrelated plan could be reported IN_SYNC, drawn, and irreversibly CANCELLED | `journal_entry_states` checks symbol, zone_id and the journal idempotency record `approve:<plan_id>`; mismatch -> `JOURNAL_IDENTITY_MISMATCH`, no write. Tests reproduce the exact scenario (`test_ir04_recreated_journal_reusing_entry_ids_is_not_trusted`, `test_ir04_entry_for_another_zone_is_identity_mismatch`) | Fixed |
| 2 | Important | Evidence panel showed Qualification AVAILABLE for a DATA_INSUFFICIENT/BLOCKED symbol, and summarised another symbol's candidates | Qualification follows the bundle check (FAILED/STALE -> UNAVAILABLE); DATA_INSUFFICIENT -> MISSING; BLOCKED/NOT_IN_UNIVERSE -> UNAVAILABLE; no status or partial -> INCOMPLETE. vitest cases added | Fixed |
| 3 | Important (display) | Later-scan comparison crossed trade types and datasets, matched on zone_id only, and called an unevaluated later symbol "zone not a candidate" | Filter on fixture, trade_type, dataset_id; match zone_id + tf; `LATER_RESULT_NOT_EVALUATED` | Fixed |
| 4 | Minor | Journal ZONE_INVALIDATED still drew the plan as live | `journal_zone_invalidated` flag; lines withheld; Plans warning | Fixed |
| 5 | Minor | The cross-fixture TP-010 assertion could not fail | Non-fixture, other-dataset and WIT-75 later scans now cover the symbol with a changed candidate | Fixed |
| 6 | Minor | Plan GET routes write and hold `db_lock` while reading the journal per linked plan | Accepted (idempotent mirror only); documented in `platform/web/docs/LIMITATIONS.md` | Disposition accepted |

Residual risks recorded by the reviewer: recoverable rather than atomic cross-file consistency; on a journal
without `journal_idempotency` only symbol + zone bind a plan; an unknown symbol status string with zero
candidates would show AVAILABLE (the scanner emits only the five canonical statuses). All tests are
synthetic or fixture tests, not external validation.

## Checked and found sound by the reviewer

W/M volume aggregation (excluded sessions, holidays, partial first period, in-progress and truncated
periods); no automatic EXPIRED path anywhere in `platform/gtf_platform`; guarded idempotent mirror and
CONFLICT reporting; startup repair; Journal "Record CANCELLED" goes through the journal's ED-3 rules; plan
overlay eligibility; `scanOutcome` never shows failed/partial/empty/unreadable scans as zero candidates;
canonical status helpers; opportunity timeframe keys; `authorises_order` false on plan paths.

## Defects found by browser validation (not by the reviewer)

- Scanner read non-existent `symbol_status` / `candidate_status` keys (FR-3.3); fixed.
- Opportunity ingest read `timeframe` instead of `execution_tf` / `zone.tf`; fixed.
- Both were masked by hand-written test fixtures using non-canonical keys; regression tests now use real
  `scanner.scan` output or the canonical shape.

## Self-correction

During supplemental browser checks I suspected a crosshair-legend defect (FR-4.2). An A/B rebuild showed the
original code works; the misreading came from my hover point lying outside the viewport. The speculative
change and its test were reverted.
