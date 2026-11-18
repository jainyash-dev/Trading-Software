# Final validation summary

**Dated 2026-11-11. Branch `main`. HEAD `9e302df1a81c2b13696d8fab61f05d377481be2e`.**

## Full suite

Command: `python3 -m nse.validation.run_all`

| Item | Result |
|---|---|
| Tests ran | 1,313 |
| Failures | 1 |
| Errors | 0 |
| Skipped | 0 |
| Verdict | FAIL, group `repository` only |
| Failing test | `test_repo.Repo.test_root_matches_the_reel` |
| local_data | PASS |
| reference_comparison | PASS. Yahoo INFY rows. Not TradingView parity |
| static_lint | PASS |
| All other groups | PASS, including architecture, data, strategy gates, membership via risk_instruments, backtest, and council |

The failure was a `.DS_Store` file at the repository root. It is a Finder file, not a source or data change. It was removed after the suite. `test_root_matches_the_reel` was then run alone and passed. The full suite was not repeated after that removal.

This failure was not present in the 2026-11-10 full run, which had no `.DS_Store` at the root. It is an environment artifact, not a trading-rule or data defect.

## What the passing groups do not prove

Synthetic and repository tests do not certify the Nifty 100, ISIN joins, corporate-action completeness, TradingView parity, or profitability.
`reference_comparison` matched a Yahoo transcription. That is not external TradingView validation.

Platform tests were not run. No platform file was changed in this pass.
