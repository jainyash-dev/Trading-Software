# Product gap register

A gap is a difference between the initial-release requirement and the working tree. IDs match [02_MASTER_CAPABILITY_MAP.md](02_MASTER_CAPABILITY_MAP.md). Statuses match [03_REPOSITORY_IMPLEMENTATION_AUDIT.md](03_REPOSITORY_IMPLEMENTATION_AUDIT.md).

Label: PRESERVE, VALIDATE, IMPROVE, PROPOSE, or REMOVE FROM SCOPE. Nothing in this file asks for a file to be deleted.

## Preserve

| ID | Why |
|---|---|
| GTF-001 through GTF-006, GTF-008 through GTF-015 | The MIT engine is the methodology. Tests in the zone, overlay, gate, adversarial, integration, and lookahead groups passed. Do not reimplement it in the browser |
| GTF-017, SD-018 | WIT stays blocked |
| EX-002, EX-014, AI-004, AI-005, PR-011 | No broker, no second cap, no eligibility override, the app runs with no model |
| DS-003, DS-004 | Raw prices and no silent fill |
| DS-016, DS-017 | Loopback session and log redaction |
| MI-002, MI-004, MI-006, PR-008 | Unavailable is the correct display until a real series exists |

## Validate before trusting

| ID | Gap | Risk if skipped |
|---|---|---|
| SD-001, SD-002, DS-008 | Universe file is unreviewed (B11-R) | A scan looks like the index and is not a certified membership |
| DS-007, MI-003 | CAL-2 cuts history (ED-44) | Higher-timeframe context is silently short |
| DS-005, DS-006 | Three ISIN splits and 46 symbols without coverage | A pass on stale data, or a joined history that should be `DATA_INSUFFICIENT` |
| GTF-001, GTF-009, GTF-010 | No TradingView reference (B8, B10, B17) | Zones and the SMA clock can be wrong on real charts and still pass synthetic tests |
| PR-004 | Two-connection cap not re-tested | An 11th `TRIGGERED` could commit if the lock is wrong |
| QR-002, QR-006 | No manifest-backed real-history run in this audit | A win rate would be a story |
| UX-003, UX-004 | Browser not used | The stubbed tests can pass while the live proxy fails |
| DS-002 | `local_data` passed for 2,478 archives. That is a hash and calendar reconciliation, not certification | Treating PASS as `DATA_READY` |

## Improve  -  required for the initial workflow

| ID | Gap | User cost |
|---|---|---|
| UX-005, OI-003, OI-004 | Chart uses fixture candles and fixture zones | The owner cannot analyse the stock the scanner just returned |
| UX-006 | Drawings API unused | Marks disappear, or a later shortcut writes them into eligibility |
| UX-007, TP-001 through TP-008, TP-011, TP-012 | Plan math is a library. The screen is a placeholder | The owner cannot size a trade in the app |
| TP-009, TP-010 | No approval and no version | A later scan can be confused with the plan that was acted on |
| UX-008, TJ-001 through TJ-004, EX-001, EX-003, EX-009, EX-012 | Journal is CLI-only | The Kite fill is not in the product |
| UX-009, PR-002, PR-003, PR-005, PR-006, PR-010, PR-012 | Portfolio page does not read `portfolio_at` | The 10/10 caps are invisible |
| EX-004, EX-013 | No planned-versus-actual view. Live expiry is not enforced outside the backtest | A stale order can be filled in the journal |
| MI-001, MI-010, MI-013, SD-014 | Overview hides job state and can show 0 for a missing status | Unknown becomes zero |
| SD-004, SD-009 | Search is the current names file. Saved configs drop risk and `as_of` | The owner cannot repeat the run they saved |
| SD-006, DS-015 | Scheduler flag is stored and not read | A setting that does nothing |
| QR-007, QR-008, QR-010 | No manifest on walk-forward or sensitivity | Those runs cannot be cited |
| QR-011, UX-011 | Reports are not exported from the app | The CLI files exist and the button refuses |
| UX-012, PR-001, TP-007 | Capital and stage are not durable settings. Pending scan body sits in `sessionStorage` | Risk inputs are easy to lose and easy to leave behind |
| DS-018 | No rehearsed backup of both databases | A disk failure loses the journal |
| AI-001 | Explain is CLI-only | The scanner already has deciding gates. The chart does not |
| DS-006 | Old envelopes can predate the G0 coverage rule | A displayed `PASS` can be stale |

