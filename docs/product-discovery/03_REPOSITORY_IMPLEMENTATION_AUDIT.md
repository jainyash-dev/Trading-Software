# Repository implementation audit

Audit date: 2026-11-10. Working tree, not HEAD. HEAD is `9e302df`. `platform/` is untracked.

## How a status was assigned

One primary status per capability ID from [02_MASTER_CAPABILITY_MAP.md](02_MASTER_CAPABILITY_MAP.md).

| Status | Rule used in this file |
|---|---|
| IMPLEMENTED_VERIFIED | The implementing path was read, and a test that does not mock that path passed in this audit, and the requirement for that ID is met by that path. External market validation is recorded as a risk, not silently upgraded into this status |
| IMPLEMENTED_PARTIAL | Some of the requirement is in code. A stated part is missing, unwired, or only a placeholder |
| IMPLEMENTED_UNVERIFIED | Code was found. This audit did not execute a non-mocked test of it |
| DOCUMENTED_ONLY | A requirement or design exists. No meaningful implementation was found |
| NOT_IMPLEMENTED | No meaningful implementation |
| BLOCKED | The capability cannot be finished until a named dependency or decision is resolved |
| NOT_IN_SCOPE | Excluded from the current product |
| DEPRECATED | Not used |

A passing unit test is evidence for IMPLEMENTED_VERIFIED only together with a read of the path it exercises. It is not evidence of TradingView parity, of a certified dataset, or of a browser session. Frontend tests stub `fetch`. They support a partial UI status. They do not verify the API.

### Tests this audit actually executed

| Suite | Result used below |
|---|---|
| `python3 -m nse.validation.run_all` for the 19 groups listed in the evidence register (repository through validation_framework) | 782 tests, 0 failures |
| Same command for `data`, `data_readiness`, `acquisition`, `legacy_day_trader_skills` | 522 tests, 0 failures |
| `PYTHONPATH=platform python3 -m pytest platform/tests` | 24 tests, 0 failures |
| `npm test` in `platform/web` | 40 tests, 0 failures |
| `npm run build` in `platform/web` | `tsc --noEmit` and Vite build succeeded |
| `python3 -m nse.validation.architecture` | PASS, 50 modules, 0 violations |
| `python3 -m nse.validation.docs_health` | PASS, 0 findings, including after this folder was added |
| `.venv/bin/ruff check` on `nse`, `tests`, `platform`, `.claude/hooks` | All checks passed |
| `git diff --check` | Clean |

The same runner was then executed for `data`, `data_readiness`, `acquisition`, and `legacy_day_trader_skills`: 522 tests, 0 failures (127, 51, 40, and 304). A `--group` invocation skips `local_data` and `reference_comparison`, so those two checks were run afterwards by calling them directly. `local_data` returned PASS: calendar years 2016-2025, no unverified calendar sources, 2,478 EOD archives loaded. `reference_comparison` returned PASS: 61 INFY rows matched a Yahoo Finance screenshot reference, 0 mismatches. That match is not independent validation. A single `python3 -m nse.validation.run_all` of every group plus those checks was not run as one process. Static lint via `run_all` was not run, because `python3 -m ruff` is not installed; ruff 0.17.4 from `.venv` was run directly and passed.

No browser session was opened against the API. No new real-data scan was started.

## Domain 1 - Market intelligence

| ID | Status | Evidence | What works | What does not | Next |
|---|---|---|---|---|---|
| MI-001 | IMPLEMENTED_PARTIAL | `GET /api/v1/overview` in `platform/gtf_platform/routes.py` returns the latest non-fixture scan, counts, and a calendar row when `as_of` is passed. `OverviewPage.tsx` calls it. The latest-scan card hardcodes job state as unavailable | Stored scan summary and calendar class can render | "Due / running" is not taken from the job runner. A missing session date skips the calendar call | Show the job row on the overview |
| MI-002 | IMPLEMENTED_PARTIAL | `routes.py` sets `index` to `None` and `index_state` to `UNAVAILABLE`. The page renders `Unavailable` | The product does not invent an index | No verified index series exists | Leave unavailable until a series is approved |
| MI-003 | IMPLEMENTED_PARTIAL | `nse/calendar/nse_calendar.py` loads `nse/data/calendar/`. `GET /api/v1/calendar` uses it. Four dates raise `CalendarAmbiguityError` | 2016-2025 classification for resolved dates | CAL-2 dates stay unresolved. The calendar README still says reconciliation covers Q1 2022 only | Owner ruling or continued unresolved state, shown in the UI |
| MI-004 | IMPLEMENTED_PARTIAL | Overview `sector` is `None`, `sector_state` is `UNAVAILABLE` | Matches D6 | No sector source | Keep unavailable |
| MI-005 | NOT_IMPLEMENTED | No relative-strength calculation in `nse/` or `platform/` | Nothing | The metric | Leave out of the initial release |
| MI-006 | IMPLEMENTED_PARTIAL | Overview `breadth` is `None` | Does not invent breadth | No labelled advance/decline over a named universe | Add only as a named count from a stored scan, or keep unavailable |
| MI-007 | NOT_IMPLEMENTED | No volatility product metric | Nothing | The metric | Do not add without a definition |
| MI-008 | DOCUMENTED_ONLY | FR-9.6 says regime splits wait for Prompt 10 | Nothing | The definition | Do not invent a regime |
| MI-009 | IMPLEMENTED_PARTIAL | `nse/data/corporate_actions/actions.csv` and `corporate_actions.py`. No economic calendar and no events screen | Corporate actions affect G0 | The Data Centre screen is static copy, including the text "Calendar: CAL-2 unresolved" | Show coverage from the API, not from a sentence in the page |
| MI-010 | IMPLEMENTED_PARTIAL | `app.py` health `data_ready` is fixed `False`. `eod_coverage.py` sets `data_ready.ready` false. Overview prints that | The UI does not claim `DATA_READY` | The flag cannot become true when the data later qualifies, because it is hardcoded | Drive the flag from the readiness verdict, still defaulting false |
| MI-011 | IMPLEMENTED_PARTIAL | `GET /api/v1/datasets` uses `run_manifest` fingerprints. Overview lists rows | Dataset id is visible | Research validation on those rows is fixed false | Keep the false validation label until R1 |
| MI-012 | IMPLEMENTED_PARTIAL | Findings are stored on the scan and in `data_quality.csv` via `reports.py`. Scanner can show quality codes from the envelope | A stored finding can be displayed | Overview does not list finding rows. Real-data findings were not re-run here | Show finding counts from the envelope on the overview |
| MI-013 | IMPLEMENTED_PARTIAL | Pipeline sets `full_universe` only when completeness is complete, the universe is not unverified, and the universe is not ad-hoc (`nse/research/pipeline.py`) | A partial or unverified scan is not labelled full | The overview does not explain ED-44's history cut | Print completeness and the universe limitation on the first screen |
| MI-014 | IMPLEMENTED_PARTIAL | `GET /api/v1/health` probes both DB files and the latest scan. Shell shows ingest date or the word unavailable | Reachability is visible | `orders_placed` is fixed false, which is correct, and scheduler state is not the value stored in settings | Show runner state and the last job error |

