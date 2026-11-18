# Sensitivity and robustness analysis

Date: 2026-11-10.

**HISTORICAL RESEARCH - NOT PERFORMANCE GUARANTEE**

No sensitivity case was run on market data. Doing so would rank assumptions on an uncertified universe and publish the best-looking one by implication. The engine is built not to rank. This report keeps that rule.

## What is already distinguished

| Kind | Examples | May it change a trading rule? |
|---|---|---|
| Predeclared methodology | Fresh demand only, G0-G8, owner caps of 10 and 10, raw prices, STOP_FIRST as the baseline same-bar rule | No. Already owner or Rulebook |
| Research-only sensitivity | `EXCLUDE` instead of `STOP_FIRST`; slippage 0.05%, 0.10%, 0.20% per side; entry and stop endpoints inside the printed ranges | No. `owner_grid` reports every combination and does not pick one |
| Hypothetical | Any cost percent without a dated source; `TARGET_FIRST`; `AT_LEVEL` gap fills | No. Must stay labelled. `TARGET_FIRST` and `AT_LEVEL` are legal models and are not in `owner_grid` |
| Owner-approved rule change | None in this mission | Would need a new owner decision |

`run_sensitivity` (`backtest.py` lines 772-786) simulates one signal history under each supplied model, in the order given. The note says the runs are not ranked. `test_side_by_side_in_input_order_with_no_ranking` is in the passing backtest group.

## Cases that matter, and why they were not executed on the archive

| Case | What it would change | Why it was not run |
|---|---|---|
| Cost percent | Net R, not the signal | No verified schedule. A typed percent would be hypothetical |
| Slippage 0.05 / 0.10 / 0.20 | Net R | The set is predeclared, but the trades underneath are not a certified sample |
| Entry delay | Not a parameter in `ExecutionModel`. The order is a limit from the next session | Would be a new assumption. Not added |
| Exit assumptions | `STOP_FIRST` versus `EXCLUDE` | Meaningful only after real signals exist. On synthetic data the unit test already shows `EXCLUDE` drops the ambiguous trade and `STOP_FIRST` keeps the stop |
| Timeframe | MIT daily execution is the implemented path. WIT is blocked | Not varied |
| Zone parameters | Would retune detection | Not permitted as an optimisation |
| Missing sessions | The backtest already stops the affected record | Not a knob |
| Capital | Not modelled (`CAPITAL_NOT_MODELLED`) | A capital sweep would be fictional |

## Fragility checks that cannot be answered yet

These are the checks to apply to a later certified run. They are not results.

- Share of total R from the best three trades, the best three symbols, and the best quarter.
- Sign of expectancy under `STOP_FIRST` and under `EXCLUDE`.
- Sign of expectancy at 0.20% slippage plus the dated cost, not only at the smallest slippage.
- Whether one year's trades are the whole result.
- Maximum closed-trade R drawdown, which is still not a rupee drawdown until capital is modelled.

There is no equity curve to show. Presenting a best scenario is not possible, and it is not the aim.

## Test evidence

Backtest group, this session: 78 tests, 0 failures, including the unranked sensitivity command test. Synthetic.

## Recommendation

When a certified window exists, run the full `owner_grid` for the predeclared entry and stop scenarios and publish every row. If the sign of expectancy depends on which row is quoted, the result is fragile. That finding would count against validation. It would not be a reason to keep the favourable row.

## Owner decision

None required to leave the methodology unchanged. A decision is required before any of these scenarios are attached to a real sample: the dated cost file, and confirmation that `ENTRY` / `STOP` pairs were listed before the run.
