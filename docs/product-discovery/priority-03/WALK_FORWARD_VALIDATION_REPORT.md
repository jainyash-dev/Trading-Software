# Walk-forward validation report

Date: 2026-11-10.

**HISTORICAL RESEARCH - NOT PERFORMANCE GUARANTEE**

No walk-forward study was run on NSE data. The sample is not certified (`HISTORICAL_DATA_CERTIFICATION.md`), and running folds on it would produce out-of-sample numbers this mission is not allowed to treat as evidence. The report below is the protocol the code already implements, and the reasons a market run was not started.

## What the implementation does

`run_walk_forward` (`nse/research/backtest.py` lines 741-769):

- Takes folds the user supplies. It does not choose the dates.
- `check_folds` requires `in_start <= in_end < out_start <= out_end` inside one fold. Overlapping out-of-sample windows are rejected (`backtest.py` lines 713-730). It does not reject a later fold whose in-sample window covers an earlier fold's out-of-sample window. Example: February is out-of-sample for fold 1 and in-sample for fold 2. That is not leakage of future bars inside one segment. It does let the same dates be both a test and a later training window. A protocol that claims sealed folds has to forbid that in the fold file. The function will not.
- Each segment is scanned only at candle ends inside its own window, on inputs truncated at the segment end (`_truncate`). Findings dated after the end are removed.
- Candles before the window stay in the input. That is prior history. It is not future data.
- A trade still open at the segment end is `OPEN_AT_END_OF_DATA` and has no R. It is not carried into the next segment. That censors both winners and losers that have not exited. Win rate on a short fold can move because of that censoring.
- Pooled out-of-sample trades keep the earliest row per symbol and zone (`backtest.py` lines 753-759). A later outcome for that zone is dropped. Only `duplicate_zone_signals_dropped` counts it. The dropped row is not in `pooled_out` metrics.
- Each fold's own metrics are computed inside that segment, before the cross-fold cap (`run` at line 671, then `apply_portfolio_rules` on the pool at line 764). The command prints those per-fold metrics (`backtest.py` lines 885-887). Two out-of-sample windows in one IST month can each show a full set of trades while `pooled_out` keeps only the cap. Quote `pooled_out` when the cap matters. Do not add the fold win counts together.
- The same `ExecutionModel` is used for every fold. The function does not fit a parameter on the in-sample window or pick a model from the out-of-sample window. `NO_SELECTION_NOTE` says the user can still do that after reading the output. The engine does not stop the user from doing it.
- Every result carries `NOT_PERFORMANCE_EVIDENCE`.

The command `backtest-walk-forward` writes the JSON and a sidecar `<output>.manifest.json` through `run_manifest.build` (`backtest.py` lines 880-921). The manifest records kind, as-of, parameters, input fingerprints, methodology hashes, code identity, limitations, and output hashes. The walk-forward JSON itself does not contain a separate dataset id field; the sidecar's `dataset_sha256` is the dataset identity.

## Protocol to use later, if the data blockers close

Record, before looking at fold metrics:

| Field | Rule |
|---|---|
| Dataset id | Manifest `dataset_sha256` of the EOD inputs, universe file, calendar, corporate-action file, coverage file, and instrument file actually passed |
| Universe | A human-reviewed membership file. An unreviewed file stays `SURVIVORSHIP_UNCONTROLLED` and is not an acceptance run |
| Research period | State the first candle the scanner will actually use. With the current calendar, history on or before 2019-10-25 is dropped |
| Training and test | Chronological. Out-of-sample starts strictly after in-sample. No shuffle. No out-of-sample window may sit inside a later fold's in-sample window. `check_folds` does not enforce that second rule |
| Warm-up | Do not treat the first 55 weekly bars, or the first three higher-timeframe periods, as a scored sample. The gates already mark short history insufficient; the report must not count those scans as clean signals |
| Methodology version | `models.PIPELINE_VERSION` and the protected-source hashes in the manifest |
| Parameters | One predeclared model. No change after the first out-of-sample trade is inspected |
| Costs and slippage | From `TRANSACTION_COST_MODEL.md`. Hypothetical costs stay labelled |
| Manifest | The sidecar written by the command |

Folds must not be redesigned after seeing which fold made money.

## Why this is not yet evidence

- The Nifty 100 file has no human review, so any fold would be survivorship-uncontrolled.
- Corporate-action coverage is missing for 46 symbols. Those names are not eligible research names.
- There is no sealed holdout from the period in which the code was written. Fixes such as ED-43 and ED-44 were made while this same 2016-2025 archive was being inspected. A walk-forward of rules that were repaired on the full sample is not an untouched future.
- No TradingView check exists, so a fold that looks good can still be scoring the wrong zones.
- No dated costs exist, so out-of-sample R would be gross of real charges except for whatever percent was typed.

## Test evidence

`test_fold_checks`, `test_a_segment_reads_nothing_after_its_window`, and `test_walk_forward_command` live in `tests/test_research_backtest.py`. The backtest group passed this session (78 tests, 0 failures). Those tests use synthetic candles. They show that the split and the manifest writer run. They do not show that the strategy persists out of sample.

## Result of the market walk-forward

Not run. Status: **INSUFFICIENT_EVIDENCE**.

## Owner decision

None. The owner has not been asked to approve a fold calendar, because the universe review is still empty and a fold calendar chosen now could be aimed at a later result. Folds should be written down only after T-001 is done, and before the command is run.