## Domain 2 - Stock discovery

| ID | Status | Evidence | What works | What does not | Next |
|---|---|---|---|---|---|
| SD-001 | IMPLEMENTED_PARTIAL | `nse/research/universe.py`, `nse/data/universe/nifty100_universe.csv` (185 periods). `GET /api/v1/universe`. `certified` is fixed false in `reference.py` | A membership file loads | Every period is unverified. B11-R has 271 blank decisions | Owner review. Do not mark certified in code |
| SD-002 | IMPLEMENTED_PARTIAL | `Universe.members` and `membership.py`. `risk_instruments` tests passed (130 in that group, which also covers risk and instruments) | As-of membership and the unverified limitation exist | No certified history. Nothing before 2020-12-31 (B11-P). TD-16: member ISIN is not compared with the bhavcopy ISIN | Review rows. Then compare ISIN at `as_of` |
| SD-003 | IMPLEMENTED_PARTIAL | `instruments.py`, `instrument_records.csv` (219 rows). Three ISIN changes are new listings, not joins | Verified lineages join. Unknown identity fails closed | BAJFINANCE, GRASIM, YESBANK stay split | Evidence for those three, or leave them `DATA_INSUFFICIENT` |
| SD-004 | IMPLEMENTED_PARTIAL | `GET /api/v1/instruments` reads the equity-names CSV in `reference._names`. `verified` is true only if a universe row is verified. Header search and `InstrumentFinder` call this route. No platform test calls the route | Search works when the names file is configured | It is the current names file, not the historical identity master. `verified` is false while B11-R is open. This route was not executed in `platform/tests` | Point search at identity records and test the route |
| SD-005 | IMPLEMENTED_PARTIAL | `POST /api/v1/scans` → `research.execute` → `pipeline.run` → `scanner.scan`. Platform test `test_mit_scan_stores_the_pipeline_envelope_and_bundle` passed on a fixture CSV. Scanner page posts the body and polls | A fixture MIT job runs through the real engine and is stored | A Nifty 100 scan was not run. The UI was not driven against the server. Non-MIT inputs are empty candles | Run one labelled real scan from the UI after B11-R, or before it with the limitation visible |
| SD-006 | IMPLEMENTED_PARTIAL | `schedule.consider` after 15:45 IST calls `prepare` and `accept_job` only when the file is already on disk. `providers` raises `PUBLIC_NSE_DOWNLOAD_DISABLED`. Default scheduler is off. The worker does not start when `testing` is set | The code path refuses to download | Not executed as a clock. Settings `scheduler_enabled` is stored and is not what `consider` reads | Wire the setting to the runner, or stop storing a dead flag |
| SD-007 | IMPLEMENTED_PARTIAL | Scan requests carry `as_of`. `scanner.scan_history` exists. Lookahead group passed (13) | A historical `as_of` is the scanner's contract | The UI was not shown replaying a real date. `scan_history` is not an API | Expose historical mode as the same job type, with the dataset id |
| SD-008 | IMPLEMENTED_PARTIAL | `filterSymbols` in `platform/web/src/features/scanner/model.ts` hides rows. Vitest covers order and status text | Filters do not reorder or rewrite status | A filter value of `PASS` matches a gate outcome, not only the candidate status. That can hide the difference between a gate and a candidate | Filter candidate status and gate outcome as separate controls |
| SD-009 | IMPLEMENTED_PARTIAL | `GET` and `POST /api/v1/scan-configs`. Secret-like keys are rejected. The client applies only `mode`, `trade_type`, and `universe` | Configs persist | `as_of`, paths, and risk inputs are not applied. `GET /api/v1/scan-configs` has no platform test | Apply the stored fields the contract allows, and test the GET |
| SD-010 | IMPLEMENTED_PARTIAL | `watchlist` tables in `db.py`. Platform test `test_watchlist_settings_drawings_and_audit` passed. The page calls the API. Vitest stubs `fetch` | Lists persist in platform SQLite and are not eligibility | The browser was not used. Eligibility is always null from the server, which is correct | Keep it that way |
| SD-011 | IMPLEMENTED_PARTIAL | Scanner renders `symbol_status`, gates, and `authorises_order` from the payload. `presentStatus` does not map an unknown code to Pass | Stored classification is shown | The client does not independently prove the server used the engine. A stored fixture `PASS` will display | Keep rendering stored fields |
| SD-012 | IMPLEMENTED_PARTIAL | Symbol route adds `explain.deciding_gates`. Reasons are on the symbol result | Stored reasons can be shown | No rank is invented, and no richer "why nothing qualified" page exists beyond the row | Show deciding gates on the row that is already returned |
| SD-013 | IMPLEMENTED_PARTIAL | Manual reasons and the checklist are on the candidate. The best status string is long enough that the UI must not shorten it to "approved" | The status text can be shown | There is no recorded human resolution workflow in the UI | Leave the checklist visible on the scanner row |
| SD-014 | IMPLEMENTED_PARTIAL | Envelope completeness and `full_universe` | The flag exists | A partial job can still show candidate rows. The history column shows job state only for the in-memory job | Label every historical row with its stored completeness |
| SD-015 | IMPLEMENTED_PARTIAL | `store.accept` reuses the same idempotency key and body, and conflicts on a different body. WIT test covers the idempotent case | Duplicate submits return the existing job | Cancel requires an idempotency header and then discards it (`routes.py` cancel). A skipped calendar job is not in the released-key set | Decide whether cancel is idempotent, and test it |
| SD-016 | IMPLEMENTED_PARTIAL | `GET /api/v1/scans` and `GET /api/v1/scans/{scan_key}` return the stored envelope. `test_stored_partial_scan_is_not_recomputed` passed | Old bytes are returned | `GET /api/v1/scans` has no platform test. Research `scans.raw_json` and platform `scan_result` are two stores | Document which store the UI reads. It reads the platform envelope |
| SD-017 | IMPLEMENTED_PARTIAL | `scanner.scan` adds `UNIVERSE_UNVERIFIED` when no universe is supplied. Ad-hoc universe path in `research.py` | The limitation is attached | A user can still read an ad-hoc scan as if it were the index | Keep the limitation on the scan header |
| SD-018 | IMPLEMENTED_VERIFIED | `scan_symbol` returns `BLOCKED` with `M4B_INTRADAY_NOT_APPROVED` when `trade_type` is not MIT (`scanner.py` lines 217-219). Platform test `test_wit_scan_is_blocked_and_idempotent` passed through `pipeline.run`. The client posts WIT and displays the returned status. It does not block by itself | WIT does not reach qualification | The WIT branches inside `qualification.py` are untested dead code relative to the scanner | Leave the short-circuit. Do not enable the branches |

