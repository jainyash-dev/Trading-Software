---
name: nse-data-engineering
description: Plan, ingest and audit NSE end-of-day files through the offline acquisition layer (nse/research/acquisition.py): backfill plans, inbox ingestion with SHA-256 provenance, duplicate and revised-file handling, quarantine, the append-only ledger and the daily update. Use when the owner has downloaded bhavcopies, when asked what data is missing for a window, or when setting up the daily EOD routine. Validation of the content itself is the data-quality-validation skill.
---

# NSE data engineering (acquisition and ingestion)

The owner downloads files; the system verifies, copies, records and reports. There is no
network-fetching code (D31) and no provider subscription (paid or licensed sources need
owner approval). Large downloads are the owner's action, never the agent's.

## Run

```
python3 -m nse.research.cli acquire-plan --start 2021-01-01 --end 2025-12-31     # HELD / MISSING / HASH_MISMATCH per session
python3 -m nse.research.cli acquire-ingest --help                                 # inbox -> raw dir + manifest + ledger
python3 -m nse.research.cli daily-update --help                                   # one session; scheduler-ready
python3 -m nse.research.cli acquire-coverage --help
python3 -m nse.research.cli health                                                # protected files, calendar, EOD, modules
python3 -m nse.validation.run_all --group data --group data_readiness --group acquisition
```

## Workflow

1. `health`, then `acquire-plan` for the window: the missing sessions are the download list.
2. The owner downloads into an inbox folder and states the source page and download date.
3. `acquire-ingest` with `--source-page`, `--downloaded-on`, `--provenance-status` as the
   owner stated them. Never invent a download date: use `UNKNOWN`.
4. Read the ledger outcomes: INGESTED, DUPLICATE, REVISED_FILE_QUARANTINED, QUARANTINED.
5. Re-run `acquire-plan`; then the data-quality-validation skill and `inventory`.

## Hard restrictions

- A UDiFF file is detected but never ingested until a real sample is documented (B18).
- A revised file for a held session is quarantined; the held raw file is never overwritten.
- Source files are copied, never moved or deleted. Nothing in `nse/data/` is cleaned up.
- Without a calendar, weekdays are candidate sessions only (CALENDAR_UNVALIDATED), never
  "expected" sessions.
- Raw and adjusted prices are never mixed; nothing here adjusts prices (B7).

## Output and verification

Report the plan counts, the ledger outcomes per file, and the coverage before and after.
Verified when `acquire-plan` shows the sessions HELD and `run_all` local_data passes.
References: D29, D31, B17, B18; `nse/docs/EOD_FORMAT_EVIDENCE.md`, `REAL_DATA_ACQUISITION_PLAN.md`.
