# GTF Trading Intelligence Platform - product requirements

> Product Prompt 00. This document is the product definition. It does not authorise
> order placement, a broker connection, or a profitability claim.
>
> Research behaviour already implemented under `nse/` remains governed by the Rulebook,
> the decision register, and [the research architecture](../ARCHITECTURE.md). This page
> states what the desktop product must do. It does not restate or change a trading rule.

## 1. Product identity

| Item | Requirement |
|---|---|
| Name | GTF Trading Intelligence Platform |
| Category | Local-first NSE research and decision-support web application |
| Initial user | One person, the owner, on one Mac |
| Market | NSE cash equities |
| Style | Positional and swing trading |
| Methodology | GTF demand and supply, as already implemented for MIT |
| Timeframes | Monthly, Weekly, Daily |
| Execution | The owner types orders in Kite / Zerodha. The application records what the owner did |
| Deployment | Local Mac. Core research runs with no cloud service |

The finished product is one application: a browser UI, a local API, and the existing
deterministic research engine (D57). Scanner, chart, trade plan, backtest, and journal all
read the same engine outputs. The first deployment is loopback on this Mac. A later
cloud host is allowed by the architecture and is not part of this release.

## 2. What the product is

The owner can:

1. See whether the local dataset, calendar, and last scan are usable.
2. Scan the supported universe after the NSE session, on demand, or at a historical date.
3. Read why each symbol passed, failed, or needs manual review.
4. Open Monthly, Weekly, and Daily charts with engine zones and separate user drawings.
5. Build a trade plan from an existing candidate, including risk and size.
6. Record a manual Kite order and the actual fill.
7. Watch open positions against the approved position and monthly trade caps.
8. Keep a journal that separates the plan from the order and the fill.
9. Backtest and review statistics only with the dataset, execution model, and manifest attached.
10. Run a labelled paper book that cannot place a live order.
11. Ask an optional assistant to explain stored research, with citations.
12. Export reports that still carry methodology, dataset, and run identity.

## 3. What the product is not

- An order router, a broker client, or an unattended trading system.
- A second copy of the Zone Engine, the MTF overlay, or G0–G8.
- A source of win rates, expectancy, drawdown, or profit figures unless a real run produced them under [release gate R4](MASTER_PROMPT_ROADMAP.md).
- A multi-user, hosted, mobile, or social product.
- An intraday, WIT, futures, or options product. WIT stays blocked (M4b).

Extension points are allowed. Those products are not built in the initial release.

## 4. Users and responsibilities

There is one user role, Owner. The owner supplies capital and risk stage, approves a
trade plan, places the Kite order, and types the fill. The software calculates
eligibility, explains it, checks the approved limits, and stores the record.

The best candidate status the engine can emit is
`ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING`. The interface keeps the pending manual
checks visible. No screen renames that status to approved, validated, or buy.

## 5. Supported universe

The research universe already modelled in this repository is the Nifty 100 point-in-time
membership file. That is the initial supported universe.

- A scan of that file follows `Universe.members(as_of)`.
- An ad-hoc symbol list is allowed and carries `UNIVERSE_UNVERIFIED`.
- A full-universe label is allowed only when membership rows are verified. Until the
  human review in B11-R is filled, every such scan stays `UNIVERSE_UNVERIFIED`.
- Scanning every listed NSE equity is an extension. It waits for membership and identity
  evidence the repository does not have.

Cash equities only. Derivatives are rejected by the existing risk check.

## 6. Principles

These match the owner's product brief and the invariants already enforced in `nse/`.

| Id | Principle | Product consequence |
|---|---|---|
| P1 | Deterministic eligibility | Only `scanner.scan` / `scan_history` through `qualification.evaluate_symbol` assigns gates and status. The chart, the API, and the assistant display that result |
| P2 | Explainability | Every candidate, rejection, and manual review shows gate outcomes, reasons, and evidence references |
| P3 | Reproducibility | A scan or backtest keeps a run manifest: dataset hash, code revision, methodology version, configuration |
| P4 | Point-in-time | A historical `as_of` uses only information `known_at` that time. Later evidence is a new run |
| P5 | One methodology | Desktop features call the existing engine. They do not reimplement zones, freshness, or gates |
| P6 | Human control | `authorises_order` stays false. Recording a fill does not send an order |
| P7 | Local-first | Market data, research, and the journal work on this Mac with the network unused |
| P8 | Unknown stays unknown | Missing inputs stay `DATA_INSUFFICIENT`, `MANUAL`, `NOT_SUPPLIED`, or `UNAVAILABLE`. They are never shown as zero or as PASS |
| P9 | Traceable operations | Scans, plan approvals, order records, fills, backups, and configuration changes append an audit event |
| P10 | No unsupported performance claims | Software completion, strategy validation, and profitability are separate labels |

