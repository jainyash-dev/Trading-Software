# Priority-02 acceptance matrix

Status values: **Met** means the criterion was observed in the isolated lab or in an automated test that exercises the real research functions. **Partial** means a stated gap remains. Nothing here closes R1, R2, or R4.

| ID | Criterion | Status | Evidence |
|---|---|---|---|
| T-008 | Open a symbol from a stored scan with the scan id, symbol, as-of, and dataset id | Met | Scanner "Open analysis" URL for `scan-8bec0a5c5d7566eb` / FIX. |
| T-008 | Candles from the candle API, not a silent fixture | Met | 11 daily bars, fixture banner, last close 112 on the chart and in the payload. |
| T-008 | Monthly, weekly, daily, empty, error, dataset mismatch | Met | Weekly route: 2 bars. Monthly: 0 bars and an empty state. Mismatch: 409. Missing scan does not keep the previous explanation. Weekly plot was not separately screenshotted. |
| T-008 | No second qualification engine | Met | Zones and status come from the stored envelope. No fresh zone, so no zone box and no pass. |
| T-009 | Plan only a stored candidate | Met | Rejected envelope refused. Unknown zone is a 404 from the candidate lookup. |
| T-009 | Risk engine prints entry, stop, target, quantity | Met | First buffer 160.44 / 154.92 / 188.56 / 181. |
| T-009 | Approve into the research journal once | Met | Entry 1, one `PLANNED` row. Second approve did not add a row. |
| T-009 | Non-actionable refused | Met | Browser: "A REJECTED candidate cannot be planned". Test: same, plus 409 `ONE_ORDER_PER_ZONE`. |
| T-009 | Client PASS cannot create eligibility | Met | Status is read from the stored envelope. The approve body has index and note only. |
| T-010 | Approved plan → typed submission → fill | Met | `KITE-LAB-1`, then `TRIGGERED` 160.44. Copy says the app did not send the order. |
| T-010 | Fees | Partial | No journal column. Not stored. |
| T-010 | Several fills | Partial | One `TRIGGERED` event is the supported record. |
| T-011 | Portfolio from `portfolio_at` | Met | Before close: monthly 1, open 1. After close: monthly 1, open 0. |
| T-011 | Valuation unavailable | Met | Valuation, sector, and drawdown rendered `UNAVAILABLE`. |
| T-011 | No second monthly counter | Met | Counts are the store's. Close did not return the monthly slot. |
| T-012 | Manifest for the completed scan | Met | `run_manifest.json` beside the report files. Git head recorded. Dirty tree recorded, not hidden. |
| T-012 | Export equals the stored file | Met | Browser body length 282 equals the file. UI text equalled the API body. Product test compares the full string on its own fixture file. |
| T-012 | Missing file fails clearly | Met | HTTP 404 "That report was not written for this scan". |
| T-012 | Partial scan not shown as complete | Met in test | Product test stores completeness `PARTIAL`. The browser scan was `COMPLETE`, so that banner was not exercised in the UI. The analysis page does warn when completeness is not `COMPLETE`. |
| T-013 | Expiry unchanged and still correct | Met | Store file untouched. Both existing expiry and concurrency tests passed. |
| T-015 | Scheduler setting matrix | Partial | Automated cases passed inside the 37 platform tests. Browser saved `scheduler_enabled: false` only. No download was added. |
| T-017 | Backup both databases, integrity, restore elsewhere, live files unchanged | Met | `/tmp/gtf-p02/backups` and `restore-checks/20261110T065806Z-6ad56037`. Both integrity checks `ok`. Live SHA-256 unchanged. |
| T-017 | Failed and corrupt backups | Met in test | Product test covers a missing backup (404) and a corrupt SQLite file (422). Not repeated against the lab files. |
| T-018 | Deterministic explanation from the engine | Met | FIX explanation quotes `NO_FRESH_EXECUTION_ZONE` and says no candidate was evaluated. Same stored row produced the same sentence on reload. No model call. |
| Safety | `authorises_order` false | Met | Plan fact and portfolio payload. |
| Safety | `DATA_READY` false | Met | Overview sentence and warning list. |
| Safety | Owner work kept | Met | No reset, clean, stage, or commit. Priority-01 data files were not edited. Lab data is under `/tmp/gtf-p02`. |

## Release-gate reassessment

R1, R2, and R4 stay open. R3 and R5 are further along on an isolated fixture lab and are not closed. Software tests are not strategy validation, and a passing frontend build is not production readiness.
