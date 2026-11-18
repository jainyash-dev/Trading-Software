# Prospective 10-setup protocol

Date frozen: 2026-11-10, before any setup in this log has been observed.

This is a manual shadow log for the owner. It is not permission to trade, not a paper-trading engine, and not T-020. The owner remains responsible for every real order. Nothing here places an order. `authorises_order` stays false.

**HISTORICAL RESEARCH  -  NOT PERFORMANCE GUARANTEE**

Ten setups are a pilot. They are not statistical proof, whether they win or lose.

## What was frozen

Rules below are the current GTF implementation plus owner decisions already on record. They are not a new strategy. They are not to be edited after the first outcome is known. A change after an outcome voids the ten and starts a new log.

| Item | Frozen value | Source |
|---|---|---|
| Eligibility | MIT only. Zone from `MtfSnapshot.eligible_after_overlay` for the daily execution timeframe. Qualification through `evaluate_symbol`. Status exactly `ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING` | Current pathway |
| Not eligible | WIT. Tested, invalidated, or unknown-freshness zones. `MANUAL_REVIEW`, `BLOCKED`, `REJECTED`, `DATA_INSUFFICIENT`. G0 MANUAL for corporate-action coverage. A symbol with `ISIN_CHANGED_WITHOUT_RECORD` across the history used. A name in the 46 empty-coverage symbols unless a later verified window covers the scan span | Current gates |
| Universe | A setup counts toward the ten only when the membership row for that symbol and date has a human `ACCEPTED` decision in `nifty100_review.csv`. Until then, log the signal as `UNIVERSE_UNVERIFIED` and do not let it consume one of the ten | D53. Today every row is blank, so the counted sample cannot start |
| Timeframe | Daily execution. Weekly trend gate. Monthly curve. Higher timeframes as the existing conflict and context rules | Existing MIT roles |
| Entry for the shadow P&L | Record the full Rulebook entry range. The single shadow fill, if the next session trades at or below the level, uses the low end of the entry range (`ENTRY_MIN`). This matches the current application route and is declared now so it cannot be chosen after the result | B9 scenario, predeclared. Proposed for the owner to confirm. If the owner rejects it before setup 1, record both ends and compute no single R |
| Stop | `NORMAL_WIDE` (largest normal buffer) as the shadow stop. Record the other printed stops beside it. Do not switch after the trade | B9, predeclared |
| Target | Structural target already on the candidate (G7). No invented target | Existing levels |
| Risk per trade | The owner's stage band. Above the stage maximum is a fail of the plan, not a larger size. Missing stage is MANUAL. No automatic promotion | P-RISK-1 |
| Position size | `risk.plan_trade` floor quantity. If capital cannot fund it, the plan is MANUAL and the size is not cut to fit | `risk.py` |
| Maximum positions | 10 open. 10 triggers per IST calendar month. Independent | D42 |
| One zone | One order | Existing journal rule |
| Exit | Stop or structural target, using `STOP_FIRST` if both could have been touched in one daily bar. Gap through a level uses the open as the proxy (`AT_OPEN`) | B12 baseline |
| Pending order | Expires after 10 verified NSE sessions. A missing or unclassifiable session does not extend it. Revalidate against a later scan before the fill. If the zone is no longer allowed, cancel | D42 |
| Costs | No verified schedule. Columns for brokerage, exchange charges, SEBI, GST, STT, and stamp duty stay blank until a dated source is attached. Do not type a remembered percent into the "verified" column | This mission |
| Slippage | Compute three shadow net-R columns at 0.05%, 0.10%, and 0.20% per side. Do not drop two of them after seeing which is attractive | B12 |
| Invalidation | A completed candle close beyond the distal line invalidates the zone. That is recorded separately from the trade stop | R4 |
| Data to keep | Scan id, dataset id, manifest, as-of, candle source path, calendar label, coverage file hash | Reproducibility |

## What counts as one of the ten

The next eligible setups in time order, with no skipping.

Count a setup when it meets the frozen eligibility row, including a setup whose limit is never touched. Do not count a hand-picked chart. Do not drop a setup because the order expires, the stop is hit, or the zone is invalidated before the fill.

Do not count:

- `UNIVERSE_UNVERIFIED` names, until the review row is accepted.
- Setups whose G0 is MANUAL.
- A second order on a zone that already has one.
- Anything found by looking backward through a favourite period. The log is prospective from the freeze date.

## Record for every setup

Copy this block. Leave outcome fields empty until the path is finished. Do not fill them from memory after the fact without the scan file.

| Field | Value |
|---|---|
| Setup ID | P3-01 … in order |
| Symbol | |
| Detection date (scan as-of) | |
| Scan ID / manifest run id | |
| Dataset ID | |
| Timeframe | D execution |
| Qualification result | Must be `ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING` to count |
| Zone ID | |
| Zone freshness | FRESH, from the overlay |
| Entry condition | Next session trades at or through `ENTRY_MIN`; range also recorded |
| Stop | `NORMAL_WIDE`, and the other printed stops |
| Targets | G7 structural |
| Risk/reward at the shadow entry | |
| Position size | From `plan_trade`, or MANUAL if capital is short |
| Planned holding | Until stop, target, or zone invalidation. No extra time stop was in the rules, so none is added |
| Actual outcome | Filled stop / filled target / expired / cancelled on revalidation / never triggered / ambiguous bar |
| Maximum favourable excursion | Only if measured from held daily bars after the signal. Else `NOT_MEASURED` |
| Maximum adverse excursion | Same |
| Exit reason | |
| Fees | Blank until a dated schedule is cited |
| Slippage columns | 0.05%, 0.10%, 0.20%, all three |
| Evidence | Paths and hashes of the scan JSON and the bhavcopy dates used |
| Notes | |

## Evaluation after ten counted setups

Not written. Counted sample size today: **0**. No outcome exists. When ten have been recorded, the evaluation may describe how many triggered, how many expired, and the three slippage columns. It may not say the strategy is validated. It should recommend a larger prospective sample. The proposed size is in `STRATEGY_ACCEPTANCE_CRITERIA.md` and is not adopted until the owner accepts it.

If the ten include fewer than ten triggers because orders expire, that is a result. It is not a reason to replace them with later winners.

## Owner decisions still required before the first counted setup

1. Accept or reject `ENTRY_MIN` and `NORMAL_WIDE` as the single shadow scenario. Rejection must happen before setup 1.
2. Accept the membership rows that will be allowed into the ten.
3. Name the risk-per-trade and the capital figure the size will use.
4. Attach a dated cost schedule, or accept that the fee cells stay blank and no net rupee result is stated.