## 7. Functional requirements

Requirements are numbered by module. "Existing" means the capability already lives under
`nse/` and the product must call it. "New" means the desktop product adds it.

### Module 1 - Market data infrastructure

| Id | Requirement | Kind |
|---|---|---|
| FR-1.1 | Ingest official NSE CM bhavcopies through the existing loader and manifest. Legacy files through 2024-07-05, UDiFF from 2024-07-08 (ED-20) | Existing |
| FR-1.2 | Keep raw files immutable. Corrections are new files plus a new manifest row, or a quarantine record | Existing |
| FR-1.3 | Normalise accepted files into the existing candle model. Raw unadjusted OHLC stays canonical (D50) | Existing |
| FR-1.4 | Maintain instrument identity intervals, including ISIN continuity. Unresolved identity becomes `DATA_INSUFFICIENT` from that date | Existing |
| FR-1.5 | Maintain historical index membership as dated intervals. Overlaps are refused | Existing |
| FR-1.6 | Store corporate-action events separately from prices. A price-scale event inside scanned history makes G0 `MANUAL` | Existing |
| FR-1.7 | Use the verified trading calendar, including special sessions. An `UNRESOLVED` date is not inferred | Existing |
| FR-1.8 | Detect missing sessions, duplicate dates, inconsistent OHLC, and conflicting source values. Conflicts remain conflicts | Existing, extended in the platform for a second provider |
| FR-1.9 | Identify every dataset by the hash the research tools already compute, plus source and validation history | Existing |
| FR-1.10 | Accept an adapter for an owner-approved provider. The adapter writes files into an inbox. It does not become the research price | New |
| FR-1.11 | Show data readiness with the same separation the readiness table uses: engineering, data, and research validation | Existing |

### Module 2 - Market overview

| Id | Requirement |
|---|---|
| FR-2.1 | Show the last accepted session, the calendar classification of today, and whether a scheduled scan is due, running, partial, or complete |
| FR-2.2 | Show index levels only when a verified series exists. Otherwise show `UNAVAILABLE` |
| FR-2.3 | Sector performance stays `UNAVAILABLE` while sector membership is unevaluated (D6) |
| FR-2.4 | Breadth, if shown, is a labelled count over a named universe and a named session. It is not a gate |
| FR-2.5 | Show symbols scanned, candidate counts by status, and data-quality counts from the scan envelope. A missing scan is `UNAVAILABLE`, not zero |
| FR-2.6 | Show application health from the existing health check plus scheduler and database checks |
| FR-2.7 | Distinguish a partial scan from a full-universe scan in the first screenful |

### Module 3 - Stock scanner

| Id | Requirement |
|---|---|
| FR-3.1 | Run MIT scans through `pipeline.run` / the existing `research` command. WIT returns `BLOCKED` |
| FR-3.2 | Support three modes: scheduled post-close, manual, and historical replay. See [system architecture](../architecture/SYSTEM_ARCHITECTURE.md) |
| FR-3.3 | Show symbol status, candidate status, overlay freshness, and G0–G8 outcomes |
| FR-3.4 | Explain rejections and manual review from stored reasons. Do not invent a rank or a score. Row order follows the engine note: symbol, zone creation time, zone id. `pre_entry_score` is display-only |
| FR-3.5 | Filter by timeframe role, status, and data-quality code. Filters hide rows; they do not change status |
| FR-3.6 | Search by symbol, company name, and ISIN from the identity records |
| FR-3.7 | Watchlists are owner-made symbol lists. Membership of a watchlist is not universe membership and does not change eligibility |
| FR-3.8 | Saved scan configurations store paths, `as_of`, trade type, and risk inputs. They do not store a private override of a gate |
| FR-3.9 | Scan history lists manifests. Opening an old run shows that run's bytes |

### Module 4 - Stock analysis workstation

