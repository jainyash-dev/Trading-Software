# Application integration audit

Scope is the existing `platform/` application. Priority-01 files (Nifty 100 review, calendar classification, TradingView intake, instrument-identity search) were not edited.

## Authority path

Platform routes load a stored scan envelope and call `nse.research`. They do not recompute G0-G8. The plan screen copies `candidate.status` from that envelope. `BLOCKED`, `REJECTED`, and `DATA_INSUFFICIENT` are refused before a draft exists. Approval calls `store.import_scan` and `store.journal_add`. The monthly cap and the open-position cap stay inside the research store.

`authorises_order` is set false on plan and portfolio payloads. No broker client, token, or OTP field was added.

## Defects found and fixed

| Defect | Evidence | Fix |
|---|---|---|
| Empty monthly candles still mounted the previous chart | June 2024 fixture returned 0 monthly bars because the month is incomplete at 18 June. `prepareSeries([])` is `ok: true`. | The chart mounts only when `series.candles.length > 0`. |
| A missing scan kept the previous symbol's qualification | `scan-missing` / `dataset_id=deadbeef` still showed FIX `NO_FRESH_EXECUTION_ZONE` and completeness `COMPLETE`. | The page clears candles, bundle, and explanation before the next request. |
| Fixture plans 404 unless the client asks for fixtures | `create_plan_route` hides fixture scans unless `include_fixtures=true`. The plan form omitted the flag. | The form sends it when the URL contains `fixtures=1`. |
| Approval crashed on a browser clock | `journal_add: cannot compare a naive and a timezone-aware time`. Scan `as_of` is naive IST. `new Date().toISOString()` is offset-aware. | `desk._match_journal_clock` converts an aware timestamp to naive IST before `journal_add`, order submission, and events. A timestamp that already matches the scan clock is unchanged. |
| Portfolio crashed on the same clock mix | `portfolio_at` compared aware `datetime.now(timezone.utc)` with naive journal rows and returned HTTP 500. | The default portfolio instant is naive IST. A caller-supplied offset is converted the same way. `StoreError` becomes HTTP 409. |
| Cold process could not import `nse` on plan preview | After an API restart, `GET /api/v1/plans/{id}` raised `ModuleNotFoundError: No module named 'nse'`. | `sources.ensure_repo_on_path()` runs before the risk and model imports. |
| Portfolio hid the journal positions | The page showed only three counts. | It lists `zones` from `portfolio_at` and prints `UNAVAILABLE` for valuation, sector, and drawdown. |
| Close was API-only | Journey E needs a recorded close. | Journal page posts `CLOSED_MANUAL` through the existing event route. |
| Backup was API-only | Journey F needs a visible backup and restore-check. | Settings calls `POST /api/v1/backup` and `POST /api/v1/restore-check`. The restore target is chosen by the server under `restore-checks/`. |

## Behaviour that was left as it is

- Fixture scans stay out of the default history until "Show fixture scans".
- Quantity on a draft stays empty until a buffer index is approved. The risk engine prints the combinations.
- Buffer rows from `plan_trade` can say `MANUAL_REVIEW`. That is the geometry status. It does not change `candidate.status`, and the screen does not call it a buy.
- The research journal has no fee or charge column. Charges were not stored in a second table.
- One `TRIGGERED` event is the fill record. The journal model does not store a list of partial fills.
- `DATA_READY` remains the research overview fact. It was not set true.
- Expiry, the 10-trade month, the 10-open cap, and ED-3 one-order-per-zone stay in `nse/research/store.py`.

## File ownership for this pass

One writer edited:

- `platform/gtf_platform/integration/desk.py`
- `platform/web/src/features/workflow/WorkflowPages.tsx`
- `platform/tests/test_product_flow.py`

`platform/gtf_platform/routes.py` and `platform/gtf_platform/db.py` were not modified. No file was renamed or deleted.
