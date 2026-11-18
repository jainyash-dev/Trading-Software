# Master prompt roadmap

> Product Prompt 00. The fourteen prompts that build the GTF Trading Intelligence
> Platform. Repository milestones MP0 and MP1 keep their evidence in
> [milestone status](../MILESTONE_STATUS.md). This page is the product series the owner
> issued on 2026-11-09. It does not rename MP0.

## 1. How the two series relate

| Repository milestone | Product prompt | Relationship |
|---|---|---|
| MP0 Repository foundation | none | Completed. Rules A1–A10, manifests, agent operating notes |
| MP1 Real NSE data readiness | Prompt 01 | Same workstream. Engineering for D47–D56 is recorded. `DATA_READY` is not claimed |
| not previously named | Prompt 00 | This blueprint |
| not previously named | Prompt 02 | The research pipeline already in `nse/research/`. Completion is Prompt 02's exit, not a rewrite |
| not previously named | Prompts 03–14 | New product work under `platform/` |

Prompt 02 is the research-engine completion pass. It consumes
[the data contract](../PROMPT2_DATA_CONTRACT.md). It does not start a second scanner.

## 2. Dependency order

```
00 blueprint
   |
   +-- 01 data readiness --------+
   |                             |
   +-- 02 research pipeline -----+--> 09 backtest UI --> 10 analytics --> 11 stress
   |                             |
   +-- 03 local API -------------+--> 07 plans and portfolio --> 08 journal and reports
   |        |                    |
   |        +-- 05 overview and scanner UI
   |        +-- 12 paper (after 03 and 02 contracts)
   |        +-- 13 assistant (after 03; no dependency on 01 finishing)
   |
   +-- 04 web shell --> 06 charts --> 14 certification
```

Prompt 03 and Prompt 04 may start from the contracts in `docs/architecture/` without
waiting for `DATA_READY` or for Prompt 02 to finish. They use labelled fixtures until
the live routes exist. They do not edit Prompt 01 or Prompt 02 paths.

Credible backtest numbers wait for validated inputs. The backtest UI and the simulator
tests may use synthetic fixtures before that, and those runs stay labelled
`FIXTURE_NOT_MARKET_DATA`.

The assistant is specified against the API and stays out of the eligibility path.

## 3. Parallel work

Genuine parallel streams after Prompt 00:

| Stream | Prompt | Writes | Does not write |
|---|---|---|---|
| Data | 01 | data modules and `nse/data/` evidence already in that workstream | `platform/`, qualification, UI |
| Research | 02 | research pipeline modules already in that workstream | `platform/`, raw evidence, UI |
| API | 03 | `platform/api`, `platform/jobs`, `platform/db`, `platform/pyproject.toml`, the one-line root-listing test | `nse/` methodology |
| Shell | 04 | `platform/web` shell, design system, navigation specimens | feature screens owned below, `nse/` |
| Scanner UI | 05 | `platform/web` overview and scanner features | chart feature, API core |
| Charts | 06 | `platform/web` analysis feature and chart primitives | scanner feature |
| Plans | 07 | plan and portfolio features, fill records | journal report exporter |
| Journal | 08 | journal and report features | plan editor |
| Quant UI | 09–12 | each feature directory named below | each other's directories |
| Assistant | 13 | assistant feature and provider adapter | gate code |
| Certification | 14 | integration tests and the release note | new product scope |

Concurrent implementation uses separate git worktrees. This checkout is already dirty
with Prompt 01 and Prompt 02 work. A later prompt does not reset or stash that work.
File locks are in [agent ownership](../architecture/AGENT_OWNERSHIP.md).

UI prompts 05–08 and 13 can proceed in parallel with fixtures once Prompt 04 has the
shell and the design-system components. They integrate with Prompt 03 when the route
they call is in the OpenAPI document.

## 4. Shared contracts

