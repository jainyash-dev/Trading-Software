# Master product capability map

Stable IDs for this audit. The same IDs are used in the implementation audit, the gap register, and the roadmap. A capability is included because the product requirements, the rulebook traceability table, or the audit brief's domain list names it. Rows marked **Recommendation** are not confirmed requirements.

Initial release means the current product scope in [01_PRODUCT_DEFINITION_AND_SCOPE.md](01_PRODUCT_DEFINITION_AND_SCOPE.md). "Degraded" means the initial release may ship the capability only with an explicit limitation, not as a certified result.

| Capability ID | Domain | Capability | User value | Required behaviour | Dependency | Initial release? |
|---|---|---|---|---|---|---|
| MI-001 | Market intelligence | Session and scan overview | See whether last session and last scan are usable | Show last accepted session, calendar class, and whether a scan is due, running, partial, or complete (FR-2.1) | Calendar, scan envelope, scheduler | Yes |
| MI-002 | Market intelligence | Index levels | See the index without a fake number | Show a level only from a verified series; otherwise `UNAVAILABLE` (FR-2.2) | A verified index series, which the repository does not have | Yes, degraded |
| MI-003 | Market intelligence | Trading calendar | Know if today is a normal session | Classify a date from the verified calendar. An `UNRESOLVED` date is not inferred (FR-1.7) | `nse/data/calendar/` | Yes |
| MI-004 | Market intelligence | Sector performance | See sector context | Stay `UNAVAILABLE` until a sector source exists (FR-2.3, D6) | Owner decision D6 | Yes, degraded |
| MI-005 | Market intelligence | Sector relative strength | Compare a stock with its sector | No approved sector model | D6 | No |
| MI-006 | Market intelligence | Market breadth | See how wide participation is | A labelled count over a named universe and session, or `UNAVAILABLE`. Not a gate (FR-2.4) | A completed scan of a named universe | Yes, degraded |
| MI-007 | Market intelligence | Volatility | See how wide ranges are | Not defined as a gate or an overview metric | A definition, if the owner wants one | No. Recommendation |
| MI-008 | Market intelligence | Market regime | Split research by environment | Only after a descriptive definition that is not a gate (FR-9.6) | Prompt 10 definition | No |
| MI-009 | Market intelligence | Corporate and economic events | Avoid trading through a known event | Corporate actions are stored apart from prices. No economic-event calendar is specified for the first release | Corporate-action file | Yes for corporate actions. No for a macro calendar |
| MI-010 | Market intelligence | Data readiness | Know whether research may be trusted | Separate engineering, data, and research validation. `DATA_READY` is a claim, not a green test (FR-1.11) | Readiness verdict | Yes |
| MI-011 | Market intelligence | Dataset identity | Repeat a run | Show the hash the research tools already compute (FR-1.9) | Manifest and run manifest | Yes |
| MI-012 | Market intelligence | Validation findings | See bad or missing data | Findings stay findings. They are not repaired into a pass (FR-1.8) | `marketdata` findings | Yes |
| MI-013 | Market intelligence | Scan completeness | Tell a partial run from a full one | Distinguish partial, ad-hoc, and full-universe on the first screen (FR-2.7) | Scan envelope `completeness` | Yes |
| MI-014 | Market intelligence | System health | See if the local app is up | Health of the API, both databases, and the scheduler (FR-2.6) | Platform health route | Yes |
| SD-001 | Stock discovery | Nifty 100 universe | Scan the supported list | Membership comes from the point-in-time file, not from today's constituents (FR-1.5) | B11-R review | Yes |
| SD-002 | Stock discovery | Point-in-time membership | Avoid survivorship bias | `Universe.members(as_of)`. Unverified rows keep `UNIVERSE_UNVERIFIED` | Human review | Yes |
| SD-003 | Stock discovery | Instrument master | Keep one identity per stock | ISIN intervals. An unresolved identity is `DATA_INSUFFICIENT` from that date (FR-1.4) | Identity records | Yes |
| SD-004 | Stock discovery | Symbol search | Find a stock by symbol, name, or ISIN | Search identity records (FR-3.6) | Instrument file exposed to the API | Yes |
| SD-005 | Stock discovery | Manual MIT scan | Run a scan on demand | `pipeline.run` for MIT. The UI does not score (FR-3.1) | Local EOD, calendar | Yes |
| SD-006 | Stock discovery | Scheduled post-close scan | Scan after the session without watching the screen | Scheduler after 15:45 IST, only if the file is already on disk (FR-3.2, FR-10.1) | Calendar, inbox file, `GTF_SCHEDULER` | Yes |
| SD-007 | Stock discovery | Historical scan | Ask what the engine would have said on a past date | `as_of` uses only information known then (FR-3.2, P4) | Point-in-time inputs | Yes |
| SD-008 | Stock discovery | Scan filters | Narrow the list | Filters hide rows. They do not change status or rank (FR-3.5) | Stored symbol rows | Yes |
| SD-009 | Stock discovery | Saved scan configurations | Repeat a setup | Store paths, `as_of`, trade type, and risk inputs. No private gate override (FR-3.8) | Platform database | Yes |
| SD-010 | Stock discovery | Watchlists | Keep an owner list | A watchlist is not universe membership and does not change eligibility (FR-3.7) | Platform database | Yes |
| SD-011 | Stock discovery | Candidate classification | See the engine status | Show symbol status, candidate status, overlay freshness, and G0-G8 (FR-3.3) | Stored envelope | Yes |
| SD-012 | Stock discovery | Failed-symbol explanation | See why a symbol produced nothing | Stored reasons. No invented rank (FR-3.4) | Envelope reasons | Yes |
| SD-013 | Stock discovery | Manual-review explanation | See why a human must look | Stored manual reasons and the checklist | Envelope | Yes |
| SD-014 | Stock discovery | Full versus partial labelling | Avoid reading a partial job as the market | Completeness and `full_universe` stay false while the universe is unverified | Pipeline envelope | Yes |
| SD-015 | Stock discovery | Duplicate scan prevention | Avoid two jobs for one request | Same idempotency key and same body return the existing job. A different body conflicts | Platform job store | Yes |
| SD-016 | Stock discovery | Scan history | Reopen an old run | Opening an old run shows that run's bytes (FR-3.9) | `scan_result` and research store | Yes |
| SD-017 | Stock discovery | Ad-hoc symbol list | Scan a named list | Allowed, with `UNIVERSE_UNVERIFIED` when membership is not verified | Universe loader | Yes |
| SD-018 | Stock discovery | WIT refusal | Avoid an intraday scan | `WIT-75` and `WIT-125` return `BLOCKED` before replay | M4b | Yes |
| GTF-001 | GTF methodology | Zone identification | See demand and supply bases | DBR/RBR and RBD/DBD, body-to-wick proximal and distal, maximum five bases | Completed candles | Yes |
| GTF-002 | GTF methodology | Zone lifecycle | Know if a zone is still fresh | Fresh, tested, invalidated, and unknown are distinct overlay states | MTF overlay | Yes |
| GTF-003 | GTF methodology | Tested-zone exclusion | Keep tested demand out of entries | A proximal touch after creation is tested and ineligible | Overlay and G1 | Yes |
| GTF-004 | GTF methodology | Invalidated-zone exclusion | Keep broken zones out | A close beyond the distal line invalidates permanently | Engine and overlay | Yes |
| GTF-005 | GTF methodology | Unknown freshness | Stop a guess from becoming a pass | Unknown, gap, or unverified session is not fresh and not `PASS` | Overlay | Yes |
| GTF-006 | GTF methodology | Core score | See the 7-point score | Freshness, strength, and base. Eligibility wants a fresh demand core of 7 with no disagreement flags | Zone engine | Yes |
| GTF-007 | GTF methodology | Confluence score | See the extra points | Display only. Sector, RSI, and stochastic stay unevaluated. No gate reads the score | `confluence.score14` | Yes, degraded |
| GTF-008 | GTF methodology | Top-down analysis | See yearly through daily context | One row per timeframe. Tested zones are not listed as the fresh zone | `topdown.tda` | Yes |
| GTF-009 | GTF methodology | MTF freshness overlay | Use one eligibility source | Candidates come only from `eligible_after_overlay` and `manual_review_after_overlay` | MTF snapshot | Yes |
| GTF-010 | GTF methodology | Timeframe roles | Apply MIT roles | Monthly location, Weekly trend, Daily execution | `models.ROLES` | Yes |
| GTF-011 | GTF methodology | Gates G0-G8 | Apply the pre-trade rules | One qualification function. Most restrictive outcome wins. G0 has no `FAIL` | `qualification.evaluate_symbol` | Yes |
| GTF-012 | GTF methodology | Status and checklist | Avoid an approved-trade label | Best status is `ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING` with the checklist attached | `derive_status` | Yes |
| GTF-013 | GTF methodology | Gate evidence | Trace a reason to a rule | Each gate stores outcome, reasons, and source references | Gate result objects | Yes |
| GTF-014 | GTF methodology | Pine-only zones | Keep a second detector from changing the trade | Pine-only zones are recorded, never eligible, and never targets. They can force G5/G7 manual | ED-4, D43 | Yes |
| GTF-015 | GTF methodology | Long only | Match the approved direction | Supply is context. Journal direction is `LONG` | D2 | Yes |
| GTF-016 | GTF methodology | Rulebook items not encoded | Know what the software does not decide | Wick-to-wick geometry, sector points, RSI/stochastic, and "coming from" analysis stay unimplemented or manual | Traceability rows 33-35 | Yes, as explicit gaps |
| GTF-017 | GTF methodology | WIT methodology | Intraday weekly-income trades | Blocked until session design and intraday data exist. Gate code for WIT is not reached by the scanner | M4b, B6, B15 | No |
| OI-001 | Opportunity intelligence | Stored candidate status | Read the decision later | Status on the stored envelope, not a live recompute | Scan store | Yes |
| OI-002 | Opportunity intelligence | Pass, fail, and manual reasons | Understand the gate | Render stored outcomes. Do not invent a reason | Envelope | Yes |
| OI-003 | Opportunity intelligence | Decision bundle | See the zone and the gates together | A bundle is the stored symbol result for a `scan_key`. A new replay is a new run (FR-4.5) | `decision_replay` or stored symbols | Yes |
| OI-004 | Opportunity intelligence | Higher-timeframe obstacles | See opposing supply | G5 evidence, including Pine-only manual cases | Structure | Yes |
| OI-005 | Opportunity intelligence | Curve and confluence context | See location and the display score | Curve from G3. Confluence is not a rank (AR-9) | Structure, confluence | Yes |
| OI-006 | Opportunity intelligence | Candidate comparison | Compare two symbols | Compare stored results. No composite rank | `explain` compare, if used | Yes, degraded |
| OI-007 | Opportunity intelligence | Similar historical setups | See whether this shape occurred before | Only if a validated, point-in-time match exists. Otherwise omit it | Not specified as an initial algorithm | No. Recommendation |
| OI-008 | Opportunity intelligence | Human review | Leave the checklist pending | The UI does not rename the best status to approved, validated, or buy | Status presentation | Yes |
| TP-001 | Trade planning | Plan from a stored candidate | Start from the engine, not from a typed guess | Copy status, gates, levels, and checks (FR-5.1) | Stored candidate | Yes |
| TP-002 | Trade planning | Entry and stop ranges | Choose inside the printed tiers | The software does not pick a buffer (FR-5.2, B9) | `levels.ranges` | Yes |
| TP-003 | Trade planning | Structural target | Keep a real opposing zone | No target is invented. Pine-only supply is not a target. Invalid geometry is manual (FR-5.4) | G7 | Yes |
| TP-004 | Trade planning | Risk/reward | See whether 2:1 is available | Minimum 2:1 on structural targets, across the printed buffers | `levels.rr_range` | Yes |
| TP-005 | Trade planning | Quantity | Size from risk per share | `floor(risk / (entry - stop))` inside the ranges. No number when geometry is invalid | `risk.py` | Yes |
| TP-006 | Trade planning | Risk stage | Stay inside the stage band | Learning 0.5-1%, Intermediate 1-1.5%, Professional 1.5-2%. Above max fails. Below min, or missing stage, is manual | P-RISK-1 | Yes |
| TP-007 | Trade planning | Capital | Size against stated capital | The owner enters capital. None is assumed (FR-6.1) | Owner input | Yes |
| TP-008 | Trade planning | Cap checks on the plan | See the 10/10 limits before acting | Monthly cap, open positions, and one-order-per-zone. `NOT_SUPPLIED` is not a pass (FR-5.7) | `portfolio_at` | Yes |
| TP-009 | Trade planning | Owner approval | Record a human decision | Approval records a person. It does not change candidate status and does not send an order (FR-5.8) | Audit event | Yes |
| TP-010 | Trade planning | Plan version | Keep the approved plan when a later scan changes | Later scans do not overwrite the approved version. The mismatch is shown (FR-5.9) | Plan store | Yes |
| TP-011 | Trade planning | One order per zone | Avoid a second order on the same zone | A submitted order holds the zone. A cancelled plan with no submission can release it (ED-3) | Journal | Yes |
| TP-012 | Trade planning | Planned versus actual | See the difference after the fill | Compare planned entry, stop, and target with recorded fills | Fill records | Yes |
| PR-001 | Portfolio and risk | Capital and stage settings | Remember the owner's risk posture | Stored capital and stage. No assumed stage | Settings | Yes |
| PR-002 | Portfolio and risk | Open positions | See the book | Positions come from the research journal, not from a second store (FR-6.5) | `portfolio_at` | Yes |
| PR-003 | Portfolio and risk | Ten open positions | Refuse an 11th concurrent position | Enforced when `TRIGGERED` commits. A close releases the slot | Journal | Yes |
| PR-004 | Portfolio and risk | Ten trades per month | Refuse an 11th trigger in the IST month | A close does not release the monthly allowance | Journal | Yes |
| PR-005 | Portfolio and risk | Independent caps | Understand the two limits | The two ceilings are separate | D42 | Yes |
| PR-006 | Portfolio and risk | Per-trade risk | See rupees at the stop | From the recorded stop and the filled quantity. A missing stop is `UNAVAILABLE` (FR-6.4) | Fills and stop | Yes |
| PR-007 | Portfolio and risk | Mark to market | See a value | Latest accepted daily close on or before the valuation date, with that date printed (FR-6.3, AR-13) | EOD close | Yes |
| PR-008 | Portfolio and risk | Sector concentration | See clustering | `UNAVAILABLE` until a sector source exists (FR-6.7) | D6 | Yes, degraded |
| PR-009 | Portfolio and risk | Portfolio drawdown | See loss from a peak | Not defined for the live book. Backtest drawdown is QR-006 and is not this figure | A book of fills | No until the journal has fills to measure. Recommendation for a live figure |
| PR-010 | Portfolio and risk | Historical portfolio state | Reconstruct the book at a time | `portfolio_at` is read-only and ignores later events | Journal | Yes |
| PR-011 | Portfolio and risk | One live counter | Avoid a second monthly count | Platform pending rows do not consume the cap. Paper must not write the live journal (AR-7, AR-17) | Journal as the only writer of `TRIGGERED` | Yes |
| PR-012 | Portfolio and risk | Risk-violation visibility | See a refused trade | A refusal is shown. It is not converted into a pass | Journal errors surfaced in the UI | Yes |
| EX-001 | Execution | Record a Kite submission | Separate "I placed it" from the plan | One append-only submission row per entry. Nothing is sent to a broker (FR-7.2) | `journal_orders` | Yes |
| EX-002 | Execution | No broker connection | Keep execution manual | No Kite client, no order route, download provider disabled | D10, D17 | Yes |
| EX-003 | Execution | Record a fill | Store the actual trade | Fill is a new record: time, price, quantity. Distinct from the plan and the submission (FR-7.3) | Journal `TRIGGERED` | Yes |
| EX-004 | Execution | Entry-price difference | See slippage against the plan | Show planned entry beside the recorded fill | Both records | Yes |
| EX-005 | Execution | Stop tracking | Keep the stop that was in force | Stop locks once the trade triggers | Journal | Yes |
| EX-006 | Execution | Target tracking | Know the planned target | Target stays the structural target from the plan | Journal levels | Yes |
| EX-007 | Execution | Open-position monitoring | Watch an existing position during the session | Status of open positions. This is not an intraday scan | A price newer than the last EOD close, which is not approved | Yes, and currently blocked on a price source |
| EX-008 | Execution | Market-hours alerts | Hear about a stop or target during the session | Alerts for an open position. Scan-to-scan diffs are a different feature | EX-007 | Yes, and currently blocked with EX-007 |
| EX-009 | Execution | Exit recording | Close the book | Owner records stop, target, or manual close. The software does not submit the exit (FR-6.8) | Journal events | Yes |
| EX-010 | Execution | Partial exits | Record a scale-out | No approved partial-exit rule is implemented | A product decision if the owner wants scale-outs | No until the owner defines it. Recommendation |
| EX-011 | Execution | Exit reason | Review why it closed | Stop, target, manual close, and zone invalidation are distinct | Journal kinds | Yes |
| EX-012 | Execution | Execution history | Read the order trail | Submission, fill, and exits in order | Journal | Yes |
| EX-013 | Execution | Pending expiry | Drop a stale order | Pending recorded orders expire after 10 verified sessions and are revalidated before a fill (FR-6.9, D42) | Calendar sessions | Yes |
| EX-014 | Execution | No automatic order | Make the boundary obvious | `authorises_order` is false. No buy or sell control | Pipeline constant | Yes |
| TJ-001 | Trading journal | Plan snapshot | Remember the setup | Symbol, zone, gates, levels, checklist (FR-7.1) | Journal entry | Yes |
| TJ-002 | Trading journal | Order record | Remember the Kite statement | EX-001 | Journal orders | Yes |
| TJ-003 | Trading journal | Entry record | Remember the fill | `TRIGGERED` with price | Journal events | Yes |
| TJ-004 | Trading journal | Exit record | Remember the close | Exit kinds with price | Journal events | Yes |
| TJ-005 | Trading journal | Screenshots and chart references | Attach the chart that was used | Owner-recorded reference. Not an eligibility input | A file or note field | Yes, degraded |
| TJ-006 | Trading journal | Rule adherence and mistakes | Review behaviour | Owner-entered class. The software does not invent a grade | Note fields | Yes |
| TJ-007 | Trading journal | Behavioural notes | Record process observations | Free text on the entry | Notes | Yes |
| TJ-008 | Trading journal | Rejected and missed opportunities | Learn from what was not taken | A record that is not a `TRIGGERED` trade and does not consume the monthly cap | A journal kind or a separate list | Yes. Recommendation for a dedicated missed-trade type; the requirement FR-7 does not yet define the schema |
| TJ-009 | Trading journal | Post-trade review | Compare the plan with the outcome | Review status stays `NOT_EVALUATED` until the owner writes it | Fills and notes | Yes |
| TJ-010 | Trading journal | Search and filter | Find a past trade | By symbol, status, month, and setup class (FR-7.6) | Journal query | Yes |
| TJ-011 | Trading journal | Audit history | See who changed a record | Append-only journal plus an audit event for approvals and fills (P9) | Audit table | Yes |
| TJ-012 | Trading journal | Paper separated from live | Keep practice trades out of the cap | `SIMULATED` records must not increment the live monthly count (FR-7.8, AR-7) | A separate book | No for a paper book. The separation rule is binding if a paper book is ever built |
| QR-001 | Quantitative research | Backtest from scan history | Test the rules that were actually used | Signals come from `scan_history`. The backtest does not re-qualify (FR-8.1) | Scanner | Yes |
| QR-002 | Quantitative research | Point-in-time inputs | Avoid lookahead | Membership, findings, and candles are cut at the window | Universe, calendar | Yes |
| QR-003 | Quantitative research | Execution assumptions | Know how a fill was simulated | Gap, same-bar, expiry, and caps come from `execution_policy` and the run config (FR-8.3) | Owner grid | Yes |
| QR-004 | Quantitative research | Transaction costs | Avoid an invented brokerage | A dated schedule the owner supplies. No Zerodha tariff in code (FR-8.5, B12) | Owner file | Yes |
| QR-005 | Quantitative research | Slippage | See assumed slippage | A required non-negative field. Zero is allowed and must be visible | Execution model | Yes |
| QR-006 | Quantitative research | Result metrics | Read win rate, expectancy, drawdown, and related figures | Computed only from a stored ledger that has a manifest. Always labelled so they are not performance evidence until R4 (FR-8.7, FR-9.1) | Manifest | Yes, degraded |
| QR-007 | Quantitative research | Walk-forward | See out-of-sample folds | Existing walk-forward command. Folds without a manifest are incomplete (FR-9.4, TD-4) | TD-4 | Yes, degraded |
| QR-008 | Quantitative research | Sensitivity | See whether the result depends on one assumption | `execution_policy.owner_grid` (FR-9.5) | Cost schedule | Yes |
| QR-009 | Quantitative research | Regime splits | See results by environment | Only after MI-008 exists | Prompt 10 | No |
| QR-010 | Quantitative research | Run manifest | Reproduce a run | Dataset hash, code revision, methodology, configuration (P3, ED-18) | `run_manifest.py` | Yes |
| QR-011 | Quantitative research | Research reports | Export the scan | Daily, candidate, and stock reports from stored records, with identity in the body (FR-13) | `reports.py`, `narrative.py` | Yes |
| QR-012 | Quantitative research | Small-sample caution | Avoid a story from a handful of trades | Below 30 closed trades the backtest sets `SMALL_SAMPLE`. The on-screen threshold is a display rule | Backtest metrics | Yes |
| QR-013 | Quantitative research | No profitability claim | Keep research separate from a promise | The software must not say the methodology works because a number was computed | R4 | Yes |
| QR-014 | Quantitative research | Paper or shadow book | Practise without touching the live cap | Separate counters. Same execution policy. No broker (FR-10) | Prompt 12 | No |
| AI-001 | AI assistant | Deterministic explanation | Read a stored decision in words | `explain` reads `scan.json` and cannot change a status | Stored scan | Yes |
| AI-002 | AI assistant | Model-written explanation | Ask a question about stored research | Citations to `scan_key`, gate, and manifest. Uncited claims are labelled (FR-11.1, FR-11.2) | OQ-2 | No until the owner enables a provider |
| AI-003 | AI assistant | Citation rule | See the source of a sentence | A claim with no stored source is uncited | Stored records | Yes, when AI-002 exists |
| AI-004 | AI assistant | No eligibility override | Keep the engine in charge | No function writes a gate, a status, a price, or an order (FR-11.3) | Process boundary | Yes |
| AI-005 | AI assistant | Assistant can be off | Use the app with no model | The rest of the application runs with the assistant disabled (FR-11.4) | None | Yes |
| AI-006 | AI assistant | Provider policy | Control what leaves the machine | A call happens only after the owner enables a provider and a payload policy. Secrets are not logged (FR-11.5) | OQ-2 | No until enabled |
| AI-007 | AI assistant | Journal and performance narration | Review a period in prose | Same citation rules as AI-002 | Journal and a manifest | No until AI-002 |
| AI-008 | AI assistant | Hallucination control | Stop invented prices and zones | The model is not a data source. Missing evidence stays missing | AI-003, AI-004 | Yes, as a constraint |
| DS-001 | Data and system | EOD ingestion | Load official files | Legacy through 2024-07-05, UDiFF from 2024-07-08, one source per date (FR-1.1, ED-20) | Loader | Yes |
| DS-002 | Data and system | 2016-2025 archive | Have a history to scan | Files on disk, matched to the manifest. Presence is not `DATA_READY` | D47, D55 | Yes |
| DS-003 | Data and system | Raw unadjusted prices | Keep the canonical price | `price_adjustment = NONE`. No silent adjustment (D50) | Corporate actions stored separately | Yes |
| DS-004 | Data and system | No silent repair | Trust gaps | Missing sessions stay missing. Conflicts stay conflicts | Findings | Yes |
| DS-005 | Data and system | Identity and ISIN history | Follow a stock across a change | Join only on a verified lineage. Otherwise `DATA_INSUFFICIENT` | B11-I | Yes |
| DS-006 | Data and system | Corporate actions | Know when the price scale changed | Events stored separately. Missing or unverified coverage is G0 `MANUAL`. Prices are not rewritten | B7, R-10 | Yes |
| DS-007 | Data and system | Calendar integrity | Know the session | 2016-2025 calendar. Four unresolved dates stay unresolved | CAL-2 | Yes |
| DS-008 | Data and system | Historical universe | Scan who was actually in the index | File from 2020-12-31 forward. No membership before that date | B11-P, B11-R | Yes, degraded before 2021 |
| DS-009 | Data and system | Dataset hash and provenance | Name the bytes that were used | Manifest SHA-256, acquisition state, run manifest fingerprints | Manifest | Yes |
| DS-010 | Data and system | Quarantine | Keep a bad file out of research | Unknown headers and incomplete downloads stay out of the accepted set | Acquisition | Yes |
| DS-011 | Data and system | Research database | Store scans and the journal | Append-only research SQLite. Platform does not migrate it | `nse/research/store.py` | Yes |
| DS-012 | Data and system | Platform database | Store jobs, watchlists, drawings, settings | Separate SQLite. No second journal | `platform/gtf_platform/db.py` | Yes |
| DS-013 | Data and system | Job runner | Run a scan off the request | States, heartbeat, idempotency, cancel | `jobs.py` | Yes |
| DS-014 | Data and system | Job recovery | Survive a crash | A dead `RUNNING` job becomes `INTERRUPTED`, never `SUCCEEDED_COMPLETE` (NFR-R1) | Startup interrupt | Yes |
| DS-015 | Data and system | Scheduler | Scan after the close | Respects the calendar. Does not download. Off unless enabled | `GTF_SCHEDULER` | Yes |
| DS-016 | Data and system | Loopback session | Keep the API on this Mac | Bind `127.0.0.1` or `::1`. HttpOnly cookie. Origin and marker checks (NFR-S1) | `security.py` | Yes |
| DS-017 | Data and system | Secret redaction | Keep tokens out of logs | Session cookie redacted. Scan-config keys that look like secrets are rejected (NFR-S3, FR-12.6) | `logsafe.py` | Yes |
| DS-018 | Data and system | Backup and restore | Recover the two databases | Copy research DB, platform DB, and manifest. Restore is rehearsed (FR-12.5) | Prompt 14 | Yes |
| UX-001 | Product experience | Application shell | Move around the product | Navigation, status language, empty and loading states | Prompt 04 | Yes |
| UX-002 | Product experience | Overview screen | Land on the truth of the last run | MI-001 through MI-014 rendered from the API, not from fixtures | Overview route | Yes |
| UX-003 | Product experience | Scanner screen | Run and read a scan | Submit, poll, cancel, history, symbol evidence | Scan routes | Yes |
| UX-004 | Product experience | Watchlist screen | Maintain lists | Create, rename, add from search, reorder | Watchlist routes | Yes |
| UX-005 | Product experience | Stock analysis chart | See Monthly, Weekly, and Daily | Same series the scanner used. Zoom, pan, crosshair. Engine zones from a bundle. The chart does not recompute gates (FR-4) | Candle route and bundle | Yes |
| UX-006 | Product experience | Drawings | Mark the chart | Line, trend, rectangle, text. Persisted per symbol and timeframe. Excluded from eligibility (FR-4.3, FR-4.8) | Drawings API | Yes |
| UX-007 | Product experience | Trade-plan screen | Build TP-001 through TP-012 | No buffer is pre-selected. Non-actionable statuses cannot be journalled | Plan API, which is not built | Yes |
| UX-008 | Product experience | Journal screen | Work the journal | TJ-001 through TJ-011 | Journal API, which is not built | Yes |
| UX-009 | Product experience | Portfolio screen | See PR-001 through PR-012 | Caps come from the research journal | Read-only journal view | Yes |
| UX-010 | Product experience | Backtest and analytics screens | Read QR results | Figures require a manifest. Fixture runs show the fixture banner (FR-9.7) | Backtest API | Yes, after a real run exists. The screen must not invent numbers before that |
| UX-011 | Product experience | Reports and export | Take a record away | CSV from existing report files. Browser print until a PDF library is pinned (FR-13) | Stored reports | Yes |
| UX-012 | Product experience | Settings | Set capital, stage, paths, backup, assistant switch | Settings do not override a gate (FR-12.4) | Settings API | Yes |
| UX-013 | Product experience | Empty, loading, and error states | See the difference between zero and unknown | Missing data is `UNAVAILABLE`, not zero (P8) | Design system | Yes |
| UX-014 | Product experience | Fixture labelling | Avoid mistaking a sample for NSE | `FIXTURE_NOT_MARKET_DATA` on the artefact and in the banner (AR-10) | Fixture flag | Yes |
| UX-015 | Product experience | Local installation | Run it on this Mac | One process, loopback, no Tauri or Electron | `platform/run_api.py`, Vite | Yes |
| UX-016 | Product experience | Accessibility | Use the interface with a keyboard and readable text | Not specified as a measured bar in Prompt 00 | A later pass | Yes, as a quality bar, not a separate product |
| UX-017 | Product experience | Updates, privacy, licensing | Know what the app is allowed to do | No sealed updater. Chart attribution required. No telemetry in the core path | AR-4 licence note | Yes for privacy and attribution. No for an updater |
| UX-018 | Product experience | Multi-user, subscription, mobile | Commercial expansion | Explicitly out of the initial release | A later product decision | No |

The map has 165 capabilities: MI 14, SD 18, GTF 17, OI 8, TP 12, PR 12, EX 14, TJ 12, QR 14, AI 8, DS 18, UX 18.
