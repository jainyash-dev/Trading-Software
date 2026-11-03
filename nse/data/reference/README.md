# Independent reference values (B8, B10)

Reference values that the replay is compared against: OHLC bars and indicator zones
recorded from TradingView, and daily OHLC bars transcribed from Yahoo Finance screenshots.
TradingView references are evidence for blockers B8 (HTF candles) and B10 (Pine parity).
**Nothing here is filled in by code, and no expected value is ever invented.**

- **Raw TradingView exports** go in `nse/data/tradingview/<SYMBOL>/` and stay out of git
  (`.gitignore`). Record each export's SHA-256 in the rows that use it.
- **Screenshots** are kept locally (`nse/data/screenshots/` is ignored by git); each row records
  the image's exact filename and SHA-256.
- **Transcribed reference rows** go in `nse/data/reference/<SYMBOL>/ohlc_reference.csv` and
  `nse/data/reference/<SYMBOL>/zone_reference.csv`, using the headers in the two
  `*.template.csv` files here. These are committed after review.
- `nse/eod/nse_reference.py` reads both files and refuses any other header or a malformed row.
  Only OHLC rows are compared so far; zone rows are validated but not yet compared.

## Columns

**`ohlc_reference.csv`**: one row per bar.

| Column | Value |
|---|---|
| `symbol`, `exchange` | e.g. `INFY`, `NSE` |
| `timeframe` | OHLC: `D`, `W`, `M`, `Q`, `HY` or `Y`. Zones: `D`, `W` or `M` only (Pine draws no Q/HY/Y zones) |
| `bar_date` | The bar's date as TradingView labels it, `YYYY-MM-DD` (for W and M, the first date of the bar) |
| `open`, `high`, `low`, `close` | Exactly as shown, plain decimals |
| `source` | `TRADINGVIEW_EXPORT` (from an export file), `TRADINGVIEW_MANUAL` (read off the chart) or `YAHOO_FINANCE_SCREENSHOT` (daily OHLC transcribed from a Yahoo Finance screenshot; regular Close, never Adj Close). Yahoo rows are never labelled as TradingView, and zone rows accept TradingView sources only |
| `export_file`, `export_sha256` | Required for `TRADINGVIEW_EXPORT` and `YAHOO_FINANCE_SCREENSHOT`: the export or screenshot file's exact name and a valid 64-character SHA-256 of its bytes. A row without both is refused |
| `chart_timezone` | As set on the chart, e.g. `Asia/Kolkata` or `Exchange` |
| `adjust_dividends`, `adjust_splits` | `ON`, `OFF` or `UNKNOWN`, as set on the chart |
| `recorded_on`, `notes` | `YYYY-MM-DD`; free text |

**`zone_reference.csv`**: one row per zone drawn by the indicator (max base candles = 5).

| Column | Value |
|---|---|
| `indicator_settings` | Every input that differs from the default |
| `side`, `pattern` | `demand` or `supply`; DBR, RBR, RBD or DBD |
| `base_start_date`, `created_date` | First base candle; the candle the zone appears on |
| `proximal`, `distal` | The zone box's two price lines |
| `score_label` | As drawn, e.g. `7/7` |
| `tested`, `first_test_date`, `invalidated_date` | `YES`/`NO`; dates if any |
| Other columns | As for OHLC rows |

## Comparison rules (`compare_ohlc`)

- Results are `MATCH`, `MISMATCH`, `BLOCKED`, `NO_ACTUAL` (a reference row with no replayed bar) or `NO_REFERENCE` (a replayed bar with no reference row). Every result keeps its reference row's source.
- Non-matches are classified `DATA_MISMATCH`, `CANDLE_CONSTRUCTION_MISMATCH`, `METHODOLOGY_AMBIGUITY` (the chart adjustment is not `OFF`/`OFF`) or `INSUFFICIENT_EVIDENCE`.
- W, M, Q, HY and Y rows are `BLOCKED` until the replay uses a validated NSE calendar (B17). Q/HY/Y rows need the replay run with those timeframes.
- **Coverage:** `coverage_summary()` reports complete only when there is at least one result and every result is a `MATCH`. Any `NO_REFERENCE` (or other non-match) makes coverage incomplete, so a missing reference date can never look like full coverage.
- **What a Yahoo Finance match means:** the replayed bars agree with the values Yahoo Finance displays. Yahoo republishes exchange data, so a match is not independent validation of NSE prices, and it says nothing about candle construction above daily, Pine parity or strategy performance.
