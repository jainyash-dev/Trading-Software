# Architecture audit

The target is the modular monolith in [SYSTEM_ARCHITECTURE.md](../architecture/SYSTEM_ARCHITECTURE.md) and [ARCHITECTURE.md](../ARCHITECTURE.md). This file records what the working tree does. It does not propose a new platform.

## Current shape

```
browser (platform/web, hash routes)
    → loopback FastAPI (platform/gtf_platform)
        → platform SQLite (jobs, scan envelopes, watchlists, drawings, settings, audit)
        → integration/ only
            → nse.research.pipeline.run → scanner.scan → qualification
            → candles, calendar, universe, corporate-action coverage, manifests
        → optional read-only open of the research SQLite
CLI (nse/research/cli.py)
    → the same engine and the research SQLite journal
```

One process is intended to host the API and the job thread (`gtf_platform/__main__.py`). A second launch hits an instance lock and prints the port. `nse/` remains a standard-library package. Platform dependencies live in `platform/pyproject.toml` (FastAPI 0.121.0, httpx 0.28.1, uvicorn 0.38.0). The root `dependencies` list is empty. This audit imported FastAPI 0.123.4 from the system interpreter to run the platform tests. That is a version skew, not a root-project dependency.

## Boundaries that hold

| Rule | Evidence |
|---|---|
| `nse/` does not import `platform/` | Architecture check passed, 50 modules, 0 violations. A repo search found no `gtf_platform` import under `nse/` |
| Platform imports `nse` only inside `platform/gtf_platform/integration/` | `test_research_imports_stay_inside_the_adapter` passed. `jobs.py`, `routes.py`, `store.py`, and `app.py` do not import `nse` |
| `qualification.evaluate_symbol` is not called from `platform/` | Production call is `scanner.scan_symbol`. `pipeline.run` calls `scanner.scan` |
| `authorises_order` stays false | Constant in `pipeline.py`. The adapter raises if a run returns anything else |
| Loopback bind | `GTF_BIND_HOST` must be `127.0.0.1` or `::1`. Test passed |
| Two databases | Platform migrates only its file. Research migrations stay in `nse/research/store.py` |
| No second monthly counter | Platform schema has no journal. See PR-011 |
| Fixtures are labelled | `FIXTURE_NOT_MARKET_DATA` on fixture envelopes. A fixture source that points at `nse/data/eod/raw` is refused in `sources.py` |
| `nse/` has no network or broker client | Repository tests passed. `platform/providers` raises `PUBLIC_NSE_DOWNLOAD_DISABLED` and is not used by a route |

Rules A1-A10 are about `nse/` only. They passed. They do not police the React application.

## Strengths

- Eligibility has one production path. Reports, replay, and the backtest consume scanner output.
- The journal enforces the caps at `TRIGGERED`, inside `BEGIN IMMEDIATE`, and refuses non-actionable candidate statuses on `journal_add`.
- The API session is an HttpOnly cookie with origin, host, and `X-GTF-Request` checks. The token is stored as a hash in process memory. A restart drops sessions.
- Job idempotency is in the platform database, not in the browser.
- The UI copy on the scanner says it does not score or approve. The code matches that sentence.
- Scan envelopes are stored and re-read. A stored partial scan is not recomputed (`test_stored_partial_scan_is_not_recomputed`).

## Violations and drift

| Item | What it is |
|---|---|
| Status documents lag the tree | Milestone text says the desktop implementation has not started. `platform/` is a large untracked tree. That is drift between the register and the files, not an import-cycle |
| Web docs lag the routes | `platform/web/docs/LIMITATIONS.md` says scan and candle routes do not exist. They do |
| OpenAPI status codes | The checked-in document records 200 for handlers that return 201 or 202. Validation errors are described as 422. The app returns 400 `REQUEST_INVALID` |
| `readiness.py` strings | The EOD capability text still says 1,233 files for 2021-2025. P-LOC-2 is described as open after the owner approved it |
| Settings versus scheduler | `app_setting.scheduler_enabled` is not the flag `schedule.consider` reads |
| Cancel versus the worker | `RUNNING` sets `cancel_requested`. `execute` has no cancel argument. The result is dropped after the function returns |
| Stale-job check | `interrupt_stale` runs at startup, not on the one-second loop |
| Client counts | A missing status inside a present `counts` object becomes 0 |
| Instrument search | The names CSV is not the identity master |
| Drawings | The API persists them. The chart keeps `MEMORY_ONLY` |
| Two scan stores | Research `scans` and platform `scan_result` both hold a run. The UI reads the platform envelope |
| Direct `evaluate_symbol` in tests | `tests/_research.py` and `tests/test_research_explain.py`. Production is still the scanner |
| CLI handlers inside domain modules | TD-1. Not a product defect |
| `decision_replay` imports `dashboard` inside the command | Exception X1, TD-2 |

