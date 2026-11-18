# Real Market Data Readiness (council milestone, 2026-11-08; live status)

Where the platform stands on real NSE historical data, and the exact evidence still needed.

All data comes from official NSE sources:
- EOD files were downloaded only under the owner-approved D47 and D55 backfills (one request per second, official `nsearchives.nseindia.com` URLs), plus the earlier owner-supplied and Q1 2022 batches.
- Corporate actions were collected under D56.
- No scheduled fetch exists, and the default stays off (OQ-3).

Synthetic tests are not evidence for any item here. Reproduce the coverage numbers with:

```
python3 -m nse.research.cli eod-coverage --start 2016-01-01 --end 2025-12-31 --symbols INFY,RELIANCE --out nse/output/data_readiness/eod_coverage_2016_2025.json
```

## 0D. After owner decision D58 (2026-11-10)

The owner approved CAL-2 option A (D58). The four Dhanteras dates are `CONFIRMED` regular
equity sessions (09:15-15:30, NORMAL_SPECIAL). The Gold ETF/SGB-only extension is kept in
each row's note and builds no candle. The sections below describe the state before this
decision; where they say the four dates are UNRESOLVED or CAL-2 is open, this section
replaces them.

| Item | Now |
|---|---|
| Calendar | No UNRESOLVED row. 2,466 trading days in 2016-2025 (was 2,462) |
| EOD (`eod-coverage`, 2016-2025) | 2,466 accepted trading-day archives, including the four Dhanteras files (previously VALIDATED only). `eod_ready` true; `data_ready` false |
| ED-44 history cut | Not applied to any current scan. A real 2025-12-26 scan of INFY, RELIANCE and HDFCBANK replays from 2016-01-01 on all six timeframes |
| DATA_READY | **Not claimed.** Still open: B11-R (universe review), B11-P (no membership before 2020-12-31), the three unevidenced ISIN changes, and no external validation (B8, B10, B17) |

## 0C. PROMPT-01 certification (2026-11-09)

**Verdict: PARTIALLY_READY. DATA_READY is not claimed.**

| Scope | Certified? |
|---|---|
| Raw official NSE CM EQ end-of-day prices, 2016-01-01 to 2025-12-31, every NSE EQ symbol | **Yes (Gate A).** Raw, unadjusted |
| Calendar 2016-2025 | **Yes (Gate B)**, with four UNRESOLVED dates contained: a scan replays only history after 2019-10-28 (ED-44) |
| Point-in-time NIFTY 100 universe | **No (Gate C).** No human review is recorded; every period is UNIVERSE_UNVERIFIED |
| Instrument identity for historical members | **Yes, except BAJFINANCE, GRASIM and YESBANK (Gate D)**, which stay unresolved across their unevidenced ISIN changes |
| Corporate actions | **Partly (Gate E)**: 145 of 191 symbols covered; 46 official responses are empty |
| Data quality and point in time | **Partly (Gate F)**: one HIGH invariant gap, in Prompt-02-owned eligibility code (P01-H1) |
| Reproducibility | **Partly (Gate G)**: the scan manifest omits identity and CA-coverage inputs (P01-H2) |

Status kinds are kept apart:
- **Engineering:** done for Prompt 01's files.
- **Data:** the EOD files are complete.
- **Research validation:** none.

### C.1 Gates

| Gate | Result | Evidence |
|---|---|---|
| A. Raw EOD | **PASS** | All 2,480 raw files hash-match the manifest (independent audit). 2,462 of 2,462 calendar trading days have exactly one accepted official archive; 0 missing, 0 conflicting, 0 corrupt. 12 excluded-session files are accepted in role `EXCLUDED_SESSION_D33` only. 4 Dhanteras files are held, not accepted. Strict loader 2.1.0: 210 non-EQ rows isolated (ED-30); no EQ row fails. Provenance caveat: 62 archives predate the download log. 59 are the Q1 2022 script batch, whose URL and status are in the manifest; 3 are owner-supplied (USER_CONFIRMED, exact page not supplied). "No file on a closed day" holds by construction, because holidays were never requested; the calendar circulars, not the downloader, establish the holidays |
| B. Calendar | **PASS with contained exceptions** | All 40 circular hashes match `sources.csv`. The independent audit extracted the text of all 10 base holiday circulars (2016-2025); every weekday holiday matches `events.csv` apart from changes made by later circulars, and no weekday is closed without an event. Muhurat and DR sessions are evidenced and their files held. CAL-2's four dates stay UNRESOLVED (D54) and are contained by ED-31, ED-42 and ED-44 |
| C. Universe | **NOT CERTIFIED** | Evidence is complete: 271 rows, 267 verified by independent agents, 4 dummy-ISIN inferences. Human review: 0 of 271 decisions. The universe is reproducible from its inputs and was regenerated today after the identity rebuild. Defect fixed: a date before the first period had no members and looked verified; it is now UNIVERSE_UNVERIFIED (`universe.py`, test `test_a_date_with_no_member_is_never_a_verified_universe`) |
| D. Identity | **PASS with 3 contained exceptions** | 30 member ISIN changes are recomputed from the bhavcopies; 27 are evidenced by an official CA record dated at the change. 219 records, all source-verified. No join across issuer prefixes. Defect fixed: five pre-2016 renames carried today's ISIN (`RealIdentityRecords`). Reproduced byte-identical from the raw archives by the repo scripts |
| E. Corporate actions | **PARTLY** | The independent completeness audit (C.4) found no missing split-sized event among covered symbols, in either direction. 46 symbols return an empty official response, including live symbols such as ICICIPRULI, ETERNAL and PAYTM; retried today, still `[]`. Those symbols are uncovered: the API is demonstrably incomplete for them (R-10). Prices are never adjusted |
| F. Data quality, point in time | **PARTLY** | Strict loader, OHLC and date checks, dated findings, the prefix-invariance tests and the excluded-session and unresolved-date containment all pass. **P01-H1 (HIGH):** G0 has no CA-coverage check. Without `--corporate-actions`, or for an uncovered symbol, a history spanning an unrecorded bonus can reach G0 PASS: the audit found RELIANCE's 2024-10-28 bonus without the CA file, and ETERNAL (uncovered) in scan v4. NSE does not adjust PREVCLOSE (C.4), so the discontinuity detector does not see splits or bonuses. A split also changes the ISIN and is caught by identity; a bonus is not |
| G. Reproducibility | **PARTLY** | The dataset id (`64c68b3b...`) is reproduced by the independent audit. Identity records, observations and the universe are reproduced from repo scripts and inputs. The loader version was bumped to 2.1.0 for the ED-38 variants. **P01-H2 (MEDIUM):** `run_manifest` does not fingerprint `--instruments` or `coverage.csv`, so a scan cannot prove which identity and coverage versions it used |

