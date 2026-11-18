# System architecture

> Product Prompt 00. The enforceable research architecture stays in
> [docs/ARCHITECTURE.md](../ARCHITECTURE.md) (rules A1–A10). This document adds the
> desktop product around that engine. It does not move research modules.

## 1. Repository baseline (2026-11-09)

Recorded at the start of Prompt 00. Re-check with git before relying on the dirty-tree
list; other workstreams are editing the same checkout.

| Item | Value |
|---|---|
| Branch | `main` tracking `origin/main` |
| HEAD | `9e302df1a81c2b13696d8fab61f05d377481be2e` (`9e302df`, "latest code") |
| Staged files | none |
| `git diff --stat` | 76 files, +9796 / −2407 against HEAD |
| Untracked work | `docs/`, universe and corporate-action data, several `nse/research` modules, `nse/validation/architecture.py`, `pyproject.toml`, new tests |
| Protected Pine SHA-256 | `14293fa5d3c8e5ba9309b45804a840bb5d8c43d47c193ebb6bca0480bc0a5519` |
| Protected Rulebook Markdown SHA-256 | `039883be6b97ca39b00e5afe80f219a5d759dae99fa9c4179475f506a275d54b` |
| Rulebook PDF SHA-256 | `e41cd0e7893513a492a39095c0f771ec67b320f1b51bc356da7c6a2c2946c2fc` |

Architectural conventions already enforced:

- Modular monolith, Python 3.10+, standard library only inside `nse/` (A5).
- Imports point at the same layer or a lower one (A2). One qualification pathway (A9).
- Candidates come from `MtfSnapshot.eligible_after_overlay` and `manual_review_after_overlay` (A10 and `tests/test_repo.py`).
- No network and no broker imports under `nse/`.
- The root directory list is pinned by `tests/test_repo.py`. Adding a new top-level directory updates that test in the same change.
- Root `pyproject.toml` keeps `dependencies = []`.

No reset, stash, clean, stage, commit, or push was performed.

## 2. Existing system and the product

```
 local files                nse/ (unchanged boundary)              platform/ (new)
 bhavcopy, calendar,   -->  loaders, engines, scanner,      -->   local API, scheduler,
 manifest, universe         qualification, reports,               desktop UI, drawings,
                            backtest, journal store               settings, paper book
```

| Question | Answer |
|---|---|
| What already exists? | Zone Engine, MTF overlay, G0–G8, scanner, research envelope, reports, explain, alerts, static HTML dashboard, decision replay, backtest, execution policy, risk, SQLite journal, calendar, identity, membership, corporate actions, EOD loader, acquisition inbox, run manifests, health check |
| What is reusable as-is? | All of the above. The desktop product calls them. Status strings and gate ids stay those in `nse/research/models.py` |
| What is incomplete? | `DATA_READY` is not claimed (B11-R; CAL-2 was closed by D58). No fills table. No interactive desktop chart. No scheduler. Walk-forward and sensitivity write no manifest (TD-4). Full-archive parses are slow (TD-17). TradingView zone parity is not done (B8, B10, B17) |
| What needs an adapter? | The browser UI and the local API, in front of existing functions and report files. A provider adapter in front of the existing inbox. A chart view in front of decision bundles |
| What is new implementation? | `platform/`: API, job runner, application database, React UI, chart overlays, drawings, fills, paper book, assistant adapter |
| What must not be rebuilt? | Zone detection, freshness, G0–G8, status derivation, bhavcopy parsing, the journal's order rule, the backtest simulator |
| Debt that affects the product | TD-1 (CLI handlers inside domain modules), TD-4 (missing manifests), TD-12 (no structured logs), TD-16 (membership ISIN not compared), TD-17 (parse cost), TD-6 (partial types). See [technical debt](../TECHNICAL_DEBT.md) |

The static dashboard (`nse/research/dashboard.py`) stays. It is the offline HTML view. The
desktop chart is a new view of the same bundles. Neither view computes a gate.

## 3. Layers

```
 Layer A   Web application         platform/web
 Layer B   Local application API  platform/api
 Layer C   GTF domain engine      nse/zone-engine, nse/mtf-freshness, nse/research qualification path
 Layer D   Application services   existing scanner, backtest, store, plus platform jobs
 Layer E   Data infrastructure    nse/eod, nse/calendar, nse/research data modules
 Layer F   Persistence            raw files, research SQLite, platform SQLite, manifests
```

Layer C is the research system documented in [docs/ARCHITECTURE.md](../ARCHITECTURE.md).
Its internal layers (contracts, engines, data, methodology, research, portfolio,
application, tooling) do not change for Prompt 00.

Rules:

1. Layer A has no trading arithmetic. It renders payloads and sends commands.
2. Layer B validates requests, starts jobs, and reads or writes application records. It calls Layer C and D. It does not reimplement a gate.
3. Layer C is imported, not copied. `platform/` may import `nse`. `nse/` may not import `platform/`.
4. Network code, if any, lives in `platform/` or in the existing data-engineering scripts outside `nse/`. It writes an inbox. `nse/research/acquisition.py` remains the ingest path.
5. One Python process hosts the API and the job runner. No separate microservice, queue broker, or database server.

## 4. Technology choices

Each choice is an architecture recommendation (AR). Licenses are confirmed from the
pinned distribution before Prompt 14 ships a build. Expected licenses are stated so a
surprise is visible.

| Component | Choice | Why | Alternatives declined | Cost |
|---|---|---|---|---|
| Research engine | Existing `nse/` on Python 3.10+ | Already tested. A5 forbids runtime dependencies there | Rewriting in TypeScript or Rust | None |
| Local API | FastAPI, pinned in `platform/pyproject.toml` | OpenAPI is the contract the UI and the tests share. Same language as the engine, in-process calls | Stdlib `http.server` (weak schemas). A message bus (extra moving part) | MIT expected. One local process |
| UI | React + TypeScript, built with Vite | Component screens, typed payloads, local bundle | Server-rendered HTML only (the current dashboard remains for offline use; it is not the product shell) | MIT expected |
| Web application | React 19, TypeScript, Vite, opened in the browser | One local origin, the same UI in development and later cloud hosting. D57 | Tauri, Electron, and a native AppKit shell. Those are not the product | MIT expected. No Rust shell |
| Charts | TradingView Lightweight Charts 5.x, plus application-owned primitives | Candles, scales, zoom, pan, crosshair, offline bundle. Drawings stay our records. Detail in section 6 | KLineChart as the fallback. Advanced Charts is unsuitable here. A from-scratch canvas duplicates scales | Apache-2.0 plus the project's attribution requirement |
| Research database | Existing SQLite in `nse/research/store.py` | Journal and scan archive already migrate there | A server database | Public domain |
| Application database | A second SQLite file owned by `platform/` | Drawings, watchlists, jobs, and settings must not collide with Prompt 2 edits to `store.py` | New tables inside `store.py` during Prompt 2 | None |
| Market data | Existing files and manifest. Optional derived parse cache keyed by archive SHA-256 and loader version | Raw files stay canonical. The cache exists to address TD-17 | A new price warehouse as the source of truth | Disk |
| Jobs | Threads or asyncio inside the API process, state in SQLite | Restart recovery without Redis or Celery | A system-wide daemon that is easy to forget on a laptop | None |
| AI | Optional adapter behind a setting, default off | P1 and NFR-V3 | Baking a provider into eligibility | Owner-funded only if enabled |

Performance: in-process calls avoid serialising the full research path through HTTP on
every candle. HTTP is for the UI boundary and for job status. Large series are read by
symbol, not as one archive dump (NFR-P6).

Maintenance: two package manifests. Root dependencies stay empty so A5 remains true.
Platform Python dependencies are pinned in `platform/pyproject.toml`. The web app pins
its own lockfile. There is no Rust shell.

Integration risk: the root listing test includes the `platform` directory. The import
package is `gtf_platform` because a `platform/__init__.py` would shadow the Python
standard library. FastAPI must not be imported from `nse/`. The chart spike is a browser
measurement, not a webview-engine gate.

Migration: research files and the research database stay where they are. The UI reads
them. Nothing is converted in Prompt 00.

## 5. Local application design

### Process model

D57. The owner opens a browser on the loopback origin. There is no desktop shell process.

1. The owner starts the API (`python3 platform/run_api.py`). The process takes an exclusive lock on `instance.lock` under the data directory (`GTF_DATA_DIR`, or Application Support on this Mac).
2. If the lock is already held, this launch reads `instance.port` only, prints `already running at http://127.0.0.1:<port>`, and exits. It does not create a session and it does not open any other file in that directory.
3. If the previous process has died, the operating system releases the lock. This launch binds a new port and writes `instance.port`. Sessions are in memory, so the old cookie stops working when the process is gone.
4. The API binds `127.0.0.1` (or `::1` if configured). Port 0 lets the operating system choose. The port is not a secret. The session value is not written beside it.
5. The React bundle is loaded from the same origin when `platform/web/dist` exists, or from the Vite dev server, which proxies `/api`. There is no CDN.
6. The browser calls the API with `credentials: "include"` and `X-GTF-Request: 1`. JavaScript cannot read the session cookie. See [API contracts](API_CONTRACTS.md) section 1.
7. Long work (scan, backtest, ingest) is a job row. The UI polls or subscribes to job events. The foundation stores job rows and marks a stale `RUNNING` row `INTERRUPTED`. It does not start a scan.
8. Quit releases the lock. A job still marked running at the next launch becomes `INTERRUPTED` when its heartbeat is stale. A completion row is not written over it.
9. A future scan job calls `pipeline.run` and stores that envelope. Job code does not import the zone engine, the MTF overlay, `qualification`, or `derive_status`.
10. While the lock is held, live journal writes are intended to go through this API on one connection, one call at a time. Those write routes are not implemented yet. The research CLI remains able to write the journal. A probe with two connections committed an eleventh `TRIGGERED` in one IST month. That gap is Prompt 02's. This prompt does not change `store.py`.