| Contract | Authority | Who may change it |
|---|---|---|
| Gate ids, outcomes, statuses | `nse/research/models.py` | Prompt 02 only, with a rule citation |
| `research-pipeline/1` envelope | `nse/research/pipeline.py` | Prompt 02 |
| [API contracts](../architecture/API_CONTRACTS.md) and the later OpenAPI file | Prompt 03 | Prompt 03, reviewed by the integration lead |
| [Domain model](../architecture/DOMAIN_MODEL.md) | Prompt 00 | Integration lead after Prompt 00 |
| [Frontend specification](FRONTEND_SPECIFICATION.md) | Prompt 00 | Prompt 04 may clarify visuals; it may not weaken a status rule |
| [Data architecture](../architecture/DATA_ARCHITECTURE.md) | Prompt 00 | Prompt 01 may extend a provider record; it may not change price authority |

A UI prompt that needs a field the contract lacks writes the gap down and waits. It
does not invent the field in the component and hope the API matches.

## 5. Prompt catalogue

### Prompt 00 - Product requirements and architecture

| Item | Content |
|---|---|
| Objective | Define the product, the boundaries, and the contracts so later prompts can build in parallel |
| Scope | Documents only |
| Deliverables | The nine files listed in section 7 |
| Dependencies | The existing repository, the Rulebook, the decision register |
| Input contracts | Current `nse/` behaviour |
| Output contracts | The architecture and product documents |
| Files owned | `docs/product/`, `docs/architecture/`, and short pointers in the existing docs named in section 7 |
| Agents | Integration lead, then independent reviewers |
| Acceptance | The documents exist, cross-links resolve, and `python3 -m nse.validation.docs_health` passes |
| Tests | Docs health and `git diff --check`. No new engine test |
| Exit | A later prompt can name its files and its fixture shape without asking what the product is |
| Must not modify | `nse/`, `nse/sources/`, the Rulebook PDF, Prompt 01 and 02 implementation files |
| Parallel | None during the writing. Reviews are read-only |

### Prompt 01 - Real NSE data readiness

| Item | Content |
|---|---|
| Objective | Reach a stated data-readiness verdict for the supported universe |
| Scope | Official EOD, calendar, identity, membership, corporate actions, provenance |
| Deliverables | The readiness note kept current; remaining blockers named with the exact owner action |
| Dependencies | D47–D56 already executed; CAL-2 closed by D58 (2026-11-10). Remaining: B11-R |
| Input contracts | [Data architecture](../architecture/DATA_ARCHITECTURE.md), existing loaders |
| Output contracts | Dataset ids, manifest rows, limitation codes the scanner already emits |
| Files owned | The data workstream paths in [agent ownership](../architecture/AGENT_OWNERSHIP.md) |
| Agents | Data validator, implementer for that workstream, independent reviewer |
| Acceptance | `DATA_READY` is claimed only if B11-R is complete and the calendar dates in range are resolved or explicitly excluded. Otherwise the verdict stays "not claimed" |
| Tests | Existing `data`, `data_readiness`, `acquisition`, and `risk_instruments` groups via `python3 -m nse.validation.run_all` |
| Exit | Prompt 02 can name, for a chosen window, which limitations a real scan will carry |
| Must not modify | Qualification rules, the desktop UI, `platform/` |
| Parallel | Prompt 02 on disjoint files, Prompt 03 and 04 on `platform/` |

### Prompt 02 - Complete GTF research pipeline

| Item | Content |
|---|---|
| Objective | One research path from local inputs to an envelope, a journal check, and a backtest, with manifests |
| Scope | Scanner, qualification, pipeline, reports, replay, risk, execution policy, backtest, store behaviour that Prompt 02 already owns |
| Deliverables | A reproducible `research` run for a declared window, limitations printed, no second qualification path |
| Dependencies | Prompt 01 for a real-data claim. Synthetic completion can precede it |
| Input contracts | [Prompt 2 data contract](../PROMPT2_DATA_CONTRACT.md) |
| Output contracts | `research-pipeline/1`, report files, `run_manifest.json` |
| Files owned | Research paths in the ownership document. Not `platform/` |
| Agents | Implementer, trading-rule auditor, quant researcher, lookahead audit |
| Acceptance | WIT remains blocked. Statuses match `derive_status`. Historical prefix tests pass. Walk-forward and sensitivity either write manifests or stay labelled incomplete (TD-4) |
| Tests | `strategy_gates`, `lookahead`, `integration`, `adversarial`, `reports`, `backtest`, `store` |
| Exit | Prompt 03 can call `pipeline.run` and persist the envelope without reimplementing a gate |
| Must not modify | `nse/sources/`, raw archives, the web shell |
| Parallel | Prompt 01 on disjoint data files, Prompt 03–04 on `platform/` |

