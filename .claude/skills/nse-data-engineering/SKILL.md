---
name: nse-data-engineering
description: Plan, ingest and audit NSE end-of-day files through the offline acquisition layer (nse/research/acquisition.py). This skill owns collection and file custody. HELD means the bytes are in custody, not that the symbol-date is verified or certified. Content checks are data-quality-validation. Certification is gtf-p0-data-certification. Use when the owner has downloaded bhavcopies, when asked what data is missing for a window, or when setting up the daily EOD routine.
---

# NSE data engineering (acquisition and custody)

This skill owns source collection and custody. `data-quality-validation` performs the read-only file checks and does not edit. `gtf-p0-data-certification` owns certification. The `data-validator` agent stays read-only. A sourced transcription correction is done by the main session under that certification skill, with provenance and a recomputed hash. Never modify raw OHLC to close a continuity gap. Never infer a missing fact. `CORPORATE_ACTIONS_UNVERIFIED` stays visible until the code and the decision record remove it.

The owner downloads files; the system verifies hashes, copies, records and reports. There is no
network-fetching code in `nse/` (D31) and no provider subscription (paid or licensed sources
need owner approval). Downloads are the owner's action unless the owner approves a scripted
run for a stated scope. Approved so far (2026-11-09):
- D47: the missing 2021-2025 sessions;
- D55: the 2016-2020 sessions, through `scripts/eod_backfill.py` (official URLs from `acquire-plan`, rate-limited, resumable, never overwriting);
- D56: NSE corporate-action records for the historical NIFTY 100 members, 2016-2025, through `scripts/collect_corporate_actions.py`.

Anything outside that scope, including unrestricted future downloading, needs a new approval.

## Run

```
python3 -m nse.research.cli acquire-plan --start 2021-01-01 --end 2025-12-31     # HELD / MISSING / HASH_MISMATCH per session
python3 -m nse.research.cli acquire-ingest --help                                 # inbox -> raw dir + manifest + ledger
python3 -m nse.research.cli daily-update --help                                   # one session; scheduler-ready
python3 -m nse.research.cli acquire-coverage --help
python3 -m nse.research.cli health                                                # protected files, calendar, EOD, modules
python3 -m nse.validation.run_all --group data --group data_readiness --group acquisition
```

## Approved backfill (D47 + D55 scope: 2016-2025 only)

```
python3 .claude/skills/nse-data-engineering/scripts/eod_backfill.py download --start 2016-01-01 --end 2025-12-31 \
    [--include-excluded] [--include-unresolved]  # excluded sessions (D52, held for D33); UNRESOLVED dates (held, never accepted, D54)
python3 .claude/skills/nse-data-engineering/scripts/eod_backfill.py ingest     # one file at a time, URL as source_page
python3 .claude/skills/nse-data-engineering/scripts/eod_backfill.py report
python3 .claude/skills/nse-data-engineering/scripts/collect_corporate_actions.py [--symbols A,B]   # D56; resumable
```

Records:
- `nse/data/eod/download_log.jsonl` (every attempt) and `nse/data/eod/acquisition_ledger.jsonl` (every ingest outcome);
- `nse/data/corporate_actions/collection_log.jsonl`, `coverage.csv` and `raw/`.

The backfill script refuses dates outside 2016-2025 and any URL other than `nse_bhavcopy.official_url(date)`. A file that fails verification stays quarantined with the loader's reason.

A new layout variant is added only as an exact, tested schema (ED-38: `LEGACY_13_CRLF`, `LEGACY_13_CRLF_SHORTDATE`, the nested-member archive). It is never accepted by loosening the checks.

Regenerate `actions.csv` after a collection: every `raw/*.json` through `corporate_actions.from_nse_json`, then `corporate_actions.write`. Unrecognised subjects become `UNPARSED_PRICE_EVENT` (ED-39).

## Workflow

1. `health`, then `acquire-plan` for the window: the missing sessions are the download list.
2. The owner downloads into an inbox folder and states the source page and download date.
3. `acquire-ingest` with `--source-page`, `--downloaded-on`, `--provenance-status` as the
   owner stated them. Never invent a download date: use `UNKNOWN`.
4. Read the ledger outcomes: INGESTED, DUPLICATE, REVISED_FILE_QUARANTINED, QUARANTINED.
5. Re-run `acquire-plan`; then the data-quality-validation skill and `inventory`.

## Hard restrictions

- One source per date (ED-20): legacy up to 2024-07-05, UDiFF from 2024-07-08. A verified file
  in the other format is quarantined (FORMAT_NOT_SELECTED_FOR_DATE); an unseen header is refused.
- A revised file for a held session is quarantined; the held raw file is never overwritten.
- Source files are copied, never moved or deleted. Nothing in `nse/data/` is cleaned up.
- Without a calendar, weekdays are candidate sessions only (CALENDAR_UNVALIDATED), never
  "expected" sessions.
- Raw and adjusted prices are never mixed; nothing here adjusts prices (B7).

## Output and verification

Report the plan counts, the ledger outcomes per file, and the coverage before and after.
File custody is shown when `acquire-plan` shows the sessions HELD and `run_all` local_data passes.
HELD is custody of the bytes. It is not data verification and it is not research-universe certification.
References: D29, D31, B17, B18; `nse/docs/EOD_FORMAT_EVIDENCE.md`, `REAL_DATA_ACQUISITION_PLAN.md`.
