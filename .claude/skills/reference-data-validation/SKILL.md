---
name: reference-data-validation
description: Compare replayed NSE data and, later, zones against approved reference records (TradingView exports, hand-recorded chart readings, other recorded sources) using nse/eod/nse_reference.py. Use when the user supplies reference files or screenshots, or when asked whether outputs match TradingView or another source.
---

# Reference data validation

## Run

```
python3 -m nse.validation.run_all          # the reference_comparison check
python3 -m nse.validation.run_all --group data
```

## Formats and rules

- OHLC references: `nse/data/reference/<SYMBOL>/ohlc_reference.csv`, header exactly
  `OHLC_REFERENCE_COLUMNS` (template in `nse/data/reference/`). Zone references:
  `ZONE_REFERENCE_COLUMNS`; zones must come from TradingView.
- Each row names its source; exports and screenshots carry their file's SHA-256. Chart time
  zone and dividend/split adjustment settings are mandatory.
- `compare_ohlc` gives MATCH, MISMATCH, BLOCKED (W/M without a validated calendar),
  NO_ACTUAL or NO_REFERENCE per bar. `coverage_summary` is complete only when every row matches.
- A Yahoo Finance screenshot republishes NSE data: a match shows the transcription and the
  replay agree, not independent validation.

## Never

- Manufacture or "fill in" a reference value.
- Treat an absent reference as a match, or a synthetic fixture as market validation.
- Compare unadjusted bhavcopy prices with adjusted chart prices without saying so.

Zone comparison: `nse/research/refcheck.py compare_zones(refs, snapshot)`. It matches on
timeframe, side and creation period (P-REF-1, PROPOSED). Prices compare exactly unless a
tolerance is passed. A MISMATCH is classified for investigation, never auto-resolved. With no
TradingView zone rows recorded, report zone parity as UNAVAILABLE. Calendar spot checks go in
`nse/data/reference/tradingview_checks.template.csv`; the observed columns stay empty until a
person fills them in.
