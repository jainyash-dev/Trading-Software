# Priority-03 test report

Date: 2026-11-10. Working tree HEAD `9e302df1a81c2b13696d8fab61f05d377481be2e`. Nothing was staged.

Synthetic and internal tests are not external validation and not a performance result. The runner prints that itself.

## Command that finished

```
python3 -m nse.validation.run_all --group zone_engine --group mtf_freshness --group strategy_gates --group lookahead --group adversarial --group backtest --group store --group risk_instruments --group reports --group integration
```

Started 2026-11-10 06:34:00 UTC. Finished 06:35:17 UTC. Exit code 0. Elapsed about 77 seconds. This finished before the other agent's validation process was observed (that process was running at 12:08 IST / 06:38 UTC).

| Group | Result | Counts |
|---|---|---|
| repository_checks (always run with the suite) | PASS | protected files OK, no staged files |
| zone_engine | PASS | ran 65, failures 0, errors 0, skipped 0 |
| mtf_freshness | PASS | ran 46, failures 0, errors 0, skipped 0 |
| strategy_gates | PASS | ran 82, failures 0, errors 0, skipped 0 |
| lookahead | PASS | ran 13, failures 0, errors 0, skipped 0 |
| integration | PASS | ran 53, failures 0, errors 0, skipped 0 |
| adversarial | PASS | ran 28, failures 0, errors 0, skipped 0 |
| reports | PASS | ran 26, failures 0, errors 0, skipped 0 |
| backtest | PASS | ran 78, failures 0, errors 0, skipped 0 |
| store | PASS | ran 57, failures 0, errors 0, skipped 0 |
| risk_instruments | PASS | ran 130, failures 0, errors 0, skipped 0 |
| local_data, reference_comparison, static_lint | not run | the command did not ask for them |

Totals: ran 578, failures 0, errors 0, skipped 0. Verdict: PASS.

What this covers relative to the mission list:

| Asked | Where it ran |
|---|---|
| Zone engine | `zone_engine` |
| Qualification | `strategy_gates` (`test_research_gates`, `test_research_confluence`) |
| MTF freshness | `mtf_freshness` |
| Instrument identity | `risk_instruments` includes `test_research_instruments` and `test_research_membership` |
| Journal | `store` (`test_research_store`) |
| Backtest, walk-forward, sensitivity | `backtest` (`test_research_backtest`, `test_research_execution_policy`) |
| Lookahead, caps, ambiguous candles, manifests | `lookahead`, `backtest`, `reports` (`test_research_run_manifest`) |
| Corporate-action coverage unknown does not pass | asserted in `tests/test_research_gates.py`, which is inside the passing `strategy_gates` group |
| Calendar file tests, bhavcopy load tests | not in this command |

No assertion was weakened. No new regression test was added. No confirmed eligibility defect required one.

## Command that was stopped

```
python3 -m nse.validation.run_all --group data --group data_readiness
```

Started 2026-11-10 06:37:16 UTC. Stopped by this mission after another agent in the same working tree started its own `run_all`, including `data` and `data_readiness`. No verdict was printed. That run is **not** a pass and **not** a failure. It is **not recorded**.

Because of that overlap, this mission does not claim a fresh calendar, bhavcopy, or eod-coverage test result. File counts and the coverage JSON hash check are in `HISTORICAL_DATA_CERTIFICATION.md`. They are not a substitute for the test group.

## Not run

- `python3 -m nse.validation.run_all` (full suite, including legacy day-trader tests)
- `python3 -m nse.validation.run_all --acceptance`
- `python3 -m pytest -q -p no:cacheprovider`
- A market backtest, walk-forward, or sensitivity command

## Protected files

Hashes at the start of the audit matched `tests/test_repo.py`. This mission did not write under `nse/sources/` and did not write the Rulebook PDF. The passing `repository_checks` line above is from the finished command, which calls `protected.check()`.
