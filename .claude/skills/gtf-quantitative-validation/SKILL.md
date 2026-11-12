---
name: gtf-quantitative-validation
description: "Autonomous quantitative research and strategy validation, including backtest integrity, bias, costs, walk-forward tests, sensitivity and strategy-acceptance language. GTF phase Pn is not Product Prompt n. GTF P7 is the Prompt 02 backtest engine plus Prompts 09, 10 and 11, not Prompt 07. Product Prompt 12 is the prospective shadow log and is not a GTF phase. Also use this skill for GTF P0 when data will be quoted as performance, and for GTF P6 so the journal stays separate from the simulator. Never activate it by matching the number alone."
---

# GTF Quantitative Validation

## 1. Mission and scope

Act as the independent quantitative research and validation lead.

Determine whether the GTF strategy has genuine, reproducible, and statistically defensible historical and prospective evidence. The goal is to decide whether the evidence justifies further research or, later, an owner review of deployment. The goal is not a more attractive backtest.

Do not change zone rules, gates, freshness, risk limits, or buffers to improve a result. Do not search parameters for the combination that maximises historical profit. Do not hide a weak sample, a failed cost test, or an excluded name. Negative findings stay in the report.

A backtest result is not a forecast. It is not permission to trade. `authorises_order` stays false. Nothing in this skill talks to a broker.

This skill owns study design, bias checks, cost treatment, walk-forward accounting, robustness, the prospective log, and strategy-acceptance language. It consumes P0's certified universe. It does not certify market data. Journal and performance reporting (P6) must not mix hypothetical backtest trades with actual fills. Production readiness (P11) must not treat a passing study as an execution approval.

## 2. Activation

Read this skill before designing, running, changing, or quoting a backtest, a walk-forward test, a sensitivity grid, a cost model, a performance number, or the prospective setup log.

GTF phase Pn is not Product Prompt n. Never activate this skill by matching the number alone. GTF P7 is the Prompt 02 backtest engine plus Prompts 09, 10 and 11. It is not Product Prompt 07. Product Prompt 12 is the owner's prospective shadow log. It is not a GTF phase. When that prompt is the task, this skill's shadow-log rules apply and actual fills stay in a different column. The full crosswalk is master-skill section 7.1.

| Roadmap phase | How this skill applies |
|---|---|
| P7 Backtesting and quantitative validation | Primary owner of research integrity, bias checks, costs, walk-forward, out-of-sample tests, sensitivity, and acceptance language |
| P0 Historical data foundation | A data change that will be used as performance evidence must satisfy this skill's prerequisites. Data certification itself is `gtf-p0-data-certification` |
| P6 Trading journal and performance reporting | Realised journal results stay separate from simulated results. The same cost, sample-size, and selection rules apply to anything presented as performance |

Also load this skill when a report mentions win rate, expectancy, drawdown, profit factor, CAGR, or "the strategy works".

Narrower checks still apply. `.claude/skills/backtest-review/SKILL.md` and `.claude/skills/lookahead-audit/SKILL.md` are the focused audits. The `quant-researcher` agent reviews changes to `nse/research/backtest.py`, `nse/research/execution_policy.py`, and `nse/research/risk.py`. This skill is the operating procedure around those reviews. It does not replace them and it does not override the master skill.

## 3. Master skill dependency

Before starting work, read `.claude/skills/gtf-autonomous-project-lead/SKILL.md` in full.

`gtf-autonomous-project-lead` remains the only governance chair. This specialist adds quantitative procedure. It does not override an explicit Rulebook rule, an owner decision, or the master skill. It cannot change approved GTF methodology. It cannot authorize automated order execution. It cannot weaken fail-closed eligibility, the owner caps, or the validation requirements in master-skill section 11.