## Domain 3 - GTF methodology engine

The engine tests that passed today are `zone_engine` (65), `mtf_freshness` (46), `strategy_gates` (82), `adversarial` (28), `integration` (53), and `lookahead` (13). They use synthetic candles unless a test name says otherwise. None of them is a TradingView comparison.

| ID | Status | Evidence | What works | What does not | Next |
|---|---|---|---|---|---|
| GTF-001 | IMPLEMENTED_VERIFIED | `nse/zone-engine/zone_engine.py` `run_engine`. Body-to-wick geometry. Traceability rows 1-4. `zone_engine` group passed | Demand and supply patterns and the 5-base limit | Wick-to-wick is not implemented (GTF-016). No external zone check (B10) | Record a TradingView sample before calling zones validated |
| GTF-002 | IMPLEMENTED_VERIFIED | Overlay `_overlay` in `nse/mtf-freshness/mtf_freshness.py`. Statuses include `FRESH`, `TESTED`, `INVALIDATED`, gap and session states | Lifecycle is distinct | Excluded-session touches block freshness rather than counting as tests. That is implemented and easy to misread | Keep the status visible on any future chart |
| GTF-003 | IMPLEMENTED_VERIFIED | Engine `state_step` and overlay. Adversarial tests in the group that passed | Tested demand is ineligible | A chart that is not built yet could still paint a tested zone as fresh if it uses the fixture book. The fixture book is separate | UX-005 must use overlay status |
| GTF-004 | IMPLEMENTED_VERIFIED | Close beyond distal sets `invalidated_index` | Invalidated zones stay ineligible | Same chart risk as GTF-003 | Same |
| GTF-005 | IMPLEMENTED_VERIFIED | Unknown, gap, and unverified session are not `usable_as_fresh_context` | Unknown does not pass | G0 and the overlay can both speak. The UI must show the overlay status, not only a gate letter | Same |
| GTF-006 | IMPLEMENTED_VERIFIED | `core_score` maximum 7. Eligibility requires fresh demand, active, core 7, and no disagreement flags. Every such zone still carries `LEGOUT_RELATIVE_SIZE_CONTEXT` | The score is separate from the checklist | A 7 does not mean the trade is approved | Display both |
| GTF-007 | IMPLEMENTED_PARTIAL | `confluence.score14`. The module note says no gate uses it. Sector and RSI/stochastic are `NOT_EVALUATED`. EMA, crossover, and gap are provisional | The display score cannot change a gate. Confluence tests sit in `strategy_gates`, which passed | The rulebook's extra points are not evaluated | Keep it off any rank column |
| GTF-008 | IMPLEMENTED_VERIFIED | `topdown.tda`. Integration results include TDA | One row per timeframe | "Coming from" analysis is manual | Leave it on the checklist |
| GTF-009 | IMPLEMENTED_VERIFIED | `eligible_after_overlay` and `manual_review_after_overlay`. Architecture A10 and `tests/test_repo.py` forbid raw `.eligible` reads. Architecture check passed | The overlay is the candidate source | `EngineResult.eligible` still exists for the engine's own assessment | Do not let a chart read it |
| GTF-010 | IMPLEMENTED_VERIFIED | `models.ROLES` for MIT | Monthly curve, Weekly trend, Daily execution | Q/HY/Y are context and are tagged `NO_PINE_REFERENCE` | Show that tag |
| GTF-011 | IMPLEMENTED_VERIFIED | `qualification.py` `_g0` through `_g8`. `evaluate_symbol` is called from `scan_symbol` (`scanner.py` line 277) and from two test helpers. `strategy_gates` passed | G0-G8 and precedence | RF4, RF5, RF9, RF10, and Essential Check 10 are checklist items by design. The WIT-only G5 branch has no test | Do not automate the checklist items without a rule decision |
| GTF-012 | IMPLEMENTED_VERIFIED | `models.derive_status` and `CHECKLIST`. The checklist is attached in `evaluate_symbol` | Best status keeps the pending checks | The UI label must not shorten it | Use `presentStatus` and the full code |
| GTF-013 | IMPLEMENTED_VERIFIED | Gate results carry evidence and source references. `explain.deciding_gates` reads the stored scan | A stored gate can be explained | `explain` cannot see a platform envelope unless that envelope is the scan JSON | Pass the stored envelope through, do not re-decide |
| GTF-014 | IMPLEMENTED_VERIFIED | Pine profile is comparison-only in `run_engine`. `_g5` and `_g7` force manual and do not use Pine-only supply as a target. ED-4 | The second detector cannot qualify a zone | A chart that draws every Pine zone as an entry would undo this | Draw Pine-only zones with a different label, or not as entries |
| GTF-015 | IMPLEMENTED_VERIFIED | Supply is `CONTEXT_ONLY`. Journal `direction` check is `LONG` | Short entries are refused | Supply zones are still required as targets and as conflict | Keep both roles labelled |
| GTF-016 | NOT_IMPLEMENTED | Traceability row 35: wick-to-wick not implemented. Row 33: sector, RSI, stochastic not evaluated. Row 34: checklist only | The gaps are explicit | Those rulebook sections have no calculator | Leave them manual. Do not invent a score |
| GTF-017 | BLOCKED | No `nse/data/intraday/`. Scanner returns before WIT gate code. B6, B15, M4b | The block is the behaviour | WIT recency and the monthly-supply branch are unreachable | Do not build WIT in the initial release |

## Domain 4 - Opportunity intelligence

