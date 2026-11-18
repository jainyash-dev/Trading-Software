# Product definition and scope

This file records the product this audit measured. It does not change a trading rule. Where two documents disagree, the disagreement is listed and left unresolved.

## 1. Intended product

Confirmed requirement, from [PRODUCT_REQUIREMENTS.md](../product/PRODUCT_REQUIREMENTS.md) and the brief that opened this audit.

| Item | Scope |
|---|---|
| User | One owner, on one Mac |
| Market | NSE cash equities |
| Style | Positional and swing. Monthly, Weekly, Daily. End-of-day research |
| Universe | Nifty 100 point-in-time membership. Any other list is allowed and must stay `UNIVERSE_UNVERIFIED` when the file says so |
| Methodology | GTF demand and supply, as already implemented for MIT. The engine is `nse/`. The UI must not reimplement it |
| Best status | `ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING`, with the manual checklist still visible |
| Execution | The owner types the order in Zerodha Kite. The application records the statement. `authorises_order` stays false |
| Position watch | Existing open positions may be monitored, and alerts may be issued, during market hours. That is not intraday opportunity scanning |
| WIT | Blocked until intraday data and a session design exist |
| Deployment | Local modular monolith. Core research works with no cloud service |
| AI | May explain stored evidence. It may not set eligibility, invent a price, or place an order |
| Out of the initial release | Intraday strategies, WIT, futures and options, broker APIs, automated orders, multi-user accounts, subscriptions, mobile, other exchanges, sector rules as a gate, tick valuation, sealed distribution |

The twelve questions the application is supposed to help the trader answer are in the audit brief (section 3). Journeys A-G in [04_USER_JOURNEY_ASSESSMENT.md](04_USER_JOURNEY_ASSESSMENT.md) are the practical form of those questions.

## 2. Authority used for this audit

Highest first, matching `CLAUDE.md` and [DECISIONS_AND_OPEN_QUESTIONS.md](../product/DECISIONS_AND_OPEN_QUESTIONS.md).

| Rank | Source | How this audit used it |
|---|---|---|
| 1 | Trading Rulebook PDF, cited through the Markdown companion in `nse/sources/` | Not modified. Section headings and [TRACEABILITY.md](../../nse/docs/TRACEABILITY.md) were read. The PDF was not re-transcribed |
| 2 | Owner decisions in [DECISION_LOG.md](../../nse/docs/DECISION_LOG.md) and the decision register | Treated as closed where the log says `USER_APPROVED` or `USER_STATED`. Not reopened |
| 3 | Pine Script in `nse/sources/` | Not modified. Used only where traceability already maps a silent rulebook point to Pine |
| 4 | Product requirements, architecture contracts, engineering decisions ED-1 onward | Used as the desktop product contract. An ED does not override the rulebook |
| 5 | Code and tests in the working tree, including untracked `platform/` | Used to decide what is implemented. A status document does not outrank the code |

[MILESTONE_STATUS.md](../MILESTONE_STATUS.md) says it is the only authority for milestone state. It is not the authority for whether untracked code exists. On 2026-11-10 the milestone text says product implementation has not started. The working tree contains `platform/`. Both facts are recorded. The milestone was not edited.

## 3. Confirmed decisions that bind the blueprint

These are not recommendations. Later work implements them.

| Topic | Decision | Where |
|---|---|---|
| Eligibility | Fresh, unbreached demand only, from the MTF overlay. Tested, invalidated, and unknown freshness do not qualify | Rulebook C5; architecture rule A10 |
| Status | `MANUAL_REVIEW`, `BLOCKED`, and `DATA_INSUFFICIENT` are not actionable | `nse/research/models.py` `derive_status` |
| Prices | Raw unadjusted OHLC is canonical. Unknown corporate-action coverage does not pass G0 | D50, ED-46 |
| Caps | 10 `TRIGGERED` trades per IST month and 10 open positions, independent. Closing a position releases only the open slot | D42, D45, D46 |
| One order per zone | A plan that was never submitted can release the zone. A submitted order does not | ED-3 |
| Buffers | The software prints tiers. It does not pick one | B9 |
| Risk stage | Above the stage maximum fails. Below the minimum, or a missing stage, is manual. No automatic promotion | P-RISK-1 |
| Pine-only supply | Can force G5 and G7 to manual. Never a target | D43, ED-4 |
| Calendar holes | Unresolved dates stay unresolved | D54, CAL-2 |
| Universe | A human accepts membership rows. An agent does not write `ACCEPTED` | D53, B11-R |
| WIT | Blocked | M4b |
| Desktop shape | Browser UI, loopback API, React and TypeScript, Lightweight Charts, two SQLite files | D57, AR-1 through AR-5 |
| Network | `nse/` does not download or place orders. A public download, if ever enabled, stays outside `nse/` and defaults off | D31, AR-6 |

## 4. Conflicts this audit did not resolve

