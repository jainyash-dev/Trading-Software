# API contracts

> Product Prompt 00. The local API is the only boundary between the desktop UI and the
> research engine. Prompt 3 implements it. This page is the contract Prompt 3, the UI
> prompts, and the tests share.
>
> Engine payloads keep the field names in `research.json` (schema `research-pipeline/1`)
> and in the scan reports. The platform may wrap them. It does not translate status strings.

## 1. Boundary

Owner decision D57 replaces the earlier Tauri command boundary. The browser is the UI.
Historical notes that mention a desktop shell are not the current contract.

| Caller | Callee | Allowed |
|---|---|---|
| React UI in the browser | API on `127.0.0.1` | Yes, with the session cookie and the checks below |
| A page on another origin | API | No |
| API | `nse.research` public functions and existing files | Yes, when a later route implements that call |
| API | broker, Kite, or any order endpoint | No |
| `nse/` | API | No |

Base URL: `http://127.0.0.1:<port>/api/v1`. The port is chosen at launch. The log may
record the port. It does not record the session value.

Session (D57):

1. The value is at least 128 bits from the operating-system generator. It stays in process memory. It is not written to sqlite, argv, a URL, localStorage, or a log line.
2. The browser receives it only as an HttpOnly, host-only cookie, `SameSite=Strict`, `Path=/`. `Secure` is off for `http://127.0.0.1` so Safari keeps the cookie, and on when `GTF_COOKIE_SECURE=1` (a later HTTPS origin).
3. Every `/api/v1` call except `OPTIONS` sends `X-GTF-Request: 1`. A form post cannot set that header.
4. `Host` must be the bound loopback host and port. `Origin`, when present, must be that origin or an origin listed in `GTF_PUBLIC_ORIGINS` (the Vite dev server). `Sec-Fetch-Site: cross-site` is refused.
5. A missing or unknown session is HTTP 401 with `error.code = UNAUTHENTICATED`. The body does not echo the cookie. `POST /api/v1/session/bootstrap` issues the cookie. `POST /api/v1/session/logout` revokes it.
6. CORS does not use `*`. A credentialed response echoes only an allowed origin. The dev server proxies `/api` so the browser stays on one origin.

One API process holds the instance lock. A second launch prints the existing URL and exits. It reads `instance.port` only. It does not receive a session. See the process model in the system architecture.

There is no `Authorization: Bearer` header and no token query parameter.

Header on creating calls: `Idempotency-Key`. A create without that header is HTTP 400.
A key whose job is `PENDING_DATA`, `VALIDATING`, or `RUNNING` returns that job and
starts nothing. `INTERRUPTED`, `FAILED`, and `CANCELLED` release the key. Only
`SUCCEEDED_COMPLETE` and `SUCCEEDED_PARTIAL` keep returning the original result. A rerun
allocates a new key and a new run id. Fill keys follow the domain model
(`live-trigger:{entry_id}`, `live-fill:{fill_id}`, `live-exit:{entry_id}:{kind}`) and
are sticky for `LINKED`, `REFUSED`, and `RECONCILE_REQUIRED`.

## 2. Envelope

Success JSON:

```json
{
  "platform_schema": "gtf-platform/1",
  "data": {},
  "meta": {"fixture": false}
}
```

`data` holds either a platform object or the engine document unchanged. When the engine
document is included, `meta.engine_schema` is `research-pipeline/1`.

Fixture success, used before real integration:

```json
{
  "platform_schema": "gtf-platform/1",
  "data": {},
  "meta": {
    "fixture": true,
    "fixture_label": "FIXTURE_NOT_MARKET_DATA"
  }
}
```

The UI treats `fixture: true` as a banner state. The API rejects a body that sets
`fixture: true` and also cites a real `dataset_id`.

Error JSON:

```json
{
  "error": {
    "code": "DATA_INSUFFICIENT",
    "message": "short human text",
    "details": {}
  }
}
```

