---
name: integration-testing
description: Exercise the whole research pipeline end to end with real components (market data, data checks, Zone Engine, MTF overlay, top-down analysis, G0-G8, candidate results, JSON/CSV reports, CLI). Use after changes that cross module boundaries or change a schema, and before claiming any feature works.
---

# Integration testing

## Run

```
python3 -m nse.validation.run_all --group integration --group reports
cd tests && python3 -m unittest -v test_research_integration
```
Smoke-test the CLI on real local files (they are git-ignored; skip if absent):
```
python3 -m nse.research.cli scan --as-of 2022-03-31 --symbols INFY,TCS \
  --bhavcopy-dir nse/data/eod/raw --manifest nse/data/eod/manifest.csv \
  --calendar nse/data/calendar --out nse/output/smoke
```

## What counts as integration evidence

- Uses the real `mtf_freshness.replay` and the real scanner. The SnapBuilder snapshots in
  `tests/_research.py` are unit fixtures and are never called integration tests.
- Asserts consistency between layers: candidate zone ids equal the overlay-kept ids; CSV
  rows equal the in-memory records; summary counts reconcile.
- Covers blocked flows (tested zone, missing session, data error, WIT) as well as the
  successful one.

## Honesty

`tests/test_research_e2e.py` uses `long_mit_candles()` (five SYNTHETIC years). It reaches
ACTIONABLE through the real replay and covers the tested, invalidated, short-history,
missing-session, unresolved-rule, conflict, prefix-invariance and WIT cases. Add a variant
there (a new waypoint or `extend`) rather than a mock. The real-data test
(`RealNseQ1Of2022`) proves the pipeline runs on official files, not that any decision is
right. Say exactly that in reports.