When instructions disagree, use the master's governance precedence. Explicit Rulebook rules outrank this skill, the master skill, and owner decisions. Owner decisions in `nse/docs/DECISION_LOG.md` outrank a convenient research design and do not override an explicit Rulebook rule. `USER_STATED` is not interchangeable with `USER_APPROVED`. Pine does not override the Rulebook. R-5 stays unresolved. B9 and B12, recorded in `nse/research/execution_policy.py`, are owner execution assumptions. Do not replace them because another assumption backtests better.

Repository safety follows master-skill section 9. A passing batch is not permission to commit. Do not reset, clean, amend, or rewrite history. Do not stage unrelated work. Do not push unless the owner asks. Do not edit `nse/sources/` or the Rulebook PDF.

## 4. Decisions you make, and decisions you do not

### 4.1 Independent authority

You may independently:

- Audit a study for look-ahead, survivorship, same-bar ambiguity, fold overlap, and cap accounting.
- Refuse to quote a metric the code did not calculate.
- Label a run `NOT_PERFORMANCE_EVIDENCE`, `SURVIVORSHIP_UNCONTROLLED`, `SMALL_SAMPLE`, or `DATA_BLOCKED` when the definitions below say so.
- Correct a simulator defect that violates an already approved rule, such as a monthly cap that resets at a fold boundary or a zone counted twice. Add the regression test first.
- Run every predeclared scenario in `execution_policy.owner_grid` and report them side by side. The grid does not pick a winner. You do not pick one after seeing the numbers.
- Split a cost window at a schedule change instead of stretching one rate across a boundary the loader refuses.
- State that a sample is too small, too concentrated, or too dependent on missing costs to support a conclusion.
- Keep rejected, expired, and never-triggered prospective setups in the log.

### 4.2 Owner authorization

Ask the owner, once, with the evidence, before:

- Adopting or changing a strategy-acceptance threshold. The hurdles in `docs/product-discovery/priority-03/STRATEGY_ACCEPTANCE_CRITERIA.md` are `PROPOSED_OWNER_DECISION`. They are not in force. They were written before any performance result existed. Do not treat them as passed or failed until the owner records an acceptance in `nse/docs/DECISION_LOG.md` before the certified run.
- Changing B9 buffer scenarios, B12 same-bar policy, gap fill, slippage set, expiry, or the 10/10 caps.
- Choosing which entry and stop inside the Rulebook ranges a study will use. Those scenarios are declared before the run. Nothing in the code may select them.
- Supplying a dated transaction-cost schedule. No Zerodha tariff is built into the repository. Do not type a remembered percent into a verified column.
- Starting the counted prospective sample. The protocol's own preconditions, including human membership acceptance for that symbol-date, are owner gates.
- Any wording that would authorise live trading, paper execution as if it were real, or automated orders.

A weak result does not need permission to be reported. Report it.

## 5. Data prerequisites

Before any number is presented as historical performance evidence, read `.claude/skills/gtf-p0-data-certification/SKILL.md` and the current certification outputs. Then verify, for the exact study window:

- the certification label (`CERTIFIED_SUBSET`, `COMPLETE_NIFTY100`, or neither)
- point-in-time Nifty 100 membership, not today's constituents
- instrument identity on every symbol-date
- corporate-action coverage status, including empty bodies and unparsed events
- price continuity and the raw-versus-adjusted policy
- calendar alignment, including any unresolved date inside the range
- the exclusion register, so omitted names are visible

Uncertified historical data is not certified performance evidence. A run may still be executed as a mechanism test or an exploratory study. It carries `NOT_PERFORMANCE_EVIDENCE`. The report names the excluded symbols, the excluded dates, and the period that remains. It does not drop those names and then describe the remainder as the Nifty 100.

D59: membership-based research starts 2020-12-31. Earlier as-of dates on a non-ad-hoc universe carry `MEMBERSHIP_BEFORE_PROVISIONAL_WINDOW`. Do not reconstruct 2016-2020 membership from a later list. Candles before the window may warm indicators only when the study says that is what they are doing.

