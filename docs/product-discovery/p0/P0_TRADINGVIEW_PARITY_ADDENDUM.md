# TradingView parity addendum

**Dated 2026-11-11. Status: `PENDING_EXTERNAL_EVIDENCE`. T-005 is not closed.**

Branch `main`. HEAD `9e302df1a81c2b13696d8fab61f05d377481be2e`.

The 2026-11-10 status file remains the inventory. This addendum confirms the current
command and the missing evidence. No observation was invented.

`python3 -m nse.research.cli compare-references` requires `--calendar`, replays series
`EQ`, and passes `assume_regular_session=False`. It compares only files the caller
supplies. The report sets `certifies_external_validation` and `t005_closed` to false.
A Yahoo match is not TradingView parity. Synthetic unit tests of the command are not
external validation.

## Missing external evidence

All 34 worksheet rows in
`docs/product-discovery/phase-01/T005_tradingview_comparison_worksheet.csv` still have
blank `tradingview_observed` cells.

| Group | Rows | Still required |
|---|---|---|
| Calendar bar present or absent | TV-CAL-01 .. TV-CAL-12 and TV-CAL-P01-13 .. 17 | INFY daily screenshots or exports, including the four Dhanteras dates and the 2016 Sunday check |
| Daily, weekly, monthly, quarterly, half-year, yearly OHLC | TV-OHLC-D/W/M/Q/HY/Y | INFY exports, splits OFF or recorded UNKNOWN |
| Adjustment | TV-OHLC-ADJ-01 | TATASTEEL, adjustments ON and OFF, or UNKNOWN if there is no toggle |
| SMA-50 | TV-SMA-D-01, W-01, M-01 | Values plus dashboard state. The four daily dates and four week-start dates are still unnamed |
| Zones and freshness | TV-ZONE-D-01, W-01, M-01 | Every demand and supply zone: boundaries, tested, first test, invalidation |
| Higher-timeframe freshness on the daily chart | TV-MTF-01 | Class C reading. No pass/fail |

Chart settings, evidence file name, SHA-256, reviewer and date are required on every row.
P0 data-foundation status and TradingView parity are separate claims. Parity is unverified.
