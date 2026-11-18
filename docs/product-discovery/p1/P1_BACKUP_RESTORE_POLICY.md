# P1 Backup and Restore Policy

**Status:** binding engineering contract for GTF P1  
**Code:** `platform/gtf_platform/integration/desk.py` (`backup_to`, `restore_copy`)  
**Tests:** `platform/tests/test_product_flow.py` backup/restore cases

## Included

| Artifact | How copied | Notes |
|---|---|---|
| `platform.sqlite` | SQLite `Connection.backup` via `*.partial` then rename | Mode `0o600` |
| `research.sqlite` | Same | Journal / portfolio canonical store |
| `manifest.csv` | `copy2` when `eod_manifest` is configured | Optional |
| `backup_manifest.json` | Written after files | `backup_format`, `created_at`, file list, table counts, `BACKUP_NOT_VERIFIED` |

Destination directory mode is `0o700`. Existing destinations and live database paths are refused (`409 CONFLICT`).

Default API path when `directory` is omitted: `data_dir/backups/<UTC-stamp>/`.

## Excluded

- Historical bhavcopy archive under `nse/data/eod/raw/`
- In-memory session digests (D57)
- Process memory, logs, browser storage
- Automated cron / `NO_BACKUP_SCHEDULE`

## Consistency

- SQLite backup API copies a consistent snapshot of each database (WAL frames included by the API; a raw filesystem copy of a live WAL DB is not acceptable).
- Manifest status after backup is always `BACKUP_NOT_VERIFIED` until restore-check succeeds.
- Application backup always requires both `platform.sqlite` and `research.sqlite` (the desk journal resolves through `research_path`, including the `data_dir/research.sqlite` fallback when `GTF_RESEARCH_DB` is unset). Missing research refuses the backup; incomplete copies are scrubbed.
- Restore-check always requires both application databases. A truncated manifest cannot drop `research.sqlite` from the requirement.

## Restore-check (non-destructive)

1. Source backup directory must exist.
2. Destination is always `data_dir/restore-checks/<stamp>-<id>/` via a `.partial` directory.
3. Live database paths are never used as the restore destination.
4. If `backup_manifest.json` lists sqlite files, every listed sqlite file must be present.
5. Without a manifest, presence of either application sqlite requires both `platform.sqlite` and `research.sqlite`.
6. Each sqlite file must pass `PRAGMA integrity_check`.
7. Table row counts for plans, jobs, journal entries/events/executions/orders/charges must match the backup file.
8. Success returns `RESTORE_CHECK_PASSED` and does not swap live files.

## Failure behaviour

| Failure | Result |
|---|---|
| Missing backup directory | `404 NOT_FOUND` |
| Empty / incomplete backup | `422 DATA_INSUFFICIENT`; `.partial` removed |
| Corrupt sqlite | `422`; live bytes unchanged |
| Overwrite / live destination | `409 CONFLICT` |
| Permission error creating dest | Exception; live unchanged |
| Any restore failure | `.partial` removed; live files untouched |

A failed restore is never reported as `RESTORE_CHECK_PASSED`.

## Live swap

Owner-authorised only. Procedure: keep damaged live files → pass restore-check into a new directory → start against that directory → reconcile caps → only then retarget the ordinary data directory.

## Known limitations

- No backup schedule.
- Application backup is not a full disaster-recovery archive of market data.
- Concurrent backup/restore against the same destination is refused by overwrite rules; operators should treat backup as a single-writer operation.
