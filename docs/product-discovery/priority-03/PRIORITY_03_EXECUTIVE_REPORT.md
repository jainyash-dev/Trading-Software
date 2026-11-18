# Priority-03 executive report

Date: 2026-11-10. Role: research validation. This is not a feature delivery and it is not a performance claim.

**HISTORICAL RESEARCH - NOT PERFORMANCE GUARANTEE**

## Verdict

The GTF research engine's checked safety rules behave as documented on synthetic tests. That does not show that the methodology finds reliable trades.

| Question | Answer |
|---|---|
| Is the strategy validated? | No. Status: **DATA_BLOCKED** and **INSUFFICIENT_EVIDENCE** |
| Was a historical return calculated? | No. The upstream sample is not certified, and no dated cost schedule exists |
| Did this pass find a rule that lets a tested, invalidated, or unknown zone become eligible? | No, on the paths read and the tests re-run |
| Should development proceed toward manual deployment? | No |
| What should happen next? | Stop performance evaluation on the current files. Restrict any later historical study. Collect the missing owner evidence. Run the prospective 10-setup log only as observation, not as proof |

`NOT_PERFORMANCE_EVIDENCE` stays on every backtest result. `DATA_READY` stays false. Release gates R1-R5 stay open.

## Recommendation

1. **Stop** any use of the current archive as evidence that the strategy works. A number produced from it would mix an unreviewed universe, unresolved calendar dates, uncovered corporate-action symbols, three unevidenced ISIN changes, no TradingView zone check, and owner-typed costs.
2. **Restrict** the historical window. There is no certified 2016-2025 Nifty 100 study. Membership evidence begins on 2020-12-31 and is unreviewed. With the official calendar loaded, a scan drops candles through the last unresolved date before its as-of, which is 2019-10-25, so 2016 through that date is not used as zone or trend history (ED-44).
3. **Continue validation** only as evidence collection: human review of `nifty100_review.csv` (T-001), a dated cost schedule (B12), and TradingView samples under the existing protocol (T-005). Do not change trading rules to improve a backtest.
4. **Collect prospective evidence** with the frozen 10-setup protocol. Ten setups, including failures and orders that never trigger, are a pilot log. They are not a large enough sample to accept the strategy.
5. **Do not correct the methodology** on this evidence. No Rulebook rule was found to be implemented as a false pass. Defects below are labelling, documentation, and missing evidence, not a new entry rule.

## What was inspected before any performance work

At the start of this audit, Priority-01 had no report folder. The task state lived in `nse/docs/REAL_DATA_READINESS.md`, `nse/docs/DECISION_REGISTER.md`, `nse/data/universe/README.md`, and `nse/docs/REFERENCE_VALIDATION_PLAN.md`. While this audit was in progress, another agent wrote `docs/product-discovery/phase-01/` and was also editing `platform/` and running `nse.validation.run_all` in this same working tree. Those phase-01 files were read before this report was closed. They do not close the blockers. Recalculation from the data files, plus that late read, agrees with the blocking claims:

| Task | State on 2026-11-10 |
|---|---|
| T-001 Nifty 100 review | 271 review rows, 271 decisions blank. 0 of 185 universe rows have a source hash. Not certified. Phase-01's review package says the same, and adds that a scratch all-ACCEPTED conversion (not a decision, not re-run here) would still leave 8 periods unverified: the three ISIN breaks and five dummy seats |
| T-002 Dhanteras | Four dates remain `UNRESOLVED`: 2016-10-28, 2017-10-17, 2018-11-05, 2019-10-25. Phase-01 read the circulars and did not reclassify `events.csv` |
| T-005 TradingView | No export. Phase-01 added a 34-row worksheet whose `tradingview_observed` and `result` cells are empty. External validation is **BLOCKED_EVIDENCE** |
| T-014 identity | 219 identity records, all source-verified in `identity_report.json`. Three ISIN changes remain unevidenced: BAJFINANCE 2016-09-09, GRASIM 2016-10-07, YESBANK 2020-03-16. Phase-01 reports search-path fixes in `platform/` and still marks T-014 partial |