### Prompt 03 - Local application backend and API

| Item | Content |
|---|---|
| Objective | A localhost API that wraps the engine and stores application state |
| Scope | Jobs, settings, watchlists, scan orchestration, read models. Fills may be stubbed until Prompt 07 if the contract is already in the schema |
| Deliverables | `platform/` package, OpenAPI document, token-bound server, job recovery |
| Dependencies | Prompt 00 contracts. Engine import surface from Prompt 02 as it stands; fixtures where a route's engine call is unfinished |
| Input contracts | [API contracts](../architecture/API_CONTRACTS.md), [domain model](../architecture/DOMAIN_MODEL.md) |
| Output contracts | OpenAPI file under `platform/`, fixture flag behaviour |
| Files owned | `platform/gtf_platform`, `platform/pyproject.toml`, `platform/tests`, and the root-list assertion in `tests/test_repo.py` that adds `platform`. Provider interfaces stay out of `nse/` |
| Agents | Implementer, independent reviewer for the session boundary |
| Acceptance | UI can run a fixture scan job and a real scan job against local files. 422 refusals match the contract. Root `dependencies` stay empty. `nse/` imports no platform module |
| Tests | `platform/tests` collected explicitly. Docs health still passes. Architecture check still passes for `nse/` |
| Exit | Prompt 05 and later can point a screen at a route |
| Must not modify | Gate logic, loaders, the Rulebook. Do not add FastAPI to the root `dependencies` list |
| Parallel | Prompt 04. Prompt 01 and 02 in their worktrees |

### Prompt 04 - local web shell and design system

| Item | Content |
|---|---|
| Objective | A browser UI on the loopback that hosts the navigation and the status language |
| Scope | Shell, tokens, status chips, empty/loading/error states, fixture banner, chart-library spike |
| Deliverables | A local web app that opens in the browser and shows specimens for every status in the frontend spec |
| Dependencies | Prompt 00 frontend spec. Prompt 03 session and health routes. Fixtures until other routes exist |
| Input contracts | [Frontend specification](FRONTEND_SPECIFICATION.md) and the session contract |
| Output contracts | A component set later prompts import |
| Files owned | `platform/web` shell, design system, and the chart spike |
| Agents | Implementer, using the vendored design skills as polish advice |
| Acceptance | The spike records chart frame time on a multi-year daily series in the browser. Attribution for the chart library is visible. There is no Tauri or Electron shell |
| Tests | Component checks for the status chips and the fixture banner. The 1100 px layout does not clip status text |
| Exit | Feature prompts can add routes without inventing colours |
| Must not modify | `nse/`, API handlers owned by Prompt 03 |
| Parallel | Prompt 03, and feature scaffolds that only consume the design system |

### Prompt 05 - Market overview and stock scanner UI

| Item | Content |
|---|---|
| Objective | Overview, scanner, and watchlists on real envelopes when the API has them, and on fixtures until then |
| Scope | Screens 5.1–5.3 |
| Deliverables | Those screens, wired to `GET /overview` and scan routes |
| Dependencies | Prompt 04 components. Prompt 03 routes for live data |
| Input contracts | API scan and overview objects |
| Output contracts | None for the engine |
| Files owned | `platform/web/src/features/overview`, `scanner`, `watchlists` |
| Agents | Implementer |
| Acceptance | Counts on screen match the envelope. A partial scan is labelled. Unavailable cards are not zero. No rank column |
| Tests | Fixture rendering and one test that a `DATA_INSUFFICIENT` count of zero is still a number while a missing scan is not |
| Exit | The owner can read a stored scan in the app |
| Must not modify | `pipeline.py`, design-system tokens except by agreement with Prompt 04 |
| Parallel | Prompt 06 and 08 on other feature directories |