An ad-hoc symbol list is `UNIVERSE_UNVERIFIED`. A backtest on an unverified universe file carries `SURVIVORSHIP_UNCONTROLLED` (ED-46). Do not relabel either run as survivorship-controlled.

Raw unadjusted OHLC is the research price (D50). A trade that stays open across a recorded price-scale event is excluded from metrics by the backtest. Do not adjust the candles so the trade can remain. Do not fill a missing session.

Synthetic or fixture inputs validate mechanics. Any result from them is `FIXTURE_NOT_MARKET_DATA` or the equivalent label the command already prints. They are not mixed into a market table.

## 6. Backtesting architecture

The strategy is the canonical pipeline. The simulator is not a second strategy.

Path for a research decision: `pipeline.run` → `scanner.scan` → `scan_symbol` → `qualification.evaluate_symbol`, with candidates taken only from `MtfSnapshot.eligible_after_overlay`. `nse/research/backtest.py` consumes those point-in-time signals. It does not re-score zones and it does not promote `MANUAL_REVIEW`, `BLOCKED`, or `DATA_INSUFFICIENT` to a fill.

`run` is one window. `run_walk_forward` evaluates user-given folds. `run_sensitivity` evaluates user-given models. The engine selects, optimises, and ranks nothing (`NO_SELECTION_NOTE`).

Keep these layers separate in every report:

| Layer | What it is allowed to decide |
|---|---|
| Strategy | Fresh demand, G0–G8, status from `derive_status`, structural levels already on the candidate |
| Signal timing | A decision uses only information available at that as-of. Scans occur at completed candle ends |
| Entry | The predeclared point inside the Rulebook entry range. Pending orders expire after 10 verified NSE sessions (D42). A missing session does not extend the life |
| Exit | Structural stop and structural target. Same-bar policy below. Gap through a level uses `AT_OPEN` as a gap proxy, not as an observed print |
| Position lifecycle | One actual order per eligible zone (ED-3). After submission, cancellation, expiry, stop-out, or closure does not release the zone allowance. Cancellation before submission may |
| Portfolio | 10 fills in an IST calendar month and 10 open positions, independent (D42, D45, D46). Closing a position releases open-position capacity only |
| Accounting | Costs and slippage as specified below. R is per share until a capital model exists. Do not present per-share R as a rupee equity curve |
| Reproducibility | Input hashes, calendar, universe file, cost schedule source, model fields, code revision, command |

`ExecutionModel` fields that affect a result are part of the method statement: `entry`, `stop`, `target`, `statuses`, `entry_expiry_sessions`, `cancel_if_target_first`, `gap_fill`, `same_bar`, `cost_pct_per_side`, `slippage_pct_per_side`, `monthly_trade_cap`, `max_open_positions`. A report that omits any field that was not left at the owner default is incomplete.

`EXECUTION_REALISM_GAPS` on the result lists what was not simulated. Quote that list. Partial fills, tick size, GTT behaviour, and liquidity are gaps until a tested model exists. Do not narrate them as if they were filled.

WIT stays `BLOCKED`. It is not a backtest universe.

## 7. Look-ahead bias

Every input to a historical decision must have been knowable at that decision time. Investigate the actual call path. A comment that says "point-in-time" is not the check.

Look for:

- Future bars inside an indicator, a zone, or a higher-timeframe candle. Higher-timeframe candles are built from completed daily bars only, calendar-aligned (D23). A weekly or monthly bar that contains the decision day before that day is over is leakage.
- A zone's later touch, breach, or outcome influencing the decision that is supposed to discover the zone.
- Membership, ISIN, or corporate-action knowledge dated after the as-of, including today's Nifty 100 list.
- A signal that fills on the same bar that formed it, unless the approved execution rule explicitly allows that bar and the price path is the conservative one in section 8.
- `recorded_on` used as if it were the market time. ED-6: `recorded_on` does not filter evidence. The market time does.
- A scan that reads the last value of a series without an as-of cut.
- Train-period statistics computed with the out-of-sample window included.

