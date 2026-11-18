# Priority-03 blockers

Date: 2026-11-10. These blockers stay open. This mission did not close a release gate.

| ID | Status | What is missing | Effect on validation |
|---|---|---|---|
| B11-R / T-001 | Open. Owner | A human decision on all 271 rows of `nse/data/universe/nifty100_review.csv`. Agent packet verdicts are not decisions. 0 source hashes are filled on the universe file. Phase-01's scratch note says eight periods would stay unverified even after a full accept | No point-in-time Nifty 100 study is certified. Runs are `UNIVERSE_UNVERIFIED` and `SURVIVORSHIP_UNCONTROLLED` |
| Concurrent edit | Open as a process conflict | Another agent wrote `docs/product-discovery/phase-01/` and `platform/` during this audit and started its own `run_all` | This mission did not continue into those files. Do not treat a `report.json` written after 12:07 IST as this mission's isolated data-group result |
| Universe hash gate | Open, not fixed | `universe.load` treats a matching `source_sha256` as verified. It does not read `nifty100_review.csv`. The converter withholds the hash until review | Pasting the withheld hash into the universe file would clear `UNIVERSE_UNVERIFIED` without a human decision. The current file still has blank hashes |
| Walk-forward disclosure | Open, not fixed | `check_folds` does not stop a later in-sample window from covering an earlier out-of-sample window. Fold metrics are printed before the cross-fold cap. The pool drops a later outcome for the same zone | A walk-forward printout can be quoted past those limits. See `WALK_FORWARD_VALIDATION_REPORT.md` |
| Backtest limitation list | Open, not fixed | The result does not copy `HISTORY_STARTS_AFTER_UNRESOLVED_DATE` from the scan. `EXCLUDED_SAME_BAR` is not in `metrics.excluded` | The JSON understates the history cut and the ambiguous-bar count |
| B11-P | Open | Membership before 2020-12-31 | 2016-2020 cannot be an index study |
| CAL-2 / T-002 | Open by owner decision D54 | Classification of 2016-10-28, 2017-10-17, 2018-11-05, 2019-10-25 | `eod_ready` is false. Scans drop history through 2019-10-25 |
| B11-I | Open | Official records for the BAJFINANCE, GRASIM, and YESBANK ISIN breaks | Those symbols are not joined across the break |
| B7 / R-10 | Open | Coverage for 46 symbols with an empty official response. Two multi-month price gaps (ADANIPOWER, CGPOWER) are unexplained. No adjustment policy beyond "do not adjust" | G0 MANUAL where coverage is missing. Trades across a price-scale event are excluded from R |
| B8, B10, B17 / T-005 | Open. BLOCKED_EVIDENCE | TradingView OHLC, SMA, and zone samples | External validation was not performed |
| B12 | Open | A dated cost schedule with sources. Typed percents are not that schedule | Net returns are not claimable |
| B6 / B15 | Open, out of scope | Intraday data | WIT stays BLOCKED |
| Prospective sample | Not started | The 10-setup log has 0 counted rows, and cannot start the count until reviewed membership exists | R5 stays open |
| Platform sample size | Observed, not fixed | `desk.run_backtest` reads `metrics["closed"]`; the engine key is `closed_trades` | The screen can hide the count. The engine label still says the result is not performance evidence |
| Stale readiness text | Observed, not fixed | `readiness.py` still calls P-LOC-2 open | Does not change eligibility. Confuses a later reader |
| Priority-02 browser proof | Still open, not this mission | Screens were not clicked in Priority-02's own report | R3 stays open. This mission did not redo that work |

## Release gates

| Gate | Status |
|---|---|
| R1 Data ready | Open |
| R2 Research ready | Open |
| R3 Application ready | Open |
| R4 Strategy validated | Open |
| R5 Operationally ready | Open |

`DATA_READY` remains false in `eod_coverage` and in the platform overview path. It was not set to true.

## Not blockers for the engine's safety tests

The synthetic and internal research groups re-run in this session passed. That removes "the tests do not run" as a blocker. It does not remove any row in the table above.

## Owner actions, in order

1. Review the universe file, or explicitly keep every scan unverified.
2. Leave CAL-2 unresolved, or supply a classification. Do not infer one from the bhavcopy.
3. Supply TradingView samples if external zone validation is wanted.
4. Supply a dated cost schedule if net results are wanted.
5. Accept or replace the proposed hurdles in `STRATEGY_ACCEPTANCE_CRITERIA.md` before any certified run.
6. Confirm or reject the shadow entry and stop in `PROSPECTIVE_10_SETUP_PROTOCOL.md` before the first counted setup.
