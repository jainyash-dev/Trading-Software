# Research Pipeline: Scanner, G0-G8 Qualification, Reports, Validation

**Status (2026-11-02):** implemented and software-tested on synthetic data, plus one run on
official NSE files (Q1 2022). M1 decisions R1-R6 are product-owner approved. **Not externally validated.** No status the scanner produces
approves a trade. Phase 1 acceptance is unaffected (see `PHASE1_EXIT_CHECKLIST.md`): this is
post-Phase-1 work requested in `CLAUDE.md`.

## 1. Architecture

| Layer | Module | Responsibility |
|---|---|---|
| A. Models | `nse/research/models.py` | Gate outcomes (PASS, FAIL, MANUAL, DATA_INSUFFICIENT, BLOCKED, NOT_EVALUATED), statuses, MIT/WIT roles, limitations, manual checklist, `derive_status` |
| B. Market data | `nse/eod/nse_bhavcopy.py` (existing), `nse/eod/nse_replay.py` (existing), `nse/research/marketdata.py` | Strict bhavcopy loading with manifest provenance; user daily CSVs; dated data-quality findings; candles stamped 09:15-15:30 (audit L7) |
| B. Universe | `nse/research/universe.py` | Point-in-time membership from a sourced file; ad-hoc lists are UNIVERSE_UNVERIFIED |
| B. Calendar | `nse/calendar/nse_calendar.py` (existing) | Official circular tables, hash-verified |
| C. Zones | `nse/zone-engine/zone_engine.py` (existing) | Detection, 7-point core, freshness, invalidation, zone-level eligibility |
| C. Freshness | `nse/mtf-freshness/mtf_freshness.py` (existing; `manual_review_after_overlay` added) | HTF candles, touches from the finest base, gaps, sessions; the **only** source of execution zones |
| D. Top-down | `nse/research/topdown.py` | Y, HY, Q, M, W, D table: nearest fresh zones, availability, unknown-freshness zones |
| D. Analysis | `nse/research/structure.py`, `trend.py`, `levels.py` | Curve, HTF conflict, coinciding; SMA-50 clock; entry / SL / target / R:R ranges |
| E. Qualification | `nse/research/qualification.py` | The one G0-G8 pathway and the alignment matrix |
| F. Scanner | `nse/research/scanner.py`, `cli.py` | Per-symbol replay + qualification; `scan_history` for point-in-time signals |
| H. Reports | `nse/research/reports.py` | Deterministic JSON and CSV |
| Readiness | `nse/research/readiness.py` | Per-capability states, confirmed against a test run |
| Data readiness | `nse/research/inventory.py` (`cli inventory`) | Local EOD and calendar coverage, history needed per timeframe for an as-of, exact acquisition spec |
| Corporate actions | `nse/research/corporate_actions.py` | Records file; an action inside the replayed history makes G0 MANUAL (B7); no adjustment |
| Zone references | `nse/research/refcheck.py` | Compares recorded indicator zones with the replay (P-REF-1); never auto-resolves |
| Backtest | `nse/research/backtest.py` (`cli backtest`) | Point-in-time signals, user-supplied execution model (no defaults), R metrics, in/out-of-sample split |
| Validation | `nse/validation/run_all.py`, `protected.py` | One command for every check |
| Pre-entry X/14 | `nse/research/confluence.py` | Spec 5.3 display; provisional / not evaluated; no gate reads it |
| Risk | `nse/research/risk.py` (`cli risk-plan`) | Rulebook C1 sizing, stage bands, monthly ceiling; separate from G0-G8 |
| Instruments | `nse/research/instruments.py` (`cli instruments-check`) | Effective-dated symbol / ISIN records; consistency with bhavcopies |
| Acquisition | `nse/research/acquisition.py` (`cli acquire-*`, `daily-update`) | Offline inbox: plan, SHA-256, duplicate / revision quarantine, ledger (D31) |
| Scenarios | `nse/research/scenarios.py`, `nse/scenarios/` | Data-driven regression cases through the real pipeline |
| Decision replay, dashboard | `nse/research/decision_replay.py`, `dashboard.py` | Point-in-time bundles; static HTML / SVG |
| Assistant, alerts, narrative | `nse/research/explain.py`, `alerts.py`, `narrative.py` | Evidence-cited answers and self-audit; watchlist alerts; markdown reports |
| Store, journal | `nse/research/store.py` | Optional SQLite: additive migrations, idempotent import, Rulebook journal |
| Health | `nse/research/health.py` (`cli health`) | Checkout health; not validation |
| Agent framework | `.claude/skills/*`, `.claude/agents/*`, `.claude/hooks/*`, `.claude/settings.json` | Skills and agents for autonomous work; deterministic guard hooks |

