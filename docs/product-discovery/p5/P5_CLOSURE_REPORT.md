# P5 Final Closure Report - Portfolio and Risk Management

**Date:** 2026-11-16  
**HEAD:** `69858d07ccb016b74bc1d518b66b9948656ad6cf`  
**Git actions:** none (no stage/commit/push)  
**Owner authority:** final acceptance remains with the owner

## Recommendation

**ACCEPTANCE_READY**

P5 is not stamped ACCEPTED here. The engineering closure criteria below are met.

## Implemented capabilities

- Canonical portfolio state from journal executions (`portfolio_at` / `position_book`)
- Weighted average entry; partial entry/exit; remaining quantity; realised PnL
- D42 monthly cap (10) and open-position cap (10), independent; close frees open only
- ED-3 one-order-per-zone, separate from D42
- Two-connection concurrency: race for 10th (one success / one refuse); both refuse an 11th
- PR-007 EOD valuation with `price_date`; STALE vs AVAILABLE; no future closes; no invented prices
- Position remaining risk and market exposure; sector/drawdown UNAVAILABLE
- Portfolio API + UI consistency; `authorises_order=false`
- Dedicated Portfolio UI tests
- Documented EOD STALE policy (`P5_EOD_STALENESS_POLICY.md`)

## Final test evidence

| Evidence | Totals |
|---|---|
| Research store + repo tests | 96 PASS |
| Platform portfolio suite | 17 PASS |
| Platform product-flow + API (closure batch) | 39 PASS |
| Dedicated Portfolio vitest | 10 PASS |
| Full frontend vitest | 58 PASS |
| `python3 -m nse.validation.run_all` | **1482 ran / 0 fail / 0 error / 0 skip** - **PASS** |

## Repository validation

- `test_root_matches_the_reel`: PASS after adding `GTF_ENGINEERING_FIRST_ROADMAP.md` as an intended permanent root document
- `test_no_em_dashes_and_no_personal_email`: PASS after replacing U+2014 in the roadmap and P5 docs
- Architecture docs-health: PASS after removing broken agent markdown links from the review note

## Independent review result

Closure independent review initially flagged Important: portfolio aggregate could read AVAILABLE while positions were STALE. Fixed so aggregate `valuation_state` / `exposure_state` become STALE whenever any open mark is STALE, with reason text. Re-tested. No unresolved critical or important findings.

## Remaining limitations

1. No maximum-age cutoff for STALE marks (documented; needs owner decision to add).
2. Sector / live drawdown UNAVAILABLE by design.
3. Empty open book valuation UNAVAILABLE with reason.
4. No profitability / P0 / R1-R5 claim.

## Acceptance criteria checklist

| # | Criterion | Met? |
|---|---|---|
| 1 | Mandatory P5 functionality implemented | Yes |
| 2 | Financial calculations and risk controls pass | Yes |
| 3 | D42 and ED-3 correct and independent | Yes |
| 4 | Concurrency tests pass | Yes |
| 5 | Portfolio API and UI consistent | Yes |
| 6 | Dedicated Portfolio UI tests pass | Yes |
| 7 | Stale and unavailable data honest | Yes |
| 8 | Repository validation green | Yes |
| 9 | Independent review: no unresolved critical/important | Yes |
| 10 | No P0 / R1-R5 claim | Yes |

## Verdict line

**ACCEPTANCE_READY** - awaiting owner acceptance.
