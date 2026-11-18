# Research engine correctness audit

Date: 2026-11-10. Read against the current working tree at HEAD `9e302df`.

A **PASS** here means the code path matches the documented rule and a regression test exists. It does not mean the rule matches a TradingView chart or a live NSE outcome. Synthetic tests are marked as such.

Production path, unchanged: `pipeline.run` → `scanner.scan` → `scan_symbol` → `qualification.evaluate_symbol`. `AUTHORISES_ORDER = False` in `nse/research/pipeline.py` line 32.

## A. Zone engine and freshness

| Rule | Class | Code | Test evidence | Limitation |
|---|---|---|---|---|
| Only a fresh, active demand zone with an unconflicted 7/7 core can be engine-eligible | PASS (synthetic) | `nse/zone-engine/zone_engine.py` `_assess`, lines 761-783 | `zone_engine` group, 65 tests, 0 failures, this session | Not compared with the Pine indicator on a chart (B10) |
| Supply zones are context, not long candidates | PASS (synthetic) | same function, lines 761-764 | same group | External zone sample missing |
| Tested demand (`fresh` false) is `INELIGIBLE` | PASS (synthetic) | lines 772-774 | zone engine tests; adversarial group 28 tests, 0 failures | Freshness is the engine's own touch count, not a TradingView "tested" mark |
| Invalidated demand (`active` false) is `INELIGIBLE` | PASS (synthetic) | lines 769-771 | same | Same limit |
| `as_of` drops candles whose close is later | PASS (synthetic) | `run_engine`, lines 812-813 | lookahead group, 13 tests, 0 failures | Caller must stamp close time, as the docstring says. A mis-stamped bar would be used early |
| Overlay eligibility is the engine's eligible list minus zones the overlay does not treat as fresh | PASS (synthetic) | `mtf_freshness.py` `eligible_after_overlay`, lines 250-256 | `mtf_freshness` group, 46 tests, 0 failures | HTF candle boundaries are not checked against TradingView (B8) |
| Manual-review zones stay out of the eligible list | PASS (synthetic) | `manual_review_after_overlay`, lines 258-265 | gates and adversarial tests | A scanner may still surface them as manual |
| Incomplete candle through the proximal line does not count as a completed test, and G1 is not a plain PASS | PASS (synthetic) | `incomplete_touches`, lines 239-247; `qualification._g1` | gates tests | - |
| Demand/supply pattern geometry, base bounds, and leg-out counting versus the Rulebook and Pine | NOT independently re-derived in this pass | `zone_engine.py` detector | Existing synthetic suite passed | **BLOCKED_EVIDENCE** for external parity. This audit did not re-prove every pattern branch from the Rulebook text |

Qualification reads execution zones only from `eligible_after_overlay` and `manual_review_after_overlay` (`qualification.py` around the `kept_e, blocked_e = snap.eligible_after_overlay(exec_tf)` call). `_g1` raises if a kept zone is not a fresh demand zone (lines 171-172).

## B. Qualification G0-G8