### Prompt 06 - Native charting and stock analysis UI

| Item | Content |
|---|---|
| Objective | The analysis workstation |
| Scope | Screen 5.4, primitives for zones, drawings, and plan lines |
| Deliverables | Chart bound to the decision bundle, persisted drawings |
| Dependencies | Prompt 04 spike result. Prompt 03 bundle route for live data |
| Input contracts | Decision bundle and candle route |
| Output contracts | Drawing records as in the domain model |
| Files owned | `platform/web/src/features/analysis`, `platform/web/src/chart` |
| Agents | Implementer, independent reviewer for "drawings do not change status" |
| Acceptance | Candles stop at `as_of`. Unknown zones are not styled as fresh. A drawing save does not change `candidates.csv`. Library attribution is on the chart |
| Tests | Fixture bundle prefix test: a bundle that omits a later candle does not gain it in the UI model |
| Exit | A candidate can be inspected visually and the status still matches the file |
| Must not modify | Zone Engine, overlay, scanner |
| Parallel | Prompt 05 |

### Prompt 07 - Trade planning and portfolio management

| Item | Content |
|---|---|
| Objective | Plans, caps, and actual fills |
| Scope | Screens 5.5 and 5.6, fill storage |
| Deliverables | Plan versions, approval, order record, fill record, portfolio projection |
| Dependencies | Prompt 03 journal routes. Prompt 02 risk and store behaviour |
| Input contracts | Trade-plan object inside `research-pipeline/1`, risk statuses |
| Output contracts | Fill and position records |
| Files owned | `platform/web/src/features/plans`, `portfolio`, and the fill tables in `platform/db` |
| Agents | Implementer, quant researcher for the cap rules |
| Acceptance | Eleventh live fill in an IST month is refused. Eleventh open position is refused. Simulated rows are ignored. `selected_quantity` stays empty until the owner chooses. Blocked candidates cannot be journaled |
| Tests | Cap tests against the platform store, plus a check that the research store's existing journal tests still pass |
| Exit | The owner can record a Kite fill the software did not send |
| Must not modify | `risk.py` bands, broker libraries |
| Parallel | Prompt 08 after the fill schema is frozen |

### Prompt 08 - Trading journal and reporting

| Item | Content |
|---|---|
| Objective | Journal narrative and exports |
| Scope | Screens 5.7 and 5.13, CSV and HTML reports |
| Deliverables | Notes, search, report artefacts with manifest ids |
| Dependencies | Prompt 07 entries and fills |
| Input contracts | Journal, fill, and scan records |
| Output contracts | Report files |
| Files owned | `platform/web/src/features/journal`, `reports`, `platform/api` report handlers if not already in Prompt 03 |
| Agents | Implementer, reporting audit |
| Acceptance | Notes do not change the plan snapshot. Fixture exports contain the fixture label. CSV from an existing scan matches the engine CSV for the same fields |
| Tests | Report snapshot tests on fixtures |
| Exit | A journal period can be exported with provenance |
| Must not modify | Eligibility, fill cap logic except to call it |
| Parallel | Prompt 09 |

### Prompt 09 - Historical backtesting

| Item | Content |
|---|---|
| Objective | Run the existing backtest from the app and show the ledger |
| Scope | Screen 5.8 |
| Deliverables | Job wired to the existing backtest, manifest displayed |
| Dependencies | Prompt 02 backtest. Prompt 03 jobs |
| Input contracts | Execution model fields the engine already requires |
| Output contracts | Backtest run id and the engine's non-performance label |
| Files owned | `platform/web/src/features/backtest` |
| Agents | Quant researcher, implementer |
| Acceptance | A refused model surfaces the engine error. The screen does not compute a second expectancy. Fixture runs are bannered |
| Tests | One refused-cap test through the API and one fixture ledger render |
| Exit | The owner can launch a backtest the CLI can also launch |
| Must not modify | Fill simulation rules inside `backtest.py` unless Prompt 02 still owns that file and agrees |
| Parallel | Prompt 08 and 10's read-only views once a ledger exists |