| Id | Requirement |
|---|---|
| FR-4.1 | Interactive candlestick charts for Monthly, Weekly, and Daily, from the same validated series the scanner used |
| FR-4.2 | Zoom, pan, and crosshair |
| FR-4.3 | Drawing tools: horizontal line, trend line, rectangle, text annotation. Drawings persist per symbol and timeframe |
| FR-4.4 | Engine demand zones, engine supply zones, MTF overlay state, and opposing supply are overlays from a decision bundle or scan. The chart does not recompute them |
| FR-4.5 | A chart opened from a stored scan renders that run's bundle. A new replay is a new run and does not replace the stored scan |
| FR-4.6 | Zone freshness and lifecycle use overlay status: fresh, tested, invalidated, unknown. Unknown is never drawn as fresh |
| FR-4.7 | G0–G8, data warnings, and evidence references sit beside the chart |
| FR-4.8 | User drawings and user annotations have their own records. They are excluded from every eligibility input |
| FR-4.9 | Trade-plan entry, stop, and target lines are a third overlay, labelled as a plan |

### Module 5 - Trade planning

| Id | Requirement |
|---|---|
| FR-5.1 | A plan starts from a stored candidate. The plan copies status, gates, levels, and manual checks |
| FR-5.2 | Entry and stop are chosen inside the ranges the engine already printed. The software does not pick a buffer (B9) |
| FR-5.3 | Show normal and exceptional stop ranges. An HTF stop is shown only when the engine supplied one; otherwise the field is `UNAVAILABLE` |
| FR-5.4 | Targets keep G7 provenance. A Pine-only opposing zone stays manual and is never an automatic target (D43) |
| FR-5.5 | Risk percentage, quantity, capital, and R:R come from `risk.py`. Invalid geometry produces no invented number |
| FR-5.6 | `selected_quantity` stays empty until the owner selects a buffer and a quantity that passes the risk plan |
| FR-5.7 | Portfolio checks for the monthly cap, open positions, and the one-order-per-zone rule are shown. `NOT_SUPPLIED` is not a pass |
| FR-5.8 | The owner marks the plan approved. Approval records a person. It does not change candidate status and does not send an order |
| FR-5.9 | Plans are versioned. A later scan that changes the candidate does not overwrite the approved version. The UI shows the mismatch |
| FR-5.10 | `BLOCKED`, `REJECTED`, and `DATA_INSUFFICIENT` candidates cannot be recorded as journal orders. That refusal already exists in the store |

### Module 6 - Portfolio and risk

| Id | Requirement |
|---|---|
| FR-6.1 | The owner enters available capital and a risk stage. No stage is assumed |
| FR-6.2 | Show planned capital, recorded orders, fills, and open positions as separate figures |
| FR-6.3 | Valuation uses the latest accepted daily close on or before the valuation date, and prints that date. With no close, valuation is `UNAVAILABLE` |
| FR-6.4 | Position risk and portfolio risk use the recorded stop and the filled quantity. A missing stop makes risk `UNAVAILABLE` |
| FR-6.5 | The live caps are the research journal's counts: 10 `TRIGGERED` trades per IST calendar month and 10 simultaneous open positions (D42). The platform does not keep a second live counter |
| FR-6.6 | A closed position releases a concurrent slot. It does not release the monthly slot |
| FR-6.7 | Sector concentration stays `UNAVAILABLE` until a sector source exists (D6) |
| FR-6.8 | Exits are recorded by the owner. The software does not submit the exit |
| FR-6.9 | Pending recorded orders expire after 10 verified NSE sessions and are revalidated against the pre-trade conditions before a fill is accepted (D42) |

### Module 7 - Trading journal

| Id | Requirement |
|---|---|
| FR-7.1 | A journal entry stores the plan snapshot: symbol, zone identity, gates, levels, checklist |
| FR-7.2 | An order record is the owner's statement that a Kite or GTT order was placed. One submission per entry (ED-3) |
| FR-7.3 | Fills are a new append-only record: time, price, quantity, side effects. They are distinct from the plan and from the order |
| FR-7.4 | The owner can record rationale, setup class, chart reference, rule adherence, and a mistake class |
| FR-7.5 | P&L and R-multiple are computed from fills and the recorded stop. Missing prices leave the figure blank |
| FR-7.6 | Search and filter by symbol, status, month, and setup class |
| FR-7.7 | Manual entry is allowed. Manual entry still passes the cap and zone-allowance checks |
| FR-7.8 | Paper and shadow activity is labelled `SIMULATED` and is stored so it cannot increment the live monthly count |

### Module 8 - Historical backtesting