| ID | Status | Evidence | What works | What does not | Next |
|---|---|---|---|---|---|
| OI-001 | IMPLEMENTED_PARTIAL | Status is stored on the platform envelope and in research `candidates`. Scanner page renders it | A stored status can be read | Stock Analysis does not open that status. Its fixture G1 is a hardcoded `PASS` behind the fixture toggle (`platform/web/src/chart/fixtures.ts`) | Drive analysis from the bundle route |
| OI-002 | IMPLEMENTED_PARTIAL | Reasons and deciding gates on `GET /api/v1/scans/{scan_key}/symbols` | Stored reasons render in the scanner | The analysis placeholder does not | Same |
| OI-003 | IMPLEMENTED_PARTIAL | `GET /api/v1/symbols/{symbol}/bundle` returns the stored symbol. `decision_replay.bundle` exists for the CLI | The API does not recompute | The chart does not call the bundle. CLI replay was not re-run on real data in this audit | One symbol page, one `scan_key` |
| OI-004 | IMPLEMENTED_PARTIAL | G5 evidence is on the candidate. Scanner can show gates | The obstacle is in the payload | It is not drawn on a chart | Overlay supply from the bundle |
| OI-005 | IMPLEMENTED_PARTIAL | G3 and `pre_entry_score` are stored. The scanner prints score as display | No rank column was found | The score can still be misread as a priority | Caption it as not a gate |
| OI-006 | IMPLEMENTED_PARTIAL | `explain.py` has a compare path over `scan.json`. `research_assistant` group passed (44) | CLI compare of stored scans | No product screen | A later report, not a rank |
| OI-007 | NOT_IMPLEMENTED | No matcher from a live candidate to a historical analogue | Nothing | The feature | Leave it out |
| OI-008 | IMPLEMENTED_PARTIAL | Checklist is always attached. `presentStatus` does not call an unknown code a pass. `app.test.tsx` asserts no buy or sell on the disconnected shell. That test stubs the network | The words are right on the scanner | Plans placeholder shows a hardcoded `MANUAL_REVIEW` badge in fixture mode. That is a label, not a decision, and it is still a fake status on a fake screen | Delete the hardcoded badge when the plan screen is real, or keep it behind the fixture toggle only |

## Domain 5 - Trade planning

There is no `/api/v1/trade-plans` route. `NOT_IMPLEMENTED` in `platform/gtf_platform/app.py` includes `trade-plans`. The engine pieces below are library and CLI behaviour.

| ID | Status | Evidence | What works | What does not | Next |
|---|---|---|---|---|---|
| TP-001 | IMPLEMENTED_PARTIAL | `pipeline.run` attaches `risk_plan_for_candidate` without changing status. Plans are not written to the store | A research run can carry a plan object | The UI Plans page shows unavailable numbers | Persist a plan only from a stored candidate id |
| TP-002 | IMPLEMENTED_PARTIAL | `levels.ranges` prints tiers. B9 is implemented as "do not pick" | Ranges exist | The UI does not present them. `selected_quantity` is not a product field yet | A control that starts empty |
| TP-003 | IMPLEMENTED_PARTIAL | `levels.select_target` and `_g7`. Invalid geometry returns manual and skips R:R | No invented target in the gate | The plan screen does not show provenance | Copy G7 evidence onto the plan |
| TP-004 | IMPLEMENTED_PARTIAL | `MIN_RR = 2.0`. Mixed buffers are manual | The gate matches the rule | A single displayed R:R would hide the buffer dependence | Show the range, not one number, until the owner picks a buffer |
| TP-005 | IMPLEMENTED_PARTIAL | `risk.py` sizes only `ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING` when the stored status matches `derive_status`. `approved` is false | Quantity is computed in the engine | Not in the UI | Call `risk.py`. Do not reimplement the formula in TypeScript |
| TP-006 | IMPLEMENTED_PARTIAL | `STAGE_BANDS` in `risk.py`. `test_research_risk` is inside `risk_instruments`, which passed | Bands match P-RISK-1 | No settings field saves a stage. The scanner can send a stage only if the risk box is checked | Settings, then the plan |
| TP-007 | IMPLEMENTED_PARTIAL | Scanner can send `risk.capital`. It is not a stored owner setting. `sessionStorage` key `gtf-scan-pending` can hold capital for the life of the tab | Capital can be submitted | It is not a durable setting, and the pending body is never cleared | Store capital in settings. Clear the pending key |
| TP-008 | IMPLEMENTED_PARTIAL | `pipeline.portfolio_checks` and `portfolio_at`. A missing count does not pass | The check exists on a research run | The platform job's portfolio input is whatever the client sent. The UI does not show the journal counts | Read `portfolio_at` inside the job. Do not trust a client-supplied count as the live book |
| TP-009 | NOT_IMPLEMENTED | No approval route, no person field, no audit event for plan approval | Nothing | The action | Add it when the plan store exists. Approval must not change the candidate status |
| TP-010 | NOT_IMPLEMENTED | No plan version table | Nothing | Mismatch versus a later scan | Store the candidate snapshot on the plan |
| TP-011 | IMPLEMENTED_PARTIAL | `store._zone_allowance` and `journal_orders`. Store group passed (56) | The journal enforces ED-3 | The UI cannot create the entry that the rule protects | Call `journal_add` from the API. Do not copy the rule |
| TP-012 | IMPLEMENTED_PARTIAL | Journal stores planned prices and a `TRIGGERED` price. `journal_summary` computes gross figures and says costs are not computed | Both numbers can exist in SQLite | No comparison view. No separate fill quantity if the trigger is one price | A read model over the journal, not a new calculator |

## Domain 6 - Portfolio and risk