Priority-02 is `docs/implementation/` (dated 2026-11-10, same HEAD). It did not decide T-001 or T-002, did not add a TradingView sample, and did not claim `DATA_READY`. Several application screens are marked implemented without a browser pass. This mission did not change the application to fill those gaps.

The working tree was already dirty. Nothing was staged or committed by this mission. No other process was writing source files at the start. By the time the reports were being finished, another agent was writing `docs/product-discovery/phase-01/` and `platform/` and running validation in this tree. This mission stopped there: it did not edit `nse/` or `platform/`, and it did not try to reconcile that agent's uncommitted platform diff. A leftover Vite preview from 2026-11-09 was still listening at the start; it was not treated as a research-tree edit.

## Work log - baseline

| Item | Value |
|---|---|
| Branch | `main`, tracking `origin/main` |
| HEAD | `9e302df1a81c2b13696d8fab61f05d377481be2e` (`latest code`) |
| Staged | none |
| Unstaged and untracked | Owner and prior-agent work already present, including `platform/`, `docs/`, universe files, corporate-action files, and modifications under `nse/research/`. Not reverted |
| Protected Pine SHA-256 | `14293fa5d3c8e5ba9309b45804a840bb5d8c43d47c193ebb6bca0480bc0a5519` (matches `tests/test_repo.py`) |
| Protected Rulebook Markdown | `039883be6b97ca39b00e5afe80f219a5d759dae99fa9c4179475f506a275d54b` |
| Protected Rulebook PDF | `e41cd0e7893513a492a39095c0f771ec67b320f1b51bc356da7c6a2c2946c2fc` |
| Files this mission added | `docs/product-discovery/priority-03/` only |
| Methodology or eligibility change | none |

## Dependency map

`Historical data → instrument identity → calendar → zone detection → qualification → risk planning → backtest → performance evaluation`

| Stage | Module | Can a later stage trust it today? |
|---|---|---|
| Historical EOD | `nse/eod/nse_bhavcopy.py`, `nse/data/eod/` | Raw unadjusted files for 2,462 trading days are loaded and accepted. Not adjusted. Not externally checked against TradingView |
| Identity | `nse/research/instruments.py`, `nse/data/universe/instrument_records.csv` | Usable except three unevidenced ISIN breaks, which fail closed |
| Calendar | `nse/calendar/nse_calendar.py`, `nse/data/calendar/` | 207 confirmed event rows. Four unresolved dates block `eod_ready` and cut scan history (ED-44) |
| Universe | `nse/research/universe.py`, `nifty100_universe.csv` | Point-in-time code exists. Human review is empty, so every scan is `UNIVERSE_UNVERIFIED` |
| Corporate actions | `nse/research/corporate_actions.py` | Records exist for 145 symbols. 46 symbols have an empty official response and are not coverage. Prices are never adjusted |
| Zone detection | `nse/zone-engine/zone_engine.py` | Synthetic tests pass. No TradingView zone sample |
| MTF freshness | `nse/mtf-freshness/mtf_freshness.py` | Overlay can only remove eligibility. Not chart-checked |
| Qualification | `nse/research/qualification.py` via `scanner.scan_symbol` | One pathway. Unknown coverage is G0 MANUAL. Not externally validated |
| Risk plan | `nse/research/risk.py` | Invalid geometry does not become a sized plan. Buffer choice inside the Rulebook range is still a predeclared scenario (B9) |
| Journal limits | `nse/research/store.py` | 10 / 10 caps and one order per zone are in code and in the passing store tests |
| Backtest | `nse/research/backtest.py` | Mechanics tested on synthetic candles. Always labelled `NOT_PERFORMANCE_EVIDENCE` |
| Performance | not run | **Not calculated.** Upstream stages are not certified |

Detail is in the companion reports in this folder. Each report separates observed facts, test results, assumptions, recommendations, and owner decisions.

## Release gates

