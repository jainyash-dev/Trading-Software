# GTF P1 backup and recovery procedures

Local-first application (D57). Two SQLite files: platform state and the research journal.
This procedure does not recover the historical bhavcopy archive under `nse/data/eod/raw/`.

Policy contracts: `P1_BACKUP_RESTORE_POLICY.md`, `P1_RECOVERY_POLICY.md`.

## Backup

1. With the API allowed to be running, call `POST /api/v1/backup` with a new empty directory, or omit `directory` to use `data_dir/backups/<UTC-stamp>/`. The research CLI `store-backup` covers the journal alone.
2. The copy uses SQLite's backup API into `*.partial`, then renames. Existing destinations are refused.
3. Files are mode `0o600`; the directory is `0o700`.
4. `backup_manifest.json` records `backup_format`, `created_at`, file list, row counts, and `status: BACKUP_NOT_VERIFIED`.
5. Until a restore-check passes, the copy is not a verified backup.

## Restore check (non-destructive)

1. Call `POST /api/v1/restore-check` with the backup directory.
2. Files are copied into `data_dir/restore-checks/<timestamp>-<id>/` via a `.partial` directory that is removed on failure.
3. Manifest-listed sqlite files must all be present. Without a manifest, both application databases are required when either is present.
4. Each sqlite file must pass `PRAGMA integrity_check`.
5. Row counts of plans, jobs, journal entries, events, executions, orders and charges must match the backup.
6. Live database paths are never used as the restore destination. Live files stay unchanged.
7. Success returns `status: RESTORE_CHECK_PASSED`.

## Interrupted backup or restore

- A failed backup removes its `*.partial` file and does not leave a half-written destination name.
- A failed restore-check removes its `*.partial` directory. Live files remain untouched.
- An old leftover `*.partial` directory under `restore-checks/` is not deleted automatically; it is not the live store.

## Session recovery after API restart

1. Stale `gtf_session` cookies receive `401 UNAUTHENTICATED`.
2. Call `POST /api/v1/session/bootstrap` (or let the UI retry once). Prior in-memory digests are cleared.
3. Journal and plans on disk remain. Re-check portfolio/journal screens after authentication.
4. Do not treat bootstrap success as `data_ready` or P0 certification.

## Live recovery (owner-authorised only)

1. Keep the damaged live files.
2. Pass restore-check into a new directory.
3. Start the application against that directory on loopback.
4. Reconcile journal caps, zone allowance, and plan counts.
5. Only then point the ordinary data directory at the verified copy, retaining the damaged files until the owner says they can go.

## Limitations

- `NO_BACKUP_SCHEDULE`  -  no cron is installed.
- Application backup does not include market data archives.
- Session tokens are process memory; a restart requires a new bootstrap. The journal on disk survives.