| HTTP | When | `error.code` examples |
|---|---|---|
| 400 | Malformed JSON or a missing field | `REQUEST_INVALID` |
| 401 | Missing or unknown session cookie | `UNAUTHENTICATED` |
| 403 | Host, origin, or request-marker refusal | `HOST_REJECTED`, `ORIGIN_REJECTED`, `CSRF_REJECTED` |
| 404 | Unknown id | `NOT_FOUND` |
| 409 | Idempotency key reused with a different body, or a second submission on one zone | `CONFLICT` |
| 422 | The domain refuses the action | engine codes such as `BLOCKED`, cap codes, `CALENDAR_UNRESOLVED` |
| 202 | Job accepted | none; the body is a job |
| 500 | Unexpected fault | `INTERNAL`. No stack trace in the body. The `job_id` or log id is in `details` |

422 is how unknown stays unknown. The API does not coerce a refused journal write into
an empty success.

## 3. Shared enumerations

Copied from the engine, not redefined:

- Gate ids `G0`–`G8`.
- Gate outcomes `PASS`, `FAIL`, `MANUAL`, `DATA_INSUFFICIENT`, `BLOCKED`, `NOT_EVALUATED`.
- Candidate statuses `BLOCKED`, `REJECTED`, `DATA_INSUFFICIENT`, `MANUAL_REVIEW`, `ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING`.
- Trade type for this product: `MIT`. `WIT-75` and `WIT-125` are accepted only to return the engine's blocked result.
- Zone overlay labels `FRESH`, `TESTED`, `INVALIDATED`, `UNKNOWN`.

Platform enumerations:

- Job state: `PENDING_DATA`, `VALIDATING`, `RUNNING`, `SUCCEEDED_COMPLETE`, `SUCCEEDED_PARTIAL`, `FAILED`, `INTERRUPTED`, `CANCELLED`, `SKIPPED_HOLIDAY`, `SKIPPED_UNRESOLVED_CALENDAR`.
- Scan completeness: `COMPLETE`, `PARTIAL`, `FAILED`.
- Plan lifecycle: `DRAFT`, `AWAITING_OWNER`, `APPROVED`, `ORDER_RECORDED`, `FILLED`, `CLOSED`, `CANCELLED`, `EXPIRED`, `SUPERSEDED`.
- Fill kind: `ENTRY`, `EXIT`.
- Fill source: `OWNER_ENTERED`.
- Book: `LIVE` or `SIMULATED`.

`SUCCEEDED_PARTIAL` is a success of the job runner and a failure of the full-universe
claim. Clients key off `completeness`, not off HTTP 200 alone.

## 4. Resources

Paths are the Prompt 3 surface. Fields marked engine are passed through.

### Health and overview

`GET /health`

Returns the existing health outcome (`OK`, `WARNING`, `FAIL`, `UNAVAILABLE`), scheduler
state, database files reachable, last successful ingest date, last scan run id.
A missing scan is `last_scan: null` plus `last_scan_state: UNAVAILABLE`. The last scan
is the latest non-fixture run.

`GET /overview?as_of=`

Copies `counts.symbol_status` and `counts.candidate_status` from the latest non-fixture
envelope. Also returns calendar classification, dataset id, and nulls for index, sector,
and breadth when those series are absent. A status the map omits is 0. When no such
scan exists, the counts object is null and the state is `UNAVAILABLE`, not a map of
zeros. Fixture runs are excluded.

### Instruments and universe

`GET /instruments?query=`

Search symbol, name, and ISIN. Results include `verified: true|false`. An unknown query
is an empty list, not an error.

`GET /universe?as_of=`

Returns members at that date and the limitation `UNIVERSE_UNVERIFIED` when the file says so.

`GET /calendar?date=`

Returns the session classification. An unresolved date returns the date with
`status: UNRESOLVED` and HTTP 200, because the calendar's answer is "unresolved", not
"missing route".

### Datasets and candles

`GET /datasets`

Lists dataset ids known locally, with manifest hash and whether research validation exists.

`GET /candles?symbol=&timeframe=&as_of=&dataset_id=`

Returns candles the replay would show at `as_of`. Timeframe is `M`, `W`, or `D`.
`as_of` is required. The response includes provenance and findings `known_at` that time.
It does not include later candles.

### Scans