`tests/test_research_lookahead.py` is the regression suite. Run it after any change to as-of handling, candle completeness, higher-timeframe construction, universe membership, or `scan_history`. A new leakage path needs a new test that fails before the fix.

Prefix invariance is the property to protect: extending the file past the as-of does not change the decision at the as-of.

## 8. Survivorship and selection bias

A survivorship-controlled result requires point-in-time constituents for the whole study window, including names that later left the index, were delisted, or were removed. D59 says that evidence does not exist before 2020-12-31, and on or after that date the periods stay `UNIVERSE_UNVERIFIED` until the human review accepts them. Until both are true for the window you are quoting, you do not claim survivorship control.

Also report selection that is easy to miss:

- Symbols dropped because their corporate-action file was empty or their identity was unresolved. Those exclusions are correct. Hiding them overstates the universe.
- A watchlist or an ad-hoc list chosen because the names are familiar.
- A date range chosen after seeing where the equity curve is smooth.
- Missing-data rules that keep winners and skip names with gaps.
- Journal statistics computed only on closed winners.

The exclusion register from the P0 skill is part of the sample description. "N trades" without "M symbol-dates excluded, and why" is not a sample description.

## 9. Same-bar execution and ambiguous outcomes

Daily bars do not order the high and the low. When a stop and a target can both be touched inside one bar, the favourable path is not assumed.

Owner baseline (B12), implemented in `execution_policy.py`:

- `same_bar` baseline is `STOP_FIRST`
- `EXCLUDE` is the sensitivity, reported beside the baseline
- `TARGET_FIRST` exists on `ExecutionModel` and is not in `owner_grid`. Do not adopt it because it improves expectancy
- a bar that opens through a level fills at `AT_OPEN`
- slippage cases are 0.05%, 0.10%, and 0.20% per side, all three, declared before the run

`STOP_FIRST` is a conservative assumption. It is not evidence that the stop was the print that happened. If `EXCLUDE` changes the sign of expectancy, the result is fragile. Say that. Do not drop the `EXCLUDE` column after seeing it.

Entry and exit on the same bar, a stop and a target on the entry bar, and a gap through both levels use the same rule. An ambiguous bar that the model cannot classify is excluded, not filled at the target.

Same-bar tests belong in `tests/test_research_backtest.py` and `tests/test_research_execution_policy.py`. A synthetic bar that proves `EXCLUDE` drops the trade and `STOP_FIRST` keeps the stop is a mechanism test. It is not a market result.

## 10. Walk-forward validation

`check_folds` requires each fold as `(in_start, in_end, out_start, out_end)` with `in_start ≤ in_end < out_start ≤ out_end`. Out-of-sample windows may not overlap, because pooled out-of-sample trades would count twice. Folds are the user's. The engine does not search for a flattering split.

For each fold:

- The in-sample segment is where a predeclared rule may be inspected. It is not a licence to change the Rulebook after seeing it.
- The out-of-sample segment is scanned only at candle ends inside that segment, using data available at each as-of.
- An indicator fitted on in-sample data is frozen before the out-of-sample segment is read. Refitting inside the out-of-sample segment is leakage.
- Overlapping in-sample windows are allowed only when the out-of-sample windows still do not overlap and you state that the in-sample fits are not independent.
- Historical files the decision could not have had, including a later reconstitution notice, stay out of the as-of.

Portfolio accounting across folds (ED-9):

- The monthly cap counts fills in the IST month (`FILL_MONTH_IST`), not signals, and not "trades reset because a new fold started".
- Two out-of-sample windows that split one IST month share one cap of 10. A fold boundary is not a new month.
- The open-position cap is shared across folds the same way. State whether open positions carry into the next fold. If the simulator flattens positions at the boundary, the result is not the owner's portfolio rule, and the report says so.
- Closing a position does not refund the monthly allowance.
- Pooled out-of-sample output keeps one record per symbol and zone id. A zone that would be realised in two folds is not two trades. The dropped duplicate count is part of the result.
- Report fold-level results and the pooled result. Do not publish only the pooled curve.

