# T-005: TradingView external validation: protocol, intake and status

**Dated 2026-11-10.**

## External validation status

**PENDING. No TradingView observation exists in the repository.** The Zone Engine, the
higher-timeframe candles and the SMA-50 inputs are **not externally validated**.

- B8, B10 and B17 stay `LIVE_VALIDATION_PENDING` / `EVIDENCE_BLOCKED`.
- No export was generated, simulated or read off a chart by an agent.
- No comparison result exists.

**Supersession, later on 2026-11-10 (D58).** Section 1 still records the ED-44 cut that
applied while the four Dhanteras dates were `UNRESOLVED`. D58 confirmed those dates as
regular equity sessions. No `UNRESOLVED` calendar row remains, so a scan is not restarted
at 2019-10-25. ED-44 remains the rule for any future unresolved date. Monthly SMA-50
warm-up is 50 completed months from the start of held history. Worksheet rows
TV-CAL-P01-13 through TV-CAL-P01-16, TV-SMA-W-01, TV-SMA-M-01 and TV-ZONE-M-01 now say
that. The section 1 row is kept so the pre-D58 reading stays visible. The "2,462 official
sessions" figure in that row was not re-counted in this correction.

This document extends [REFERENCE_VALIDATION_PLAN.md](../../../nse/docs/REFERENCE_VALIDATION_PLAN.md)
(2026-10-29) and the INFY matrix in
[REAL_DATA_READINESS.md §6](../../../nse/docs/REAL_DATA_READINESS.md). Both are left
unchanged; their procedure, evidence classes and resolution rules still apply. What is new:

- Coverage now reflects the 2016-2025 data held.
- The Dhanteras and ED-44 effects are added.
- Each observation gets a row in a worksheet.
- An intake checklist for the owner.

## 1. What changed since the plan was written

| Then (plan, §6) | Now (facts, 2026-11-10) | Consequence |
|---|---|---|
| Bhavcopies held for Q1 2022 and 2023-12-29 only | 2,462 official sessions, 2016-01-01 to 2025-12-31 (D55) | HY/Y OHLC and W/M SMA-50 (P5, P7, P9) are now comparable locally |
| Calendar for 2021-2025 | 2016-2025, reconciled with EOD files | Calendar spot checks can include 2016-2019 sessions |
|: | ED-44: a scan's history starts after the last UNRESOLVED date (2019-10-25) | The engine has no candle before 2019-10-28. Monthly SMA-50 exists only from about Dec 2023; zones created earlier cannot exist in the engine. Compare inside the engine's window only |
| Template gaps listed (§6) | Still open: the canonical readers accept the template headers exactly | The extra metadata (recorded_by, Pine SHA-256, export hash for zones, settings) goes in the worksheet, keyed by `obs_id`; the canonical CSVs keep their headers |
| A comparison runner for OHLC | `run_all` compares INFY Q1 2022 D/W/M only, against the Yahoo rows, with `assume_regular_session=True` | **Gap:** no driver yet replays with the official calendar and Q/HY/Y, or runs `refcheck.compare_zones` / `compare_trend` against an engine snapshot. The functions exist and are unit-tested; the wiring does not |

## 2. Test matrix

The full matrix, 34 observations, is
[T005_tradingview_comparison_worksheet.csv](T005_tradingview_comparison_worksheet.csv).
Each row has:
- `obs_id`, category and evidence class;
- symbol, timeframe and date range;
- TradingView chart settings and Pine settings;
- required screenshot or export, and the canonical file it goes in;
- how the GTF output is produced;
- expected GTF output, TradingView observed;
- tolerance, difference classification, pass/fail criteria;
- result, reviewer, evidence reference and SHA-256.

`expected_gtf_output` is produced at comparison time from the held data. It is never
pre-filled. `tradingview_observed`, `result` and `reviewer` are blank.

| Area | Observations | IDs | Class |
|---|---|---|---|
| A. Zone detection, boundaries, creation date, pattern, score | INFY D (2024 H1), W (2021-2025), M (2020-2025) | TV-ZONE-D-01, W-01, M-01 | A |
| A. Fresh vs tested, invalidation | the same zone rows' `tested`, `first_test_date`, `invalidated_date` | as above | A |
| A. Multi-timeframe interaction (freshness overlay) | W/M zones read on the D chart | TV-MTF-01 | **C (human reading).** The indicator does not compute the overlay |
| B. SMA-50 calculation, warm-up, close alignment | D, W, M at listed dates | TV-SMA-D-01, W-01, M-01 | A |
| B/C. HTF candle construction (D23) | D, W, M, Q (3M), HY (6M), Y (12M) | TV-OHLC-D/W/M/Q/HY/Y | A |
| B. Corporate-action adjustment | TATASTEEL split, 2022-07-29 ISIN change, adjustments ON and OFF | TV-OHLC-ADJ-01 | A |
| C. Calendar, special and missing sessions | the 12 prepared checks, the 4 Dhanteras dates, a Sunday Muhurat | TV-CAL-01..12, TV-CAL-P01-13..17 | A |

**Supply zones** are covered by the same zone rows (`side = supply`). The engine never
makes supply zones candidates, but their geometry and freshness feed G5 and G7, so they
are compared too.

## 3. Comparison rules