| Topic | Documents | Classification | What the code does |
|---|---|---|---|
| How much EOD history is held | [VALIDATION_SCORECARD.md](../VALIDATION_SCORECARD.md) section 3 still says 62 of 1,233 sessions. [MILESTONE_STATUS.md](../MILESTONE_STATUS.md) section 5 and [PRODUCT_MASTER_STATUS.md](../../PRODUCT_MASTER_STATUS.md) section 4 say 2,462 of 2,462 trading days for 2016-2025 | Documentation inconsistency. The later milestone and the files on disk are the current description. The scorecard section was not rewritten | The manifest and `nse/data/eod/raw/` hold the later archive. This audit did not finish the data test group before the narrative was drafted; see the test table in the evidence register |
| UDiFF | [DATA_REQUIREMENTS.md](../../nse/docs/DATA_REQUIREMENTS.md) line 23 says the paragraphs below are the 2026-10-26 history. The next bold sentence still says UDiFF is not verified. The table above that sentence says the two schemas are verified | Documentation inconsistency inside one file. ED-20 and `nse/eod/nse_bhavcopy.py` are the implementation | Loader 2.1.0 selects legacy through 2024-07-05 and UDiFF from 2024-07-08 |
| Calendar reconciliation | [nse/data/calendar/README.md](../../nse/data/calendar/README.md) line 79 says 2016-2025 reconciles. Line 118 says reconciliation covers Q1 2022 only | Documentation inconsistency. Line 79 matches the milestone. Line 118 is a stale open item | `NseCalendar` still raises on the four Dhanteras dates |
| Corporate actions and Nifty 100 in the master status | [PRODUCT_MASTER_STATUS.md](../../PRODUCT_MASTER_STATUS.md) section 4 still says corporate actions are an interface with no records, and that Nifty 100 is a loader with no data. Section 5 and the milestone say 2,064 events and a transcribed universe awaiting review | Documentation inconsistency. Section 4 was only partly updated | `nse/data/corporate_actions/actions.csv` and `nse/data/universe/` exist |
| P-LOC-2 | Approved on 2026-11-08 in the master status. `nse/research/readiness.py` still says P-LOC-2 remains open. [DECISIONS_AND_OPEN_QUESTIONS.md](../product/DECISIONS_AND_OPEN_QUESTIONS.md) AS-4 says not to reopen it from that sentence | Confirmed decision, stale string in code | This audit did not re-test the curve rule. The string is debt, not an open trading choice |
| Product prompts 03-05 | Milestone section 6 says implementation has not started. `platform/` contains an API, a shell, and three screens | Documentation inconsistency. The code is uncommitted owner work that post-dates the milestone paragraph | See the implementation audit |
| Web limitations | [platform/web/docs/LIMITATIONS.md](../../platform/web/docs/LIMITATIONS.md) says scan, candle, plan, and journal routes are not implemented | Documentation inconsistency for scan and candle routes. Accurate for plan, journal, fill, backtest, and assistant routes | `POST /api/v1/scans` and `GET /api/v1/candles` exist. Plan and journal routes do not |
| EOD loader text | `readiness.py` still describes 1,233 official files for 2021-2025 | Stale capability string. The milestone describes 2016-2025 | Loader code is the 2.1.0 selector, not the sentence |
| Monthly-cap atomicity | AR-17 records a 2026-11-09 probe where two connections committed 11 triggers. `store.py` now takes `BEGIN IMMEDIATE` before the count. The product decision file still calls the non-atomic cap an engine defect | Implementation has moved. The written defect note was not updated. This audit did not re-run two connections | See `journal_event` in `nse/research/store.py` |
| B11-R period count | Blockers Part 10 says 171 unverified periods. Part 11 says 185 | The later part is the one to use. A file count in this audit agreed with 185 periods | `nifty100_universe.csv` |
| `scanner.scan` as the only caller of `evaluate_symbol` | Architecture text says qualification is called only by the scanner. The function is called by `scan_symbol`, which `scan` calls. Tests in `tests/_research.py` and `tests/test_research_explain.py` also call it | Implementation matches the production rule. Tests are an allowed direct call. `platform/` does not call it | `nse/research/scanner.py` |

No conflict in this table was closed by choosing the more convenient reading.

## 5. Initial release versus later expansion

Initial release, if the gates are met: one owner, NSE cash MIT, Nifty 100 or a labelled ad-hoc list, EOD scans, charts of stored zones, a plan, a manual fill record, the existing journal caps, reports that carry a manifest, and an assistant that stays off.

Not initial release, even though a screen or a module name already exists: WIT, intraday discovery, broker integration, automated orders, paper trading as a second book, strategy-validation claims, sector ranks, market regime, subscriptions, multi-user accounts, and a mobile app. Placeholder routes for some of those names are navigation, not a commitment to build them before the core workflow.

## 6. What this audit inspected

Inspected closely: `docs/product/`, `docs/architecture/`, milestone and scorecard files, blockers, readiness, traceability, engineering decisions, `nse/research/`, `nse/eod/`, `nse/calendar/`, `nse/zone-engine/`, `nse/mtf-freshness/`, `platform/gtf_platform/`, `platform/tests/`, `platform/web/src/`, and the data directories named in the data assessment.

Inspected at inventory level, not line by line: the legacy `trader-*` packages, vendored skills, the Rulebook PDF body, and every scenario JSON. The Rulebook Markdown headings and the traceability table were read. The Pine script was not re-audited as a strategy.

Not modified: `nse/sources/`, the Rulebook PDF, trading logic, and the repository layout.
