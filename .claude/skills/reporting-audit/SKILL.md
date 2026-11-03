---
name: reporting-audit
description: Verify that scanner reports (scan.json, candidates.csv, fresh_zones.csv, blocked_zones.csv, data_quality.csv, summary.json, readiness.json) faithfully represent the pipeline's decisions. Use after any change to nse/research/reports.py, the result models or the CLI, and before sharing a scan.
---

# Reporting audit

## Run

```
python3 -m nse.validation.run_all --group reports --group integration
```

## Checks (each has a test; add one when a new field appears)

- Blocked, rejected and data-insufficient results appear in every export; nothing is hidden.
- Manual-review items and the manual checklist survive JSON and CSV (round trip).
- Gate outcomes in CSV equal the in-memory gates; statuses equal; counts in summary.json
  reconcile with the rows.
- Zone ids and scores match the underlying engine objects.
- `as_of` is the requested replay time; `generated_at` is only what the caller passed (no
  clock), so identical inputs give byte-identical files.
- Limitations (NOT_EXTERNALLY_VALIDATED, TRADINGVIEW_PARITY_UNVERIFIED,
  CORPORATE_ACTIONS_UNVERIFIED, CALENDAR_UNVALIDATED, UNIVERSE_UNVERIFIED) reach every record
  they apply to.
- The fresh-zone report lists only overlay-fresh zones; supply rows say "context: not a candidate".

## Manual spot check of a real scan

```
python3 -m nse.research.cli scan --as-of <date> ... --out nse/output/audit
```
Pick one candidate in candidates.csv and trace it in scan.json: zone, each gate's reasons
and evidence, levels, limitations. Every number must trace to an input.