| Rule | Class | Code | Test evidence | Limitation |
|---|---|---|---|---|
| WIT is blocked at G0 | PASS (synthetic) | `_g0`, lines 119-121 | gates group, 82 tests, 0 failures | WIT remains out of scope |
| Data-quality errors and a missing execution series are `DATA_INSUFFICIENT`, and later gates are `NOT_EVALUATED` | PASS (synthetic) | `_g0` lines 122-128; `evaluate_symbol` lines 537-538 | `test_truncated_execution_series_is_data_insufficient` and related cases in `tests/test_research_gates.py` | - |
| No calendar, or unresolved calendar dates, are G0 MANUAL | PASS (synthetic) | `_g0` lines 130-133 and 157-159 | `test_no_calendar_or_unresolved_dates_need_review` | - |
| A recorded corporate action or PREVCLOSE discontinuity in the history is G0 MANUAL. Prices are not adjusted | PASS (synthetic) | `_g0` lines 134-141 | research data tests (see test report for the data group) | Adjustment policy is intentionally absent (D50) |
| Missing coverage, or a symbol outside a verified window, is G0 MANUAL. An empty official response is not coverage | PASS (synthetic). This closes the older P01-H1 gap in the current code | `_g0` lines 147-156 | `test_corporate_action_coverage_unknown_unverified_and_covered` asserts the status is not `ACTIONABLE` | The check is only as good as `coverage.csv`. 46 symbols have no window |
| Most restrictive gate wins. MANUAL, FAIL, BLOCKED, and DATA_INSUFFICIENT cannot become actionable. A `NOT_EVALUATED` gate cannot either | PASS (synthetic) | `models.derive_status`, lines 192-207 | gates and adversarial groups | The best status is still `ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING`, with checklist items outstanding |
| G0 MANUAL does not skip G1-G8 | PASS as designed | `evaluate_symbol` lines 537-548. Only `DATA_INSUFFICIENT` stops the later gates | status assertion above | Later gate text can still be read. It cannot upgrade the status |
| Unknown HTF zone status does not pass coinciding | PASS (synthetic) | `_g6` lines 361-364 | gates group | - |
| Opposing Pine-only zone in the conflict band is G5 MANUAL, not a target and not a silent pass | PASS (synthetic) | `_g5` lines 314-327 | gates group | D43 |

No tested, invalidated, or unknown-freshness zone was found on a path into `eligible_after_overlay`.

## C. Lookahead and leakage

| Path | Class | What the code does | Evidence | Limit |
|---|---|---|---|---|
| Future daily bars in a scan | PASS (synthetic) | `mtf_freshness.replay` keeps candles with `end <= as_of` (lines 480-482). `scan_symbol` calls that replay | `tests/test_research_lookahead.py` in the passing lookahead group. Prefix invariance is what that module is written to check | Not re-proved here by a new fixture |
| Future findings | PASS (synthetic) | `inp.findings_at(config.as_of.date())` | same group | - |
| Future corporate actions | PASS (synthetic) | `corporate_actions.in_history` is called with the as-of date as the end (`scanner.py` lines 249-251) | data tests cover the interface | There is no adjustment, so a later event cannot rewrite an earlier price. It also cannot repair a price that should have been adjusted |
| Future index membership | PASS for the function | `Universe.members` keeps rows whose effective interval contains the as-of date (`universe.py` lines 47-52). `scan_history` passes the universe into each scan | `test_history_respects_point_in_time_membership` is in the passing backtest module | The file's rows are unverified, so the label is `UNIVERSE_UNVERIFIED` even when the date filter is right |
| Unresolved calendar date | PASS as a restriction | `_last_unresolved_date` then drops candles on or before that date (`scanner.py` lines 224-234) | implementation of ED-44 / D54 | This is why a later scan does not use 2016 through 2019-10-25 as history |
| SMA | PASS (synthetic) | `trend.reading_from_closes` uses completed closes. Fewer than 55 candles is `INSUFFICIENT_HISTORY`, not sideways (`trend.py` lines 12-13, 78-80) | gates group | SMA values are not checked against TradingView |
| Backtest fills | PASS (synthetic) | `simulate` reads candles with `start > signal_end` (`backtest.py` lines 206 and 264-266) | `test_only_candles_after_the_signal_are_read` | Same-bar path after the signal is an execution assumption, not a signal input |
| Walk-forward segment | PASS (synthetic) | `_truncate` drops candles and findings after the segment end (`backtest.py` lines 699-706). `check_folds` requires in-sample to end before out-of-sample and rejects overlapping out-of-sample windows (lines 713-730) | `test_a_segment_reads_nothing_after_its_window`, `test_fold_checks` | Candles before the window remain, which is history, not future data. Open trades are censored at the window end |

## D. Risk