No microservices, Redis, or extra databases were found.

## Duplication

| Duplicated idea | Why it matters |
|---|---|
| Research store and platform scan envelope | A bug fix in one report path can leave the UI showing the other |
| `EngineResult.eligible` and the overlay methods | Safe only while the UI never reads `.eligible` |
| Fixture chart zones and engine zones | The fixture book can teach the wrong freshness if the toggle is misunderstood |
| Legacy `trader-*` scanner and `nse/research/scanner.py` | Different products, same repository. TD-10 |
| `inbox/` and `raw/` | Same zip names. `inbox/` is not the full archive |

## Reliability

| Behaviour | Assessment |
|---|---|
| Idempotent scan create | Implemented for the same key and body |
| Crash during `RUNNING` | Becomes `INTERRUPTED` if the heartbeat is older than 30 seconds at the next startup. Not retried |
| Succeeded scan | Left in place. Not marked failed |
| Download interrupt | Quarantine holds `.download` files. They are not the research input |
| Append-only research rows | Triggers in `store.py`. Store tests passed |
| Backup | Research CLI only. Platform DB has no restore test |
| Scheduler after sleep | Not executed. The code paths a file that is already on disk |
| Monthly cap under two connections | The write lock is in the source. This audit did not repeat the 2026-11-09 two-connection probe |

## Security

No secrets are copied into this report.

| Control | Finding |
|---|---|
| Bind | Loopback only. Test passed |
| Cookie | HttpOnly, `SameSite=Strict`, `Secure` off by default so Safari can store it on `http://127.0.0.1` |
| CSRF | Not a secret token. The marker header is the static string `X-GTF-Request: 1`, plus origin and host checks |
| Auth | No password. Anyone who can open the loopback origin can bootstrap a session |
| localStorage | Theme and sidebar only. The session cookie is not written by the client. `sessionStorage` holds the pending scan body, which can include capital |
| Logs | Cookie redaction test passed |
| Database files | Created mode `0o600` |
| Input | Secret-like scan-config keys rejected. Pydantic errors become a fixed `REQUEST_INVALID` body |
| Audit | Digests, not before/after payloads |

This is an appropriate bar for one owner on loopback. It is not a multi-user design. UX-018 stays out of scope.

## Performance

Measured in this audit: the 19 research groups took about 79 seconds; the data, acquisition, and legacy groups took about 584 seconds; the platform tests took about 1 second; the frontend tests took about 3.5 seconds; the production build took about 1 second. Those times are suite times, not a Nifty 100 scan.

TD-17 is the known cost: every real-data command re-parses the archives. No new measurement of a full scan was taken. The UI poll interval defaults to 2 seconds. No evidence in this audit says the chart, the watchlist, or the API is too slow, because those paths were not timed against the archive. The Prompt 06 frame-time note in `platform/web/docs/CHARTING.md` was not re-run. It describes synthetic candles.

Do not add a cache until a scan of the real archive is timed. If a cache is added, AR-8 already says it must be keyed by archive hash and loader version and must stay disposable.

## Recommended improvements

These are repairs to the current shape, not a redesign.

1. Keep `nse/` as the only eligibility implementation.
2. Store the run-manifest id on the platform scan row so the UI and the CLI name the same bytes.
3. Drive `data_ready` from the readiness verdict. Leave it false until R1.
4. Point the chart at the candle route and the stored bundle.
5. Add plan and journal routes that call the research store in one transaction.
6. Fix the overview zero-count, the unused scheduler setting, and the OpenAPI status codes when those files are next edited.
7. Leave WIT, paper, and the assistant unbuilt.
