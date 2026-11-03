---
name: backtest-review
description: Audit backtest design, assumptions, implementation, results, and claims for validity and robustness.
---

# Backtest Review

Use `engineering-council` and `trading-council` together: Combined (Mode A + Mode B), `backtest` workflow.

## Audit Areas

### Data integrity
- Point-in-time universe and survivorship bias
- Look-ahead and leakage, including zone formation/confirmation timing
- Corporate actions, splits, dividends, and adjusted prices
- Missing data, symbol changes, delistings, and duplicate records

### Execution realism
- Entry/exit execution timing
- Gaps
- Slippage
- Brokerage
- Taxes
- Liquidity

### Statistical validity
- Train/validation/test separation
- Walk-forward design
- Parameter overfit
- Benchmark
- Drawdown
- Exposure
- Turnover
- Expectancy
- Trade distribution
- Regime sensitivity
- Reproducibility

## Important Distinction

Separate infrastructure/test success from strategy performance.

Synthetic data validates mechanics, not market edge.

Do not state profitability without real, verified, appropriately controlled results.

Report exact data coverage and limitations.


## Council routing (Combined)

- `/llm-council backtest <code, diff or results file>`.
- Engineering specialists B, C and E review the implementation (`nse/research/backtest.py`,
  `scanner.scan_history`). Trading specialists C, E and F review the methodology and the
  interpretation.
- Evidence:
  ```
  python3 -m nse.validation.run_all --group backtest --group lookahead
  python3 -m nse.research.cli inventory --as-of <last signal date> --window-start <first data date>
  ```
- Check against the repository's own limits, in `nse/docs/RESEARCH_PIPELINE.md` "Backtest
  readiness":
  - every execution assumption is a user input (B9, B12);
  - trades across price-scale events are excluded;
  - without a universe file the result is SURVIVORSHIP_UNCONTROLLED;
  - MANUAL_REVIEW signals had no manual checks.
- Report software correctness and strategy validity as separate statuses (Combined Review
  template).
