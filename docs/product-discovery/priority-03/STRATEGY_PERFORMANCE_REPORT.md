# Strategy performance report

Date: 2026-11-10.

**HISTORICAL RESEARCH  -  NOT PERFORMANCE GUARANTEE**

No performance metric was calculated on historical trades. The backtest label `NOT_PERFORMANCE_EVIDENCE` is unchanged. This report lists the metrics the mission asked for and the reason each one is blank.

## Why the sample was refused

From `HISTORICAL_DATA_CERTIFICATION.md` and `BACKTEST_INTEGRITY_AUDIT.md`:

- Nifty 100 membership is unreviewed, so a run would be `SURVIVORSHIP_UNCONTROLLED`.
- The scanner, with this calendar, does not use candles through 2019-10-25.
- 46 symbols have no corporate-action coverage. G0 is then MANUAL, and those names are not clean eligible trades.
- Three ISINs are not joined.
- There is no TradingView check of the zones that would have been traded.
- There is no dated cost schedule, so a net return cannot be stated.
- Capital is not modelled, so rupee drawdown, exposure, and capital utilisation are not defined.

Calculating a win rate anyway would be a number without a certified book. It was not done. No manifest of a market backtest was produced, because no market backtest was started.

## Metrics

| Metric | Value | Basis |
|---|---|---|
| Trades | Not calculated | No certified run |
| Winning trades | Not calculated |  -  |
| Losing trades | Not calculated |  -  |
| Win rate | Not calculated | Would be misleading alone even after a run |
| Average win | Not calculated | Engine would report `avg_win_r` in R, not rupees |
| Average loss | Not calculated | `avg_loss_r`. An R at or below 0 is a loss |
| Expectancy | Not calculated | `expectancy_r` is mean R of closed trades only |
| Profit factor | Not calculated | Engine returns null, not infinity, when there is no loss |
| Maximum drawdown | Not calculated | Engine drawdown is on cumulative R of closed trades, in exit order. It is not a rupee drawdown |
| Average holding period | Not calculated | The engine does not compute it |
| Exposure | Not calculated | Not implemented |
| Capital utilisation | Not calculated | `CAPITAL_NOT_MODELLED` |
| Monthly trade frequency | Not calculated |  -  |
| Consecutive losses | Not calculated | Engine can compute `max_consecutive_losses` on a real run |
| By timeframe | Not calculated | MIT daily execution is the only unblocked path |
| By symbol | Not calculated |  -  |
| By market regime | Not calculated | No regime definition is an owner-approved input. None was invented |

Gross versus net: `r_multiple` is already net of the typed cost percent and the typed slippage, on both sides. It is not gross, and it is not net of STT, stamp duty, GST, exchange charges, or brokerage minimums. With no typed schedule applied to market trades, there is neither a gross nor a net result.

## What a later report must include before any figure

- Dataset id and manifest.
- Universe file hash and the review status.
- The scan window and the history the scanner actually kept.
- The execution model, including same-bar policy.
- Cost source and whether it is verified or hypothetical.
- Closed trades, excluded trades, ambiguous trades, and trades refused by the caps.
- The sentence **HISTORICAL RESEARCH  -  NOT PERFORMANCE GUARANTEE**.
- `NOT_PERFORMANCE_EVIDENCE` until `STRATEGY_ACCEPTANCE_CRITERIA.md` is both accepted by the owner and met.

## Interpretation

There is no historical equity curve to interpret. Passing unit tests are not a win rate. Ten future setups would not be one either.

## Status

**INSUFFICIENT_EVIDENCE.** Also **DATA_BLOCKED** for a Nifty 100 historical performance claim.