### C.2 EOD coverage by year (`eod_coverage_2016_2025.json`)

| Year | Expected trading sessions | Raw files | Accepted (trading) | Accepted (excluded role) | Not accepted | Missing | Rejected non-EQ rows | Schemas |
|---|---|---|---|---|---|---|---|---|
| 2016 | 245 | 247 | 245 | 1 | 1 (Dhanteras, CAL-2) | 0 | 0 | LEGACY_14 |
| 2017 | 246 | 248 | 246 | 1 | 1 (Dhanteras) | 0 | 0 | LEGACY_14, 1 LEGACY_13_CRLF |
| 2018 | 244 | 246 | 244 | 1 | 1 (Dhanteras) | 0 | 0 | LEGACY_14 |
| 2019 | 243 | 245 | 243 | 1 | 1 (Dhanteras) | 0 | 0 | LEGACY_14 |
| 2020 | 251 | 252 | 251 | 1 | 0 | 0 | 0 | LEGACY_14, 1 LEGACY_13_CRLF_SHORTDATE |
| 2021 | 247 | 248 | 247 | 1 | 0 | 0 | 1 | LEGACY_14 |
| 2022 | 247 | 249 | 247 | 1 | 1 (standalone copy of a held archive) | 0 | 0 | LEGACY_14 |
| 2023 | 245 | 247 | 245 | 1 | 1 (standalone copy) | 0 | 0 | LEGACY_14 |
| 2024 | 246 | 249 | 246 | 3 (Muhurat, 2 DR Saturdays) | 0 | 0 | 27 (T0) | LEGACY_14 128, UDIFF_2024B 121 |
| 2025 | 248 | 249 | 248 | 1 | 0 | 0 | 182 (T0) | UDIFF_2024B |

Duplicates: 2, each an owner-supplied standalone CSV identical to its archive. Conflicts: 0. Files on closed days: 0.

### C.3 Universe review report

`nse/data/universe/nifty100_review_packet.csv` is the review artifact. Per row it gives the proposed record, its hash and its official evidence; the agent verdict, and for corrected rows the earlier value and the correction; and the reason for any uncertainty.

| Item | Count |
|---|---|
| Rows | 271: 100 baseline, 146 changes, 25 count exceptions |
| Changes | 62 ADD, 61 REMOVE, 10 RENAME, 13 ISIN_CHANGE |
| Events | 23 |
| Verdicts | 267 VERIFIED (28 by a second independent pass); 4 INFERENCE, the dummy ISINs of DUMMYITC, DUMMYSIEMS, DUMMYTATAM and DUMMYHDLVR |

For the reviewer:
- DUMMYREL's ISIN on 2023-07-20 is taken from the later JIOFIN listing, and its EQ series has no evidence.
- Some counts are 101: "6 inclusions, 5 exclusions" from 2023-09-29 to 2024-08-29 is declared by the release and should be re-read.

Periods: 185, all UNVERIFIED until a human fills `nifty100_review.csv`. There is no membership before 2020-12-31 (B11-P).

### C.4 Corporate-action completeness report (`ca_completeness_2016_2025.json`)

Script: `.claude/skills/nse-data-engineering/scripts/ca_completeness_audit.py`.

Method:
- **Finding:** NSE's bhavcopy PREVCLOSE is the unadjusted previous close (TATASTEEL 2022-07-28: PREVCLOSE 959.4, open 98.1). Price-scale events therefore show as price gaps, not as PREVCLOSE breaks.
- **Forward check:** every one-session gap of 1.4x or more for 189 member symbols. 86 of 86 match a recorded price action. 7 of those match events without a ratio (DEMERGER, UNPARSED), not a matching ratio.
- **The 2 other split-sized moves** (ADANIPOWER 2021, CGPOWER 2021-22) span months with no EQ row; they are not one-session gaps.
- **Reverse check:** 94 of 94 recorded split, bonus and consolidation events, combined per day, show a gap consistent with their ratio.

Limits:
- An event below 1.4x (a small bonus) is not detectable this way.
- The reverse tolerance (x1.35) cannot fail an event whose ratio is at or below 1.35. The 13 such events are observed within 8% anyway.
- 46 uncovered symbols are outside every check that needs records.

### C.5 Identity-gap report

| Case | Evidence | Status | Proposed resolution |
|---|---|---|---|
| BAJFINANCE 2016-09-09 (INE296A01016 to 01024) | The split's ex-date is 2016-09-08 and its printed record date a Saturday | Unresolved, not joined | An NSE notice for the ISIN change; owner acceptance |
| GRASIM 2016-10-07 (INE047A01013 to 01021) | The split's ex-date is 2016-10-06 and its printed record date Saturday 2016-10-08 | Unresolved, not joined | as above |
| YESBANK 2020-03-16 (INE528G01027 to 01035) | No official price event (reconstruction scheme) | Unresolved, not joined | The NSE / RBI scheme document |
| HDFC, MINDTREE, PEL, TATAMTRDVR | Absent from EQUITY_L | LISTING from the first held session; end not recorded | Official delisting / merger records |
| ETERNAL (ZOMATO), TMPV (TATAMOTORS), other renames | `symbolchange.csv`, same ISIN in the bhavcopies | Joined (D51) | none |
| 5 DUMMY placeholders | Never listed instruments | UNKNOWN_INSTRUMENT | none (a membership placeholder only) |