### Prompt 10 - Quantitative validation

| Item | Content |
|---|---|
| Objective | Present statistics from stored ledgers with sample size and scope |
| Scope | Screen 5.9. Regime splits only with a written descriptive definition |
| Deliverables | Validation records pointing at manifests |
| Dependencies | Prompt 09 artefacts. TD-4 acknowledged for walk-forward files that lack manifests |
| Input contracts | Backtest output |
| Output contracts | `evidence_label` and `sample_size` on every figure |
| Files owned | `platform/web/src/features/analytics`, `platform/api` analytics read model |
| Agents | Quant researcher |
| Acceptance | No figure renders without a source manifest. Missing months are gaps. The screen does not say the strategy is profitable |
| Tests | A fixture ledger of a known handful of trades has hand-checked totals |
| Exit | Gate R4 has a place to put evidence. The gate itself may still be open |
| Must not modify | Trade selection in the backtest |
| Parallel | Prompt 11 on disjoint files once the ledger schema is stable |

### Prompt 11 - Robustness and stress testing

| Item | Content |
|---|---|
| Objective | Show the owner grid and stress the ledger without changing rules |
| Scope | Slippage and same-bar sensitivities the execution policy already lists. Additional stress is labelled experimental |
| Deliverables | A stress report tied to a validation id |
| Dependencies | Prompt 10 |
| Input contracts | `execution_policy.owner_grid` |
| Output contracts | A report that lists each assumption |
| Files owned | `platform/web/src/features/stress` |
| Agents | Quant researcher, contrarian reviewer |
| Acceptance | The grid runs the published scenarios. A scenario is not promoted into a new default rule |
| Tests | The three slippage rates and `STOP_FIRST` / `EXCLUDE` appear as named cases |
| Exit | A reader can see how sensitive a cited run is |
| Must not modify | Eligibility or the owner caps |
| Parallel | Prompt 12 |

### Prompt 12 - Shadow testing and paper trading

| Item | Content |
|---|---|
| Objective | A simulated book driven by post-close scans |
| Scope | Screen 5.10, paper-run storage, scheduler hook |
| Deliverables | Paper runs with private cap counters |
| Dependencies | Prompt 02 scan, Prompt 03 jobs, execution policy |
| Input contracts | Scan envelopes and the execution model |
| Output contracts | `book: SIMULATED` |
| Files owned | `platform/web/src/features/paper`, paper tables |
| Agents | Quant researcher, implementer |
| Acceptance | A simulated fill does not increase the live monthly count. No network order call exists. Assumptions are stored on the run |
| Tests | A regression that writes a paper fill and then reads the live cap unchanged |
| Exit | The owner can compare a paper run with a named backtest manifest |
| Must not modify | Live journal submission rules |
| Parallel | Prompt 13 |

### Prompt 13 - AI research assistant

| Item | Content |
|---|---|
| Objective | Cited commentary, off by default |
| Scope | Screen 5.11 and a provider adapter |
| Deliverables | Explain endpoint, payload preview, disabled state |
| Dependencies | Prompt 03. Stored scans from Prompt 02 when answers are about real runs |
| Input contracts | Object ids in the API |
| Output contracts | `commentary` plus citations. No status field |
| Files owned | `platform/web/src/features/assistant`, `platform/assistant` |
| Agents | Implementer, independent reviewer |
| Acceptance | With the setting off, the route returns `ASSISTANT_DISABLED` and every other screen still works. The adapter has no write method for gates, prices, or orders. Logs do not contain the provider credential |
| Tests | Disabled-path test and a citation test against a fixture scan |
| Exit | The owner can enable a provider later without an engine change |
| Must not modify | `qualification.py`, `scanner.py` |
| Parallel | Prompt 12 and 14's non-AI checks |