A walk-forward that was not given folds is not a walk-forward. Do not describe a single in-sample run with a later "holdout glance" as one.

## 11. Transaction costs and slippage

Costs and slippage are different numbers.

`CostSchedule` in `nse/research/execution_policy.py` is dated and instrument-specific. `rate_for` returns a rate only when the whole lookup window sits inside one period that has that instrument type. Overlapping periods are refused. A missing period is refused. A missing instrument key is refused. Do not catch `CostScheduleError` and substitute today's brokerage.

The owner-facing schedule is a separate document the owner supplies. The repository does not contain Zerodha's tariff. The platform backtest route rejects a request that omits `cost_pct_per_side` rather than inventing one.

Before a result is described as using actual known charges, itemise, for each historical period the study touches:

- brokerage
- exchange charges
- securities transaction tax
- GST
- SEBI charges
- stamp duty
- any other charge the schedule names

Each line has an effective date range and the official source. A single percent is acceptable as `cost_pct_per_side` only when the schedule shows it is the sum of those named components for that period, or when the report calls it an undifferentiated owner-supplied percent and does not call it a reconstructed tariff.

Use the rates in force on the trade date. A current schedule applied to every year of the sample is a methodology error. When the schedule changes inside the study, split the window. Do not average two regimes.

Slippage stays in `slippage_pct_per_side`. The required reported cases are 0.05%, 0.10%, and 0.20% per side. Slippage is an assumption about execution shortfall. It is not a statutory charge. Liquidity, spread, and impact are not measured by that percent. If you did not model the order book, say that liquidity was not modelled.

Blank fee cells in the prospective log stay blank until a dated source is attached.

## 12. Performance metrics

Report a metric only when this run calculated it. Copying a figure from an older note, or from a fixture test, is a fabricated result.

When the run did calculate them, and the data prerequisites hold, include:

- number of trades, with closed and excluded counts separate
- win rate
- average win and average loss
- expectancy
- profit factor, beside the loss count, because a book with no losses does not define it
- maximum drawdown, labelled as closed-trade R or as rupees, whichever was actually computed
- CAGR only when a capital curve was computed. Otherwise `UNAVAILABLE`
- exposure and turnover, or `NOT_MEASURED`
- risk/reward at the planned levels
- holding period
- consecutive losses
- the distribution of returns, not only the mean
- breakdowns by symbol, timeframe, setup, and market regime

A market-regime breakdown requires a regime rule written down before the run. A regime discovered from the equity curve is a story, and it is labelled as one.

Always publish the sample size. `SMALL_SAMPLE` fires below 30 closed trades. The code comment states that 30 is not statistical significance. Do not treat a cleared `SMALL_SAMPLE` flag as significance. Win rate and net profit, alone or together, are not a conclusion.

Uncertainty: state the sample size, the concentration (share of total R from the largest symbol and the largest quarter), and the direction of the result under `EXCLUDE` and under 0.20% slippage. If you cannot compute an interval, say the interval was not computed. Do not invent a confidence interval.

Section 13 of the master prompt still applies: no win rate, expectancy, drawdown, or profitability figure without a real dataset, a defined execution model, and a reproducible result. Passing unit tests are not that dataset.

The engine attaches `NOT_PERFORMANCE_EVIDENCE` to every backtest result. Leave it in place until a pre-registered run meets hurdles the owner has already accepted. Reports you write also keep the sentence `HISTORICAL RESEARCH - NOT PERFORMANCE GUARANTEE`, including after a study looks strong. That sentence is a publication rule from the acceptance document. It is not a second engine flag, and a strong table does not remove it.

`NOT_EXTERNALLY_VALIDATED` stays until external parity exists. This skill does not clear it.

## 13. Robustness and sensitivity

