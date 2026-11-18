# Backtest integrity audit

Date: 2026-11-10. Module: `nse/research/backtest.py`. No market backtest was run. Synthetic tests in the `backtest` group passed (78 tests, 0 failures) and are mechanics only.

**HISTORICAL RESEARCH - NOT PERFORMANCE GUARANTEE**

The result label `NOT_PERFORMANCE_EVIDENCE` is unconditional (`_limitations`, line 579). This audit does not remove it.

## How a run is built

1. `run` calls `scanner.scan_history`. There is no second eligibility path inside the backtest.
2. The first time a zone appears in an allowed status, that scan's levels are the order (`_from_history`, lines 640-668). One zone, one signal, in that run.
3. `simulate` reads only candles that start after the signal time.
4. A missing calendar is refused, not replaced with a candle count (lines 615-619).
5. Caps above 10, a null cap, or expiry above 10 verified sessions raise `ValueError` (D45).
6. Metrics are R multiples of the simulated records. They are not rupee profit and not a live-account curve.

## Assumptions the code will not invent

`ExecutionModel` requires entry, stop, target, statuses, expiry, `cancel_if_target_first`, gap policy, same-bar policy, cost percent, and slippage percent. Statuses may not include BLOCKED, REJECTED, or DATA_INSUFFICIENT.

Owner baseline, when `execution_policy.owner_grid` is used: gap fill `AT_OPEN`, same-bar `STOP_FIRST`, with `EXCLUDE` as a side-by-side sensitivity, slippage 0.05%, 0.10%, and 0.20% per side, expiry 10, monthly cap 10, open-position cap 10. The grid does not include `TARGET_FIRST`.

`TARGET_FIRST` can still be constructed by a caller. It books the target when stop and target are both inside one bar. That is the optimistic reading. It is not the baseline and it is not what `desk.run_backtest` uses (`same_bar="STOP_FIRST"`).

## Confirmed behaviour

| Topic | Behaviour | Class |
|---|---|---|
| Signal path | `scanner.scan_history` only | PASS (synthetic) |
| Entry | Limit at the chosen level. A bar that opens through the level fills at the open when `gap_fill` is `AT_OPEN`, otherwise at the level. `AT_LEVEL` adds `GAP_FILL_AT_LEVEL_UNTRADED_PRICES` | PASS (synthetic). `AT_OPEN` is a gap proxy, not a print |
| Stop and target | After the fill, a later bar that trades through the stop exits at the stop, or at the open if the open gaps through and the policy is `AT_OPEN` | PASS (synthetic) |
| Same bar, both stop and target | `STOP_FIRST` records a stop. `EXCLUDE` sets `EXCLUDED_SAME_BAR` and no R. `TARGET_FIRST` records a target | PASS for the baseline. `EXCLUDE` removes the trade from win rate and expectancy; it stays visible as an exit reason and in `not_closed` / assumption counts. It must not be the headline result |
| Fill bar that also touches the target, without a stop | `STOP_FIRST` does not book the target. The trade stays open if the data ends. `TARGET_FIRST` books the win. Test: `test_same_bar_policies` | PASS for the baseline. The intrabar order is unknown |
| Shortened session | Cannot supply a fill or exit price. If a level is inside its range, the record stops as `DATA_EXCLUDED_SESSION` | PASS (synthetic) |
| Missing, duplicate, incomplete, or unclassifiable session | The record stops with `DATA_*` and no R. It is not skipped in favour of the next bar | PASS (synthetic) |
| Losing trades | A stop has an R. A trade excluded for a price-scale event keeps `excluded_reason` and a null R. A cap refusal keeps `not_traded.would_have` and is not counted as a win | PASS (synthetic), with the disclosure below |
| Price-scale event during the trade | R is cleared and the trade is excluded (lines 665-668) | Required, because unadjusted prices on the two sides are not one series. Excluded trades must be reported with the metrics. Dropping them can change expectancy |
| Monthly cap | Fill month in IST. The 11th fill is `NOT_TRADED_MONTHLY_CAP`. Selection is fill order, not "the best 10". Label `MONTHLY_CAP_SELECTION_BY_FILL_ORDER` | PASS (synthetic). The Rulebook's human choice of the best 10 is not simulated |
| Concurrency | A trade that exits on the fill bar still counts as open. Pending orders hold no slot | PASS (synthetic). Conservative on the unknown intraday order |
| Closing a trade | Does not free a monthly slot | PASS |
| One zone | `seen` set stops a second order for the same zone in the run | PASS (synthetic) |
| Universe | No universe, an ad-hoc symbol list, or any unverified row adds `SURVIVORSHIP_UNCONTROLLED` | PASS as a label. It does not refuse the run. A reader can still see a win rate beside the label |
| Manual status in `statuses` | Allowed, and adds `MANUAL_REVIEW_SIMULATED` | The platform route does not do this. It allows only `ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING` |
| Costs | One non-negative percent per side, applied symmetrically on entry and exit inside `r_multiple` | Not a dated schedule. See `TRANSACTION_COST_MODEL.md` |
| Capital, quantity, bands, partial fills, tick size, GTT, liquidity | Listed in `EXECUTION_REALISM_GAPS` and not simulated | BLOCKED as realism. R is per share, not a portfolio equity curve |