| Id | Requirement |
|---|---|
| FR-8.1 | Signals come from `scan_history`. The backtest does not re-qualify zones |
| FR-8.2 | The run uses point-in-time membership and point-in-time inputs |
| FR-8.3 | Entry, stop, target, gap, same-bar policy, expiry, and the two caps use `execution_policy` and `backtest` |
| FR-8.4 | Configurations above the owner caps, or with no calendar, are refused (D45, ED-2) |
| FR-8.5 | Costs come from a dated schedule the owner supplies. No broker tariff is built in (B12) |
| FR-8.6 | The run writes a trade ledger, an equity curve, a manifest, and the existing realism-gap list |
| FR-8.7 | Output remains labelled so it is not performance evidence until gate R4 says so |

### Module 9 - Strategy analytics

| Id | Requirement |
|---|---|
| FR-9.1 | Win rate, expectancy, profit factor, maximum drawdown, average R, average holding period, consecutive losses, and monthly and yearly tables are computed only from a stored backtest ledger that has a manifest. The journal screen shows per-trade R and does not present the journal summary win rate as a strategy result |
| FR-9.2 | Each figure shows sample size, date range, universe label, cost assumption, and manifest id |
| FR-9.3 | Small samples carry a visible caution. The caution threshold is a display rule recorded in Prompt 10, not a trading rule |
| FR-9.4 | Out-of-sample and walk-forward views use the existing walk-forward command's results. Folds that wrote no manifest (TD-4) are labelled incomplete |
| FR-9.5 | Sensitivity uses the owner grid already defined in `execution_policy.owner_grid` |
| FR-9.6 | Market-regime splits appear only after Prompt 10 defines the regime from stored prices and labels it descriptive |
| FR-9.7 | The screen refuses to render these figures for a fixture run unless the fixture banner is visible |

### Module 10 - Shadow testing and paper trading

| Id | Requirement |
|---|---|
| FR-10.1 | After a new official session is ingested, the scheduler can run a scan and store the envelope |
| FR-10.2 | Simulated orders, fills, expiries, cancellations, and exits use the same execution policy as the backtest |
| FR-10.3 | Simulated positions are tracked in a paper book with its own cap counters. Paper code does not call the live journal and does not feed `merge_portfolio` |
| FR-10.4 | A paper run records the execution assumptions and can be compared with a named backtest manifest |
| FR-10.5 | No code path submits an order to a broker or to Kite |

### Module 11 - AI research assistant

| Id | Requirement |
|---|---|
| FR-11.1 | The assistant can explain a candidate, a rejection, an MTF conflict, a scan summary, a backtest, a data finding, and a journal period, using stored records |
| FR-11.2 | Answers cite `scan_key`, gate, and file or manifest ids. A claim with no stored source is labelled uncited |
| FR-11.3 | The assistant has no function that writes a gate, a status, a price, or an order |
| FR-11.4 | The rest of the application runs with the assistant disabled |
| FR-11.5 | A provider call happens only after the owner enables a provider and a payload policy. Secrets are not logged |

### Module 12 - System operations

| Id | Requirement |
|---|---|
| FR-12.1 | A local scheduler runs the post-close scan, respects the calendar, and recovers after sleep, quit, and restart |
| FR-12.2 | The owner can start, inspect, and cancel a manual scan. Cancel stops the job without marking it successful |
| FR-12.3 | Scan history, manifests, structured logs, and an audit trail are stored locally |
| FR-12.4 | Settings cover data locations, methodology version display, risk stage, capital, backup folder, and the assistant switch |
| FR-12.5 | Backup copies the research database, the application database, and the manifest. Restore is tested in Prompt 14 |
| FR-12.6 | Logs exclude OTPs, passwords, access tokens, and the session cookie |

### Module 13 - Reports and exports

| Id | Requirement |
|---|---|
| FR-13.1 | Daily, scan, candidate, stock, trade-plan, backtest, validation, portfolio, and journal reports render from stored records |
| FR-13.2 | CSV export reuses the existing report files where they already exist |
| FR-13.3 | PDF export is a rendered report with the manifest id in the footer. Until a PDF library is pinned, the browser print dialog is the export |
| FR-13.4 | Every report prints methodology version, dataset id, `as_of`, and code revision |
| FR-13.5 | Fixture reports carry the fixture banner in the body, not only in a tooltip |

## 8. Non-functional requirements

Targets below are proposals. None of them has been measured for the browser application.
Prompt 3 and Prompt 6 replace the proposals with measurements. A missed proposal is a
planning fact, not permission to drop a safety check.

### Performance