| ID | Status | Evidence | What works | What does not | Next |
|---|---|---|---|---|---|
| PR-001 | IMPLEMENTED_PARTIAL | Risk config on a scan request. `PATCH /api/v1/settings` exists. The Settings page does not call it. The volume checkbox is component state | A scan can carry capital and stage | The settings screen does not save them | Persist stage and capital in settings, and show them as owner inputs |
| PR-002 | IMPLEMENTED_PARTIAL | `portfolio_at` in `store.py`. Platform `research.py` can open the research DB read-only when `GTF_RESEARCH_DB` is set | The journal is the book | Default research DB is `None`. The Portfolio page shows "usage unavailable of 10" | Point the API at the research DB and render `portfolio_at` |
| PR-003 | IMPLEMENTED_PARTIAL | `_open_positions` refuses the 11th inside the `TRIGGERED` transaction | The cap is enforced at commit | Not visible in the UI. An exit at the same timestamp still counts as open, by the code's ordering | Surface the refusal text |
| PR-004 | IMPLEMENTED_PARTIAL | `MONTHLY_TRADE_CEILING = 10`. The count is `TRIGGERED` events in the IST month | An exit does not free the month | The two-connection probe in AR-17 was not repeated. No test with that name was found | Add a two-connection test before relying on the new lock in production use |
| PR-005 | IMPLEMENTED_PARTIAL | Store tests cover a close freeing a slot and not the month. The group passed | The independence is in the journal | The UI text "of 10" twice is static, not a reading | Render both counts from `portfolio_at` |
| PR-006 | IMPLEMENTED_PARTIAL | `risk.py` for a plan. Live risk from a filled quantity is specified and not implemented in the platform | Plan-time risk exists | Position risk after the fill does not | Compute it from the journal row when the position view exists |
| PR-007 | NOT_IMPLEMENTED | No valuation function in `platform/`. AR-13 names the daily close | Nothing | Mark to market | Use the last accepted close and print the session date |
| PR-008 | IMPLEMENTED_PARTIAL | Portfolio placeholder does not invent a sector percentage | Unavailable is the right answer | It is copy, not a field from the API | Keep unavailable until D6 |
| PR-009 | NOT_IMPLEMENTED | Backtest `max_drawdown_r` is a research metric, not the live book | Nothing for the live book | A drawdown of the owner's account | Do not put the backtest number on the portfolio page |
| PR-010 | IMPLEMENTED_PARTIAL | `portfolio_at(at)` ignores later events | Point-in-time book in the CLI | No API | Read-only route |
| PR-011 | IMPLEMENTED_VERIFIED | Platform schema has no journal and no fill table (`db.py` migrations). `NOT_IMPLEMENTED` includes `journal` and `fills`. `test_meta_does_not_claim_orders_or_implemented_fills` passed. `authorises_order` is false | There is no second monthly counter | The next prompt could add one. AR-17 warns against it | Any fill route must call `journal_event` |
| PR-012 | IMPLEMENTED_PARTIAL | `JournalRefused` messages exist. The API does not journal, so the UI cannot show them | The engine refuses | The product does not | Return the refusal text unchanged |

## Domain 7 - Execution and monitoring

| ID | Status | Evidence | What works | What does not | Next |
|---|---|---|---|---|---|
| EX-001 | IMPLEMENTED_PARTIAL | `journal_order_submitted` and CLI `journal-order-submitted`. One row per entry | A manual submission can be stored from the CLI | No API and no UI. The owner cannot do it in the app | One route that writes `journal_orders` |
| EX-002 | IMPLEMENTED_VERIFIED | `platform/providers/__init__.py` raises `ProviderDisabled`. No order route. `nse/` network and broker bans are in `tests/test_repo.py`, and the repository group passed. Platform test asserts the provider source text | Nothing places an order | A future provider must stay outside `nse/` | Keep the disabled provider |
| EX-003 | IMPLEMENTED_PARTIAL | `TRIGGERED` is the fill event, with a price. It is not a separate fills table. FR-7.3 asks for a distinct fill record | The event is distinct from `journal_orders` | Quantity on the fill is the planned quantity. Partial quantity cannot be stored. No API | Keep one event. Add quantity only if the rule needs it |
| EX-004 | NOT_IMPLEMENTED | No view computes planned entry minus fill | The columns exist | The comparison | A journal read model |
| EX-005 | IMPLEMENTED_PARTIAL | Stop revisions after `TRIGGERED` are refused (`store.py`, RB 2139) | The lock exists in the CLI journal | No UI | Same journal route |
| EX-006 | IMPLEMENTED_PARTIAL | `planned_target` on the entry. `TARGET_HIT` is an exit kind | The target is stored | Nothing tracks an approach to the target during the session | EX-007 |
| EX-007 | BLOCKED | No quote feed. OQ-1 is open. EOD close is the research price. The product definition wants session monitoring and forbids intraday scanning | Nothing watches an open position | A market-hours price | An owner-approved quote that is not written back as the research price |
| EX-008 | BLOCKED | `alerts.py` diffs two scans into local events. No scheduler delivery, no market-hours path. The group `research_assistant` passed, which includes alert tests | Scan-diff events exist for two stored scans | They are not position alerts during the session | Do not pretend scan diffs are live alerts |
| EX-009 | IMPLEMENTED_PARTIAL | Exit kinds `STOP_LOSS_HIT`, `TARGET_HIT`, `CLOSED_MANUAL` | CLI can record them | No UI | Journal route |
| EX-010 | NOT_IN_SCOPE | No partial-exit kind. No owner decision defining scale-outs | Nothing | Scale-out | Leave it out of the initial release |
| EX-011 | IMPLEMENTED_PARTIAL | Exit kind is the reason. `ZONE_INVALIDATED` is separate from the stop | The kinds exist | There is no free-text taxonomy beyond `note` | The kind is enough for the first journal screen |
| EX-012 | IMPLEMENTED_PARTIAL | `journal_events` and `journal_orders` are ordered | CLI history | The Journal page is a placeholder. Fixture mode shows an `EXAMPLE` entry at 100 | Build the screen from the journal |
| EX-013 | IMPLEMENTED_PARTIAL | Backtest expires a pending simulated order after `entry_expiry_sessions` (the owner grid uses 10). The journal can store `EXPIRED`. Nothing in the platform expires a recorded order on a clock | The simulator has the rule | A live recorded order is not auto-expired or revalidated | The journal must refuse a late fill. Do not only simulate it |
| EX-014 | IMPLEMENTED_VERIFIED | `pipeline.py` sets `authorises_order` false. `research.execute` raises if the envelope says otherwise. Platform MIT test asserts false. The shell test finds no buy or sell control while disconnected | The flag and the absent control match the rule | A connected browser was not clicked | Keep the assertion on every new write route |

## Domain 8 - Trading journal

| ID | Status | Evidence | What works | What does not | Next |
|---|---|---|---|---|---|
| TJ-001 | IMPLEMENTED_PARTIAL | `journal_entries` stores zone, levels, checklist, and only two candidate statuses | CLI `journal-add` | No product screen. `BLOCKED`, `REJECTED`, and `DATA_INSUFFICIENT` are refused | API over the existing function |
| TJ-002 | IMPLEMENTED_PARTIAL | `journal_orders` | CLI | No UI | EX-001 |
| TJ-003 | IMPLEMENTED_PARTIAL | `TRIGGERED` | CLI | No UI | EX-003 |
| TJ-004 | IMPLEMENTED_PARTIAL | Exit kinds | CLI | No UI | EX-009 |
| TJ-005 | NOT_IMPLEMENTED | No screenshot column. `alert_note` is text | A note could name a file | There is no attachment record | A path note is enough for the first version. Do not make it an eligibility input |
| TJ-006 | IMPLEMENTED_PARTIAL | `note` on events and `manual_review_resolution` on the entry | Text can be stored | No mistake-class field and no UI | Add a class only if the owner names the classes |
| TJ-007 | IMPLEMENTED_PARTIAL | Same note fields | Text | No behavioural prompt in the UI | A note box |
| TJ-008 | NOT_IMPLEMENTED | No missed-trade or rejected-opportunity table. A scan row is not a journal of a decision the owner refused | Nothing | The record | A later journal type that cannot become `TRIGGERED` |
| TJ-009 | NOT_IMPLEMENTED | Journal page fixture says `NOT_EVALUATED` and hides it until the fixture toggle | The placeholder is honest | No review workflow | After fills exist |
| TJ-010 | NOT_IMPLEMENTED | No journal query API. CLI summary is by month | Month math in `journal_summary` | Search by symbol or setup in the UI | A read API with filters |
| TJ-011 | IMPLEMENTED_PARTIAL | Research tables are append-only. Platform `audit_event` stores digests for watchlists, drawings, and settings. Plan approval and fills are not audited because those routes do not exist | Append-only journal | P9 is not met for plans and fills | Audit those actions when they exist |
| TJ-012 | NOT_IMPLEMENTED | No `SIMULATED` book. AR-7 forbids sharing `journal_orders` | The live journal is the only book | Paper cannot yet be separated because paper does not exist | Build paper only as a separate store |