`owner_grid` returns every combination of the predeclared entry and stop scenarios, the three slippage rates, and the same-bar pair (`STOP_FIRST`, `EXCLUDE`), in a fixed order. `run_sensitivity` reports them side by side. It does not rank them and it does not select a model.

Vary, and show, only designs that were declared before the results were read:

- the predeclared entry and stop endpoints inside the Rulebook ranges (B9)
- the same-bar pair
- the three slippage rates
- the dated cost schedule against a stated "costs unknown" refusal
- inclusion or exclusion of names the P0 register already excluded, as a coverage statement, not as a search for the profitable subset
- an alternative conservative execution rule that is stricter than the owner baseline, reported as a sensitivity, not smuggled in as the new baseline

Do not add `TARGET_FIRST` to the grid to see if the study survives. Do not move a buffer, a freshness rule, or a gate because a nearby setting has a higher profit. Parameter search of that kind is overfitting even when each individual run is coded correctly.

Timeframe sensitivity stays inside the approved hierarchy (D11, D14, D21). Daily execution with Weekly trend and Monthly context is the MIT study. A different timeframe mix is a different study and needs an owner decision if it changes the methodology.

If the sign of expectancy depends on one symbol, one quarter, one slippage rate, or `TARGET_FIRST`, the finding is fragility. Record it.

## 14. Prospective validation

The frozen protocol is `docs/product-discovery/priority-03/PROSPECTIVE_10_SETUP_PROTOCOL.md`. Re-read it before logging a setup. It is a manual shadow log. It is not a paper-trading engine and it does not place orders.

Product Prompt 12 is this shadow-testing workflow. It is in scope when that prompt is the task. It is recorded separately from the journal. It does not authorise broker integration, order placement, or an automated paper-trading engine. A hypothetical shadow observation and an actual fill stay in different columns. Do not copy one into the other.

Hold the protocol to these rules:

- A setup is written down before its outcome exists. Outcome fields stay empty until the path is finished.
- The eligibility evidence is the scan id, dataset id, manifest, as-of, and file hashes. Do not reconstruct a setup from memory.
- The detection time is the scan as-of, not the time you noticed the chart.
- Rejected, expired, cancelled, and never-triggered setups remain in the log. They are results.
- The counted ten are the next eligible setups in time order. Do not skip a loser. Do not look backward through a favourite period. The log is prospective from the freeze date.
- A setup counts toward the ten only when the protocol's eligibility row holds, including human `ACCEPTED` membership for that symbol-date and a qualification status of `ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING` from the canonical pathway. Until then the row is `UNIVERSE_UNVERIFIED` and does not consume a slot.
- Hypothetical shadow P&L and an actual fill the owner records in the journal are different columns. Do not copy one into the other.
- Rule adherence is a field: did the live decision match the frozen entry, stop, and size rules? A deviation is data.
- The shadow entry (`ENTRY_MIN`) and shadow stop (`NORMAL_WIDE`) are predeclared and still need the owner's confirmation before setup 1, as the protocol says. If that confirmation is absent, record the range and compute no single R.
- Three slippage columns are always computed when a shadow result is computed. Do not delete the unattractive ones.
- Fee cells stay blank without a dated schedule.
- Ten observations are a pilot. They are not validation. The proposed further bar of 30 consecutive eligible setups is not adopted until the owner accepts it.

A change to the frozen rules after the first outcome voids that log and starts a new one. Keep the voided log.

## 15. Strategy acceptance

Do not invent a pass mark. Do not silently promote the proposed hurdles into policy.

The existing proposal, which is not owner-approved, lives in `STRATEGY_ACCEPTANCE_CRITERIA.md`. Its rationale is practical and tied to failures this system can measure. It is not a power calculation. If the owner accepts those numbers, the acceptance is written into `nse/docs/DECISION_LOG.md` before the first certified backtest command. A change after that command has been read is a new study. The old result remains labelled exploratory.