`risk.plan_trade` (`nse/research/risk.py` lines 195-209) refuses non-finite or non-positive entry or stop, a non-finite target, and a stop that is not below the entry. Quantity is a floor division of risk-per-trade by the risk distance. A zero quantity is FAIL. Capital that cannot fund the risk-sized quantity is MANUAL, and the size is not silently reduced. A derivative flag is FAIL. The plan sets `approved` false on invalid levels.

Class: **PASS (synthetic)** for invalid-geometry refusal. The `risk_instruments` group ran 130 tests with 0 failures. Buffer endpoints inside the Rulebook ranges remain a predeclared choice (B9), not a single Rulebook price. Class for "one true entry price": **MANUAL / owner scenario**, not a defect.

## E. Journal and trade limits

| Rule | Class | Code | Test evidence |
|---|---|---|---|
| 10 triggers per IST month, counted with the insert under `BEGIN IMMEDIATE` | PASS (synthetic) | `store.py` lines 832-860 | store group, 57 tests, 0 failures, including the two-connection case that this block was written for |
| 10 open positions, independent of the monthly count | PASS (synthetic) | same block, lines 858-860 | store group |
| Closing a position does not return a monthly slot | PASS as designed | monthly count is triggers in the IST month, not open positions | backtest `apply_portfolio_rules` counts fills and does not decrement the month when a trade exits |
| One order per zone while a prior entry holds the allowance; a never-submitted cancel does not hold it | PASS (synthetic) | `store.py` lines 644-652 | store group |
| Fill after 10 verified sessions is refused | PASS (synthetic) | `store.py` around `verified_sessions_after` and `ORDER_EXPIRED` | Priority-02 re-ran `test_fill_after_ten_verified_sessions_is_refused_and_expired_still_records`; this session's store group also passed |
| Events must be chronological; stop locks after trigger | PASS (synthetic) | `journal_event`, lines 808-827 | store group |
| Backtest refuses caps above 10 or a missing calendar | PASS (synthetic) | `ExecutionModel.__post_init__` lines 154-169; `run` path lines 615-619 | `test_cap_above_ten_is_refused`, `test_invalid_rule_values_are_refused` |

## Confirmed defects

No defect was confirmed that makes a tested, invalidated, or unknown zone eligible, or that lets unknown corporate-action coverage pass G0.

Documentation drift, not a behaviour change:

- `backtest.load_model`'s docstring still says omitted portfolio fields are "not applied". The code and `test_old_model_json_loads_and_lists_rules_not_applied` apply the owner limits of 10 and 10. The test name describes the old behaviour.
- `scanner.scan_history`'s docstring still says fills are not implemented. Fills live in `backtest.py`. The scan function itself still only scans.
- `readiness.py` still lists P-LOC-2 as an open human decision. The decision register records it as approved on 2026-11-08. This audit did not re-open the rule. The readiness sentence is stale.

Application reporting, left unchanged because Priority-03 does not repair the application:

- `platform/gtf_platform/integration/desk.py` `run_backtest` returns `sample_size` from `metrics.get("closed")`. The engine key is `closed_trades` (`backtest.metrics`, line 424). The sample size shown by that route is empty even when the engine counted trades. The route does set `not_performance_evidence` true and does not pass a universe, so the engine also attaches `SURVIVORSHIP_UNCONTROLLED`.

## Added after the rule audit

The rule audit read the same functions and did not re-run the tests. This session had already run them. Nothing in that reading contradicts the table above.

`nse/docs/REAL_DATA_READINESS.md` still says, in Gate F and section C.6, that G0 can PASS with no corporate-action file. The current `_g0` does not. The document is stale. The gate is not.

A verified coverage window with an empty event list can still G0 PASS. An action the official file omitted would be invisible. That is the recorded limit R-10, not a new hole.

At VLOC, a sideways or down weekly reading is forced to MANUAL even where a Rulebook cell would execute. The result is review, not an actionable candidate. It was not changed.

## What was not marked correct

Pattern-by-pattern Pine parity, SMA numeric parity, HTF candle parity, and any claim that a passing unit test is a market result. Those are **BLOCKED_EVIDENCE** or **NOT_TESTED** on real charts.