All modules use the Python standard library only. None imports network, broker or order code
(`tests/test_repo.py` enforces it).

## 2. Workflow

```
daily files (bhavcopy or CSV) --marketdata--> DailyInput + dated findings
   | ERROR finding dated <= as_of -> symbol DATA_INSUFFICIENT (stops)
   v
mtf_freshness.replay(daily base, htf = D W M Q HY Y, as_of, calendar)   [cuts at as_of first]
   |   Zone Engine on every completed series; overlay applies every daily candle to every zone
   v
MtfSnapshot.eligible_after_overlay("D")        -> G2 can PASS
MtfSnapshot.manual_review_after_overlay("D")   -> G2 is MANUAL at best
   (blocked zones are listed with the overlay's reasons, never evaluated)
   v
G0 data  G1 fresh zone  G2 core 7/7  G3 curve  G4 trend + matrix  G5 HTF conflict
G6 coinciding  G7 levels and R:R  G8 red flags / essential checks
   v
status = most restrictive outcome: BLOCKED > REJECTED > DATA_INSUFFICIENT > MANUAL_REVIEW
         > ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING (always with the manual checklist)
   v
scan.json, candidates.csv, fresh_zones.csv, blocked_zones.csv, data_quality.csv,
summary.json, readiness.json
```

MIT: location M, trend gate W (M as context, D21), execution D, target W supply (M as
reference). WIT-75 / WIT-125: location W, trend gate D only (D22), execution 75m / 125m,
target D supply. **WIT is BLOCKED**: no intraday output until the 75/125-minute session and gap
design (audit M4b) is approved. The scanner does not load data for WIT; the gate code still
applies WIT roles so their differences are tested.

## 3. Safeguards

| Risk | Enforcement | Test |
|---|---|---|
| Tested zone as a candidate | Only overlay-kept zones are evaluated; G1 asserts demand, test_count 0, overlay FRESH, no base touch | `test_research_adversarial` q1, q2, sweep; `test_research_integration` |
| Invalidated zone | Same; overlay INVALIDATED is never kept | q2 |
| Unknown freshness (gap, unverified session, pending close) | Overlay status other than FRESH blocks; disposition DATA_INSUFFICIENT | q3; `test_a_missing_session_never_reads_as_fresh` |
| Overlay bypass | `nse/research` never calls `run_engine` or reads the engine's own eligible list | q4; `test_repo` safety boundaries |
| Manual review lost | Gate manual items -> `manual_review`; JSON and CSV carry it | q5 |
| Later gate overriding a failure | `derive_status` takes the most restrictive outcome | `StatusDerivation`, q6 |
| Intraday output | G0 BLOCKED for WIT; scanner returns BLOCKED without data | q7, `Wit` |
| Lookahead | `replay` cuts at as_of; findings dated after as_of are not read | `test_research_lookahead` (prefix invariance, future touch, intraday as_of, incomplete candle, future corrupt row) |
| Missing HTF data as "no conflict" | Missing M/Q/HY -> DATA_INSUFFICIENT; missing W/Y -> MANUAL | q9 |
| Overstated validation | NOT_EXTERNALLY_VALIDATED and TRADINGVIEW_PARITY_UNVERIFIED on every record; readiness keeps external validation False | q10 |
| Unresolved rule defaulting to pass | Every undetermined case returns MANUAL with a reason | q12 and the gate tests |
| Tests that cannot fail | Mutation canaries switch a gate off and require the outcome to change | `TestsExerciseTheirPath` |

## 4. D41 interpretations and M1 approvals

These engineering readings are recorded under **D41** in `DECISION_LOG.md`. Product owner
decisions R1-R6 were approved on 2026-11-02 and are authoritative as recorded in
`DECISION_REGISTER.md`. Other readings in this table remain PROPOSED; approval of R1-R6
does not approve D41 as a whole.

