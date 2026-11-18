# Data readiness and blockers

Verdict: **PARTIALLY_READY**. `DATA_READY` is not claimed. Release gate R1 is open.

The files below were inspected in this audit. The `data`, `data_readiness`, and `acquisition` test groups passed on 2026-11-10 (127, 51, and 40 tests, 0 failures). `local_data` then returned PASS (2,478 archives loaded, calendar years 2016-2025, no unverified calendar source, zero months with an issues list). Twelve months record information only: an EOD file on an excluded session, or one of the four unresolved Dhanteras dates. `reference_comparison` returned PASS for 61 INFY rows against a Yahoo screenshot reference and 0 mismatches. The checker’s own note says that match is not independent validation. A new download was not started.

## What is on disk

| Set | Location | What this audit accepts as the current description |
|---|---|---|
| EOD archive | `nse/data/eod/raw/`, `nse/data/eod/manifest.csv` | Cash-market bhavcopies for 2016-01-01 through 2025-12-31. Milestone and the file inspection: 2,462 trading days have a file, legacy through 2024-07-05, UDiFF from 2024-07-08. This is the whole cash market, not a Nifty 100 extract |
| Inbox | `nse/data/eod/inbox/` | A backfill copy. It is not the archive to scan. It does not contain every raw file |
| Quarantine | `nse/data/eod/quarantine/` | Incomplete downloads and the first refusal of two odd legacy layouts later accepted under loader 2.1.0 |
| Evidence samples | `nse/data/eod/evidence/` | Format samples. Not the research dataset |
| Calendar | `nse/data/calendar/` | 2016-2025. 4 `UNRESOLVED` Dhanteras rows. 40 circulars recorded in `sources.csv` |
| Corporate actions | `nse/data/corporate_actions/` | `actions.csv` has 2,064 events. `coverage.csv` has 145 symbols. 46 collected symbols returned an empty body and are not coverage |
| Universe | `nse/data/universe/` | Baseline of 100 names at 2020-12-31. 185 converted periods, all with an empty source hash and review status not accepted. `nifty100_review.csv` decisions are blank |
| Identity | `instrument_records.csv` | 219 rows. 27 evidenced ISIN changes. BAJFINANCE, GRASIM, and YESBANK are not joined |
| Reference OHLC | `nse/data/reference/INFY/` | 61 Yahoo daily rows for Q1 2022. The file says the adjustment is unknown. A Yahoo match is not independent validation |
| TradingView | `nse/data/tradingview/` | Not present |
| Intraday | `nse/data/intraday/` | Not present |

`nse/research/eod_coverage.py` sets `data_ready.ready` to false even when the file check is clean, because the universe review and identity evidence are outside that report. `eod_ready` is false while the four unresolved dates sit in the window.

## Certification

| Gate in the milestone | State on 2026-11-10 |
|---|---|
| A. Raw EOD 2016-2025 | Files and the loader exist. Not a research certification by itself |
| B. Calendar | Resolved dates classify. CAL-2 is contained, not closed |
| C. Universe | Not certified. B11-R |
| D. Identity | Fail-closed, with three unevidenced ISIN changes |
| E. Corporate actions | Partial. Empty responses are not coverage |
| F. Point-in-time quality | G0 is manual without verified coverage (ED-46). A scan stored before that fix must not be reused as current |
| G. Reproducibility | Scan manifests can fingerprint instruments and coverage. Walk-forward does not write a manifest (TD-4) |

No scan in this tree is a certified full-universe research result. `pipeline.py` withholds `full_universe` while `UNIVERSE_UNVERIFIED` is set. `scanner.py` adds `TRADINGVIEW_PARITY_UNVERIFIED` and `NOT_EXTERNALLY_VALIDATED`.

## How a missing fact changes a result

| Gap | Effect on a scan |
|---|---|
| Blank universe review | `UNIVERSE_UNVERIFIED` on every scan of this file. A backtest adds `SURVIVORSHIP_UNCONTROLLED` |
| CAL-2 | History after the last unresolved date before `as_of` is all the scanner uses (ED-44). Monthly and higher context before 2019-10-28 is absent |
| Empty corporate-action response | That symbol is not in `coverage.csv`. G0 is `MANUAL` |
| Unevidenced ISIN change | `DATA_INSUFFICIENT` from the break. The history is not one series |
| No membership before 2020-12-31 | B11-P. A ten-year index study cannot start in 2016 |
| No TradingView export | Zones, SMA, and calendar holidays are not externally checked |
| No cost schedule | A backtest can run at zero cost. That number is not a Zerodha result |

## Blocker register

Severity is the effect on trusting a research result or finishing the initial workflow. Owner means the owner must supply a decision or a document. Engineering means code can move without that decision, and must not pretend the blocker is closed.

