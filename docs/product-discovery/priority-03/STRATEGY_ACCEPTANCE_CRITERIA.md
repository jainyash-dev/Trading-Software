# Strategy acceptance criteria

Date pre-registered: 2026-11-10. **No performance result has been seen**, because none was calculated. These thresholds are **proposed owner decisions**. They are not statistically derived. They must not be edited after a backtest or after the ten-setup log in order to obtain a pass.

Current status against this framework: **DATA_BLOCKED** and **INSUFFICIENT_EVIDENCE**. Not `VALIDATION_CRITERIA_MET`.

Even a later pass would not be a guarantee of future profitability.

## Status vocabulary

| Status | When it applies |
|---|---|
| NOT_EVALUATED | No audit of this kind has been written |
| DATA_BLOCKED | A required input is missing or unreviewed. This is the current data state |
| METHODOLOGY_FAILED | A confirmed implementation or rule failure that admits bad zones or future data. Not the finding of this audit |
| INSUFFICIENT_EVIDENCE | The book is too small, too concentrated, or too dependent on unverified costs to judge. This is the current performance state |
| PROMISING_BUT_UNVALIDATED | A certified sample cleared the proposed hurdles and the prospective pilot is not finished. Not claimed |
| VALIDATION_CRITERIA_MET | Every row below is met on a pre-registered run. Not a forecast |

## Proposed hurdles

Each row is `PROPOSED_OWNER_DECISION`. The rationale is practical, tied to failures this system can actually measure. It is not a power calculation.

| Hurdle | Proposed bar | Rationale |
|---|---|---|
| Data quality, before any metric | Human acceptance of every membership row in the window. Corporate-action coverage for every symbol that can trade. Identity resolved or the symbol excluded. Calendar either classified or the scan history honestly cut, as ED-44 already does. At least one TradingView zone-and-SMA sample for the execution timeframe recorded under `REFERENCE_VALIDATION_PLAN.md`, with mismatches left as mismatches | Without these, the trades are not known to be the strategy's trades |
| Historical closed trades | At least 100 closed trades from zones that were eligible under the frozen rules | Round convention for "more than a handful". The engine's own `SMALL_SAMPLE` flag is 30, and the code comment says 30 is not significance. 100 is stricter and still not a proof |
| Out-of-sample closed trades | At least 40 of the 100 in pre-registered walk-forward out-of-sample windows | Stops a fully in-sample story. 40 is a proposal, not a computed minimum |
| Independence | At least 20 symbols. No symbol contributes more than 15% of total R. No single quarter contributes more than 40% of total R | The failure mode to catch is a result that is a few names or one period |
| Costs | Expectancy in R positive at the widest predeclared slippage (0.20% per side) **and** a dated schedule. If the schedule is missing, expectancy is not eligible for this row | A result that only works with zero costs is not accepted |
| Profit factor | Not a pass/fail by itself. If it is shown, show it beside expectancy, the loss count, and the excluded-trade count | Profit factor with no losses is undefined in the engine. A high profit factor on a tiny sample is not a hurdle |
| Drawdown | Cumulative closed-trade R drawdown no worse than 10R | One full losing month at the owner's cap of 10 is the unit already chosen for risk. A deeper hole fails this proposal. This is not a rupee limit and not a market-derived value-at-risk |
| Same-bar robustness | Expectancy stays positive under `STOP_FIRST` and does not rely on `TARGET_FIRST`. The `EXCLUDE` column is published beside it. If `EXCLUDE` changes the sign, the result is fragile and this framework does not call it validated | Ambiguous daily bars are common enough to move a short sample |
| Consistency | At least four separate quarters have a positive total R, and at least one of the pre-registered out-of-sample folds is not the source of the entire gain | A single regime should not be the whole case |
| Prospective | The 10-setup log is necessary and not sufficient. Proposed further bar: 30 consecutive eligible setups, including non-triggers, recorded under the frozen protocol, before anyone uses the word promising | Ten observations cannot support the historical hurdles |
| Publication | Every report keeps `NOT_PERFORMANCE_EVIDENCE` until all of the above are met. `HISTORICAL RESEARCH  -  NOT PERFORMANCE GUARANTEE` stays even after that | The label is the control against a green tile |

## What was deliberately not set

- A win-rate minimum. Win rate without the average loss is not an acceptance test.
- A rupee return target.
- A benchmark alpha. No benchmark was specified by the owner, and inventing one after the fact would be fitting.
- A change to zone parameters, gates, or the fresh-zone rule in order to clear a hurdle.

## Change control

If the owner accepts these numbers, write that acceptance into `nse/docs/DECISION_LOG.md` as an owner decision **before** the first certified backtest command. If the owner wants different numbers, change them before that command. A change after the command has been read is a new study, and the old result stays labelled as exploratory.

This file does not record that acceptance. The owner has not signed it.

## Current scorecard

| Hurdle | Met? |
|---|---|
| Data quality | No |
| 100 closed trades on a certified book | Not run |
| Out-of-sample 40 | Not run |
| Concentration limits | Not run |
| Dated costs and 0.20% slippage | No schedule |
| Drawdown | Not run |
| Same-bar pair | Not run on market data. Synthetic tests show the two policies differ, which is why both must be shown |
| Prospective 10, then 30 | 0 recorded |
| Criteria accepted by the owner | No |

Verdict: **INSUFFICIENT_EVIDENCE**, with the data gate **DATA_BLOCKED**.