| Item | Rule |
|---|---|
| Tolerance, OHLC and zone prices | 0. TradingView shows the exchange tick |
| Tolerance, SMA-50 | 0.005: half the 2-decimal display precision. Record it as a widening, as plan §4.2 requires. Use 0 if an export gives full precision |
| Dates | Exact. W and M bars are labelled by their first date (README in `nse/data/reference/`) |
| Classification | `nse_reference` / `refcheck` assign DATA_MISMATCH, CANDLE_CONSTRUCTION_MISMATCH, METHODOLOGY_AMBIGUITY or INSUFFICIENT_EVIDENCE. Each investigation closes as REFERENCE_ERROR, DATA_ERROR, INTENDED_DIFFERENCE_D12, USER_DECISION or IMPLEMENTATION_DEFECT, with evidence |
| Expected differences | Muhurat and DR sessions (excluded, D30); W/M test timing (PR8, D12); Pine-only paths (PR1); max base candles (set to 5, PR4); a history restart only when an UNRESOLVED date exists (ED-44; none after D58); adjusted prices |
| Pass | Every row in range is a MATCH and coverage is complete (no NO_ACTUAL or NO_REFERENCE), or every difference is closed with an evidenced resolution |
| Never | Change code, thresholds or rules to make a reference match (plan §4.5). Any implementation defect first gets a failing regression test |

Investigation order (from the plan, unchanged):
1. Is the observation right?
2. Is the data right?
3. Is it an intended difference?
4. Is the rule ambiguous? (an owner decision)
5. Only then: a suspected implementation defect.

## 4. Owner intake checklist: what to capture in TradingView

Set up the chart **once** and screenshot the settings dialogs. Record the result in every row:

- [ ] Symbol `NSE:INFY` (and `NSE:TATASTEEL` for the adjustment check).
- [ ] Session **Regular**; time zone **Asia/Kolkata**.
- [ ] **Adjust data for dividends: OFF.** For splits: OFF if your plan offers a toggle,
  otherwise record `UNKNOWN`. Whether TradingView offers a split toggle, and whether
  export needs a paid plan, is *unverified* here.
- [ ] Add the **unmodified** "Demand&Supply Indicator" Pine script. Its SHA-256 must be
  `14293fa5d3c8e5ba9309b45804a840bb5d8c43d47c193ebb6bca0480bc0a5519`.
- [ ] Indicator inputs:
  - max base candles **5** (the default is 3; the engine uses 5, D12 / PR4);
  - everything else at its default (list in the worksheet `pine_settings`);
  - tested zones visible.
- [ ] Add a plain SMA 50 on close, or use the indicator's own SMA line.

Then, per worksheet row:

| Capture | How | Where it goes |
|---|---|---|
| OHLC bars (D, W, M, 3M, 6M, 12M) | Prefer **Export chart data** (CSV) per timeframe. Otherwise a screenshot per bar with the data window open | Raw file: `nse/data/tradingview/INFY/` (git-ignored). Values: `nse/data/reference/INFY/ohlc_reference.csv`, template header, `source = TRADINGVIEW_EXPORT` or `TRADINGVIEW_MANUAL` |
| SMA-50 values | Data-window value per listed bar, plus the indicator dashboard trend/clock state | `nse/data/reference/INFY/trend_reference.csv` |
| Zones | One screenshot per zone box, with the base candles' data window. Read side, pattern, base start, created date, proximal, distal, score label, tested Y/N, first test date, invalidated date | `nse/data/reference/INFY/zone_reference.csv`. Screenshot file name and SHA-256 go in the worksheet (the zone template has no hash column) |
| Calendar checks | One screenshot per date, showing whether a bar exists | A filled copy of `tradingview_checks.template.csv`, plus the worksheet for TV-CAL-P01-* |
| MTF reading | Your written reading per W/M zone: first touch date seen on D; still fresh on W/M at that date? | The worksheet's `tradingview_observed` (class C) |

For every capture, record:
- the file name and SHA-256 (`shasum -a 256 <file>`);
- the date recorded;
- your name as reviewer.

Do not round. Do not reconstruct a value you cannot see.

## 5. Missing samples (all of them, today)

| Needed | Count | Unblocks |
|---|---|---|
| INFY OHLC exports or screenshots, D/W/M/3M/6M/12M | 9 rows | B8 (HTF construction) |
| TATASTEEL D bars across the split, adjustments ON and OFF | 1 row (2 captures) | Adjustment behaviour |
| INFY SMA-50 readings, D/W/M | 3 rows (12 values) | D14 trend inputs |
| INFY indicator zones, D/W/M, with freshness fields | 3 rows (every zone in range) | B10 (Pine parity), D24-D28 |
| Human MTF reading | 1 row | Overlay review (class C) |
| Calendar screenshots | 17 rows | B17 corroboration; CAL-2 support |

Also missing, from the engineering side (not the owner):
- the comparison driver from §1;
- the Phase 02 candidate to build it, with tests, before the first exports arrive.

## 6. Reproducing a comparison (another reviewer)

1. Check the protected hashes (`tests/test_repo.py`): the Pine script `14293fa5…a5519`,
   the Rulebook PDF `e41cd0e7…c2fc`.
2. Load the reference rows with `nse_reference.read_ohlc_reference`,
   `nse_reference.read_zone_reference` or `refcheck.read_trend_reference`. They refuse malformed rows.
3. Replay the symbol from the held bhavcopies with the official calendar and the needed
   timeframes. Build the engine snapshot for the range end.
4. Run `compare_ohlc`, `compare_trend` or `compare_zones` at the tolerance in §3. Record
   the counts and `complete`.
5. Log every non-match in a copy of `nse/data/reference/disagreements.template.csv`, and
   investigate in the order in §3.

Steps 3 and 4 have no command-line driver yet (§1).
