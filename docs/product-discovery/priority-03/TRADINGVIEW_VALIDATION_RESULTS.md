# TradingView validation results

Date: 2026-11-10. Protocol: `nse/docs/REFERENCE_VALIDATION_PLAN.md` (dated 2026-10-29). That plan states that no TradingView observation had been recorded. This pass checked whether one has been added since.

## Result

**BLOCKED_EVIDENCE.** No owner-supplied TradingView export or screenshot was found. No zone, SMA, HTF candle, or session comparison was run. GTF outputs were not edited to force a match. `nse/sources/` was not edited.

During this audit, `docs/product-discovery/phase-01/T005_TRADINGVIEW_VALIDATION_PROTOCOL.md` and `T005_tradingview_comparison_worksheet.csv` appeared. The worksheet has 34 rows. On 2026-11-10 every `tradingview_observed`, `result`, and `reviewer` cell was empty. `expected_gtf_output` is a method note or the phrase "Produced at comparison time", not a filled engine measurement. That packet does not contain a comparison.

## What was searched

| Location | Found |
|---|---|
| `nse/data/tradingview/` | Directory does not exist |
| `nse/data/reference/**/*.csv` | Templates with a header and no observation rows, plus one filled file: `nse/data/reference/INFY/ohlc_reference.csv` |
| `tradingview_checks.template.csv` | 12 prepared check rows, not filled results |
| `zone_reference.template.csv`, `trend_reference.template.csv`, `disagreements.template.csv` | Headers only (0 data rows) |
| `ohlc_reference.template.csv` | Header only |

## The only filled reference file

`nse/data/reference/INFY/ohlc_reference.csv` has 61 data rows.

| Field | Observed |
|---|---|
| Symbol | INFY |
| Timeframe | D only |
| Dates | 2022-01-03 through the Q1 2022 rows in that file (61 daily bars) |
| Source column | `YAHOO_FINANCE_SCREENSHOT` on every row |
| Adjustment | `UNKNOWN` / `UNKNOWN` on every row |
| Screenshots named in the file | Two local screenshot filenames with SHA-256 values. This pass did not open the images |

The reference README says a Yahoo match checks transcription against republished prices. It is not TradingView, not an adjustment-off chart, and not a zone or SMA check. Class under the protocol: **B, republication**, not class A.

No comparison table is produced below, because there is no TradingView output to put in it.

## Items the protocol asked to compare

| Area | Status | Rows compared |
|---|---|---|
| A. Zone existence, bounds, creation, freshness, tested, invalidation, timeframe behaviour | BLOCKED_EVIDENCE | 0 |
| B. SMA values, periods, close alignment, warm-up, missing candles | BLOCKED_EVIDENCE | 0 |
| C. Historical candles versus TradingView, special sessions, OHLC | BLOCKED_EVIDENCE | 0 |
| D. Discrepancy classification | Not applicable | No pair exists to classify |

Difference classes 1-7 in the mission statement were not used. Inventing a "match" or an "acceptable tolerance" without a chart value would be a fabricated result.

## What would unblock this

Owner exports, recorded as the plan already specifies:

- Daily OHLC with adjustment off, for an agreed symbol and window.
- Weekly, monthly, and higher-timeframe bars at period boundaries.
- SMA 50 on the timeframes the trend clock uses.
- Zones from the unmodified indicator with max base candles = 5, including tested and invalidated marks.

Until those files exist, zone detection, the SMA clock, and HTF aggregation stay **not externally validated**. The Yahoo INFY file can stay a transcription check only.

## Owner decision

None taken. T-005 remains open. No methodology difference was demonstrated, because no paired observation exists.