## Domain 9 - Quantitative research

| ID | Status | Evidence | What works | What does not | Next |
|---|---|---|---|---|---|
| QR-001 | IMPLEMENTED_PARTIAL | `backtest.py` takes `scan_history`. It does not call `evaluate_symbol`. Backtest group passed (78) | The simulator runs on the caller's scans | No API and no UI. The Backtest page says "Status: not run" and submits nothing | Do not put a Run button on the placeholder until it calls this module |
| QR-002 | IMPLEMENTED_PARTIAL | Lookahead tests passed. Walk-forward truncates candles. An unverified universe adds `SURVIVORSHIP_UNCONTROLLED` | The controls exist | A real-history backtest was not run in this audit. B11-R makes any current Nifty 100 run survivorship-uncontrolled | Run one only with that label |
| QR-003 | IMPLEMENTED_PARTIAL | `execution_policy.owner_grid` fixes gap, same-bar, slippage grid, and the 10/10/10 limits | Assumptions are explicit | They are not shown in the UI | Print them beside any future number |
| QR-004 | IMPLEMENTED_PARTIAL | `CostSchedule.rate_for` refuses an undated or cross-period range. No Zerodha numbers are hardcoded | The engine will not invent fees | B12 has no owner schedule, so a realistic costed run cannot be claimed | Wait for the owner's file |
| QR-005 | IMPLEMENTED_PARTIAL | Slippage is a required field. Zero is legal | It is applied symmetrically in `r_multiple` | Zero can be mistaken for "no assumption" | Show the number |
| QR-006 | IMPLEMENTED_PARTIAL | `metrics` computes win rate, expectancy, drawdown, profit factor, and more. Every result includes `NOT_PERFORMANCE_EVIDENCE` and `EXECUTION_REALISM_GAPS`. The Analytics page renders those names as `Unavailable` | The CLI can compute. The page does not invent figures | A fixture backtest also computes a win rate. The label has to travel with the number | The screen refuses figures unless a manifest id is on the payload |
| QR-007 | IMPLEMENTED_PARTIAL | `backtest-walk-forward` exists. TD-4: it writes no run manifest | Folds run | Results are less reproducible than `backtest` | Call `run_manifest` from the handler |
| QR-008 | IMPLEMENTED_PARTIAL | `backtest-sensitivity` uses the owner grid. Same TD-4 gap | The grid exists | No manifest | Same |
| QR-009 | NOT_IMPLEMENTED | No regime field | Nothing | Splits | Wait for a definition |
| QR-010 | IMPLEMENTED_PARTIAL | `run_manifest.py` on scan and backtest CLI. Reports group passed (26), including manifest tests | Scan and backtest write a sidecar | Walk-forward and sensitivity do not. The platform job stores an envelope, not the research manifest file, unless the pipeline wrote one on disk | Store the manifest id on the platform scan row |
| QR-011 | IMPLEMENTED_PARTIAL | `reports.write_all` and `narrative.daily_report`. No win rate in the scan summary | CLI reports | The Reports page only toasts that export is not implemented | Export the existing CSV files for a `scan_key` |
| QR-012 | IMPLEMENTED_PARTIAL | `SMALL_SAMPLE` under 30 closed trades | The flag exists | The UI does not show it | Show it with any metric |
| QR-013 | IMPLEMENTED_PARTIAL | Notes in `backtest.py`, `store.journal_summary`, and `reports.summary` | The code labels the arithmetic | `journal_summary` still computes a win rate from the owner's own fills. FR-9.1 says the journal screen must not present that as a strategy result | Keep the journal figure per-trade. Do not promote it to a strategy win rate |
| QR-014 | NOT_IMPLEMENTED | Paper page is a placeholder. No paper store | Nothing | The book | After the live journal UI exists |

## Domain 10 - AI research assistant

| ID | Status | Evidence | What works | What does not | Next |
|---|---|---|---|---|---|
| AI-001 | IMPLEMENTED_PARTIAL | `explain.py` reads a scan file. Tests in `research_assistant` passed | Deterministic explanation | It is not wired to the API. It is not a language model | Call it for the open symbol. Do not add a model for this |
| AI-002 | NOT_IMPLEMENTED | `NOT_IMPLEMENTED` includes `assistant`. The page has no client | Nothing | Answers | Leave the route absent until OQ-2 |
| AI-003 | DOCUMENTED_ONLY | FR-11.2 | Nothing | Citations | A constraint on AI-002, not a feature to build now |
| AI-004 | IMPLEMENTED_VERIFIED | No assistant module writes gates. Architecture A9 passed. Platform code raises if `authorises_order` is not false | The current process cannot override eligibility | A later assistant tool could | Do not give the assistant a write tool |
| AI-005 | IMPLEMENTED_VERIFIED | The API and the three screens have no assistant call. Frontend tests pass without one | The app runs with no model | Nothing | Keep the dependency optional |
| AI-006 | DOCUMENTED_ONLY | OQ-2 and FR-11.5. `.env.example` says the engine needs no credential | Nothing is called | Provider policy | Owner decision before any network call |
| AI-007 | NOT_IMPLEMENTED | No narration of the journal | Nothing | The feature | Same as AI-002 |
| AI-008 | IMPLEMENTED_PARTIAL | The deterministic explainer returns `NOT_IN_SCAN` for missing items. There is no model to hallucinate | The CLI path fails closed | There is no model-output filter because there is no model | Keep it that way until AI-002 |

## Domain 11 - Data and system

