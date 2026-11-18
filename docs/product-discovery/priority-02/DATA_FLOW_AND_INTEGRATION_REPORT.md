# Data flow and integration

## Scan

The scanner page posts `/api/v1/scans`. The job runs the existing research pipeline and `reports.write_all`. For the lab fixture run the files are:

`/tmp/gtf-p02/reports/scan-8bec0a5c5d7566eb/`

`candidates.csv`, `fresh_zones.csv`, `blocked_zones.csv`, `data_quality.csv`, `run_manifest.json`.

The platform row stores the envelope, dataset id, as-of, completeness, fixture flag, and limitations. Fixture rows are omitted from list and get routes unless `include_fixtures=true`. Export reads the file bytes and returns that text. It does not run the scanner again.

The manifest for the lab run records `git_head`, a dirty-tree hash, input file hashes, `as_of`, and limitations including `FIXTURE_NOT_MARKET_DATA`. Missing metadata is not filled in.

## Candles

`GET /api/v1/candles` requires `symbol`, `timeframe`, `as_of`, and `dataset_id`. If `dataset_id` is not the hash of the local files, the route returns 409 "dataset_id does not match the local files". The chart plots `session_date` plus OHLC from that payload. It does not compute zones. Zone boxes come from the stored candidate geometry, and only when proximal and distal are numbers and the timeframe matches.

An incomplete monthly bar is absent (0 rows for June 2024 on an 18 June as-of). The page says so.

## Plan and journal

1. Create plan loads the stored envelope (fixture scans only with the query flag) and finds `symbol` + `zone_id` inside it.
2. Refused statuses never become a draft.
3. Preview calls `risk.plan_trade` with saved capital, `rpt_pct`, and stage. No stop or target is invented when the candidate has no structural target; the combination list stays empty.
4. Approve imports the stored scan dict, then `journal_add`. The client does not send a status. An aware `recorded_at` is converted to naive IST so it can be compared with the scan `as_of`.
5. A second approve of an approved plan returns the existing `entry_id` and does not insert another journal row.
6. `POST /api/v1/journal/{id}/order` calls `journal_order_submitted`. The row is a typed reference, not an order the app placed.
7. `POST /api/v1/journal/{id}/events` calls `journal_event`. `TRIGGERED` is the fill. `CLOSED_MANUAL` is the close. Caps and expiry run inside the research store.
8. Portfolio calls `portfolio_at` and adds no prices.

Journal times stored for the lab trade:

| Event | Clock stored |
|---|---|
| PLANNED | `2026-11-10T12:20:42` |
| Order submitted | `2026-11-10T12:22:02` ref `KITE-LAB-1` |
| TRIGGERED | `2026-11-10T12:22:12` price 160.44 |
| CLOSED_MANUAL | typed price 170, after the fill |

## Backup and restore

Default backup directory is `{data_dir}/backups`. The lab directory was `/tmp/gtf-p02/backups`. Both `platform.sqlite` and `research.sqlite` are copied with the SQLite backup API. `POST /api/v1/restore-check` with `{"directory": "<backup dir>"}` copies them to `{data_dir}/restore-checks/<UTC timestamp>-<8 hex>` and runs `PRAGMA integrity_check`. The handler refuses a destination that is a live database path. It does not delete older backups and it does not replace the live files.

Settings in the app calls those two routes. The restore button stays disabled until a backup directory has been returned.

## Scheduler

`scheduler_enabled` in saved settings wins when it is a real boolean. A missing row uses the process flag. A non-boolean stored value does not enable scheduling. The scheduler does not download market data. The lab settings save left it false.

## Session note

The session cookie is checked by the API. Restarting the API process invalidated the browser cookie until the page bootstrapped again. That is why Portfolio once rendered "has not been read" against a 401, and why the successful portfolio reading followed a reload.