Configuration that would change on a later cloud host (`GTF_BIND_HOST` stays loopback until that host exists, `GTF_PUBLIC_ORIGINS`, `GTF_PLATFORM_DB`, `GTF_RESEARCH_DB`, `GTF_COOKIE_SECURE`, `GTF_DATA_DIR`) is read at process start. Domain functions take paths and origins as arguments.

### Request path

```
UI screen -> browser fetch -> API handler -> nse function or platform store
                                         -> existing report folder or SQLite
```

The API returns the engine's JSON. It may add a `platform` object. It does not rename
`candidate_status`, gate ids, or `authorises_order`.

### Scheduling

Three scan modes share one job type.

| Mode | Trigger | Inputs |
|---|---|---|
| Scheduled | After the NSE cash session, when the calendar says the date traded, and the accepted bhavcopy for that date is ingested | Verified calendar, configured universe, MIT |
| Manual | Owner starts it | Chosen symbols or the supported universe, chosen dataset, chosen `as_of` |
| Historical replay | Owner starts it | An `as_of` no later than the newest accepted session. Loaders hide later findings |

The scheduler accounts for:

- Holidays and special sessions from `nse/calendar`. An `UNRESOLVED` date yields `SKIPPED_UNRESOLVED_CALENDAR`, not a guessed session.
- Delayed and missing files: the job stays `PENDING_DATA` until the file is accepted or the owner cancels. It does not scan a hole and report success.
- Duplicate execution: the idempotency key is dataset id, `as_of`, trade type, universe digest, pipeline version, and config digest. A key in `SUCCEEDED_COMPLETE` or `SUCCEEDED_PARTIAL` is returned. A rerun uses a new key and a new run id. `INTERRUPTED` and `FAILED` release the key.
- Shutdown, sleep, and restart: on launch and on wake, a running job whose heartbeat stalled becomes `INTERRUPTED`, then the scheduler looks for a due session with no complete run. It does not assume the process was awake at 15:45 IST.
- Interrupted runs: status `INTERRUPTED`, partial files kept, UI says the run is incomplete.
- Retry: the owner or the next wake starts a new attempt. Attempts do not stack identical complete runs.

Completeness values are `COMPLETE`, `PARTIAL`, and `FAILED`. `COMPLETE` requires every
symbol in the requested universe to have a symbol result. Symbols that finished as
`DATA_INSUFFICIENT` were scanned. Symbols that were never opened were not.
`UNIVERSE_UNVERIFIED` can still be `COMPLETE` as a run, and the UI still shows the
limitation. A partial run is never titled as a full-universe scan.

### Error handling

Domain refusals (cap exceeded, blocked candidate, unresolved calendar in range) are
structured errors with the engine's code. They are not HTTP 500. Detail is in
[API contracts](API_CONTRACTS.md).

## 6. Charting

Checked on 2026-11-09 against the public Lightweight Charts README
(`tradingview/lightweight-charts`, Apache-2.0, attribution text and a user-visible link,
`attributionLogo` can satisfy the link), the TradingView free-charting-libraries
comparison (Advanced Charts and Trading Platform are proprietary; the vendor states they
are not offered for personal use), and the KLineChart repository (Apache-2.0, built-in
overlays).

| Need | Lightweight Charts 5 | KLineChart 10 | Advanced Charts | Custom canvas |
|---|---|---|---|---|
| Candles and volume of history for one symbol | Built for this | Built for this | Built for this | Would have to be written |
| Zoom, pan, crosshair | Yes | Yes | Yes | Would have to be written |
| Drawing tools | Not built in. Series and pane primitives are the extension point | Built-in overlays, including segments and rectangles | Large drawing set | Would have to be written |
| Zone overlays | Primitives we own | Overlays we own | Vendor objects we would have to keep separate | Ours |
| Offline Mac app | Bundle the script. No TradingView login | Bundle the script | Proprietary licence, and not offered for personal use | No vendor |
| React | Wrappers exist; the app can also hold a ref to the chart | Usable from React | A separate integration product | Ours |
| Licence for this product | Apache-2.0 plus the README attribution | Apache-2.0 | Proprietary, personal use excluded by the vendor | None |
| Maintenance | Active vendor, plugin API | Smaller project, v10 already moved once | Vendor relationship | Entirely ours |