## Lookahead

Signal candles are cut at `as_of` by the scanner. Outcome candles start after the signal. Revalidation uses later scans that are themselves point-in-time, and only to cancel a pending order (lines 285-290). After the fill, later scans do not change the exit (comment at line 274, test `test_revalidation_cancels_a_pending_order_but_not_a_filled_trade`).

Membership is evaluated on each scan date. Future constituents do not enter `members(as_of)` if the file's effective dates are right. The current Nifty 100 file has empty hashes, so the run is unverified even when the date filter works.

Corporate actions after `as_of` are not passed into the scan. An event between entry and exit excludes the trade rather than adjusting the past.

## Defects

| Item | Class | Correction proposed, not applied |
|---|---|---|
| No engine defect found that uses future bars to create a signal | - | None |
| `TARGET_FIRST` remains a legal model | Residual, not the baseline | Keep it out of any reported scenario. `owner_grid` already does |
| `EXCLUDE` omits ambiguous trades from expectancy | Disclosed sensitivity | Quote `STOP_FIRST` if a result is ever published, and print the excluded count beside it |
| Unverified universe still returns metrics | Label, not a hard stop | Do not publish those metrics. This mission did not add a hard stop, because the label is the existing contract and a refusal would be a behaviour change |
| Platform `sample_size` reads `closed` | Reporting defect in `desk.run_backtest` | Read `closed_trades`. Out of scope for an application edit in this mission |
| Platform backtest passes no universe and no corporate-action file | The engine then marks survivorship uncontrolled, and G0 coverage is unknown, so actionable signals should not appear | Do not treat a zero from that screen as "the strategy had no trades" until the limitations are read |
| `load_model` docstring says omitted caps are not applied | Stale comment. Code applies 10 and 10 | Docstring only, if a later edit touches that function |

## Unresolved assumptions

- Which entry and stop inside the printed ranges (B9). The engine stores the caller's choice. It does not know which choice a trader would have used.
- Whether `cancel_if_target_first` matches how the owner works a GTT. It is a user flag. The platform route sets it true.
- Intrabar order when stop and target are both touched. Baseline is the stop. That is conservative and still not the true path.
- Transaction costs. No schedule is in the repository.
- Portfolio capital. Not modelled, so drawdown in R is not a rupee drawdown and not exposure.

## Added after the quantitative review

These were checked against the current functions. They do not let a tested zone become eligible. They do change how a result can be misread. No patch was applied.

| Finding | Class | Where | What a later report must do |
|---|---|---|---|
| The backtest limitations list is built from the model, the universe object, and the calendar. It does not copy scan limitations | Disclosure gap | `_from_history` lines 672-676. `HISTORY_STARTS_AFTER_UNRESOLVED_DATE` stays on the symbol result inside the scan | State the history cut explicitly. The JSON will not |
| `SURVIVORSHIP_UNCONTROLLED` is added for a missing, ad-hoc, or unverified universe. The scan's own `UNIVERSE_UNVERIFIED` string is not copied | Disclosure gap | `_limitations` lines 589-591 | Read both labels. An empty `source_sha256` produces the backtest label today. Filling that cell from the withheld hash in the notes would clear it without a row in `nifty100_review.csv` (`membership._out_row` blanks the hash until review; `universe.load` only checks the hash) |
| `EXCLUDED_SAME_BAR` has no `excluded_reason`, so `metrics.excluded` does not count it. It is inside `not_closed` | Disclosure gap | `metrics` lines 428-429 | Count exit reason `EXCLUDED_SAME_BAR` separately |
| The first scan on which a zone has an allowed status consumes that zone, including when `plan` then returns no order (`NOT_TRADED_RR_BELOW_2`) | Stricter than the journal | lines 645-656. A journal plan that was never submitted and was cancelled does not hold the zone (`store.py` lines 644-652) | Do not describe the two rules as the same |
| Walk-forward pool keeps the earliest row and drops a later outcome for the same zone | Disclosure gap | lines 753-759 | Use the dropped count. Do not assume the kept row is the only time the zone could have traded |
| Per-fold metrics ignore the later cross-fold cap. `check_folds` allows one fold's out-of-sample dates inside a later fold's in-sample window | Disclosure gap | lines 713-730 and 749-764 | See `WALK_FORWARD_VALIDATION_REPORT.md` |

## What would make a historical result invalid even if the code is right

Using today's constituents for an unverified past, counting `EXCLUDE` or `TARGET_FIRST` as the main case, ignoring `excluded_reason` trades, treating synthetic tests as market edge, or running through 2019-10-25 as if those candles were in the scan history. They are not, once the official calendar is loaded.

## Test evidence

Command and counts: `PRIORITY_03_TEST_REPORT.md`, group `backtest`. Representative test names read in `tests/test_research_backtest.py`: `test_only_candles_after_the_signal_are_read`, `test_same_bar_policies`, `test_a_trade_across_a_price_scale_event_is_excluded_not_counted`, `test_eleventh_fill_in_a_month_is_not_traded`, `test_history_respects_point_in_time_membership`, `test_cap_above_ten_is_refused`, `test_an_incomplete_bar_ends_the_record_instead_of_being_skipped`. The group passed. Individual names were not executed alone in this session.