| Blocker ID | Kind | Description | Impact | Affected capabilities | Evidence required to close | Owner decision? |
|---|---|---|---|---|---|---|
| B11-R | Data | 271 review rows have a blank decision. 185 periods are unverified | No certified universe. Every such scan stays `UNIVERSE_UNVERIFIED` | SD-001, SD-002, MI-013, QR-002 | A human `ACCEPTED` or equivalent decision per the universe README, on the current file hashes | Yes |
| CAL-2 | Data | 2016-10-28, 2017-10-17, 2018-11-05, 2019-10-25 are `UNRESOLVED` | Full-window `eod_ready` is false. HTF context before the last of these dates is dropped | MI-003, DS-007, GTF-008, SD-007 | An NSE document that classifies the equity session, and an owner ruling. Guessing is not a close | Yes |
| B7 / R-10 | Data | 46 symbols returned an empty corporate-action body. 10 `UNPARSED_PRICE_EVENT` rows exist | G0 stays `MANUAL` where coverage is missing. Prices are not adjusted, by D50 | DS-006, GTF-011, MI-009 | A non-empty official response, or an owner decision that an empty body is verified absence | Yes for the empty-body policy. The collection itself is done |
| B11-I | Data | BAJFINANCE 2016-09-09, GRASIM 2016-10-07, YESBANK 2020-03-16 have no join | Those histories are `DATA_INSUFFICIENT` | DS-005, SD-003 | An official price-scale record on the first new-ISIN session, per ED-37 | Yes, the evidence |
| B11-P | Data | No point-in-time membership before 2020-12-31 | Survivorship-controlled history cannot start in 2016 | SD-002, DS-008, QR-002 | An earlier baseline or an owner-approved reverse step (TD-15) | Yes |
| B8 / B10 / B17 | Validation | No TradingView zone, SMA, or holiday export | External validation is none | GTF-001, GTF-009, GTF-010, MI-003 | Recorded references and `refcheck` | Yes, when the owner records them |
| B6 / B15 / M4b | Product decision and data | No intraday data and no WIT session design | WIT stays blocked | GTF-017, SD-018 | Out of the initial release | Yes, later |
| B9 | Product decision | The owner must pick a buffer. The software must not | Plans stay ranges | TP-002, TP-004 | The owner's selection at plan time | Yes, per trade |
| B12 | Data | No dated cost schedule | Backtests must not invent brokerage | QR-004, QR-006 | A dated schedule file | Yes |
| PROV-1 | Data | Download-log gaps for some archives. Three files are user-confirmed without an independent page | Provenance is the manifest hash, not a second witness | DS-009 | Optional. It does not by itself change a price | No |
| OQ-1 | External dependency | No approved quote provider | Market-hours monitoring cannot be built without a price that is not the research close | EX-007, EX-008 | A named source, rights, and a rule that it never replaces the bhavcopy | Yes |
| OQ-2 | Product decision | No assistant provider or payload policy | The assistant stays off | AI-002, AI-006 | A written allow-list of fields | Yes |
| TD-4 | Code | Walk-forward and sensitivity write no manifest | Those runs are weaker than `backtest` | QR-007, QR-008, QR-010 | A `run_manifest` sidecar | No |
| TD-16 | Code | Membership is matched by symbol. ISIN is stored and not compared | A rename inside a period fails closed later, or could be looked up under the old symbol | SD-002 | A comparison at `as_of` after B11-R | No |
| TD-17 | Code | Full archive parse on every real-data command | A universe scan is slow. Not a correctness block | SD-005, DS-001 | A measured cache, only after a timed scan | No |
| CAP-RACE | Validation | `BEGIN IMMEDIATE` is in `journal_event`. The two-connection probe was not repeated here | The 11th-trade failure mode may be fixed and is not re-proven | PR-004 | A test with two connections | No |
| APP-PLAN | Code | No plan, journal, fill, or backtest API | Journeys C-F do not exist in the app | TP-009, EX-001, UX-007, UX-008 | The routes in the roadmap | No |
| APP-CHART | Code | The chart does not call the candle API | Journey B does not exist | UX-005 | Bind the chart to the bundle | No |
| STALE-SCAN | Data | A scan stored before the G0 coverage fix can show an old `PASS` | The UI will display it | DS-006, OI-001 | Re-run before showing that envelope | No |
| DOC-DRIFT | Documentation | Scorecard, master status section 4, calendar README line 118, data-requirements UDiFF paragraph, web limitations, and the milestone "not started" sentence disagree with the tree | A reader can certify the wrong thing | MI-010 | Edit the stale sentences when the owner next updates those files. This audit did not | No |

Closed for files, and not reopened here: DATA-1, DATA-2, the UDiFF parser for the two known headers (B18 engineering), CAL-1 as a missing-year problem, and DQ-1 once the 12 excluded-session files are held. "Closed for files" is not `DATA_READY`.

## What would close R1

R1 needs the readiness note to say the claimed window is ready, B11-R done for a verified-universe claim, and CAL-2 either resolved or outside that window. A green test suite does not close it. The milestone already says this. This audit agrees.