### C.6 Owner decisions and hand-offs

**Owner decisions (genuine):**
1. **B11-R:** the row-level human review of the universe. Recommended: review the 4 INFERENCE rows and the 101-member windows first. Until then, every universe scan is UNIVERSE_UNVERIFIED.
2. **P01-H1 policy (with Prompt 02):** should G0 be MANUAL when a symbol's history has no verified CA coverage (no `--corporate-actions`, or one of the 46 empty symbols)? Recommended: yes. Unknown corporate actions become MANUAL, as the invariant "unknown never becomes PASS" requires. The cost is that those symbols' candidates become MANUAL.
3. **CAL-2 / D54:** evidence for the four Dhanteras dates, if Monthly-to-Yearly context before 2019-10-28 is wanted.

**Hand-offs to Prompt 02 (its locked files; not edited here):**
- P01-H1: G0 coverage check (`qualification.py`).
- P01-H2: fingerprint `--instruments` and the sibling `coverage.csv` in `run_manifest.scan_input_paths` and the parameters.
- P01-H3: review the data-driven changes the D52-D56 round made in Prompt 02 files: ED-33 (D52 rule, G1 guard), ED-40 (`--corporate-actions` wiring), ED-43 (H2a in `mtf_freshness`) and ED-44 (history after the last unresolved date, `scanner`).
- P01-H4: `backtest.py` adds SURVIVORSHIP_UNCONTROLLED only for ad-hoc universes, not for an unverified universe file.

### C.7 What Prompt 02 can consume now

| Input | Status |
|---|---|
| Raw EOD archives and manifest, 2016-2025 | Safe: dataset id `64c68b3b...` |
| Calendar | Safe, with CAL-2 handled by ED-44 |
| `instrument_records.csv` | Safe; the 3 unresolved cases fail closed |
| `actions.csv` with `coverage.csv` | Safe as event evidence. Not proof of absence for the 46 uncovered symbols |
| `nifty100_universe.csv` | Restricted: UNVERIFIED |

Changed contracts:
- `nse_bhavcopy.load_many(..., keep=)`;
- loader 2.1.0 (new schema labels);
- `NseCalendar.COVERAGE_ERRORS`;
- `universe.Universe.limitations` (empty membership is unverified).

## 0B. After the owner decisions D52-D56 (2026-11-09)

**Verdict: DATA_READY is not claimed.** Three statuses are kept apart:
- **Engineering:** complete for D52-D56. Code, tests and records are below; independent review is in the final report.
- **Data:** EOD 2016-2025 complete for every calendar trading day. Two acceptance criteria fail:
  - the universe has no human review (B11-R);
  - four calendar dates are unresolved (CAL-2, by owner decision D54).
- **Research validation:** none. No backtest result exists, and none is claimed.

