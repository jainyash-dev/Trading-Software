---
name: data-quality-validation
description: Validate NSE market-data inputs (bhavcopies, user daily CSVs, the trading calendar, the EOD manifest) before they feed the research pipeline. Use when new data files arrive, when a scan reports DATA_INSUFFICIENT or data-quality findings, or when asked whether the data can be trusted.
---

# Data quality validation

## Run

```
python3 -m nse.validation.run_all --group data          # loader, calendar, replay tests
python3 -m nse.validation.run_all                       # adds local_data: circular hashes,
                                                        # EOD archives vs manifest, calendar
                                                        # vs EOD reconciliation per month
python3 -m nse.research.cli scan --as-of <date> --symbols <S> --bhavcopy-dir nse/data/eod/raw \
    --manifest nse/data/eod/manifest.csv --calendar nse/data/calendar --out nse/output/dq
```
Then read `nse/output/dq/data_quality.csv` and the `series` block of `scan.json`.
For coverage and what a scan at a date needs:
`python3 -m nse.research.cli inventory --as-of <date> --symbols <S>`. It reports files on
hand, missing sessions, per-timeframe history sufficiency, and the acquisition spec.

## What is checked, and where

| Check | Code |
|---|---|
| Format, header, Decimal prices, provenance by SHA-256 | `nse/eod/nse_bhavcopy.py` (strict; refuses deviations) |
| Duplicates, order, non-positive or non-numeric prices, OHLC consistency, weekend rows | `nse/research/marketdata.py check_rows` (ERROR stops the symbol at G0) |
| Missing sessions, partial sessions, excluded sessions, unresolved calendar dates, truncated series | `mtf_freshness.replay`, surfaced by `marketdata.snapshot_findings` |
| Calendar circular hashes and coverage | `nse/calendar/nse_calendar.py` |
| Calendar vs dates that have an EOD file | `nse_calendar.reconcile`, run per month by `run_all` |

## Rules of judgement

- A missing candle is never "no trading". Without a calendar every missing weekday is an
  unverified gap (D28); with one, a missing session truncates the series (D37).
- A file existing is not provenance: only a manifest or sources.csv hash match is.
- Distinguish verified defects from unverified assumptions (`verified` column).
- Prices are unadjusted (B7). A result that carries `CORPORATE_ACTIONS_UNVERIFIED` keeps that limitation until the code and the decision record remove it. This check does not clear it.
- This skill is read-only. Report the defect. Do not edit the file.
- A sourced transcription correction belongs to the main session under `gtf-p0-data-certification`, with provenance and a recomputed hash. The `data-validator` agent stays read-only. Never modify raw OHLC to close a continuity gap. Never infer a missing fact.
- `HELD` in the acquisition ledger is file custody. It is not verification and it is not certification.
- Downloading anything needs user approval (D31).