| ID | Status | Evidence | What works | What does not | Next |
|---|---|---|---|---|---|
| DS-001 | IMPLEMENTED_PARTIAL | `nse/eod/nse_bhavcopy.py` loader 2.1.0. `acquisition.py` quarantines an unknown header. This audit's `data` group result is in the evidence register | Legacy and UDiFF selection is implemented | A new header is refused, which is correct. Older docs still say UDiFF is unverified | Trust the loader, not the 2026-10-26 paragraph |
| DS-002 | IMPLEMENTED_PARTIAL | `nse/data/eod/raw/` and `manifest.csv` are present. Milestone and the data inspection in this audit describe 2,462 trading days and 2,478 archive dates. `eod_ready` is false because of CAL-2 | The files are on disk | Presence is not certification. `inbox/` is a partial copy and must not be scanned as the archive | Point scans at `raw/` plus the manifest |
| DS-003 | IMPLEMENTED_PARTIAL | `price_adjustment = "NONE"` in the loader. No adjustment in `corporate_actions.py` | Prices stay raw | A PREVCLOSE gap still has to be explained. It is not filled | Keep NONE |
| DS-004 | IMPLEMENTED_PARTIAL | Findings for missing sessions. The scanner candle table counts gaps and does not fill them | Gaps stay gaps | A client could still draw a fixture series. The analysis chart does, behind a toggle | Keep the toggle |
| DS-005 | IMPLEMENTED_PARTIAL | ED-29 and ED-37. Three unevidenced ISIN changes | Fail closed | Those histories are not one series | B11-I |
| DS-006 | IMPLEMENTED_PARTIAL | 2,064 events, 145 covered symbols, 46 empty responses not in `coverage.csv`. G0 manual when coverage is missing (`qualification.py`) | Unknown coverage does not pass | A stored scan from before that check can still show an old G0 `PASS`. This audit did not re-run that scan | Re-run any scan that will be shown in the UI |
| DS-007 | IMPLEMENTED_PARTIAL | Calendar load. Four `UNRESOLVED` rows. ED-44 cuts history in `scan_symbol` | The hole is not guessed | Monthly context before 2019-10-28 is absent on a later `as_of` | Say so on the scan |
| DS-008 | IMPLEMENTED_PARTIAL | Baseline 2020-12-31. Changes through 2025. Review file blank | The converter exists | Not certified. Count exceptions include days with 101 names | B11-R. Do not hide the 101-count rows |
| DS-009 | IMPLEMENTED_PARTIAL | Manifest hashes, `run_manifest`, dataset id in coverage JSON | Provenance for archives | Three archives are `USER_CONFIRMED` with no independent page. PROV-1 notes download-log gaps | Keep those limitations on the dataset row |
| DS-010 | IMPLEMENTED_PARTIAL | `nse/data/eod/quarantine/` holds incomplete downloads and the first refusal of two odd layouts that were later accepted under loader 2.1.0 | Quarantine is separate from `raw/` | A scan pointed at the wrong directory would change the universe of files | The API should refuse a fixture path that resolves at the real archive, which `sources.py` already does for one case |
| DS-011 | IMPLEMENTED_PARTIAL | Research migrations v1-v3 in `store.py`. Store tests passed | Scans and journal persist | Platform does not write this database except by calling the engine, which writes through the pipeline's own store when configured | One writer |
| DS-012 | IMPLEMENTED_PARTIAL | `db.py` creates jobs, scans, watchlists, configs, drawings, settings, audit. File mode `0o600` | Platform state persists | Drawings and settings are not used by the UI. No migration history table beyond the applied statements in code | Use the drawing table from the chart, or stop advertising it |
| DS-013 | IMPLEMENTED_PARTIAL | `JobRunner` polls every second. Heartbeat every 5 seconds. Platform tests drain jobs | A scan job completes in-process on fixtures | Cancel does not stop `execute` mid-call. It discards the result afterwards. Nothing requeues `INTERRUPTED` | Document that cancel is "do not store", not "kill the parser" |
| DS-014 | IMPLEMENTED_VERIFIED | `interrupt_stale` at startup. Tests `test_stale_running_job_becomes_interrupted` and `test_startup_interrupts_a_running_job_and_migrations_replay` passed | A stale `RUNNING` row becomes `INTERRUPTED` | The check is not repeated inside the one-second loop. A job that hangs with a fresh heartbeat is not interrupted | Repeat the stale check on the loop before unattended use |
| DS-015 | IMPLEMENTED_PARTIAL | `schedule.py` | See SD-006 | The stored setting is ignored | SD-006 |
| DS-016 | IMPLEMENTED_VERIFIED | `config.py` refuses a non-loopback bind. Cookie is HttpOnly and `SameSite=Strict`. `secure` defaults off. Tests for host, origin, marker, logout, and expiry passed | The boundary holds in the test client | Bootstrap has no password. `GTF_COOKIE_SECURE` defaults to `0`, which is required for `http://127.0.0.1` | Keep bind on loopback |
| DS-017 | IMPLEMENTED_VERIFIED | `logsafe.py` redacts `gtf_session=`. Test `test_logs_do_not_keep_a_session_cookie` passed. Secret-like scan-config keys are rejected | The cookie is not in the log line the test captures | `sessionStorage` can hold capital and risk. That is not a password. It is still sensitive | Clear `gtf-scan-pending` |
| DS-018 | NOT_IMPLEMENTED | CLI `store-backup` exists for the research DB. No platform backup and no restore rehearsal | A research backup command exists | FR-12.5 is not met | One command that copies both DB files and the manifest, tested on a copy |

## Domain 12 - Product experience

