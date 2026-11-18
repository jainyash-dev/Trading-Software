# Prioritised implementation roadmap

This is the order of remaining work. It is not permission to start it in this session. No dates are estimated. The critical path is the sequence in section 2.

Priority:

- **P0** - without this, a research result or a stored trade decision cannot be trusted.
- **P1** - required for the owner to finish the initial workflow in the application.
- **P2** - the product becomes calmer and more repeatable after P1 works.
- **P3** - later expansion.

## 1. Tasks

| Task ID | Capability ID | Task | Priority | User value | Dependencies | Acceptance criteria | Risk |
|---|---|---|---|---|---|---|---|
| T-001 | SD-001, SD-002, DS-008 | Owner reviews `nse/data/universe/nifty100_review.csv` and records a decision per row | P0 | A scan can be described as the index only after this | Current file hashes | Verified rows match the README gate. Unreviewed rows still force `UNIVERSE_UNVERIFIED`. No agent writes `ACCEPTED` | A bulk accept without reading the packet |
| T-002 | MI-003, DS-007 | Owner classifies the four Dhanteras dates or leaves them unresolved and excludes them from any window that claims `eod_ready` | P0 | Higher-timeframe history is either real or visibly cut | The four circulars already on disk | `eod_ready` is true only for a window that does not contain an unresolved date. The scanner still refuses to guess | Marking the dates `NORMAL` because a bhavcopy exists |
| T-003 | DS-006, GTF-011 | Treat empty corporate-action responses as not covered, and re-run any scan the UI will show | P0 | G0 does not pass on an unknown price scale | Coverage file | A symbol absent from `coverage.csv` is G0 `MANUAL`. A displayed envelope is newer than ED-46 | Reusing the stored ETERNAL `PASS` described in the blockers |
| T-004 | DS-005, SD-003 | Leave BAJFINANCE, GRASIM, and YESBANK split until ED-37 evidence exists | P0 | A renamed identity is not a silent join | Official price-scale evidence | Those symbols stay `DATA_INSUFFICIENT` across the break | Joining them to make a chart look continuous |
| T-005 | GTF-001, GTF-009, GTF-010 | Record a small TradingView reference set and run the existing comparison tool | P0 | Zones and the SMA clock can be checked against a chart the owner already uses | Owner exports | Mismatches stay mismatches. Synthetic tests are not cited as the comparison | Tuning a rule to force a match |
| T-006 | PR-004 | Add a two-connection test for the 11th `TRIGGERED` | P0 | The monthly cap holds when two writers race | Current `BEGIN IMMEDIATE` path | One commit succeeds and one raises `JournalRefused`. The test uses two connections | Weakening the assertion to green |
| T-007 | MI-001, MI-013, SD-014, UX-002 | Show completeness, universe limitation, ED-44 cut, and job state on the overview. A missing status stays unavailable | P0 | The first screen cannot turn unknown into zero or into a full scan | Stored envelope | Overview test: missing count is not 0. A fixture scan is excluded until requested | Printing a friendlier label that hides `UNIVERSE_UNVERIFIED` |
| T-008 | UX-005, OI-003, OI-004, UX-006 | Stock Analysis reads `GET /api/v1/candles` and the stored bundle. Zones use overlay status. Drawings use the drawings API and never enter `inputs.load` | P1 | The owner can see the stock the scanner returned | T-007 so the scan header is honest. A `scan_key` | The chart has no hardcoded `PASS`. A candle after `as_of` is absent. User drawings round-trip. Engine zones are not draggable | Recomputing gates in the browser |
| T-009 | TP-001 through TP-012, UX-007 | Plan screen copies a stored candidate, shows ranges, leaves quantity empty until the owner picks a buffer, and checks caps through `portfolio_at` | P1 | A plan that matches the engine | T-008 for context. Research DB path | `BLOCKED`, `REJECTED`, and `DATA_INSUFFICIENT` cannot be saved. `authorises_order` stays false. Approval stores a person and does not change the candidate status | A second quantity formula in TypeScript |
| T-010 | EX-001, EX-003, EX-009, EX-012, TJ-001 through TJ-004, UX-008, PR-011 | Journal screen calls `journal_add`, `journal_order_submitted`, and `journal_event` | P1 | The Kite order and the fill are recorded without sending them | T-009 | The 11th trigger is refused with the journal's message. Platform tables gain no monthly counter | A platform `fills` table that counts trades |
| T-011 | PR-001, PR-002, PR-007, UX-009, UX-012 | Portfolio reads `portfolio_at`. Valuation is the last accepted close and the session date, or `UNAVAILABLE`. Capital and stage are settings | P1 | The book and the caps are visible | T-010 | Sector stays unavailable. No tick feed | Valuing from a quote that then becomes the research price |
| T-012 | QR-010, QR-011, UX-011 | Store the manifest id on the platform scan. Export the existing CSV for that id | P1 | A scan can be cited | T-007 | The file bytes match the CLI report for the same run | Building a second report writer |
| T-013 | EX-013 | Refuse a journal fill when the recorded order is past 10 verified sessions unless it was revalidated | P1 | A stale GTT is not recorded as a fresh plan | T-010, calendar | The backtest rule and the journal rule match. The owner can still record `EXPIRED` | Auto-cancelling a live Kite order. The app must not talk to Kite |
| T-014 | SD-004, SD-009 | Search uses identity records. Saved configs restore `as_of` and risk inputs and still cannot override a gate | P2 | Repeat a scan | T-007 | A secret-like key is still rejected. An unverified symbol is not marked verified | Treating the names CSV as the historical master |
| T-015 | SD-006, DS-015 | One scheduler flag. It does not download | P2 | An unattended post-close scan of a file that is already on disk | T-007 | A holiday does not run. A second tick reuses the job | Enabling `PUBLIC_NSE_DOWNLOAD` by default |
| T-016 | QR-004, QR-006, QR-007, QR-008, UX-010 | Backtest screen runs only with a manifest, a calendar, a cost schedule, and the not-performance label. Walk-forward writes a manifest | P2 | The owner can see a study without mistaking it for proof | T-001, T-002, B12, TD-4 | Fixture runs show the fixture banner. Sample size is visible. R4 stays a separate gate | A win-rate tile with no sample |
| T-017 | DS-018 | Backup both databases and the manifest. Restore onto a copy | P2 | The journal can be recovered | T-010 | A restore test uses a temporary directory. The live files are not overwritten by the test | A backup command that deletes the source |
| T-018 | AI-001 | The symbol view calls `explain` on the stored envelope | P2 | A plain-language reading of the gates | T-008 | The explainer cannot change a status. Missing items stay `NOT_IN_SCAN` | Sending the envelope to a model |
| T-019 | EX-007, EX-008 | Position monitor and session alerts | P3 | Watch an open trade during the day | OQ-1, T-011 | The quote is labelled and is not written into the research price. No new scan of the universe runs intraday | Building WIT under another name |
| T-020 | QR-014, TJ-012 | Paper book with its own counters | P3 | Practice without using the monthly cap | T-010, T-016 | Paper code cannot call `journal_event` for a live entry | Sharing `journal_orders` |
| T-021 | AI-002, AI-006 | Assistant, only after OQ-2 | P3 | Questions over stored records | T-018, OQ-2 | No write tool. Secrets are not logged. The app still starts with the provider unset | A tool that sets a gate |
| T-022 | GTF-017 | WIT | P3 | Intraday weekly trades | B6, B15, M4b | Remains blocked until those exist | Enabling the untested WIT branch |
| T-023 | TD-17 | Optional parse cache | P3 | Faster scans | A measured full-archive scan | Cache key is archive hash plus loader version. Output matches the uncached parse | A warehouse that becomes the price |

