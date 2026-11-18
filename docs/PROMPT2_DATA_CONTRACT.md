# What the research pipeline needs from data readiness

The research command reads data through the existing loaders. It does not acquire files,
certify a dataset, or treat a finished process as `DATA_READY`.

## Consumed, read only

| Input | Flag | Effect when missing or unverified |
|---|---|---|
| Daily bars | `--csv-dir` or `--bhavcopy-dir` plus `--manifest` | A symbol with no file, or an input error dated at or before `as_of`, is `DATA_INSUFFICIENT` |
| Calendar folder | `--calendar` | `CALENDAR_UNVALIDATED`. An excluded session with no candle keeps the zone manual |
| Corporate-action CSV and `coverage.csv` beside it | `--corporate-actions` | No file: prices stay unadjusted and the unverified limitation remains. A price-scale action inside the scanned history makes G0 manual |
| Instrument records | `--instruments` | No verified point-in-time ISIN: the report says the ISIN is unavailable or unverified. A future lineage segment is ignored |
| Universe membership CSV | `--universe` | No file, or an unverified row: `UNIVERSE_UNVERIFIED`. Membership is resolved at `as_of` |
| Journal database | `--journal` | Optional. Counts are read at `as_of`. The file is not created and no row is inserted |

## Still required before a real-data research claim

1. Accepted EOD for the dates being scanned, with the manifest hashes the loader already checks.
2. A calendar that classifies those dates, including the unresolved sessions the scanner already cuts around.
3. Corporate-action records and coverage for the symbols, or an explicit acceptance that G0 stays manual when a price-scale break is possible.
4. Instrument identity whose lineage covers each symbol at `as_of`.
5. Reviewed historical membership for a full-universe run. An ad-hoc symbol list stays `UNIVERSE_UNVERIFIED`.

Until those are present, run the command on the files that do exist and read the limitations. Do not describe the output as a certified universe or as evidence that a setup is profitable.

## Replay

```
python3 -m nse.research.cli research --replay-of <folder> --out <new-folder>
```

The new folder is written beside the original. A matching `research.json` digest exits 0. A difference exits 1.