| ID | Status | Evidence | What works | What does not | Next |
|---|---|---|---|---|---|
| UX-001 | IMPLEMENTED_PARTIAL | `Shell.tsx`, `routes.ts`, 14 destinations. `app.test.tsx` renders every heading. Build succeeded | Navigation and the "Later" label | `available: false` does not block the route. Unknown hashes become overview | Keep placeholders labelled |
| UX-002 | IMPLEMENTED_PARTIAL | `OverviewPage.tsx` calls overview, datasets, universe, calendar, scans, and watchlists | It does not fall back to sample numbers when disconnected | Job state on the latest card is hardcoded unavailable. A present `counts` object turns a missing status into 0 (`model.ts`), which fights P8 | Treat a missing status key as unavailable, not zero |
| UX-003 | IMPLEMENTED_PARTIAL | `ScannerPage.tsx` posts, polls, cancels, and loads history. Vitest covers the stubbed flow | The client contract matches the API | Not exercised in a browser. Candle "chart" is an HTML table of 12 bars | Browser pass on a fixture job, then a real job |
| UX-004 | IMPLEMENTED_PARTIAL | `WatchlistsPage.tsx` | Search does not insert a typed symbol that the API did not return. Tests cover that with a stub | No browser pass | Same |
| UX-005 | IMPLEMENTED_PARTIAL | `CandleChart.tsx` uses Lightweight Charts 5 (`package-lock.json` resolves 5.2.1) with `attributionLogo: true`. The only mount is the Analysis placeholder, and only after the fixture toggle. Candles are `generateCandles` for symbol `EXAMPLE` | The library spike exists. `npm run build` includes it | It does not call `GET /api/v1/candles`. Zones are five hardcoded rectangles. G1 `PASS` is fixture copy. No render test mounts the chart | Prompt 06: bind the chart to the candle route and the bundle. Delete the hardcoded `PASS` from any non-fixture path |
| UX-006 | IMPLEMENTED_PARTIAL | `POST /api/v1/drawings` persists M/W/D drawings. The chart keeps drawings in React state with `persistence: "MEMORY_ONLY"`. The page says so | The API can store a drawing | The chart never calls it. Drawings are excluded from eligibility only because they never reach the engine | Connect the chart to the API. Keep drawings out of `inputs.load` |
| UX-007 | NOT_IMPLEMENTED | `Plans` in `pages.tsx` shows unavailable figures | The page admits it is unavailable | No plan | TP-001 |
| UX-008 | NOT_IMPLEMENTED | `Journal` placeholder | Honest empty state | No records | TJ-001 |
| UX-009 | NOT_IMPLEMENTED | `Portfolio` placeholder with static "of 10" | Does not invent a balance | No book | PR-002 |
| UX-010 | NOT_IMPLEMENTED | Backtest, Analytics, and Paper placeholders. Analytics names win rate and expectancy and renders `Unavailable` | Does not invent a performance figure | No run | QR-006 after a manifest exists |
| UX-011 | NOT_IMPLEMENTED | Reports button toasts that export is not implemented | The refusal is visible | No CSV download | QR-011 |
| UX-012 | IMPLEMENTED_PARTIAL | Theme and sidebar in `localStorage` (`gtf-theme`, `gtf-sidebar`). No broker password field | Local display preferences | Capital, stage, paths, backup, and the assistant switch are not saved. `GET /api/v1/settings` is unused | Wire settings that are not gates |
| UX-013 | IMPLEMENTED_PARTIAL | `Unavailable`, `EmptyState`, `Skeleton`. Overview tests check a missing scan is not zero | Loading and empty states exist | Missing status inside a counts object becomes 0. Data Centre copy is static | Fix the zero. Replace static data-centre sentences |
| UX-014 | IMPLEMENTED_PARTIAL | Fixture responses add `FIXTURE_NOT_MARKET_DATA`. The banner also turns on if any dataset row is a fixture (`store.tsx` / overview). Vitest covers the explicit button | Samples are labelled once the banner is on | The web doc says the banner appears only when fixture mode was requested. The code is wider. `gtf-scan-pending` can survive | Align the doc with the code. Prefer the wider banner |
| UX-015 | IMPLEMENTED_PARTIAL | `platform/run_api.py` and `gtf_platform/__main__.py` bind loopback. Vite proxies `/api` to `127.0.0.1:8765`. This audit built `platform/web/dist` and did not start the server | A production bundle exists | There is no packaged Mac app, no installer, and no onboarding. `web/dist` was absent at the start of the audit, so `GET /` returned the not-built JSON | Document the two-process local start. Do not add Electron |
| UX-016 | IMPLEMENTED_UNVERIFIED | Buttons and inputs exist. No accessibility pass was run. The 1100 px claim in Prompt 04 was not remeasured | The shell renders in jsdom | Contrast, focus order, and zoom were not checked | A keyboard pass when the real screens exist |
| UX-017 | IMPLEMENTED_PARTIAL | Chart attribution flag is on. No telemetry client was found in `platform/web/src`. No updater | Privacy of the core UI is local | Licence text for the pinned Lightweight Charts build was not re-checked in this audit. AR-4 asks for that before Prompt 14 | Confirm the SPDX notice from the lockfile version |
| UX-018 | NOT_IN_SCOPE | Requirements section 9. No user table, no subscription, no mobile shell | Nothing | Those products | Do not build them in the initial release |

## Legacy `trader-*` modules

Not a GTF capability. The root README and `trader-broker`, `trader-scanner`, and the other `trader-*` folders are the US day-trading skill pack. `run_all` still has the group `legacy_day_trader_skills`. This audit did not read those packages line by line and does not treat them as Zerodha integration or as the NSE scanner. TD-10 records the confusion. They should stay until the owner decides to split the repository. They are not DEPRECATED by an owner decision, so they are not marked deprecated here.

## Prompt claims checked against the tree

| Claim | Verdict |
|---|---|
| Prompt 00 documents exist | Met. Nine blueprint files are under `docs/product/` and `docs/architecture/`. This audit did not re-run their original review |
| Prompt 01 data work | Engineering for D47-D56 is in the tree. `DATA_READY` is not claimed. The milestone is right on that point and wrong if read as "no files" |
| Prompt 02 engine | The pipeline, journal, and backtest exist and the related test groups passed. Walk-forward manifests (TD-4) and external validation do not. R2 is open |
| Prompt 03 API | Substantially present and untracked: sessions, jobs, scans, watchlists, drawings, settings, candles. Fills, journal, plans, backtests, assistant, reports, and paper are absent, as `app.py` states. OpenAPI records 200 where handlers return 201 or 202 |
| Prompt 04 shell | Present: navigation, status chips, fixture banner, chart spike. No Tauri shell. Browser frame-time was not remeasured |
| Prompt 05 overview, scanner, watchlists | Present as API clients. Not verified in a browser. Not a certified scan |
| After Prompt 05 | No later prompt is implemented. Analysis, plans, journal, portfolio, backtest, analytics, paper, assistant, data centre, reports, and settings-beyond-theme are placeholders |

## End-to-end traces

| Path | Traced | Executed this audit |
|---|---|---|
| Scanner page → `POST /api/v1/scans` → job → `pipeline.run` → `scanner.scan` → platform `scan_result` → `GET` symbols | Code yes | Platform test on a fixture CSV yes. Browser no |
| Overview → `GET /api/v1/overview` → latest platform scan row | Code yes | Frontend stub yes. Server no |
| Watchlist page → platform `watchlist` tables | Code yes | Platform test yes. Browser no |
| Analysis page → candle API → engine zones | Broken. The page uses `fixtures.ts` | No |
| Plan or journal page → research journal | No route | No |
| CLI `journal-event` → caps | Code yes | Store tests yes. Not through the API |