### Prompt 14 - Production integration and certification

| Item | Content |
|---|---|
| Objective | Prove the journeys on this Mac and record which release gates are met |
| Scope | End-to-end journeys, backup restore, dependency review, documentation of what is not validated |
| Deliverables | A certification note citing commands and results. A local browser build served by the loopback API |
| Dependencies | The prompts whose journeys are claimed. Unfinished prompts stay listed as open |
| Input contracts | All contracts above |
| Output contracts | Gate statuses R1–R5 |
| Files owned | `platform/tests/certification`, the certification note under `docs/product/` |
| Agents | Independent reviewer, quant researcher, contrarian reviewer, integration lead |
| Acceptance | The journeys in the frontend spec that are claimed were actually run. Unrun journeys are named. Protected hashes unchanged. No profitability sentence without an R4 record |
| Tests | `python3 -m nse.validation.run_all` and the platform suite. Both results pasted into the note |
| Exit | The owner can see a gate table that separates software completion from strategy evidence |
| Must not modify | Trading rules to make a journey pass |
| Parallel | Only read-only review |

## 6. Release gates

| Gate | Meaning | Evidence required | Explicitly insufficient |
|---|---|---|---|
| R1 Data ready | Official history, calendar, identity, and universe evidence for the claimed window | Readiness verdict in `nse/docs/REAL_DATA_READINESS.md` with B11-R done for a verified-universe claim, and CAL-2 either resolved or outside the claimed window | A green test suite. Engineering complete on D47–D56 |
| R2 Research ready | Engine, scanner, MTF, G0–G8, and trade-plan envelope integrated | Prompt 02 exit, including prefix tests and one real-data scan whose limitations match the data verdict | The web application looking finished |
| R3 Application ready | Shell, API, charts, persistence, and the daily journeys | Prompt 14 journey log for journeys 1–12 | Fixture screenshots |
| R4 Strategy validated | Historical, out-of-sample, and robustness evidence against the criteria Prompt 10 wrote down before looking at the result | Cited manifests, sample sizes, cost schedule, and the stress report | Any single in-sample run. Any fixture run |
| R5 Operationally ready | Paper book, recovery, backup restore, and certification | Prompt 12 and 14 records, including a killed scan that resumed as `INTERRUPTED` rather than complete | A week of the app staying open |

R4 is not a claim that the owner should trade the strategy. It is a claim that the
declared statistical exercise was run and reported. Profitability remains a separate
sentence and needs its own evidence.

Current gate reading on 2026-11-09, from the milestone file and the readiness note:
R1 open (`DATA_READY` not claimed). R2 open (pipeline code exists and is still an
active workstream). R3–R5 not started.

## 7. Prompt 00 document set

| File | Role |
|---|---|
| [PRODUCT_REQUIREMENTS.md](PRODUCT_REQUIREMENTS.md) | Vision, requirements, acceptance |
| [FRONTEND_SPECIFICATION.md](FRONTEND_SPECIFICATION.md) | Screens, journeys, visual system |
| [MASTER_PROMPT_ROADMAP.md](MASTER_PROMPT_ROADMAP.md) | This file |
| [DECISIONS_AND_OPEN_QUESTIONS.md](DECISIONS_AND_OPEN_QUESTIONS.md) | Recommendations and remaining decisions |
| [SYSTEM_ARCHITECTURE.md](../architecture/SYSTEM_ARCHITECTURE.md) | Layers and technology |
| [DOMAIN_MODEL.md](../architecture/DOMAIN_MODEL.md) | Entities |
| [API_CONTRACTS.md](../architecture/API_CONTRACTS.md) | Local API |
| [DATA_ARCHITECTURE.md](../architecture/DATA_ARCHITECTURE.md) | Providers and provenance |
| [AGENT_OWNERSHIP.md](../architecture/AGENT_OWNERSHIP.md) | Who may edit what |

Research architecture, the existing agent page, and milestone state stay where they are.
Pointers in those files lead here.
