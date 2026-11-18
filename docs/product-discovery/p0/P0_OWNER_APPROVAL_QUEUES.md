# P0 Batch 6 - Owner approval queues

**Date:** 2026-11-15  
**Rule:** Recommendations are not approvals. Agents create no approval markers and write no ACCEPTED/REJECTED tokens.

---

## Queue A - Corporate-action completeness windows (D66)

No row is ready for approval today. Template for each future proposal:

| Field | Required value |
|---|---|
| Symbol | Exact ticker |
| Date window | YYYY-MM-DD..YYYY-MM-DD |
| Source A hash | SHA-256 of official non-API file A |
| Source B hash | SHA-256 of official non-API file B (distinct) |
| Independence evidence | Distinct paths, distinct bytes, not API-shaped, provenance recorded |
| Reconciliation record | Path + SHA-256; schema `gtf.ca_reconciliation.v1`; status `RECONCILED`; unresolved empty |
| Discrepancies | Confirmation all resolved or EQUIVALENT with documentation |
| Decision-log marker | `- **Completeness window accepted:** <sha_a> <sha_b> <recon_sha> <SYMBOL> <from>..<to>` under a `USER_APPROVED` decision |

**Current queue depth:** 0 proposable windows. Blocked on acquisition authorization (`P0_CA_SOURCE_ACQUISITION_PROPOSAL.md`).

---

## Queue B - Membership ledger decisions

See `P0_MEMBERSHIP_OWNER_DECISION_PACK.md`.

| Bucket | Groups | Owner action |
|---|---|---|
| Evidence sufficient | 24 | ACCEPTED or REJECTED per row_key |
| Evidence insufficient | 14 | Decide only after missing evidence, or leave blank / REJECT |
| Not applicable (counts) | 25 | No membership decision (D60 arithmetic already separate) |

Each card must keep separate:

- membership evidence
- identity evidence
- EQ status
- recommended action (not an approval)

Never combine membership acceptance with identity verification.

---

## Queue C - Exception / optional rules

| Item | Decision type |
|---|---|
| OD-ID-1 / OD-ID-2 | Choose one effective session or keep unjoined |
| OD-PX-4 | Adopt or decline Muhurat/shortened PREVCLOSE rule |
| OD-PX-3 | Optional market-move exception mechanism (none exists) |
| OD-MEM-2/3 | Optional non-tradable seat accounting rule |
| TV-1 | Supply chart exports or leave pending |
| CA acquisition scope | Authorize providers/symbols/windows (`P0_CA_SOURCE_ACQUISITION_PROPOSAL.md`) |

---

No decision-log edits were made in this programme.
