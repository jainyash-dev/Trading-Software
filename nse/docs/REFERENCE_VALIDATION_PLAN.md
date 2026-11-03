# Reference Validation Plan (prepared; no observation recorded yet)

**Dated 2026-10-29.** This plan says what independent observations would test, how they are
recorded and compared, and what a disagreement does. **No TradingView observation exists in
the repository.** Nothing below is a result.

## 1. What counts as independent

| Class | Examples | Independent of what | Proves | Does not prove |
|---|---|---|---|---|
| A. Independent computation over exchange data | TradingView chart OHLC on D/W/M/3M/6M/12M; its SMA 50 values; the unmodified Pine indicator's zones | Our candle construction, HTF aggregation, calendar boundaries and engine logic | That our candles, trend inputs and zones agree with a separate implementation | That NSE's prices are right: both read the same exchange prices |
| B. Republication of exchange data | Yahoo Finance (the existing INFY rows), the NSE website, other vendors | Nothing beyond transcription | That the replay reproduces published prices | Candle construction, zones, trend, Pine parity |
| C. Recorded human judgement | A person's curve boundaries, matrix reading or gate verdict for one setup | The code's decision path | Where code and a trained reader agree or differ on a rule | Correctness of either: it is a review, not a measurement |

Only class A can validate engine behaviour. Class C is used for gate outcomes, because
no external system computes G0-G8. It is always labelled as human review.

## 2. Minimum observations

Record each in the existing format. Fill every column; empty `observed` cells stay empty
until a person has looked.

| What | Timeframes | File (template in `nse/data/reference/`) | Compared by | Covers |
|---|---|---|---|---|
| Calendar spot checks | D | `tradingview_checks.template.csv` (12 checks prepared) | by hand against `events.csv` | B17, D30, D40 (incl. 20 Jan 2024) |
| Daily OHLC, adjustment OFF/OFF | D | `ohlc_reference.template.csv` | `nse_reference.compare_ohlc` | B8 data path |
| HTF OHLC at period boundaries | W, M, Q, HY, Y | `ohlc_reference.template.csv` | `compare_ohlc` (Q/HY/Y supported since 2026-10-29; replay with those timeframes) | D23, B8 |
| SMA 50 value per bar | W, M (MIT trend, context); D (WIT) | `trend_reference.template.csv` | `refcheck.compare_trend` | D14 clock inputs |
| Zones drawn by the unmodified indicator (max base candles = 5) | D, W, M | `zone_reference.template.csv` | `refcheck.compare_zones` (key P-REF-1) | B10: geometry, pattern, creation, test, invalidation |
| Freshness and invalidation | D, W, M | the zone rows' `tested`, `first_test_date`, `invalidated_date` | `compare_zones` | D24-D28; PR8 timing differences are classified as intended (D12) |
| Curve and matrix reading | M (MIT) | class C worksheet: the zones a person uses as curve bottom and top, the position, the Weekly clock reading | by hand against G3/G4 evidence in `scan.json` | P-LOC-1, P-LOC-2, P-TREND-1 |
| Final gate outcomes | all | class C: a person's verdict per gate for chosen candidates | by hand against `candidates.csv` | spec 8 as implemented |

The indicator does not compute curve, matrix, conflict or R:R. Those can only be compared
with class C records.

## 3. Initial validation set (recommended, for approval)

The set is small enough to record by hand, and chosen from the already proposed sample
(`DATA_REQUIREMENTS.md` §6). Event dates there come from filings and reports and are
*unverified* here.

| Symbol | Why | Observations |
|---|---|---|
| INFY | Control; Q1 2022 files and Yahoo rows already held | D OHLC: Q1 2022 and Jan-Feb 2024. W/M OHLC: 2022 and 2024. Q/HY/Y OHLC: 2021-2025 boundaries. SMA 50 on W and M at 4 dates. All D/W/M indicator zones in 2023-2024 |
| TATASTEEL | Split (reported ex-date 2022-07-28) | D OHLC on the ex-date and the days around it, with adjustment ON and OFF. Zones drawn across the ex-date, to see what an unadjusted series does |
| RELIANCE | Demerger (reported 2023-07-20) and bonus (reported record date 2024-10-28) | As for TATASTEEL, at both events |
| LICI | Recent listing (reported 2022-05-17) | First W/M/Q candles (partial first period, D23); insufficient-history behaviour |

Calendar checks: the 12 prepared rows (INFY), above all 28/29 June 2023, 20 Jan 2024
(inferred hours), the Muhurat sessions and the DR sessions.

**Chart settings, recorded on every row:** exchange NSE, time zone Asia/Kolkata, regular
session, adjustments as stated. The indicator inputs that differ from its defaults go in
`indicator_settings`.

## 4. Procedure

1. **Record.** For each observation, fill the row and save the screenshot or export outside
   git, with its SHA-256 in the row. Do not round or reconstruct values.
2. **Compare.** Load the row with the readers in `nse_reference` / `refcheck`, which refuse any
   malformed row. Replay with the official calendar and the same timeframes. Compare with
   tolerance 0. If you widen the tolerance, record it in the result.
3. **Log every non-match** in a copy of `disagreements.template.csv`: reference file and
   line, source class, expected, actual, and the comparison's own classification.
4. **Investigate in this order.** Settle each question before the next:
   1. Is the observation right? Re-read the chart; check its settings and adjustment.
   2. Is the data right? Compare the bhavcopy row, then the class B sources.
   3. Is it an intended difference? D12 lists them (PR1, PR4, PR5, PR8); `compare_zones`
      already marks Weekly/Monthly test timing as METHODOLOGY_AMBIGUITY.
   4. Is the rule ambiguous? Then it is a decision for you; add it to `DECISION_REGISTER.md`.
   5. Only then: a suspected implementation defect. It needs a failing regression test
      before any code changes.
5. **Never** change the implementation, a threshold or a rule so that a reference matches.
   The `resolution` column is one of: REFERENCE_ERROR, DATA_ERROR, INTENDED_DIFFERENCE_D12,
   USER_DECISION, IMPLEMENTATION_DEFECT. Each needs evidence in `investigation`. A
   disagreement stays OPEN until then.
6. **Coverage.** A comparison counts only when every row is a MATCH and nothing is
   NO_REFERENCE or NO_ACTUAL (`coverage_summary`, `compare_zones` / `compare_trend` `complete`).

## 5. What exists and what is still needed

- **Tested tooling:**
  - readers and comparisons for OHLC (D to Y), zones and SMA 50;
  - a disagreement log template;
  - the calendar check list.
- **Not built:** a reader for class C worksheets. Its format should follow the first real
  worksheet rather than be guessed.
- **Needed from you:**
  - approval of the validation set;
  - the TradingView plan, if exports need a paid plan (*unverified*, `DATA_REQUIREMENTS.md` §3);
  - the observations themselves.