| ID | Reading | Effect | Where |
|---|---|---|---|
| P-TREND-1 / R2 | Pine "12 o'clock" (RB 1688 "Extreme Uptrend") maps to STRONG_UP for the matrix; retain the Extreme label in diagnostics and reports [USER_APPROVED] | Can PASS G4 | `trend.READINGS`, `trend_for`, `reports` |
| P-LOC-1 / R1 | Curve position uses CMP only (RB 1591); execution PL does not influence G3/G4 [USER_APPROVED] | Resolves only the location-reference ambiguity | `qualification._g3`, `_g4` |
| P-LOC-2 | Price inside a TESTED HTF demand zone: VLOC needs a fresh zone (RB 1587, 1597) but the redraw rule (situation 3) describes a bounce; MANUAL [OPEN] | Restricts | `structure.build_curve` |
| P-LOC-3 | A curve boundary of unknown freshness stops the boundary search (MANUAL) instead of being skipped | Restricts | `structure.build_curve` |
| P-MAT-1 / R5 | EQB + Down long rejects under RB 1599 [USER_APPROVED] | Can FAIL | `qualification.matrix_long` |
| P-MAT-2 / R5 | HOC + Up long rejects; HOC + Sideways is MANUAL pending sector support; HOC + Down follows RF3 [USER_APPROVED] | Mixed | `matrix_long`, `_g3`, `_g8` |
| P-COIN-1 / R3 | Actual inclusive range overlap between execution and qualifying HTF demand is COINCIDING; non-overlapping Aggressive remains distinct [USER_APPROVED] | G6 is MANUAL for Aggressive pending its separate Rulebook conditions | `structure.coinciding`, `qualification._g6` |
| P-COIN-2 / R6 | Known absence of qualifying HTF location zone: G6 PASS as Standard; unknown freshness/DL status MANUAL [USER_APPROVED] | Can PASS G6 only; G3 stays independent | `qualification._g6` |
| P-CAL-1 | No calendar: G0 MANUAL (D28 limitations: unverified gaps, undetectable special sessions) | Restricts | `qualification._g0` |
| P-LVL-1 | Buffer tiers: the union of the tiers of PL, normal DL and exceptional DL, tier edges inclusive on both sides (B9) | Widens ranges; more MANUAL | `levels.ranges` |
| P-LVL-2 | Target: nearest FRESH opposing zone with PL above the entry maximum; a tested one is skipped; one of unknown freshness, or inside the entry range, stops the search (MANUAL) | Restricts | `levels.select_target` |
| P-CONF-1 | HTF conflict distances measured from the PL and from both entry bounds; if the band differs between them and that changes the outcome, MANUAL | Restricts | `structure.htf_conflict` |
| P-G8-1 | RF7 (reaction zone with poor closing) is MANUAL whenever the leg-out did not close beyond the leg-in extreme; whether the zone is a "reaction zone" is a human call | Restricts | `qualification._g8` |
| P-DQ-1 | A data-quality finding is dated by the trade date it concerns; an earlier scan does not read later findings (prefix invariance). Undated findings (bad header, bad date) always apply | Neutral | `marketdata.Finding.known_at` |
| P-LVL-3 | Invalid levels (SL <= 0, inverted zone geometry, non-finite price) make G7 MANUAL; no R:R or quantity is computed | Restricts | `levels.problems`, `_g7` |
| P-CA-1 | A price-scale corporate action inside the replayed history (ex-date on or before as_of) makes G0 MANUAL; nothing is adjusted | Restricts | `corporate_actions.in_history`, `_g0` |
| P-REF-1 | Zone references match on timeframe, side and creation period; prices compare exactly unless a tolerance is passed | Neutral (comparison only) | `refcheck.compare_zones` |
| P-BT-1 | A backtest needs every execution assumption from the user; signals come from point-in-time scans, one order per zone | Neutral (nothing runs without inputs) | `backtest.ExecutionModel`, `run` |

## 5. How to run

```
# scan official bhavcopies (local, git-ignored) with the official calendar
python3 -m nse.research.cli scan --as-of 2022-03-31 --symbols INFY,TCS \
    --bhavcopy-dir nse/data/eod/raw --manifest nse/data/eod/manifest.csv \
    --calendar nse/data/calendar --out nse/output/scan-2022-03-31

# scan your own daily CSVs (one SYMBOL.csv each: date,open,high,low,close)
python3 -m nse.research.cli scan --as-of 2024-06-28 --csv-dir path/to/csvs \
    --calendar nse/data/calendar --price-adjustment UNKNOWN --risk-per-trade 1000 --out nse/output/x

# point-in-time membership from a sourced universe file (format: nse/research/universe.py)
python3 -m nse.research.cli scan --as-of 2024-06-28 --universe path/to/nifty100.csv --csv-dir ... --out ...

python3 -m nse.research.cli inventory --as-of 2024-01-31 --symbols INFY   # what data a scan needs
python3 -m nse.research.cli backtest --model model.json --start <d> --end <d> --symbols INFY \
    --bhavcopy-dir nse/data/eod/raw --manifest nse/data/eod/manifest.csv --calendar nse/data/calendar \
    --out nse/output/bt.json       # model.json must set every backtest.ExecutionModel field
python3 -m nse.research.cli manifest-rows <archives> --source-page "<page>" --downloaded-on <date> \
    --provenance-status USER_CONFIRMED [--append]     # provenance rows for new bhavcopies
python3 -m nse.validation.run_all --acceptance --require-window 2021-01-01 2025-12-31   # data window complete?
python3 -m nse.research.cli readiness            # capability readiness table
python3 -m nse.validation.run_all                # every check; report in nse/output/validation/
python3 -m nse.validation.run_all --acceptance   # a missing local prerequisite FAILS
python3 -m nse.validation.run_all --list         # test groups
```
`nse/output/` is git-ignored. `--generated-at` records a label; no clock is read, so the same
inputs give byte-identical reports. Historical point-in-time scans: `scanner.scan_history`.