## Not implemented, and required before the workflow is complete

| ID | Requirement |
|---|---|
| PR-007 | Mark to market from the last accepted close, with the date |
| TJ-009, TJ-010 | Post-trade review and search |
| UX-010 | Backtest and analytics screens that refuse a number without a manifest |

TJ-005 (screenshots) and TJ-006 (a mistake class) can wait for a note field. They are not the blocking gap.

## Remove from the initial release

| ID | Why |
|---|---|
| GTF-017, SD-018 as a feature to enable | WIT is blocked on purpose |
| EX-010 | No owner rule for partial exits |
| UX-018 | Multi-user, subscription, and mobile |
| MI-005, MI-007 | Relative strength and volatility are not defined |
| MI-008, QR-009 | Regime is not defined |
| OI-007 | Similar-setup search would imply a validated analogue. None exists |
| QR-014, TJ-012 | A paper book before the live journal UI adds a second source of truth |
| AI-002, AI-006, AI-007 | A model before the stored evidence is on screen |
| EX-007, EX-008 until OQ-1 | A live monitor without a quote will invent one or will stall |
| PR-009 as a live drawdown | The backtest drawdown is not the account |

## Proposals that are not requirements

| Proposal | Problem it solves | Why it can wait | Depends on | Initial release? |
|---|---|---|---|---|
| Parse cache for bhavcopies (TD-17, AR-8) | A full scan re-reads every archive | Correctness does not require it. Measure a scan first | Loader version and file hash | No |
| Dedicated missed-trade type (TJ-008) | The owner cannot review a setup they skipped | The scan history already lists the candidate. A second list needs a rule so it cannot consume the monthly cap | Journal | No |
| Sector breadth as a named count (MI-006) | The overview is empty of market context | D6 forbids a sector gate. A count is optional and easy to misread | A completed scan of a named universe | No |
| Browser print of a report (FR-13.3) | Sharing a scan | CSV already exists from the CLI | A stored envelope | After UX-011 |

## Defects that are smaller than a missing screen

| Item | Where | Why it matters |
|---|---|---|
| Missing status key becomes 0 | `platform/web/src/features/overview/model.ts` | P8 says unknown is not zero |
| OpenAPI says 200 for 201 and 202 | `platform/gtf_platform/openapi.json` | A client that trusts the document mishandles create |
| Cancel discards the idempotency header | `routes.py` cancel handler | A retry can do the wrong thing |
| Scheduler setting is unread | `app_setting` versus `GTF_SCHEDULER` | The owner can think the job is armed |
| `gtf-scan-pending` is never cleared | `platform/web/src/features/scanner/storage.ts` | Capital stays in the tab |
| Fixture G1 `PASS` | `platform/web/src/chart/fixtures.ts` | A specimen status on synthetic bars |
| Stale sentences | Scorecard section 3, calendar README line 118, `DATA_REQUIREMENTS.md` UDiFF paragraph, web `LIMITATIONS.md`, milestone "implementation has not started" | The next reader certifies the wrong system |

## Domain summary

| Domain | What the owner can do today | What is only partial | What they cannot do |
|---|---|---|---|
| Market intelligence | See a stored scan summary and a hardcoded not-ready flag | Calendar, datasets, findings | Trust an index, sector, or breadth number. None is shown, which is correct |
| Discovery | Submit a scan job and keep a watchlist, in code | Universe, search, schedule, history labelling | Treat the result as the certified Nifty 100 |
| Methodology | Run MIT gates in the engine | Confluence score | Use WIT. Use wick-to-wick geometry |
| Opportunity | Read stored gates on the scanner | Bundle, comparison | See them on a real chart |
| Planning | Compute ranges in the library | Caps inside a research run | Approve a plan in the app |
| Portfolio | Enforce caps in the journal | CLI `portfolio_at` | See the book |
| Execution | Refuse to send an order | CLI submission and fill | Record the Kite order in the app. Monitor the session |
| Journal | Store an entry from the CLI | Notes | Search, review, or attach a chart in the app |
| Research | Backtest and report from the CLI, with labels | Manifest coverage | Read a certified performance study |
| Assistant | Explain a scan file from the CLI | Citation rules for a model that does not exist | Ask a model |
| Data | Load the archive and fail closed | Certification | Call the dataset ready |
| Experience | Use three API screens and a shell | Chart spike, settings theme | Finish a trade workflow |