| Input | Result | Evidence |
|---|---|---|
| EOD 2016-2025 (D47 + D55) | 2,480 files held (2,478 official archives plus 2 owner-supplied standalone copies), all parsed and validated. **2,474 ACCEPTED_FOR_RESEARCH:** 2,462 trading days (all of them; 0 missing) and 12 excluded-session files in role `EXCLUDED_SESSION_D33`. 6 not accepted: 4 Dhanteras files (CAL-2) and 2 standalone CSV copies of held archives. Schemas: `LEGACY_14` 2,108, `LEGACY_13_CRLF` 1, `LEGACY_13_CRLF_SHORTDATE` 1, `UDIFF_2024B` 370. `eod_ready` false only because of CAL-2 | `nse/output/data_readiness/eod_coverage_2016_2025.json` (dataset id `64c68b3b7b92b9644d9c3210abf3453f1bdf5b35a105ec22dee2b9399bcdf0fa`), `backfill_report.json` |
| 2016-2020 download (D55) | 1,228 files on the first pass (rate 1/s, 0 HTTP 404). 2 failed verification: `cm10JUL2017` (CRLF, 13 columns) and `cm13JUL2020` (the same, with a nested member and `DD-Mon-YY` dates). Both were accepted after the exact variants of ED-38 and re-verified. A second pass fetched the 12 excluded sessions | `nse/data/eod/download_log.jsonl`, `acquisition_ledger.jsonl` |
| DQ-1 (D52) | NSE serves Muhurat and DR-switch bhavcopies, so the discontinuity is gone at source for all 12 sessions of 2016-2025. The D52 fallback and the G1 guard (ED-33) apply only where such a file is missing | `test_research_data.ExcludedSessionD52` |
| Corporate actions (D56) | 189 historical members requested from NSE's corporate-actions API (2016-2025). 145 returned non-empty records (coverage); 44 empty responses, never counted as coverage. 2,064 events: DIVIDEND 1,935, BONUS 69, SPLIT 28, RIGHTS 13, DEMERGER 9, UNPARSED 10. An audit found 2 abbreviated splits ("Fv Splt Frm ...") silently skipped; fixed so that unrecognised subjects are UNPARSED (fail closed) | `nse/data/corporate_actions/` (`collection_log.jsonl`, `coverage.csv`, `conversion_report.json`) |
| Identity (D51, D56) | 30 ISIN changes of member symbols are visible in the 2016-2025 bhavcopies; 27 are evidenced by an official split or bonus record dated at the change (ED-37), and records were rebuilt (219 records, all source-verified). The identity check over every member observation leaves three findings, each unevidenced and never joined: BAJFINANCE 2016-09-09 and GRASIM 2016-10-07 (the split's printed record date is the Saturday after the change; matching it would be an inference, D56) and YESBANK 2020-03-16. The SRTRANSFIN to SHRIRAMFIN rename now carries the ISIN traded at the rename | `nse/data/universe/instrument_records.csv`, `identity_report.json` |
| Nifty 100 (D53) | Each of 271 rows independently verified against NSE evidence (`nifty100_review_packet.csv`). Jio Financial is `DUMMYREL` (official NIFTY 50 list of 31 Jul 2023), renamed `JIOFIN` on 2023-08-21 (NSE circular). The 101-member periods are kept. **185 periods UNVERIFIED until a human fills `nifty100_review.csv`** | `nse/data/universe/README.md` |
| Real scan 2025-12-26 (7 symbols, `--instruments --corporate-actions`) | INFY, RELIANCE, HDFCBANK, TMPV and ETERNAL are evaluated on D/W/M/Q/HY/Y; the excluded-session G0 MANUAL of R-9 is gone; no candidate is ACTIONABLE. BAJFINANCE and YESBANK are DATA_INSUFFICIENT (unevidenced ISIN changes). Two regressions the 2016 data exposed were fixed: the first week starting before calendar coverage (ED-43), and the unresolved dates ending every series (ED-44) | `nse/output/scan-d52-d56-2025-12-26-v4/` |
| CAL-2 (D54) | Unchanged: UNRESOLVED. The four Dhanteras bhavcopies show ordinary EQ trading, but that is not a calendar classification and is not used as one | `nse/data/calendar/README.md` |

**Still needed for DATA_READY:** B11-R (human row review). For the full ten-year window, also CAL-2 evidence. Optional: B11-P (2016-2020 membership); an independent CA completeness check (R-10); evidence for the three unevidenced ISIN changes.

## 0A. After the owner decisions D47-D51 (2026-11-09)

**Verdict: DATA_READY is not claimed.**
- **Passed validation:** EOD files and the calendar.
- **Not passed:** universe membership is transcribed but unreviewed (D49), and identity has documented gaps (D51).

| Input | Result | Evidence |
|---|---|---|
| EOD 2021-2025 (D47) | **1,233 of 1,233** calendar trading days accepted; 0 missing; 0 conflicts. Formats: 867 legacy (to 2024-07-05) and 368 UDiFF (`UDIFF_2024B`). 210 non-EQ rows isolated in 112 files (T0, E1; ED-30) | `nse/output/data_readiness/eod_coverage_2021_2025.json` (dataset id `301ae81e516b1ad0aa8832f9b79cf3f5eb9a72026e77977e501db1d451b41b29`), `backfill_report.json`, `nse/data/eod/download_log.jsonl`, `acquisition_ledger.jsonl` |
| Backfill run | 1,171 sessions fetched from `nsearchives.nseindia.com`, rate 1 request per second, 0 HTTP 404. 112 first refused under the whole-file rule, then re-fetched and verified after ED-30. All 1,171 ingested, 0 quarantined | `.claude/skills/nse-data-engineering/scripts/eod_backfill.py` |
| Calendar 2016-2020 (D48) | 18 official circulars hash-registered: 5 base, 2 amendments, 11 session notices. 106 rows: 102 CONFIRMED, 4 UNRESOLVED Dhanteras dates (CAL-2). Each transcribed date was re-checked against its circular's text | `nse/data/calendar/`, `test_nse_calendar_data` |
| Calendar 2021-2025 | Unchanged, and now reconciled with all EOD files: a file on every trading day and none on a closed day | coverage report |
| Nifty 100 (D49) | Baseline 2020-12-31; 23 events, 123 rows; 9 renames; 19 dated counts other than 100 (101 during spin-off and DVR windows). Two independent transcriptions agree on 122 of 123 rows. The universe equals the official lists of Mar 2021, Sep 2021 and Mar 2022. **171 periods UNVERIFIED pending human review** | `nse/data/universe/` (README) |
| Identity (D51) | Renames joined only through verified ISIN continuity (ED-29). Records built from NSE `EQUITY_L.csv` and `symbolchange.csv`. 17 member ISINs unresolved: 4 no longer listed, 13 with a later ISIN (B11-I) | `instrument_records.csv`, `build_report.json` |
| Corporate actions (D50) | Raw prices canonical; nothing adjusted. A separate event store holds INFY and RELIANCE 2016-2025 (36 events); price-scale events keep G0 MANUAL | `nse/data/corporate_actions/actions.csv` |

**Still needed for DATA_READY:**
1. **B11-R:** the human review of the universe transcription.
2. **B11-I:** official ISIN-change evidence for 13 members, and listing records for 4.

**Optional extensions:**
- DATA-2 / B11-P: 2016-2020 EOD files and membership;
- B7-C: corporate-action records for every member;
- CAL-2: the four Dhanteras dates.

## 0. Master Prompt 1 update (2026-11-09)

This section supersedes sections 3, 4, 5 and 9 where they differ. Evidence is held locally,
hash-recorded and listed in each folder's `sources.csv` or `manifest.csv`. Nothing was
added to the research dataset (`nse/data/eod/raw/`); ED-23 explains why.

### 0.1 Formats (B18 resolved for research use; ED-20)

- **Supported:** both formats, through one strict loader. Legacy covers trade dates up to 2024-07-05 and UDiFF covers dates from 2024-07-08 (NSE/MSD/62424).
- **UDiFF header variants:** two were seen, `UDIFF_2024A` (Jan-May 2024) and `UDIFF_2024B` (from July 2024). Any other header is refused.
- **Overlap check:** legacy and UDiFF agree exactly on four official overlap dates (`EOD_FORMAT_EVIDENCE.md` §9).
- **Contrarian caveat:**
  - three of those four dates are Saturday special sessions;
  - no UDiFF sample after 2024-07-08 is held;
  - a later header change is untested, but it would be refused, not misread.
  - Recommended before relying on 2025 data: one UDiFF sample per quarter from 2024-Q3 to 2025-Q4, and an overlap comparison on 3-5 ordinary weekdays.

### 0.2 Coverage, 2021-01-01 to 2025-12-31

Reproduce with:
`python3 -m nse.research.cli eod-coverage --start 2021-01-01 --end 2025-12-31 --symbols INFY,RELIANCE,HDFCBANK --out nse/output/data_readiness/eod_coverage_2021_2025.json`

| Item | Value |
|---|---|
| Calendar trading days | 1,233. Seven more sessions are excluded (Muhurat and the two DR-switch Saturdays) |
| Files held / parsed / validated / accepted | 64 / 64 / 64 / 62 (all legacy, schema `LEGACY_14`). The other 2 are standalone CSV copies of accepted archives |
| Accepted trading days | 62 (5.03%): 2022-01-03 to 2022-03-31, and 2023-12-29 |
| Missing trading days | 1,171: 247 in 2021, 186 in 2022, 244 in 2023, 246 in 2024, 248 in 2025 |
| Earliest / latest accepted | 2022-01-03 / 2023-12-29 |
| Missing fields | none in accepted files (the strict loader refuses a file with any) |
| INFY, RELIANCE, HDFCBANK | an EQ row on all 62 accepted dates |
| Dataset id | `0e7bfd7c594563a1c6e5cb4f330b2f8ba0ef2ce6f521354728bb2528267e01c0` (manifest sha256 `6bb67070...80189`, loader 2.0.0) |
| `research_ready` | **false**: missing sessions |

**Ten years.** About 2016 onwards needs, in addition:
- the 2016-2020 legacy files (roughly 1,230 sessions);
- the NSE holiday circulars for 2016-2020. *[Done 2026-11-09 under D48: the calendar covers 2016-2025; see section 0A.]*

**What history buys.** Weekly and Monthly zones and the SMA-50 clock need several years of continuous history before an as-of date. `inventory --as-of <date>` prints the required start for each timeframe. 62 isolated sessions support daily replay only. A gap on a calendar trading day hides the zone's distal line (fail-closed).

### 0.3 Nifty 100 history (B11): evidence held, transcription not done

- **Held** (`nse/data/universe/evidence/`, URLs verified by an independent byte-identical re-fetch):
  - the dated NSE Indices list "Constituents of NIFTY 100 | March 31, 2022" (`indices_dataMar2022.zip`; 100 symbols, no ISINs);
  - ten NIFTY 100 releases from Feb 2021 to Aug 2025, including the HDFC / HDFC Bank ad-hoc release;
  - the Aug 2021 release, which is image-only;
  - `IndexInclExcl.xls`, last saved in 2020 and not parsed.
- **Wording convention:** "effective from X (close of Y)", where Y is the last session before X. X is the first session of the new composition, as `membership.py` expects.
- **Count exception:** 17 Aug 2023 has 6 NIFTY 100 inclusions and 5 exclusions, so 101 members from 2023-09-29. Declare it in `count_exceptions` (ED-22).
- **Still needed:**
  - **Review the extraction:** a human-reviewed transcription into `nifty100_baseline.csv` / `nifty100_changes.csv`. The extracted lists in `sources.csv` are unreviewed, and one symbol was truncated in extraction.
  - **Ad-hoc events** not yet collected: for example the Jio Financial spin-off (2023), and merger replacements such as LTIMindtree in 2022.
  - **ISINs:** one per member. The 31 Mar 2022 bhavcopy is held and gives the ISIN of every EQ symbol on that day.
  - **Before the baseline:** dates before 2022-03-31 need the Feb 2022 release applied in reverse. The converter rolls forward only, so either a dated baseline before 2022-03-31 is needed, or an owner-approved reverse step.
  - **2016-2020:** those releases.

### 0.4 Corporate actions (B7)

- **Held:** the NSE corporate-actions API returns ex-date, record date and a free-text purpose. The INFY and RELIANCE responses for 2016-2025 are in `nse/data/corporate_actions/raw/`. For example: INFY bonus 1:1, ex 2018-09-04; RELIANCE bonus 1:1, ex 2017-09-07 and 2024-10-28; RELIANCE demerger, ex 2023-07-20.
- **Missing:**
  - records for every universe symbol;
  - a completeness check;
  - a parser for the ratio text;
  - an owner decision on adjustment.
- **Unchanged:** raw prices stay unadjusted. A PREVCLOSE discontinuity makes G0 MANUAL. Limit: an event before the first held file, or one where NSE does not reset PREVCLOSE, is not caught by that check.

### 0.5 Instrument identity on every scan (ED-21)

Every bhavcopy input is checked, and each of these is DATA_INSUFFICIENT from its date:
- an ISIN change without a record;
- a symbol reused for another ISIN;
- a symbol the supplied records do not cover;
- a symbol whose ISIN traded under another symbol earlier, i.e. a rename (`SYMBOL_HISTORY_SPLIT`), because its series would start mid-history. A recorded rename is no exception until histories are joined by ISIN (TD-13).

Without verified records for the symbol, the input also carries `IDENTITY_UNVERIFIED`; that label alone does not block.

### 0.6 Owner actions, in priority order

1. **Backfill 2022-04-01 to 2023-12-28**, then all of 2021, 2024 and 2025. `acquire-plan` now prints, per missing session, the selected format, the exact NSE file name and the official URL. Put the files in `nse/data/eod/inbox`, then run `acquire-ingest` with the URL page and download date. The tool computes size and SHA-256; nothing is typed by hand.
2. **Approve or decline extending the calendar window (D29)** to 2016-2020 for ten-year history, and supply those holiday circulars.
3. **B11:** review a transcription of the held NSE Indices evidence (section 0.3) and supply the ad-hoc notices.
4. **B7:** choose the corporate-action adjustment policy, and approve collecting the API records for the universe.
5. **B8 / B10 / B17:** export INFY from TradingView (section 6). Nothing is read off a chart.

## 1. D40 evidence resolution (D40-Q1)

Two council reviewers worked independently, each with their own stdlib PDF text extractor, on the held
circulars. Both verified every file's SHA-256 against `nse/data/calendar/sources.csv`, and
they agreed on every material point.

| Date | Official notice (held) | Site | Normal Market windows | Withdrawn? | Calendar class | Expiry |
|---|---|---|---|---|---|---|
| 2024-01-20 | NSE/MSD/60340: "Live trading session on Saturday, January 20, 2024 on Primary site"; "regular trading sessions ... from primary site ... as per regular market timings" | Primary only, no switch-over | Not printed; 09:15-15:30 is inferred from NSE/CMTR/41180 (provisional normal-hours evidence) | It withdraws NSE/MSD/59999, 60300 and 60318. **Held since 2026-11-09:** 59999 had planned a two-window primary/DR session (09:15-10:00 primary, 11:30-12:30 DR); 60300 and 60318 only updated ENIT and member-portal timings. The plan was withdrawn before the day | `NORMAL_SPECIAL` (D30 provisional rule) | A normal trading day: one session |
| 2024-03-02 | NSE/MSD/60677: "Special Live trading session ... with intra day switch over to DR site" | Primary, then DR | 09:15-10:00 (primary); 11:30-12:30 (DR); closing session 12:40-12:50; orders purged before DR trading; one closing price "for the day" | Not withdrawn by any held notice | `EXCLUDED_SHORTENED` (D30) | One trading date (D40) |
| 2024-05-18 | NSE/MSD/61893: the same wording and windows; "T0 session is not scheduled ... due to settlement holiday" | Primary, then DR | As 2 Mar | Not withdrawn by any held notice | `EXCLUDED_SHORTENED` (D30) | One trading date (D40) |

**Resolution.** The owner's D40 instruction ("two-part primary/DR normal-market sessions; one
trading date for expiry; do not create candles across the break or discard valid
observations") describes **2 Mar and 18 May 2024**, not 20 Jan 2024. The owner's approval is kept as given; the correction is factual only.
- **Calendar data:** `events.csv` row 61 (20 Jan) no longer claims what the withdrawn circulars said. The classifications of all three dates are unchanged, because both reviews confirm them.
- **Expiry (implemented, ED-10):** a two-window session counts as one verified session for a pending order. Its daily bar spans the DR break, so it is never a fill or exit bar (D30). Its high and low are used only to show that no level could have been reached:
  - when the bar shows no level was reached, the record continues;
  - when it shows a level could have been reached, the record ends `DATA_EXCLUDED_SESSION` (which window traded is unknowable);
  - a missing bar on such a date is `DATA_MISSING_SESSION`;
  - Muhurat sessions are unchanged: they still end the record.
- **Still unverified:** the 20 Jan 2024 hours (taken from NSE/CMTR/41180). The three withdrawn circulars have been held since 2026-11-09, which closes the rest of the evidence trail (section 0).

## 2. Calendar coverage and exceptions (2022-2023 window)

- **Official tables:** 2021-2025 (D40). Every weekday of 2022-2023 can be classified: 0 weekdays are uncovered and 0 dates are unresolved.
- **Trading days in 2022-2023:** 492.
- **Excluded sessions in the window:** Muhurat on 2022-10-24 and 2023-11-12 (`EXCLUDED_MUHURAT`; no file held, none is required).
- **Outside this window:** the 2024 exceptions are in section 1. `events.csv` sha256 after the correction is `e05a87a9c8ce30dff64503e1c3f0fecacba75d91d2250b08793f604994933a12`.

## 3. Historical EOD coverage (2022-01-01 to 2023-12-31; superseded by section 0.2)

| Item | Value |
|---|---|
| Raw files | 64, all in the verified legacy format (`LEGACY_BHAVCOPY`); 0 UDiFF |
| Loaded by the strict loader | 64 of 64, so there are 0 invalid records and 0 missing OHLC / quantity / ISIN fields (the loader refuses a whole file on any bad field) |
| Manifest provenance | every file matches its manifest row (`USER_CONFIRMED`, `SCRIPT_DOWNLOADED_USER_APPROVED`, `USER_CONFIRMED_COPY_OF_ARCHIVE_MEMBER`); `manifest.csv` sha256 `6bb670706d643ab77a61ce0cdae9aa536c107d9e660547269158648e97880189` |
| Distinct trade dates | 62: 2022-01-03 to 2022-03-31 (61 sessions) and 2023-12-29 |
| Earliest / latest | 2022-01-03 / 2023-12-29 |
| Duplicates | 2, both `IDENTICAL_CONTENT` (an archive and its own extracted CSV: 2022-01-03 and 2023-12-29) |
| Calendar trading days held | 62 of 492 |
| **Missing sessions** | **430**: 2022-04-01 to 2023-12-28 (186 in 2022, 244 in 2023) |
| Files on non-trading days | 0 |
| EQ rows per file | 1,635 - 1,805 |
| EQ symbols seen | 2,206. 920 are absent on some held dates; with only Q1 2022 and one 2023 day held, listings, delistings and renames explain much of this, and B11 is needed before any absence is called missing data |
| INFY, RELIANCE, HDFCBANK | an EQ row on every held date; no non-EQ-only days |

**A missing session is never treated as a holiday.** The 430 dates are calendar trading
days with no file. The legacy loader is verified only on 2022-01-03 and 2023-12-29 (B18).
Every other file is checked against that evidence, never assumed to match it.

## 4. UDiFF readiness (B18: BLOCKED; superseded by section 0.1 and ED-20)

- **Now:**
  - `acquisition.detect_format` recognises a UDiFF header by its leading columns `TradDt,BizDt,Sgmt` and quarantines the file (`UDIFF_UNVERIFIED`); it is never ingested.
  - `nse_bhavcopy` refuses UDiFF.
  - No UDiFF parser exists, by design: a parser written without a sample would encode an unverified format.
- **What is required:** exactly one official file, plus its evidence.
  1. One UDiFF capital-market bhavcopy archive from NSE's official reports page for a trade date after the switch. Keep the file name exactly as served.
  2. The NSE circular or page that announces the UDiFF switch date, with the date it took effect.
  3. If NSE published both formats for any overlapping dates, the legacy file for the same trade date (a field-by-field cross-check).
  4. A manifest row: `file_name, kind, trade_date, size_bytes, sha256, source_page, downloaded_on, provenance_status`.
- **Checks once a sample exists.** Each must pass before B18 can close:
  - header: the exact column list and order recorded in `EOD_FORMAT_EVIDENCE.md` from the sample itself; encoding, line endings, quoting;
  - field mapping to `BhavRow`: symbol, series, ISIN, trade date, open, high, low, close, last, previous close, traded quantity, traded value, number of trades. Any field without a legacy counterpart is recorded, not dropped;
  - EQ filtering: the series and instrument-type columns that identify cash equities. Non-EQ-only symbols are reported as in legacy (`EOD_FORMAT_EVIDENCE.md` §7.3);
  - symbol and ISIN: same pattern checks; one row per (symbol, series);
  - trade date: the in-file date equals the file-name date, and the business-date column is understood;
  - OHLC: positive values, low <= open, close <= high; for an overlap date, equality with legacy prices (exact; tolerance 0);
  - traded quantity: whole numbers; equal to legacy TOTTRDQTY on an overlap date;
  - provenance: size and SHA-256 match the manifest, and the archive and member hashes are both recorded.
- **Then:** a strict `nse_udiff` loader with tests built from the sample. The switch date comes from the circular, never from guesses based on file names.

## 5. Historical Nifty 100 universe (B11: BLOCKED; evidence and converter in section 0.3)

- **What exists:**
  - `universe.py` reads membership rows with inclusive `effective_from` / `effective_to`.
  - `scanner.scan` and `scan_history` apply membership at each as_of.
  - A row is verified only if its source file is held with a matching SHA-256.
  - `instruments.py` holds identity records (LISTING, SYMBOL_CHANGE, ISIN_CHANGE, DELISTING, MERGER) and returns `UNKNOWN_INSTRUMENT` for anything it cannot resolve.
  - No membership file is held, so every scan is `UNIVERSE_UNVERIFIED` / `SURVIVORSHIP_UNCONTROLLED`. *[2026-11-09: a transcribed universe is now held in `nse/data/universe/`, still UNVERIFIED until reviewed (D49); see section 0A.]*
- **Gaps:**
  - no announcement date;
  - no per-event additions, removals or replacement pairs;
  - membership is not keyed by ISIN (the `isin` column is read but not stored);
  - no overlap check (the last row wins) and no 100-member balance check;
  - no DEMERGER record type;
  - identity is not wired into the scanner;
  - a historical member with no data file is not reported (it silently drops out).
- **Reconstitution-history schema (to be supplied; converts into the existing universe rows):**

`nifty100_baseline.csv`, one dated snapshot of 100 rows:
`index_name,as_of_date,symbol,isin,series,source,source_doc_id,source_file,source_sha256,recorded_on,notes`

`nifty100_changes.csv`, one row per addition or removal:
`event_id,index_name,announcement_date,effective_date,action,symbol,isin,series,replaces_isin,reason,source,source_doc_id,source_file,source_sha256,recorded_on,notes`
(`action` is ADD or REMOVE; `reason` is RECONSTITUTION, CORPORATE_ACTION or OTHER).

**Validation rules (all must pass):**
- exact headers;
- ISIN matches `IN[A-Z0-9]{10}`;
- `announcement_date <= effective_date`;
- in each `event_id`, the count of ADD equals the count of REMOVE, and every `replaces_isin` is a REMOVE in the same event;
- an ADD is not already a member and a REMOVE is one;
- no overlapping periods for one ISIN;
- exactly 100 members after each effective date;
- every ISIN resolves through `instruments.resolve` at its effective date, otherwise the row is `UNKNOWN_INSTRUMENT` and unverified;
- every source file is held with a matching SHA-256;
- every member with no market-data input is reported.

**Open interpretation (an owner or evidence decision; not guessed):** NSE Indices notices often say "effective from close of trading on X". Whether the first day of the new composition is X or the next session must be settled from the notice text. The converter will refuse a notice whose wording it cannot classify.
- **What is needed:**
  - the NSE Indices reconstitution press releases or notices covering the research window, plus one dated full constituent list (factsheet or index file) as the baseline;
  - for identity: the NSE symbol-change, delisting and merger notices for the affected symbols.

  Today's constituent list is never used for history.

## 6. INFY TradingView parity preparation (B8 / B10 / B17: BLOCKED)

Comparable locally means engine inputs exist for the period: held bhavcopies cover
2022-01-03..2022-03-31 and 2023-12-29. The existing `INFY/ohlc_reference.csv` is transcribed
from Yahoo screenshots with unknown adjustment, so it is not independent validation.

| # | Observation | Timeframe | Periods | Fields | Comparable locally? |
|---|---|---|---|---|---|
| P1 | Daily OHLC | D | every session 2022-01-03..2022-03-31, and 2023-12-29 | O, H, L, C, volume | Yes |
| P2 | Weekly OHLC | W | weeks starting 2022-01-03..2022-03-21 (the week of 24 Jan has the 26 Jan holiday) | O, H, L, C | Yes |
| P3 | Monthly OHLC | M | 2022-01, 2022-02, 2022-03 (1 Mar 2022 a holiday) | O, H, L, C | Yes |
| P4 | Quarterly (TV 3M) | Q | Q1 2022 | O, H, L, C | Yes |
| P5 | Half-year / year (TV 6M / 12M) | HY, Y | H1 2022, 2022 | O, H, L, C | No (incomplete periods held) |
| P6 | SMA-50 | D | sessions from the 50th held session (mid-Mar 2022) | SMA value, Pine trend state | Partly (the clock needs 55 candles) |
| P7 | SMA-50 | W, M | any | SMA value, trend state | No (needs 50+ weeks / months of history) |
| P8 | Demand / supply zones | D | zones created 2022-01..2022-03 | side, pattern, PL, DL, created date, tested date, invalidated date, score | Yes (once history permits detection) |
| P9 | Zones | W, M | any | as P8 | No (needs years of history) |
| P10 | Calendar checks | D | the 12 rows of `tradingview_checks.template.csv` | presence or absence of the bar | Yes |

**Pine settings to record with every export** (from the protected script; read only):
- `i_zone_method` (L9, default "Body to Wick");
- `i_max_base_candles` (L10, default **3**: set it to **5** to match the engine, D12 / PR4, and record it);
- `i_base_threshold` (L11, 0.5) and `i_legout_threshold` (L12, 0.5);
- `i_enable_exceptional` (L15, true);
- tested-zone visibility on (L42-43, L55, L66);
- `i_conflict_distance_pct` (L71, 5.0);
- `i_ema200_type` (L101, "SMA");
- `i_clock_lookback` (L205, 5) and `i_dash2_ranging_pct` (L207, 0.1);
- SMA length 50 is hard-coded;
- chart settings: NSE:INFY, regular session, Asia/Kolkata, adjustments for dividends and splits OFF.

**Template gaps to fix before recording:**
- zone rows have no `export_file` / `export_sha256`;
- no template records the Pine script SHA-256 or the session setting;
- the OHLC, trend and zone templates have no `recorded_by`;
- the trend template has no Pine dashboard state or clock reading;
- settings are free text, not separate columns;
- the Q / HY / Y to 3M / 6M / 12M mapping is unstated.

Only actual exports are compared; nothing is read off a chart by Claude.

## 7. ED-3 (journal one-order-per-zone), implemented

- **Rule:**
  - A plan never submitted as an order does not use the zone's one-order allowance. A plan CANCELLED without a submission record frees the zone.
  - Once the owner records `journal-order-submitted` (a manual Kite / GTT order; nothing is sent), the allowance is used even if the order is later cancelled, expires, stops out or closes.
  - A plan still pending blocks a second plan.
  - An EXPIRED entry with no submission record still holds the zone. Expiry belongs to a live order, and journals from before migration 2 have no submission rows; this is the conservative reading.
- **Schema:** additive migration 2, `journal_orders` (append-only, one row per entry). Migration 3 adds an INSERT guard and snapshots the entries that predate submission records; a legacy CANCELLED entry keeps its zone used. An existing store upgrades in place.
- **Tests:** `test_research_store.JournalAuditRegressions20261106.test_ed3_*`, 9 tests.

## 8. Transaction-cost gap report

- **The model today:**
  - Symmetric percentage costs plus slippage per side, applied to R per share (`backtest.r_multiple`).
  - A dated percentage schedule per instrument type (`execution_policy.CostSchedule`).
  - Every backtest result now lists `EXECUTION_REALISM_GAPS`.

Indian equity-delivery cost **structure** (all items UNVERIFIED; no rates are given, and
none may be invented):

| Component | Basis | Expressible today? |
|---|---|---|
| Brokerage | % of order value or flat per order, with possible minimum or cap | % yes; flat / min / cap no |
| STT | % of turnover (side rules per schedule; rounding per contract note) | % yes; side-specific and rounding no |
| Exchange transaction charge | % of turnover | yes |
| SEBI turnover fee | % of turnover | yes |
| Stamp duty | % of buy-side turnover, possible cap | no (side-specific) |
| GST | % of a set of other components | no (needs the base list) |
| DP / demat charge | flat per scrip per sell day | no |

**Why flat and capped charges need quantity:** a flat charge F costs F / (qty x (entry - SL))
in R, which is about F / RPT. The backtest has no quantity or capital, so these charges can
only be modelled after an owner decision on RPT / capital in backtests.

**Proposed data contract:** dated periods with `components[]`, each holding:
- `id`;
- `side` (BUY / SELL / BOTH);
- `basis` (PCT_TURNOVER / FLAT_PER_ORDER / FLAT_PER_SCRIP_SELL_DAY / PCT_OF_COMPONENTS);
- `rate`, `amount`, `min_per_order`, `max_per_order`;
- `base_components`, `rounding`, `source_ref`.

The function is `order_cost(schedule, instrument_type, side, price, quantity, trade_date)`. It refuses any missing or ambiguous component, and each leg is priced on its own trade date.

**Fee provenance needed, for each period:**
- the issuing document (NSE / SEBI circular, stamp-duty notification, the broker's pricing page snapshot);
- its URL, retrieval date and SHA-256;
- the effective-from date as stated, and the effective-to date taken from the superseding document;
- a clause reference for each component.

Dates before the first snapshot stay UNVERIFIED.

**Other realism gaps** (now disclosed on every backtest result):

| Gap | Severity |
|---|---|
| Price bands / circuit limits | High for stop exits |
| GTT trigger-then-limit semantics: the model is a resting limit | Medium |
| Partial fills | Medium |
| Tick-size rounding | Low-medium |
| Liquidity versus quantity | Low-medium for Nifty 100 |
| Capital / T+1 lock | Low until capital is modelled |

## 9. Prioritised acquisition requirements (owner actions, in order; superseded by section 0.6)

1. **2022-04-01 to 2023-12-28 legacy bhavcopies: 430 sessions** (the official NSE archive, `cmDDMMMYYYYbhav.csv.zip`). This unlocks a full-year real-data MIT window. Place them in `nse/data/eod/inbox` and run the acquisition ingest, which records hashes and the manifest. Track progress with `inventory` / `eod-coverage`.
2. **History before 2022** for the Monthly / Weekly curve and SMA-50 (`inventory --as-of <date>` prints the required start per timeframe).
3. **B11:** the NSE Indices Nifty 100 reconstitution notices for the window, plus one baseline constituent list (section 5 schema).
4. **B7:** corporate-action records (ex-date, ratio, source document) for the scanned symbols.
5. **B18:** one official UDiFF sample with its switch-date circular (section 4). It is only needed for dates after the switch.
6. **B8 / B10:** the INFY TradingView exports in section 6.
7. **Calendar trail:** NSE/MSD/59999, 60300 and 60318, to close the 20 Jan 2024 note.
8. **Costs:** a dated Zerodha schedule with source documents (section 8). Before flat charges can be modelled, the owner must decide whether backtests use RPT / capital.