Added 2026-11-02 (`python3 -m nse.research.cli <command> --help` for every option):
```
python3 -m nse.research.cli health
python3 -m nse.research.cli acquire-plan --start 2021-01-01 --end 2025-12-31 --calendar nse/data/calendar
python3 -m nse.research.cli acquire-ingest <files> --quarantine-dir Q --ledger L.jsonl --source-page "<page>" \
    --downloaded-on <date|UNKNOWN> --provenance-status USER_CONFIRMED --recorded-at <iso>
python3 -m nse.research.cli replay-decision --symbol INFY --as-of 2022-03-31 --bhavcopy-dir nse/data/eod/raw \
    --manifest nse/data/eod/manifest.csv --calendar nse/data/calendar --out nse/output/replay/INFY
python3 -m nse.research.cli dashboard --scan-dir nse/output/scan --out nse/output/dash --bundles-dir nse/output/replay
python3 -m nse.research.cli explain --scan nse/output/scan/scan.json --why INFY     # or --audit, --change, --compare
python3 -m nse.research.cli report --scan nse/output/scan/scan.json --daily --out nse/output/daily.md
python3 -m nse.research.cli risk-plan --scan nse/output/scan/scan.json --capital 100000 --rpt-pct 1 --stage LEARNING
python3 -m nse.research.cli alerts --watchlist w.json --scan curr/scan.json --previous prev/scan.json --jsonl alerts.jsonl
python3 -m nse.research.cli store-import --db nse/output/research.db --scan nse/output/scan/scan.json
python3 -m nse.research.cli scenarios-run
python3 -m nse.research.cli backtest-walk-forward --model m.json --folds f.json ...
```

## 6. End-to-end evidence (software, SYNTHETIC data)

`tests/test_research_e2e.py` runs the real replay, Zone Engine, overlay, gates, reports and
CLI on `long_mit_candles()`: five years of synthetic weekday candles. Their waypoints make
the engine itself produce the zones every gate needs:
- Monthly curve top and bottom;
- a tested but DL-intact Monthly zone, which is the coinciding zone;
- a Weekly target supply;
- a 7/7 Daily DBR.

Demonstrated, each by a test:
- One candidate reaches ACTIONABLE (manual checks pending) with every gate decided on engine evidence.
- A later touch removes it (TESTED). A close below its DL removes it (INVALIDATED).
- Shorter history makes Y missing (G5 MANUAL), and then HY too (G5 DATA_INSUFFICIENT; trend 53 of 55 weeks).
- A missing session stops the symbol.
- A zone above the Monthly PL stops at G6 MANUAL (P-COIN-1).
- A Weekly supply near the entry gives G5 MANUAL.
- No calendar, or no risk per trade, keeps the result in MANUAL REVIEW.
- Appended future candles never change an earlier scan.
- On the leg-out day the zone is 6/7, and only the follow-through candle completes 7/7.
- WIT is BLOCKED.

Mutation runs (patching status precedence, the as_of cut, the overlay, the conflict check,
and missing-HTF handling) each make these tests fail. **None of this is market evidence.**

## 7. Readiness classes

| Class | Meaning | Status (2026-10-29) |
|---|---|---|
| Research-ready | The scanner works end to end for documented use cases; safeguards tested; outputs traceable; limitations visible | **MIT daily: yes, for research on supplied data**, with every result marked NOT_EXTERNALLY_VALIDATED. WIT: no (BLOCKED) |
| Validation-ready | Data, references and open decisions sufficient for rigorous external and historical evaluation | **No.** Missing: the EOD range (inventory), corporate actions (B7), TradingView references (B8, B10), constituents (B11), the trading decisions in `DECISION_REGISTER.md`, a backtest execution model (B9, B12) |
| Live-trading consideration | Independent verification, historical evaluation, operational risk review | **No.** Not attempted; no broker integration exists or is planned (D10, D17) |