Recommendation (AR-4): use Lightweight Charts as the candle and scale renderer. Render
demand zones, supply zones, MTF marks, user drawings, annotations, and trade-plan levels
as series primitives that supply their own autoscale bounds. A trend-line end in the
right margin stores an explicit time after the last candle. Zone and plan primitives
have no drag handles. Persist drawings in the application database. Show the required
TradingView attribution on the chart.

The chart has no eligibility function. Indicators shipped by a chart library are not
inputs to G0–G8. If a later screen draws a moving average, it is decorative unless it is
the series `trend.py` already calculated, and it is labelled as that series.

Chart spike, in the browser, before the dependency is treated as final:

- About ten years of daily bars for one liquid symbol, plus weekly and monthly.
- Fresh, tested, invalidated, and unknown zones in different styles.
- A rectangle and a trend line with hit-testing.
- Pan and zoom while a decision bundle is loaded.
- Offline launch with the network disabled.

If hit-testing or frame time fails, switch the renderer to KLineChart and keep the same
persisted drawing records. Do not switch to Advanced Charts under the current vendor terms.
Do not start with a custom canvas.

### Chart object model

| Object | Producer | May affect eligibility |
|---|---|---|
| Market candles | Loaders and replay | They are the price input the engine already used |
| Demand zones | Zone Engine via the overlay | Only through the scanner, before the chart opens |
| Supply zones | Zone Engine via the overlay | Same |
| MTF overlay state | `MtfSnapshot` / decision bundle | Same |
| User drawings | Owner | No |
| User annotations | Owner | No |
| Plan entry, stop, target | Trade-plan record | No. The plan was copied from the candidate |

Each object stores its source, the `as_of` it was drawn for, and a content hash or
manifest id. Deleting a drawing does not change a stored scan.

## 7. Data flow

```
 official file --> inbox --> acquisition ingest --> manifest + raw archive
                                      |
                                      v
                              loaders --> DailyInput --> scanner.scan
                                      |                      |
                                      |                      v
                                      |               reports + research.json
                                      |                      |
                                      v                      v
                               decision bundle         research SQLite
                                                              |
 UI chart <--- API reads the bundle and the envelope ---------+
 UI journal <--- API reads store.py and platform fill rows
```

Historical replay uses the same arrows with an `as_of`. Later files may exist on disk.
`known_at` decides what a new scan can see. A chart opened from a stored `scan_key`
renders that run's bundle and does not recompute it. A replay started as a new job is a
new run. It is not written back onto the old scan. The overview's "last scan" ignores
jobs whose `meta.fixture` is true.

## 8. Persistence

| Store | Path | Authority |
|---|---|---|
| Raw archives | `nse/data/eod/raw/` (gitignored) | Canonical prices |
| Manifest | `nse/data/eod/manifest.csv` | File identity |
| Calendar, universe, corporate actions | `nse/data/` | Reference data, with their own evidence files |
| Scan folders | an output directory the owner chooses | The run's JSON and CSV |
| Research SQLite | the existing journal path | Scans imported there, journal entries, order submissions |
| Platform SQLite | a file under the application support directory, outside git | Jobs, watchlists, drawings, settings, fills, paper book, audit |
| Logs | application support directory | Diagnostics |

Derived results, including a parse cache and an equity curve, are never copied back onto
a raw archive.

## 9. Desktop packaging

Initial deployment is a developer-run local web process on this Mac. The owner opens
`http://127.0.0.1:<port>` in a browser. A later cloud deployment is configuration and
hosting, and it is not built here. The research engine is imported from the checkout so
methodology fixes ship with the code the tests already run.

The web bundle contains the chart library. TradingView attribution stays visible. The
bundle does not contain API keys or the session value.

## 10. Concurrency with Prompt 1 and Prompt 2

Prompt 1 owns data acquisition and the evidence files. Prompt 2 owns the research
pipeline modules it is already changing. Prompt 00 only adds documents. Later prompts
add `platform/` and do not edit those occupied paths unless the roadmap names the file
and the other workstream has released it.

See [agent ownership](AGENT_OWNERSHIP.md) and [the roadmap](../product/MASTER_PROMPT_ROADMAP.md).
