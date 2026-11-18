# P0 owner decision pack (post-Batch-6)

**Date:** 2026-11-15  
**Status:** `P0_CERTIFICATION_BLOCKED`  
**Purpose:** Single place for outstanding owner decisions before any CA acquisition authorization.

Agents will not write membership `ACCEPTED`/`REJECTED`, will not write completeness markers, and will not download CA sources until you authorize.

Reviews retrieved (not assumed): independent-reviewer agent `9524e165-d46d-4379-aec7-253cf51e8e7a` **PASS**; contrarian-reviewer agent `c914a68e-0228-41c6-aab3-dbdef7e11b68` **reject historical certification claim / force BLOCKED**. Details: `P0_POST_BATCH_6_STATUS.md`.

---

## Decision 1 - Corporate-action source acquisition

**Not authorized today.**

Read: `P0_CA_SOURCE_ACQUISITION_PROPOSAL.md`, `P0_CA_PROVIDER_COMPARISON.md`.

Please answer:

| # | Question | Your answer |
|---|---|---|
| 1.1 | Authorize new CA evidence acquisition? | YES / NO |
| 1.2 | Source A provider class | NSE circulars / NSDL / CDSL / other: ___ |
| 1.3 | Source B provider class (must be independent of A and of NSE API) | ___ |
| 1.4 | Symbol tranche | 85 verified-period symbols first / all 164 / other |
| 1.5 | Date windows | D59 only (2020-12-31..2025-12-31) / also 2016-2020 context |
| 1.6 | Storage path OK? (`nse/data/corporate_actions/evidence/<provider>/`) | YES / NO / alternate |
| 1.7 | Cost / paid-source limit | ___ |

Until 1.1 = YES with 1.2-1.3 filled, no downloads.

---

## Decision 2 - Membership ledger (24 sufficient groups)

Read: `P0_MEMBERSHIP_DECISION_SUMMARY.md`, `P0_MEMBERSHIP_OWNER_DECISION_PACK.md`.

Counts re-verified: **24** sufficient / **14** insufficient / **25** N/A.

| # | Action |
|---|---|
| 2.1 | For each of 91 sufficient `row_key`s: set `decision` ACCEPTED or REJECTED |
| 2.2 | Do not combine with identity verification |
| 2.3 | Note: acceptance does not certify member-dates under D66 |

Optional later: insufficient groups (dummies, BE-only, BAJFINANCE/GRASIM baseline) - see summary section B.

---

## Decision 3 - OD-ID-1 BAJFINANCE

Read: `P0_IDENTITY_BLOCKER_DECISIONS.md`.

| # | Choice |
|---|---|
| 3.1 | Keep unjoined (fail-closed) |
| 3.2 | OR name one effective session + document id to acquire/hold |

Affected: ~1098 UNKNOWN_INSTRUMENT member-dates in isolated matrix; baseline row blank.

---

## Decision 4 - OD-ID-2 GRASIM

| # | Choice |
|---|---|
| 4.1 | Keep unjoined (fail-closed) |
| 4.2 | OR name one effective session + document id to acquire/hold |

Affected: 1234 UNKNOWN_INSTRUMENT member-dates; baseline row blank.

---

## Decision 5 - Optional exceptions (not required to unblock CA path)

| ID | Choice |
|---|---|
| OD-PX-4 | Adopt / decline Muhurat-shortened PREVCLOSE rule (~700 dates) |
| OD-PX-3 | Add market-move exception mechanism? (none exists) |
| OD-MEM-2/3 | Non-tradable dummy seat accounting rule? |
| TV-1 | Supply TradingView exports or leave pending |

---

## Decision 6 - After CA evidence exists (future)

Only then: per-window marker under a `USER_APPROVED` decision:

`- **Completeness window accepted:** <sha_a> <sha_b> <recon_sha> <SYMBOL> <from>..<to>`

No markers are prepared or written now (0 windows ready).

---

## Validation reminder (not a decision)

| Item | State |
|---|---|
| Builder | 1.6.0 |
| Production summary | 1.5.0 / 0 certified |
| Isolated summary | 1.6.0 / 0 certified |
| Full local-data `run_all` | Not completed |

---

**Stop for owner review.** Reply with decisions 1-4 (and optional 5) when ready. No further autonomous acquisition or ledger writes until then.