Until that owner decision exists, the only honest status for a market study is one of `NOT_EVALUATED`, `DATA_BLOCKED`, or `INSUFFICIENT_EVIDENCE`. You may describe mechanism tests as mechanism tests.

When you need a word the product roadmap also uses, map it as follows and do not upgrade it:

| Phrase | When it is allowed |
|---|---|
| Research-ready | The study window's data gates and the execution model are specified well enough to run an exploratory or certified study. This is not strategy acceptance |
| Insufficient evidence | The sample, the costs, the universe, or the concentration cannot support a conclusion. This includes `DATA_BLOCKED` |
| Promising but unvalidated | Only the document's `PROMISING_BUT_UNVALIDATED`: a certified sample cleared hurdles the owner has already accepted, and the prospective pilot is not finished. Not available while the hurdles are still proposals |
| Rejected | `METHODOLOGY_FAILED` after a confirmed implementation or rule failure, or an owner decision to reject a study. A weak backtest is insufficient evidence. It is not a rejection of the Rulebook |
| Eligible for prospective observation | The frozen protocol's preconditions for a counted setup are met. Observation is not validation |
| Eligible for a future deployment review | The owner-accepted acceptance criteria are met and the evidence pack is ready for the owner. This skill does not open that review by itself and does not authorise trading |

`VALIDATION_CRITERIA_MET` is reserved for a pre-registered run that meets owner-accepted hurdles. Even that status is not a guarantee of future profitability and is not an execution approval.

A positive backtest never independently authorises live trading, automated execution, or a change to `authorises_order`.

## 16. Quantitative decision protocol

For each research finding, write these twelve items before the conclusion:

1. Hypothesis, stated so that a result could refute it.
2. Dataset, with file hashes and the P0 certification label.
3. Data eligibility, including exclusions.
4. Research period and the as-of rule.
5. Methodology, including the `ExecutionModel` and the fold dates.
6. Assumptions, including gap fill, same-bar policy, and costs.
7. Biases considered: look-ahead, survivorship, selection, overfitting, same-bar optimism.
8. Execution: the command, the code revision, and where the output file is.
9. Alternative assumptions actually run, not merely listed.
10. Uncertainty: sample size, concentration, and what was not calculated.
11. The challenge: what would make this conclusion false, and whether that check was run.
12. Limitations, in the same place as the conclusion.

A conclusion that skips an item is not ready to quote.

## 17. Failure and uncertainty

Fail closed. An unknown input becomes a limitation, an exclusion, or a refused run. It does not become a favourable performance number.

- Missing certification: run only as a labelled mechanism or exploratory study.
- Missing cost schedule: do not invent rates. Expectancy is not eligible for a cost hurdle. The run may still show gross R if it labels costs as excluded.
- `CostScheduleError`: split or refuse the window.
- Ambiguous bar: `STOP_FIRST` in the baseline column, `EXCLUDE` beside it, never the favourable path as the only column.
- Overlapping out-of-sample folds: `check_folds` must keep refusing them. Do not weaken the check.
- Cap exceeded: the extra signal is not a trade. Do not raise the cap.
- Duplicate zone: one outcome.
- A metric you did not compute: `NOT_MEASURED` or omit it. Never zero as a stand-in for "not computed", because zero is a result.
- A failed test: report the failure. Do not delete the test.
- The urge to retune a gate: stop. That is a methodology change.

## 18. Testing and validation

After any change to the simulator, the execution policy, or a study command:

```
python3 -m nse.research.cli backtest --help
python3 -m nse.research.cli backtest-walk-forward --help
python3 -m nse.research.cli backtest-sensitivity --help
python3 -m nse.validation.run_all --group backtest --group lookahead --group strategy_gates --group adversarial
```

The tests have to cover the behaviour, not the function name:

| Behaviour | What a passing test shows |
|---|---|
| Look-ahead | A decision at T is unchanged when bars after T are appended |
| Survivorship | An unverified universe and a pre-window as-of carry the limitation flags, and today's names are not written back into earlier dates |
| Same-bar ambiguity | `STOP_FIRST` and `EXCLUDE` differ on an ambiguous bar, and `TARGET_FIRST` is not the owner baseline |
| Fold overlap | Overlapping out-of-sample windows raise |
| Monthly cap | Fills in one IST month stop at 10 even when two folds share that month. A fold boundary does not reset the counter. Closing a trade does not refund it |
| Open positions | The eleventh simultaneous position is refused. The cap is independent of the monthly cap |
| Duplicate zones | Pooled out-of-sample output keeps one record per symbol and zone id |
| Partial fills | Until a model simulates them, the result lists them under the realism gaps and does not report a partial-fill P&L |
| Transaction costs | A window crossing two schedule periods is refused. A missing source is refused. Slippage is a separate field |
| Historical restrictions | `MEMBERSHIP_BEFORE_PROVISIONAL_WINDOW` and `SURVIVORSHIP_UNCONTROLLED` attach when their conditions hold |
| Reproducibility | The same inputs and model produce the same trades. The manifest records hashes and revision |
| Sensitivity | The grid length equals the declared scenarios times three slippages times two same-bar policies, with no dropped cell |
| Out-of-sample separation | In-sample statistics are not computed from out-of-sample bars |

Run the data groups from the P0 skill when the study claims certified evidence. Report commands and counts. A green backtest group on synthetic trades is a mechanism result. Say that in the same breath as the test count.

## 19. Documentation and audit trail

Write the twelve-point protocol into the study note that already lives with the quantitative reports, or into the next section of the existing priority-03 report set. Do not open a second acceptance document that could drift away from `STRATEGY_ACCEPTANCE_CRITERIA.md`.

Keep the output file, the command, the model, the fold file, the cost-schedule hash, and the data certification label. A number in chat without that bundle is not a finding you may repeat later as fact.

If you fix a simulator defect, record an `ED-<n>` rather than an owner decision, unless the owner changed a rule. Cite the test that failed before the fix.

## 20. Phase completion

P7 is complete for a named study only when:

- the data label is explicit and matches the P0 outputs for that window
- the execution model is the owner baseline plus declared sensitivities, not a fitted one
- walk-forward folds, if claimed, pass `check_folds` and the caps hold across folds
- costs are either a dated itemised schedule or clearly absent
- every quoted metric was produced by the run
- the acceptance status uses section 15 and does not invent a pass
- `authorises_order` is still false
- the tests in section 18 were actually run

P7 complete does not mean the strategy is profitable, and it does not mean P11 may authorise execution. The strongest successful outcome of this skill is an evidence pack the owner can read. Deployment remains an owner decision the production skill is not allowed to shortcut.

P0 can be unfinished and P7 can still run mechanism tests. P7 cannot convert those tests into certified performance. P6 can report journal facts for trades the owner actually recorded. Those facts are not a backtest, and a backtest is not a journal.

## 21. Execution protocol

1. Read the master skill, then this file. If the study uses historical NSE data as evidence, read the P0 skill and the current certification label before choosing a dataset.
2. Record branch, HEAD, and the dirty tree. Do not disturb unrelated work.
3. Write the hypothesis and the dataset scope before running the study.
4. Verify eligibility, calendar, identity, corporate actions, and exclusions. If they fail, label the run exploratory or stop the performance claim.
5. Freeze the execution model, the folds, and the cost source. Then run.
6. Run the alternative assumptions in section 13. Do not add assumptions after seeing a winner.
7. Challenge the result with section 16, item 11.
8. Run the tests in section 18 when code changed. When code did not change, still record the command that produced the numbers.
9. Publish the status from section 15, the limitations, and the file paths. Do not recommend live trading.
10. If the work is a production certification, hand the status to `gtf-production-readiness` as evidence. That skill decides readiness. This skill does not.

A later reader should be able to rerun the command from the note and obtain the same trades.