| Gate | Status | Why it stays open |
|---|---|---|
| R1 Data ready | Open | Universe unreviewed, four calendar dates unresolved, 46 symbols without corporate-action coverage, three ISIN breaks |
| R2 Research ready | Open | Engine tests are synthetic or internal. No independent zone, SMA, or HTF-candle check |
| R3 Application ready | Open | Priority-02 recorded no browser journey. This mission found one reporting mismatch: the platform backtest reads `metrics["closed"]`, while the engine writes `closed_trades`. Not fixed here |
| R4 Strategy validated | Open | Acceptance criteria are proposed, not met. No certified sample |
| R5 Operationally ready | Open | No prospective book has been observed |

## Facts, assumptions, recommendations, owner decisions

**Facts.** Counts in `HISTORICAL_DATA_CERTIFICATION.md` were recomputed from the current files. The coverage JSON's manifest hash matches the current `manifest.csv`. Research test groups listed in `PRIORITY_03_TEST_REPORT.md` passed in this session. No TradingView comparison file exists.

**Assumptions.** Raw unadjusted OHLC stays canonical (D50). STOP_FIRST plus AT_OPEN is the owner baseline (B12). An empty corporate-action response is not evidence of no event. Agent verdicts in `nifty100_review_packet.csv` are not human acceptance.

**Recommendations.** Do not run or quote a full-universe backtest until T-001, a dated cost file, and a minimum TradingView sample exist. Exclude BAJFINANCE, GRASIM, and YESBANK from any joined price history until their ISIN evidence exists. Treat 2016-01-01 through 2019-10-25 as context that the scanner will not use while CAL-2 is unresolved.

**Owner decisions required.** Fill `nifty100_review.csv`. Classify the four Dhanteras dates or keep them excluded. Supply TradingView exports. Supply a dated, sourced cost schedule. Accept or reject the proposed acceptance thresholds before any performance run. Choose whether the prospective log may use the single shadow scenario in `PROSPECTIVE_10_SETUP_PROTOCOL.md`.

## Independent review, after the first draft

Four read-only reviews finished after the first draft. They did not change the verdict. They added disclosure gaps. No code was changed in response.

| Review | What it confirmed | What was added to the record |
|---|---|---|
| Trading-rule audit, agent id 7b7fd0c8-6089-41a8-b21c-10f3bdf6b687 | Tested, invalidated, and unknown-freshness zones stay off the candidate path. G0 is MANUAL without a verified corporate-action window. That closes the P01-H1 hole. `REAL_DATA_READINESS.md` still describes the hole as open | Stale-text note in the correctness audit |
| Data certification, agent id 2d43e40a-c40d-4a43-afc8-4ab5ca0bb924 | 2,478 archives hash-match the manifest. Calendar reconcile found 0 missing trading days. 0 of 271 review decisions are filled. 46 symbols have an empty latest corporate-action response. TradingView evidence is blocked | Raw-byte and session-reconcile confirmation, plus the 10 retry files and the 16 empty-coverage names still on the universe list |
| Backtest review, agent id 04b77084-a286-4764-9a94-f785dc64afa8 | Signals come only from `scan_history`. Caps above 10 are refused. `NOT_PERFORMANCE_EVIDENCE` is unconditional. No Zerodha schedule exists | Walk-forward fold isolation, fold metrics printed before the cross-fold cap, and backtest JSON omitting the scan's own limitation flags |
| Contrarian review, agent id 74bb4e6b-65ee-40d0-ac51-3c8dd59b1cdd | R4 stays open. A 2021-2025 single-name study would still be an assumed daily path without a chart comparison | The membership gate is an empty hash, not a read of `nifty100_review.csv`. Copying a withheld hash into `source_sha256` would clear `UNIVERSE_UNVERIFIED` without a human decision |

The backtest review's proposed code edits were not applied. They do not create a false eligible zone, and another agent was already editing this working tree. `STOP_FIRST` remains the owner baseline. The contrarian review is right that an ambiguous daily bar does not prove the stop was hit. The acceptance rules already require the `EXCLUDE` column beside it, and still do not treat either column as proof.

## What this mission did not do

No broker connection, no paper-trading engine, no new strategy, no parameter search, no edit under `nse/sources/`, no fabricated membership, corporate action, or chart evidence, and no commit.