## 8. What limits real use today

- **History:** Y needs three completed years, HY and Q three completed periods. With less,
  G5 is DATA_INSUFFICIENT or MANUAL and nothing is ACTIONABLE. The weekly trend gate needs 55
  completed weeks. The repository holds Q1 2022 and one day of December 2023 only.
- **Corporate actions (B7):** prices are unadjusted; every record says so.
- **Universe (D1, B11):** no constituent file; every scan is UNIVERSE_UNVERIFIED.
- **TradingView (B8, B10):** no HTF candle or zone parity recorded.
- **Backtesting:** infrastructure built (`backtest.py`). It needs a user execution model
  (B9, B12), a point-in-time universe (B11) and the data range before any run means anything.
  No performance figure has been produced.

### Backtest readiness (assessed 2026-10-29)

**Verdict:** the infrastructure is testable and tested on synthetic data. **It is not ready to
produce a meaningful result on real data, and no performance figure exists.** Nothing will
be run on real data until the items marked "needed" are in place.

| Area | Status | Kind |
|---|---|---|
| Lookahead | Signals come from point-in-time scans (prefix-invariance tests); the simulation reads only candles after the signal; the levels are those of the first allowed scan | Controlled (tested) |
| Data leakage | No parameter is fitted to outcomes; the in/out-of-sample split is by signal date and reported separately | Controlled. The split date is a user input |
| Survivorship | Per-date universe membership is applied when a universe file is given (`scan_history(..., universe)`, fixed in the second pass). Without one, SURVIVORSHIP_UNCONTROLLED | **Needed:** constituent history (B11); delisted or merged symbols' data |
| Corporate actions | Prices unadjusted. A trade alive across a recorded action or a PREVCLOSE discontinuity is excluded from metrics (fixed this pass), and the scanner holds G0 at MANUAL | **Needed:** B7 records and an adjustment decision |
| Fills | Stop exits on touch (RB 2141); levels are fixed at the signal (RB 2139); gap fills, same-bar ordering, expiry and cancel-if-target-first are required user inputs | **Needed:** B12 choices |
| Buffers | Entry and SL choice inside the printed ranges is a required input | **Needed:** B9 choice |
| Costs | Percentage per side plus slippage | Flat per-order charges (for example a per-sell depository charge) are not modelled. **Needed:** official cost schedule and a decision |
| Not modelled | Capital and concurrent positions, the 10-trades-per-month cap (RB 2392), price bands and circuit limits, liquidity versus volume, re-checking an order after its signal | Each needs a user decision before it is built |
| Data | 62 legacy files held; the window needs 1,233 (`REAL_DATA_ACQUISITION_PLAN.md`) | **Needed:** download approval, UDiFF samples and loader |
| Runtime | About 0.04 s per symbol per scan date on five years of daily data (measured): 10 symbols over two years of daily signals is about 3 minutes | Adequate |
| Strategy | Signals follow the current PROPOSED readings (D41); P-COIN-1 sends most non-coinciding setups to MANUAL REVIEW | **Needed:** decisions in `DECISION_REVIEW.md`. Only statuses you select are traded; MANUAL_REVIEW signals have had no manual check |

## 9. Autonomous engineering framework

- **Skills** (`.claude/skills/`): project-orchestrator, repository-guardian, rulebook-compliance,
  data-quality-validation, zone-mtf-validation, strategy-gate-validation, lookahead-audit,
  integration-testing, adversarial-testing, reference-data-validation, reporting-audit,
  release-readiness. Each names the validation command that checks its area.
- **Agents** (`.claude/agents/`): implementer, independent-reviewer (read-only), data-validator
  (read-only), trading-rule-auditor, test-engineer.
- **Hooks** (`.claude/settings.json`): `guard.py` before Bash/Edit/Write blocks writes to the
  Rulebook and Pine Script, `git add/commit/push/tag` without `NSE_ALLOW_GIT_WRITE=1`,
  destructive git commands (reset --hard, clean, checkout --, restore, stash, rebase, amend,
  branch -D), recursive deletes of repository folders, and broker endpoints. It is
  deliberately conservative: a shell command that mentions a protected file name with a
  write-like token is refused even if the write goes elsewhere. `post_edit.py` after
  Edit/Write checks Python syntax and the protected hashes. Neither runs the test suite.
- **Bounded repair:** the orchestrator skill allows at most three repair cycles per failure
  before escalating with evidence.
