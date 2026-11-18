# P0 TradingView validation status

**Dated 2026-11-10. Status: `PENDING_EXTERNAL_EVIDENCE`. T-005 is open.**

This is the current-status record for the P0 campaign. The Phase 01 protocol and worksheet
remain the intake documents. Their pre-D58 sentences are kept, with a dated supersession
in the protocol. No TradingView value in this file was read off a chart.

Investigation: TradingView evidence, agent id 05b5f31d-0ec9-4493-800a-8165d22f9fdc (read-only).
Files changed by that investigation: none. The corrections below were applied afterwards
from D58 and from that inventory.

## 1. Conclusion

External validation of OHLC, SMA-50, zone boundaries, freshness and higher-timeframe
candles cannot be completed. The repository contains no TradingView export and no
recorded TradingView observation. An internal calculation that matches its own fixture is
not TradingView validation.

B8, B10 and B17 stay open.

## 2. What was inspected

| Item | Result |
|---|---|
| Worksheet | `docs/product-discovery/phase-01/T005_tradingview_comparison_worksheet.csv`, 34 data rows, 22 columns. Before this correction its SHA-256 was `75a65ce7525ba43d17002acf2d59d7095c8b8d00b17bc62f76d69e0e8d8b5c39`. `tradingview_observed`, `result`, `reviewer`, `evidence_reference` and `evidence_sha256` are blank on 34/34 |
| Protocol | `docs/product-discovery/phase-01/T005_TRADINGVIEW_VALIDATION_PROTOCOL.md`. Pre-correction SHA-256 `696cc33aba375008a1ef607d9b77f5be78183b75b2984721bfdccd92bd540581` |
| Filled reference file | `nse/data/reference/INFY/ohlc_reference.csv`, SHA-256 `09bed3ef2f12b554204638d5ac30f3ff149edc36c4c42b03189eaa3258e0549d`. 61 daily rows, 2022-01-03 through 2022-03-31, `source=YAHOO_FINANCE_SCREENSHOT`. `chart_timezone`, `adjust_dividends` and `adjust_splits` are `UNKNOWN` on every row |
| Screenshots | Five PNGs under `nse/data/screenshots/yahoo/INFY/`. Each file's SHA-256 matches the hash written in the Yahoo CSV. Prices were not read from the images |
| Other reference CSVs | Templates, or 12 prepared checks in `tradingview_checks.template.csv` with the observed side blank. No `zone_reference.csv`. No `trend_reference.csv`. No `nse/data/tradingview/` |
| Image walk | Those five PNGs only |

The reference README classes a Yahoo match as a transcription check against published
prices. `nse/eod/nse_reference.py` accepts `YAHOO_FINANCE_SCREENSHOT` for OHLC only. Zone
and trend readers accept `TRADINGVIEW_EXPORT` and `TRADINGVIEW_MANUAL` only.

## 3. Tooling

`refcheck.compare_zones` and `refcheck.compare_trend` exist and are unit-tested on
synthetic rows. Those tests state that the rows are not TradingView readings.

No command replays with the official calendar and then calls `compare_zones` or
`compare_trend`. `nse/research/cli.py` has no such subcommand. `run_all.check_reference`
loads the Yahoo INFY file, replays Q1 2022 with `assume_regular_session=True`, and calls
`compare_ohlc`. It does not pass the calendar, so `calendar_validated` stays false, and
it does not compare zones or SMA-50.

`python3 -m nse.research.cli compare-references` replays one symbol from the EQ series
with the official calendar (`assume_regular_session` stays false) and compares any
supplied OHLC, zone and SMA-50 files. A missing file stays `PENDING_EXTERNAL_EVIDENCE`.
The report sets `certifies_external_validation` and `t005_closed` to false. It does not
write observations back into the reference files. T-005 stays open until the 34
observations exist and a person reviews every difference.

## 4. Corrections applied after the inventory

D58 (`USER_APPROVED`, 2026-11-10) confirmed 2016-10-28, 2017-10-17, 2018-11-05 and
2019-10-25 as regular equity sessions, 09:15-15:30. The decision log states that the
ED-44 history cut no longer applies, and that ED-44 remains the rule for any future
unresolved date.

The worksheet still told a future comparison that those four dates were `UNRESOLVED`
and that the engine would ignore them, and that weekly SMA-50, monthly SMA-50 and
monthly zones were bounded by a restart at 2019-10-25. Those instruction cells were
updated:

| Rows | Change |
|---|---|
| TV-CAL-P01-13 .. TV-CAL-P01-16 | Expected engine behaviour is now the confirmed regular session. The Gold ETF/SGB extension builds no candle |
| TV-SMA-W-01, TV-SMA-M-01 | Warm-up is 50 completed bars from held history. The restart date is removed |
| TV-ZONE-M-01 | A monthly zone can exist from the start of held history when the engine forms one |
| TV-OHLC-D-02 | The window is ordinary 2024 history. The Phase 01 claim that INFY actions after 2019-10 are dividends only, with ex-date 2024-05-31, was not re-checked. Adjustment must still be recorded OFF or UNKNOWN |