`POST /scans`

Body: `mode` (`SCHEDULED`, `MANUAL`, `REPLAY`), `as_of`, `trade_type`, `universe`
(`SUPPORTED` or a symbol list), `dataset_id`, optional `risk` inputs.
Returns 202 and a job. The job's result link is a `scan_key`.

`GET /scans?limit=&cursor=`

History of non-fixture manifests. Each row has completeness, limitations, and `as_of`.
`include_fixtures=true` adds fixture rows, which keep `meta.fixture` true.

`GET /scans/{scan_key}`

`data` is the stored `research-pipeline/1` document, unchanged. The UI does not derive a
status, a count, or a gate. A fixture run is returned only when the request sets
`include_fixtures=true`, and `meta.fixture` is true.

`GET /scans/{scan_key}/symbols`

Each symbol object from that document, unchanged, including `symbol_status`, candidate
status, `gates`, and zone overlay status. The server may attach `deciding_gates` by
calling the existing `explain.deciding_gates` helper. The screen renders that list. It
does not compute one.

`POST /scans/{scan_key}/cancel`

Allowed while the job is `PENDING_DATA`, `VALIDATING`, or `RUNNING`. Result state
`CANCELLED` or `INTERRUPTED`.

### Decision bundle

`GET /symbols/{symbol}/bundle?as_of=&dataset_id=&trade_type=&scan_key=`

When `scan_key` is present, the response is the bundle stored for that run. The server
does not recompute it. Without `scan_key`, the server may build a new bundle, and the
response is a new run, not an edit of an older scan. `replay` is `RUN` or `NOT_RUN` as
the engine sets it. The API does not add candles. The plan action is enabled only when
the stored candidate status is present in that payload. Overlay styling alone does not
enable it.

### Watchlists and saved configurations

`GET|POST /watchlists`
`PATCH /watchlists/{id}`

`GET|POST /scan-configs`

A saved config is parameters only.

### Drawings

`GET /drawings?symbol=&timeframe=`
`POST /drawings`
`DELETE /drawings/{drawing_id}`

A drawing record stores symbol, timeframe, geometry in price and time, and a version.
The write does not modify a scan file, a decision bundle, or a zone's proximal or distal.
Zone and plan overlays are not drawing records and have no write route.

### Trade plans

`POST /trade-plans`

Body cites `scan_key`, symbol, zone natural key. The server copies the candidate.
If the candidate is absent, 404. The copy includes `authorises_order: false`.

`GET /trade-plans/{plan_id}`

Returns every stored version. Each version includes the copied `candidate_status`,
`gates`, `portfolio_checks`, `risk_plan`, `authorises_order` false, and
`selected_quantity` as `risk.py` stored it, including null. The screen renders those
fields and does not calculate a quantity, a status, or a gate.

`POST /trade-plans/{plan_id}/versions`

Owner selections: entry, stop structure, stop price, quantity, risk stage, risk percent.
The server runs `risk.py`. It stores the risk status. It does not silently clamp a
quantity. The response is the stored version, with the same fields as the GET.

`POST /trade-plans/{plan_id}/approve`

Records the owner and the version. 422 if required selections are empty or the risk
status is `RISK_RULE_FAILED` or `INVALID_LEVELS`.

### Journal, orders, fills

`POST /journal/entries`

Creates the journal entry from an approved plan version. 422 for statuses the store
already refuses.

`POST /journal/entries/{entry_id}/order`

One manual submission. 409 on a second one. Body: `submitted_at`, `order_ref`, `note`.

`POST /journal/entries/{entry_id}/fills`

Follows the domain-model write order. The first entry fill for an entry uses
`live-trigger:{entry_id}` and is the only fill that may call
`journal_event(..., TRIGGERED)`. A later entry fill on that entry uses
`live-fill:{fill_id}` and does not call `journal_event`. An exit uses
`live-exit:{entry_id}:{kind}` and calls the matching exit kind once.

The route returns the stored fill row. `LINKED` is HTTP 200. `REFUSED` is HTTP 422 and
includes the journal refusal text. `RECONCILE_REQUIRED` is HTTP 409. A repeated key
returns the stored row and does not call the journal again. The route is closed while
any fill is `JOURNAL_EVENT_PENDING`.