| Id | Proposal | Status |
|---|---|---|
| NFR-P1 | A stored scan summary for the Nifty 100 MIT universe opens in the UI within 1 second on this Mac | Proposed |
| NFR-P2 | A single-symbol daily chart covering the accepted history becomes interactive within 2 seconds after the series is cached | Proposed |
| NFR-P3 | Pan and zoom of that chart stay responsive. The Prompt 6 spike records frame time | Proposed |
| NFR-P4 | Read-only API responses for a stored artefact return within 500 ms at the 95th percentile, measured locally | Proposed |
| NFR-P5 | A full-universe scan's duration is dominated today by parsing archives (TD-17). No duration target is set until a parse cache is measured. The scheduler must show running progress rather than a guessed ETA | Measured constraint, no target |
| NFR-P6 | The UI holds one symbol's candles in memory. It does not load every archive into the window. The engine already avoids holding every row at once (ED-41) | Required |

### Reliability

| Id | Requirement |
|---|---|
| NFR-R1 | A scan that stops because the app quit, the Mac slept, or the process died is `INTERRUPTED`, then retryable. It is never `SUCCEEDED_COMPLETE` |
| NFR-R2 | Re-running the same idempotency key against unchanged inputs returns the existing manifest |
| NFR-R3 | An interrupted download stays in the inbox or quarantine. It is not ingested as accepted |
| NFR-R4 | Research rows that are already written are append-only. A failed later step does not delete them |
| NFR-R5 | Backup and restore are rehearsed on a copy before Prompt 14 exits |

### Security

| Id | Requirement |
|---|---|
| NFR-S1 | The API listens on `127.0.0.1` only. A session cookie is required. The cookie is HttpOnly and is not stored in localStorage, a URL, or frontend source |
| NFR-S2 | The React UI calls the API on that origin with the session cookie and `X-GTF-Request`. Another origin is refused |
| NFR-S3 | Secrets live outside git. `.env.example` continues to document that no credential is required for the engine |
| NFR-S4 | Dependencies of `platform/` are pinned and reviewed before Prompt 14. The root project dependencies stay empty |
| NFR-S5 | `nse/` continues to satisfy the existing ban on network and broker imports |

### Maintainability

| Id | Requirement |
|---|---|
| NFR-M1 | Module boundaries in [system architecture](../architecture/SYSTEM_ARCHITECTURE.md) are the ownership map |
| NFR-M2 | Rules A1–A10 keep covering `nse/`. Platform code is not a reason to weaken them |
| NFR-M3 | Engine tests stay in `tests/` and `run_all`. Platform tests live under `platform/` so an unassigned `tests/test_*.py` module is not created by accident |
| NFR-M4 | Public API fields are additive. Renaming an engine field is a contract change, not a UI convenience |

### Observability

| Id | Requirement |
|---|---|
| NFR-O1 | Logs are structured, include `run_id` or `job_id`, and contain no secrets |
| NFR-O2 | The overview shows scan status, data-source health, and the last error |
| NFR-O3 | Every research run keeps `run_manifest.json` |
| NFR-O4 | Audit events cover settings changes, plan approval, order recording, fills, and restores |

### Privacy

| Id | Requirement |
|---|---|
| NFR-V1 | Core scanning, charting, journaling, and backtesting send nothing off the machine |
| NFR-V2 | Official file download, when enabled, requests only the public URL already used for bhavcopies |
| NFR-V3 | Assistant requests are off until the owner enables them, and the payload preview lists the fields that would leave the machine |

## 9. Out of scope for the initial product

Intraday strategies, WIT, futures and options, automated order execution, broker API
integration, multi-user accounts, subscriptions, social or copy trading, a mobile
application, other exchanges, and unrelated strategies.

Also deferred inside an otherwise in-scope module:

- Live tick valuation.
- A sector model (D6).
- Treating any third-party series as the research price, until a named provider is approved.
- Sealed distribution outside this Mac.

## 10. Product acceptance criteria

The product is fit for daily use only when release gates R1–R5 in
[the roadmap](MASTER_PROMPT_ROADMAP.md) are met. In particular:

1. A scheduled or manual MIT scan of the supported universe produces a manifest and the existing report set.
2. The owner can open a symbol, see zones at an `as_of`, and see the same status as `candidates.csv`.
3. A trade plan cannot authorise an order. A recorded fill is something the owner typed.
4. The monthly cap and the open-position cap both refuse an eleventh actual trade or position.
5. A historical replay omits later candles and later findings.
6. Sample data is visibly labelled and cannot be exported as an NSE result.
7. Disabling the network and the assistant still allows a scan of files already on disk.

Prompt 00 itself is accepted when the blueprint documents listed in the roadmap exist,
`python3 -m nse.validation.docs_health` passes, and no file under `nse/` was edited for
this prompt.
