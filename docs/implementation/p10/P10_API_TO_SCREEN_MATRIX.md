# P10 API-to-Screen Matrix

Source of routes: `platform/gtf_platform/routes.py` and `app.py` (cross-checked with `openapi.json`, 58 paths). "Used by" is after P10.

| API | Methods | Used by (P10) | Notes |
|---|---|---|---|
| `/api/v1/session`, `/session/bootstrap`, `/session/logout` | GET, POST | Shell (probe) | Cookie session, D57 |
| `/api/v1/health` | GET | Shell status, Overview, Data Health, Jobs | `data_ready`, `readiness_state`, `certified_p0_data`, scheduler, DB reachability |
| `/api/v1/overview` | GET | Overview, Jobs | Counts, `job`, `active_job`, `job_phase`, `scan_due`; `index/sector/breadth` null |
| `/api/v1/datasets` | GET | Overview, Scanner, Data Health | Manifest hash, validation, fixture |
| `/api/v1/universe` | GET | Overview, Data Health | `certified` false; limitations |
| `/api/v1/calendar` | GET | Overview, Data Health | Session classification |
| `/api/v1/instruments` | GET | Global search, Watchlists | Identity verified flag |
| `/api/v1/scans` | GET, POST | Scanner, Scan History, Overview, Assistant, Reports | POST returns a job (202) |
| `/api/v1/scans/{k}`, `/symbols`, `/cancel` | GET, POST | Scanner, Analysis | Stored envelope |
| `/api/v1/scans/{k}/reports/{name}` | GET | Reports | 8 allowed file names |
| `/api/v1/scan-configs` | GET, POST | Scanner | |
| `/api/v1/jobs/{id}` | GET | Scanner, Jobs (lookup) | **No list route** |
| `/api/v1/symbols/{s}/bundle` | GET | Analysis, Scanner | |
| `/api/v1/symbols/{s}/explain` | GET | Analysis, AI Assistant (deterministic) | Rule-based text from stored scan |
| `/api/v1/candles` | GET | Analysis, Scanner | `certified` always false |
| `/api/v1/drawings` (+ `/{id}`) | GET, POST, PATCH, DELETE | Analysis | |
| `/api/v1/watchlists` (+ `/{id}`) | GET, POST, PATCH, DELETE | Watchlists, Overview, Scanner, Opportunities | |
| `/api/v1/opportunities` (+ ingest, detail, history, notes, transition) | GET, POST | Opportunities | |
| `/api/v1/plans` (+ detail, history, notes, submit, approve, reject, cancel, reopen, rationale) | GET, POST | Trade Plans, Analysis overlay, Overview activity | Journal mirror on read |
| `/api/v1/portfolio` | GET | Portfolio, Risk Overview, Overview caps | Journal-derived; EOD valuation |
| `/api/v1/journal` (+ detail, performance, export, order, executions, events, charges, notes, reviews, attachments) | GET, POST | Trading Journal, Overview activity | Canonical execution record |
| `/api/v1/settings` | GET, PATCH | Settings, Risk Overview | |
| `/api/v1/backtests` | POST | Backtesting | Returns labelled result; no run list |
| `/api/v1/backup`, `/restore-check` | POST | Settings | |
| `/api/v1/audit` | GET | not used | Requires `object_id`; no global feed |
| `/api/v1/meta` | GET | not used | |

## Screens without a backend (shown as capability-status pages)

| Screen | Missing backend | Status shown |
|---|---|---|
| Strategy Analytics | No analytics or manifest route | `NOT_IMPLEMENTED` |
| Shadow / Paper | No simulator (TJ-012, owner-deferred) | `NOT_IMPLEMENTED` |
| AI Assistant (language model) | No provider (AI-002, OQ-2) | `NOT_IMPLEMENTED`; deterministic explain is connected |
| Job list / activity feed | No list route | Jobs page shows latest and active job from `/overview`, plus lookup by id |