The protocol's section 1 row that describes the pre-D58 cut is kept. A supersession note
at the top states the current rule. The "2,462 official sessions" figure in that row was
not re-counted here.

## 5. Evidence the owner still has to supply

Nothing in this list is in the repository. For every row, also record the chart settings,
the evidence file name, its SHA-256, the date recorded and the reviewer. Raw exports
belong in `nse/data/tradingview/<SYMBOL>/`. Do not reconstruct a value that is not on
the chart.

Shared rules from the protocol: OHLC and zone prices at tolerance 0; dates exact; SMA-50
tolerance 0.005, recorded as a widening of plan section 4.2, or 0 when the export has
full precision. Chart setup: NSE symbol, Regular session, Asia/Kolkata, dividends OFF,
splits OFF if the plan has a toggle, otherwise `UNKNOWN`, bar type Candles.

| obs_id | Symbol | Timeframe | Window | Record |
|---|---|---|---|---|
| TV-CAL-01 .. 12 | INFY | D | The twelve prepared calendar dates in the worksheet | Bar present or absent, and OHLC when a bar exists |
| TV-CAL-P01-13 .. 16 | INFY | D | 2016-10-28, 2017-10-17, 2018-11-05, 2019-10-25 | Daily bar and OHLC. A missing bar is logged. The circular remains the authority |
| TV-CAL-P01-17 | INFY | D | 2016-10-30, with 2016-10-27 .. 2016-11-01 | Whether a Sunday bar exists |
| TV-OHLC-D-01 | INFY | D | 2022-01-03 .. 2022-03-31 | O, H, L, C. The Yahoo file does not fill this row |
| TV-OHLC-D-02 | INFY | D | 2024-01-01 .. 2024-06-28 | O, H, L, C |
| TV-OHLC-W-01 | INFY | W | Weeks starting 2022-01-03 .. 2022-03-21 | O, H, L, C, labelled by the first date |
| TV-OHLC-W-02 | INFY | W | Weeks starting 2024-01-01 .. 2024-06-24 | Same |
| TV-OHLC-M-01 | INFY | M | 2022-01 .. 2022-12 | Same |
| TV-OHLC-M-02 | INFY | M | 2024-01 .. 2024-12 | Same |
| TV-OHLC-Q-01 | INFY | Q (TV 3M) | 2022 and 2024, each quarter | Same |
| TV-OHLC-HY-01 | INFY | HY (TV 6M) | 2022 H1/H2 and 2024 H1/H2 | Same |
| TV-OHLC-Y-01 | INFY | Y (TV 12M) | 2022, 2023, 2024, 2025 | Same |
| TV-OHLC-ADJ-01 | TATASTEEL | D | 2022-07-21 .. 2022-08-04 | Two captures, adjustments ON and OFF, or UNKNOWN if there is no split toggle |
| TV-SMA-D-01 | INFY | D | Four sessions in 2024-04 .. 2024-06 | The worksheet does not name the four dates. Record each date, SMA-50 and the dashboard trend/clock state |
| TV-SMA-W-01 | INFY | W | Four weeks in 2022-01 .. 2025-12 | The four week-start dates are not named. Same fields |
| TV-SMA-M-01 | INFY | M | 2024-06, 2024-12, 2025-06, 2025-12 | SMA-50 and dashboard/clock state |
| TV-ZONE-D-01 | INFY | D | Zones created 2024-01-01 .. 2024-06-28 | Every demand and supply zone: side, pattern, base start, created date, proximal, distal, score label, tested, first test date, invalidated date |
| TV-ZONE-W-01 | INFY | W | Zones created 2021-01 .. 2025-12 | Same |
| TV-ZONE-M-01 | INFY | M | Zones created 2020-01 .. 2025-12 | Same |
| TV-MTF-01 | INFY | W and M viewed on D | The W and M zone windows | Class C. First Daily touch date, and whether the W/M indicator still showed the zone fresh. No pass/fail |

Pine settings for the SMA, zone and MTF rows are on the worksheet: unmodified script
SHA-256 `14293fa5d3c8e5ba9309b45804a840bb5d8c43d47c193ebb6bca0480bc0a5519`,
`i_max_base_candles=5`, Body to Wick, base and leg-out thresholds 0.5.

## 6. Owner decisions still required

| ID | Question | Why it blocks T-005 |
|---|---|---|
| TV-1 | Supply the 34 observations above | No external comparison can run |
| TV-2 | Name the four daily sessions for TV-SMA-D-01 and the four week-start dates for TV-SMA-W-01 | The worksheet leaves those dates unnamed |
| TV-3 | State whether the TradingView plan can export chart data, and whether it has a split-adjustment toggle | The protocol marks both as unverified |

P-REF-1's wording inside the decision log was reported as conflicting (a D41 `PROPOSED`
reading and a later `USER_APPROVED` bullet). This pass does not settle that conflict.
`DECISION_REGISTER.md` still says the match key is confirmed against the first real
TradingView references.

## 7. What this status does not close

- T-005, B8, B10, B17 and T005-G1 stay open.
- The Yahoo INFY file stays a transcription check.
- No readiness gate moves because of this inventory.
- No performance, zone or calendar claim is externally validated.