## 2. Critical path

```
T-001 universe review ──┐
T-002 calendar ruling ──┼── T-007 honest scan header ── T-008 chart ── T-009 plan ── T-010 journal ── T-011 portfolio
T-003 coverage re-run ──┤                                                              │
T-004 identity splits ──┘                                                              └── T-013 expiry rule
T-005 external samples (parallel, does not unblock the UI)
T-006 cap test (parallel, before T-010 is used with real money records)
T-012 manifest id (with T-007)
T-016 backtest UI only after T-001, T-002, and a cost file
T-019, T-020, T-021, T-022 after the live journal exists
```

T-001 and T-002 are owner work. Engineering can build T-007 through T-011 on uncertified data if every screen keeps the limitations. It must not flip `data_ready` to true.

## 3. Phases

### Phase A - Trust the inputs

**Objectives:** R1 stays honest. No certified claim.

**Tasks:** T-001, T-002, T-003, T-004, T-005, T-006, T-007.

**Exit:** A scan the UI can open states universe status, calendar cut, coverage gaps, and identity splits. `data_ready` is still false unless B11-R and CAL-2 are actually closed. The two-connection cap test exists.

**Risk:** Editing the readiness flag in the API to match a wish.

### Phase B - See the stock and write the decision

**Objectives:** Journeys B, C, and D in the application.

**Tasks:** T-008, T-009, T-010, T-011, T-012, T-013.

**Exit:** From a stored scan the owner can open candles and zones, save a plan, record a Kite submission and a fill, and see the journal caps move. No order leaves the machine. The browser is exercised, not only a stubbed test.

**Risk:** A second portfolio counter, or a chart that recomputes G0-G8.

### Phase C - Repeat it

**Objectives:** The daily loop is less manual, and a research number can be cited.

**Tasks:** T-014, T-015, T-016, T-017, T-018.

**Exit:** A saved config reruns. The scheduler does not download. A backtest on screen has a manifest, a cost line, and the not-performance label. A backup restore is rehearsed on a copy. R4 is still a separate decision and is not implied by the screen existing.

**Risk:** Showing expectancy from a fixture or from an unreviewed universe without the label.

### Phase D - Later

**Objectives:** None of this is required for the first reliable workflow.

**Tasks:** T-019, T-020, T-021, T-022, T-023.

**Exit:** Each item has its own owner decision. Until then the routes stay in `NOT_IMPLEMENTED`.

## 4. What not to do in parallel with Phase A

Do not start the assistant, the paper book, WIT, a broker client, or a sector model. Do not rewrite `qualification.py` to make a scan look actionable. Do not delete `trader-*` as cleanup.