`GET /portfolio?as_of=`

Returns the research journal's triggered-month count and open-position count unchanged.
`LINKED` fills supply quantity and price. Valuation is a decimal plus `priced_on`, or
null plus `valuation_state: UNAVAILABLE`. `REFUSED`, `PENDING`, and paper rows are
omitted from quantity. A `TRIGGERED` event with no `LINKED` fill is
`FILL_NOT_RECORDED`. `RECONCILE_REQUIRED` is listed and is not given a second quantity.

`POST /journal/entries/{entry_id}/events`

Owner notes and the existing event kinds. Simulated events are rejected on a live entry.

### Backtests and analytics

`POST /backtests`

Body is the execution model the engine already requires. 422 when the engine would
refuse (no calendar, cap above 10, expiry above 10). The default body is the owner grid:
slippage 0.05, 0.10, and 0.20, with `STOP_FIRST` as the baseline and `EXCLUDE` as the
sensitivity. `TARGET_FIRST`, or any other slippage, is accepted only when the body sets
`experimental: true`, and the result is labelled experimental. Returns a job.

`GET /backtests/{run_id}`

Ledger, equity curve, manifest id, realism gaps, and the engine's non-performance label.
Walk-forward figures quoted from this API are the pooled result, not a sum of fold totals.

`GET /analytics/{validation_id}`

Figures computed from cited manifests. 404 if the manifest is missing. The payload
includes `sample_size`, `evidence_label`, and `NOT_PERFORMANCE_EVIDENCE`. An ad-hoc or
missing universe also includes `SURVIVORSHIP_UNCONTROLLED`. The journal screen does not
render `journal_summary` win rate as a strategy result. It shows per-trade R when the
prices exist.

### Paper

`POST /paper-runs`
`POST /paper-runs/{id}/steps`

Steps create simulated orders under that run. The handler does not call `journal_add`
or `journal_event` and does not pass paper counts into `merge_portfolio`. The response
`book` is `SIMULATED`. The live portfolio endpoint ignores these rows. The paper run
refuses its own eleventh simulated fill and its own eleventh open simulated position.

### Assistant

`POST /assistant/explain`

Body: a question and a list of object ids (`scan_key`, `entry_id`, `run_id`).
If the assistant is disabled, 422 `ASSISTANT_DISABLED`.
The response cites the object ids used. It has no `status` field that could be mistaken
for a candidate status. Suggested text is `commentary`.

### Reports

`POST /reports`

Body: report type and source id. Returns a job whose artefact is HTML or CSV.
PDF is the print path until a library is pinned.

### Settings, jobs, audit

`GET|PATCH /settings`
`GET /jobs/{job_id}`
`GET /audit?object_id=`

`PATCH /settings` writes an audit event. Capital and risk stage are ordinary fields.
The patch schema rejects unknown keys.

## 5. Job object

```json
{
  "job_id": "job-…",
  "kind": "SCAN",
  "state": "RUNNING",
  "idempotency_key": "…",
  "completeness": null,
  "progress": {"done": 10, "total": 100, "unit": "symbols"},
  "result_ref": null,
  "error": null
}
```

`progress.total` is omitted when the total is not known yet, rather than sent as zero.
`completeness` is null until the job finishes.

## 6. Compatibility rules

1. Adding a field is allowed. Removing or renaming a field already in this document is a new `platform_schema` version.
2. Engine schema changes are owned by the research workstream. The API passes them through and records `meta.engine_schema`.
3. Clients must ignore unknown fields.
4. Money and prices are decimal strings, matching the engine's decimal discipline. They are not binary floats in the contract.
5. Empty lists are empty lists. Missing data is `null` plus a state field.

## 7. What Prompt 3 must publish

A checked-in OpenAPI document generated from the implementation, diffed against this page.
Where this page and the code disagree, the disagreement is a defect in one of them and is
fixed before a UI prompt depends on the route. Until that file exists, this page is the
contract, and UI prompts use labelled fixtures that match these shapes.
