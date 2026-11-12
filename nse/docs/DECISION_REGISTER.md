# Decision Register (human decisions outstanding)

**Dated 2026-11-02; owner approvals of 2026-11-08 added below.** Open items and approved methodology decisions that change what the system may conclude.

## Owner approvals (2026-11-08 task brief; detail in `DECISION_LOG.md` section 1F)

These close the matching "USER DECISION REQUIRED" rows in the tables below. Those rows are
kept as history; where they disagree with this table, this table is current.

| ID | Status | What the code does now | Tests |
|---|---|---|---|
| D42 | USER_STATED, owner-approved operating constraints (D46) | 10 positions; 10 trades per IST month by first fill / trigger; revalidation before fill; 10 verified-session expiry; a backtest without a calendar is refused | `test_research_execution_policy`, `test_research_store.JournalIstMonth20261108` |
| D43 (was PINE-ONLY-1) | USER_APPROVED | A relevant opposing Pine-only supply makes G5 / G7 MANUAL (`PINE_ONLY_ZONE_REVIEW`); never a target | `test_research_gates.PineOnlyD43` |
| D44 (was UNDATED-ERR-1) | USER_APPROVED | A BAD_DATE row is dated by its neighbours when they bound it; otherwise it blocks every scan | `test_research_lookahead.FutureDataQuality.test_d44_*` |
| D45 | USER_APPROVED | `ExecutionModel` refuses caps that are None or above 10, and expiry above 10 | `test_research_execution_policy.D45Refusals`, `test_research_backtest.Portfolio` |
| D46 | USER_APPROVED | D42 stays USER_STATED, enforced in journal and backtest | as D42 |
| D57 | USER_APPROVED 2026-11-09 | Local-first web application in the browser, not a Tauri or Electron shell. Loopback bind, HttpOnly session cookie, no session value in the page. Cloud hosting is a later option and is not built | `platform/tests` session and host checks |
| D58 | USER_APPROVED 2026-11-10 | Four Dhanteras dates are confirmed regular equity sessions, 09:15-15:30. The Gold ETF/SGB extension stays in the note | `test_nse_calendar_data` |
| D59 | USER_APPROVED 2026-11-10 | Membership-based Nifty 100 research is labelled from 2020-12-31 onward. It is not certification. Pre-window as-of dates carry `MEMBERSHIP_BEFORE_PROVISIONAL_WINDOW`. Review, identity and G0 rules are unchanged | `test_research_reports`, `test_research_backtest.ProvisionalWindow` |
| CAP-IST-1, B12-CAP | Closed by D42 / D46 | Month = IST month of the first fill (`models.ist_month`) | `IstMonth` |
| P-LOC-2 | USER_APPROVED | Price inside a TESTED Monthly demand: redraw from the next fresh Monthly demand below; unknown -> MANUAL | `G3.test_price_inside_a_tested_monthly_demand_redraws_from_the_next_fresh_zone`, `test_redraw_*` |
| P-LOC-3 | USER_APPROVED | Unknown Monthly boundary freshness -> MANUAL (unchanged) | `G3`, `test_redraw_stops_at_a_boundary_of_unknown_freshness` |
| P-RISK-1 | USER_APPROVED | `risk.assess_config` (unchanged; matches every branch) | `test_research_risk` |
| B9 | USER_APPROVED | Tier-union ranges unchanged; backtest scenarios declared up front (`execution_policy.owner_grid`) | `test_research_execution_policy.OwnerGrid` |
| B12 | USER_APPROVED | `execution_policy`: AT_OPEN, STOP_FIRST + EXCLUDE, slippage 0.05 / 0.10 / 0.20, dated per-instrument `CostSchedule` (user file; no figures built in) | `test_research_execution_policy` |
| D40 | USER_APPROVED; D40-Q1 resolved by evidence (2 Mar / 18 May 2024 are the two-window sessions) | Two-window sessions count once for expiry and are never fill bars (ED-10); 20 Jan 2024 row 61 note corrected | `test_nse_calendar_data`, `test_research_execution_policy.D40TwoWindowSessions` |
| D41 | USER_APPROVED for the readings named in DECISION_LOG section 1F | Those named readings, as already implemented | as listed per reading |
| RB-VERSION-1 | USER_APPROVED: the PDF is canonical; the Markdown is the citation companion | Citations unchanged; hashes pinned | `test_repo` |

**Still open (owner):**

| ID | Question | Effect today | Smallest owner action |
|---|---|---|---|
| D40-Q1 | The brief calls 20 Jan 2024 a "two-part primary/DR" session; NSE/MSD/60340 says regular primary-site trading. The two-window sessions are 2 Mar and 18 May 2024, which D30 excludes | None for daily MIT except that a backtest record meeting 2 Mar / 18 May 2024 ends `DATA_EXCLUDED_SESSION` (fail closed) | **RESOLVED 2026-11-08** by two independent evidence reviews (`REAL_DATA_READINESS.md` §1); no owner action left except holding NSE/MSD/59999, 60300, 60318 to close the trail |
| ED-3 | Should a CANCELLED plan with no order ever placed free the zone in the journal? | **RESOLVED 2026-11-08 by the owner brief:** it does; a submitted order (`journal-order-submitted`) never releases the zone | none |
| M4b | WIT session / gap design | WIT BLOCKED | Decide when intraday data (B6) exists |
| D40-Q1 (update 2026-11-09) | The withdrawn NSE/MSD/59999 is now held: it planned the two-window session for 20 Jan 2024, and 60340 withdrew it | None (classifications unchanged) | Acknowledge the factual correction |
| CAL-1 (MP1) | Extend the approved calendar window (D29: 2021-2025) to 2016-2020 for ten-year history? | **DECIDED 2026-11-09 (D48)**; implemented (ED-26).  Pre-2021 dates are CALENDAR_UNVALIDATED; never called missing or trading | Approve or decline; if approved, supply the 2016-2020 NSE holiday circulars |
| DATA-1 (MP1) | Backfill 1,171 missing 2021-2025 sessions: owner download, or an explicit approval for a scripted download as for the Q1 2022 batch | **DECIDED 2026-11-09 (D47)**; executed: 1,171 files ingested (ED-25).  `research_ready` false; 62 of 1,233 trading days accepted | Download per `acquire-plan` (names and URLs per date), or approve a scripted run outside `nse/` |
| B11-T (MP1) | Review a transcription of the held NSE Indices evidence; approve a reverse step for dates before 31 Mar 2022, or supply an earlier dated list (TD-15) | **DECIDED 2026-11-09 (D49)**; transcription prepared, review pending (B11-R).  UNIVERSE_UNVERIFIED on every scan | Review `nse/data/universe/evidence/sources.csv` extractions against the PDFs |
| B7-P (MP1) | Corporate-action adjustment policy, and approval to collect NSE corporate-action records for the universe | **DECIDED 2026-11-09 (D50)**; policy implemented (ED-28).  CORPORATE_ACTIONS_UNVERIFIED; G0 MANUAL on a detected discontinuity | Choose a policy (e.g. none plus MANUAL, or a back-adjusted series kept separate from raw) |
| CAL-2 (2026-11-09) | Dhanteras "extended live trading" days 2016-10-28, 2017-10-17, 2018-11-05, 2019-10-25: regular hours plus an evening session for Gold ETFs / SGBs only. Classify as NORMAL_SPECIAL for equities, or record no row? | **DECIDED 2026-11-10 (D58, option A): confirmed regular equity sessions (`CONFIRMED`, 09:15-15:30, NORMAL_SPECIAL); the Gold ETF/SGB extension is kept in the notes.** History: D54 (2026-11-09) had held them UNRESOLVED, with the four files VALIDATED and 2016-2025 `eod_ready` false. Since D58 the files are ACCEPTED_FOR_RESEARCH and the ED-44 cut no longer applies | None |
| B11-R (2026-11-09) | Human review of `nse/data/universe/nifty100_*.csv` (D49) | **DECIDED 2026-11-09 (D53): row-level human review (ED-35).** Every row independently verified against NSE evidence (`nifty100_review_packet.csv`); the Jio Financial entity is `DUMMYREL` from 2023-07-20 and `JIOFIN` from 2023-08-21, both from official documents; 101-member periods kept. Every scan stays UNIVERSE_UNVERIFIED until a human fills `nifty100_review.csv` | Fill `decision`, `reviewer`, `reviewed_on` per row of `nifty100_review.csv` (README there); agents never do |
| DATA-2 (2026-11-09) | Extend D47's download scope to the 2016-2020 EOD files for the ten-year window? | **DECIDED 2026-11-09 (D55); executed.** 1,242 files downloaded (1,230 trading days, 4 then-UNRESOLVED Dhanteras dates, 8 excluded sessions), all parsed and validated (2 needed the exact variants of ED-38). After D58 those four archives are accepted equity sessions: 2016-2025 is 2,466 of 2,466 equity sessions plus 12 excluded-session files. CAL-2 no longer blocks `eod_ready`. `DATA_READY` stays unclaimed because universe review is open | none |
| B7-C (2026-11-09) | Approve collecting NSE corporate-action records for every universe member (D50 store) | **DECIDED 2026-11-09 (D56); executed (ED-39).** 189 symbols requested; 145 non-empty official responses held as coverage; 2,021 events in `actions.csv` (10 `UNPARSED_PRICE_EVENT`, G0 MANUAL); symbols with an empty response stay uncovered | Optional: an independent CA source to test the API's completeness (R-10) |
| B11-I (2026-11-09) | Which official source should link old and new ISINs for the 13 members whose ISIN changed (D51)? | **DECIDED 2026-11-09 (D56): official NSE corporate-action records; implemented (ED-37).** 30 member ISIN changes in 2016-2025, 27 evidenced, records rebuilt (219, all verified). Unevidenced and not joined (DATA_INSUFFICIENT across them): BAJFINANCE 2016-09-09 and GRASIM 2016-10-07 (record date a Saturday, after the change) and YESBANK 2020-03-16. The 4 delisted members have LISTING records from their first held session | Optional: official documents for those three ISIN changes |
| P01-H1 (2026-11-09, PROMPT-01) | Should G0 be MANUAL when a symbol's history has no verified corporate-action coverage (no `--corporate-actions`, or a symbol whose official response was empty)? | **Directed in the Prompt-02 closure review and implemented (ED-46).** G0 is MANUAL: coverage absent is `CORPORATE_ACTION_COVERAGE_UNKNOWN`; a span outside a hash-verified window is `CORPORATE_ACTION_COVERAGE_UNVERIFIED`. An empty response is not coverage. A verified window with no recorded price-scale action can pass this check | none for this check; R-10 (API completeness) remains with the data workstream |
| DQ-1 (2026-11-09) | A PREVCLOSE discontinuity whose only explanation is a calendar-confirmed excluded session between two held files | **DECIDED 2026-11-09 (D52); implemented (ED-33, ED-34).** NSE does serve those bhavcopies; all 12 of 2016-2025 are now held, so the discontinuity disappears at source. Where a file is not held, the strict D52 rule applies, and an unobserved excluded session inside a zone's span makes G1 MANUAL | none |

## Product-owner approvals (M1, 2026-11-02)

The following R1-R6 decisions are **USER_APPROVED** and authoritative. Approval of R1-R6
is limited to these six decisions. Later approvals are the 2026-11-08 table above and
DECISION_LOG section 1F. A reading that table and section 1F do not name stays proposed.

| ID | Approved behaviour | Implementation / test trace |
|---|---|---|
| R1 | Curve position uses CMP only. Execution PL does not affect curve classification. HOC at CMP applies even if execution PL is LOC. | `_g3`; G3 and end-to-end tests |
| R2 | 12 o'clock / Extreme Uptrend maps to `STRONG_UP` for eligibility and matrix evaluation; preserve the original label in reports and diagnostics. | `trend.READINGS`; trend and report tests |
| R3 | Coinciding means actual price-range overlap between demand zones on different timeframes. Aggressive remains separate; a zone merely above the HTF PL is not Coinciding. Preserve applicable D15 tested-zone / DL-untouched requirements. | `structure.coinciding`; overlap, non-overlap, D15 and G6 tests |
| R4 | A completed candle close beyond a demand zone's DL invalidates it under D24. A wick / temporary breach alone is not invalidation or a bounce. An active-trade SL touch is recorded separately from zone invalidation. Apply approved timeframe rules consistently. | Zone Engine, MTF overlay and backtest event tests |
| R5 | HOC + Up + demand long is REJECT; HOC + Sideways is MANUAL pending sector support; HOC + Down follows RF3, with no invented exception. Keep the outcomes explicit. | `matrix_long`, `_g3`, `_g8`; matrix and qualification tests |
| R6 | Known absence of a qualifying HTF zone passes G6 as Standard; unknown freshness / DL status is MANUAL. G3 independently determines whether a curve exists. G6 PASS is not overall qualification. | `_g6`; G3 / G6 regression tests |

The earlier P-LOC-2 reading about price inside a tested HTF demand is not the same decision
as this approved R4 DL-invalidation rule. Section 1F records P-LOC-2 as `USER_APPROVED`
on 2026-11-08: redraw from the next fresh Monthly demand below. That approval is not R4.

**Detailed review:** `DECISION_REVIEW.md` has, for each item, verbatim Rulebook quotes, the
alternatives, the gate outcomes and tests that would change, and a recommendation.
- **Approved in M1:** R1-R6 above (P-LOC-1, P-TREND-1, P-COIN-1, P-MAT-1, P-MAT-2,
  P-COIN-2, plus the distinct DL-invalidation rule R4).
- **Section 1F names P-CONF-1 and P-G8-1** among the 2026-11-08 approvals. The recorded
  behaviour keeps the manual outcome already implemented. That is not a new rule.
- **2026-11-02 items later recorded in section 1F:** P-LOC-2, D40, B9, B12 and RB-VERSION-1.
  D40-Q1 was an evidence discrepancy; the log records the factual correction. M4b (WIT
  session design) was not approved and stays open. Nothing
here is approved merely by being listed. "Type": **TRADING** (a strategy rule; only the user
decides), **ENGINEERING** (software behaviour; the recommendation can be adopted on
approval without changing any rule), **EVIDENCE** (needs external data or records).
Effect states what the code does **today** while the item is open.

## 1. Trading-rule items (approval required)

| ID | Source | Current behaviour | Alternatives | Effect on G0-G8 / eligibility | Tests | Recommendation |
|---|---|---|---|---|---|---|
| P-TREND-1 / R2 | RB 1688 "Extreme Uptrend" (12 o'clock); matrix rows say "Strong Up" (RB 1889-1897) | 12 o'clock maps to `STRONG_UP`; preserve Extreme label | Separate Extreme reading -> MANUAL | **Can PASS G4** | Trend and report tests | **USER_APPROVED R2 (2026-11-02)** |
| P-MAT-1 / R5 | RB 1599 (EQB: trade only in the ITF trend direction); spec 7.6 lists EQB + Down as no row | EQB + Down long -> REJECT | MANUAL (spec 7.6 "not listed") | **Can FAIL G4** | Matrix and qualification tests | **USER_APPROVED R5 (2026-11-02)** |
| P-MAT-2 / R5 | RB 1600-1601, 1901; spec 7.2 | HOC + Up REJECT; HOC + Sideways MANUAL; HOC + Down follows RF3 | HOC always REJECT unless sector support (not evaluated) | Restricts; clear Down also reaches RF3 | Matrix and qualification tests | **USER_APPROVED R5 (2026-11-02)** |
| P-COIN-1 / R3 | RB 1833, 1847, 1853-1855; D15; spec 7.5 | Actual overlap of demand-zone price ranges -> Coinciding; Aggressive is separate | No numeric tolerance is added | G6 reflects overlap and keeps unknown status manual | G6, overlap tests | **USER_APPROVED R3 (2026-11-02)** |
| P-COIN-2 / R6 | D15; spec 7.5 silent | Known absence -> G6 PASS as Standard; unknown DL/freshness -> MANUAL | MANUAL for all absence | G3 remains independent | G6 and G3 tests | **USER_APPROVED R6 (2026-11-02)** |
| P-LOC-1 / R1 | RB 1591 ("CMP"); entry at PL (RB 2010) | CMP only; execution PL does not affect curve position | Execution PL or dual reference | CMP alone drives G3/G4 position | G3 and end-to-end tests | **USER_APPROVED R1 (2026-11-02)** |
| P-LOC-2 | RB 1587, 1597, 1617-1622 | Monthly: redraw from the next fresh Monthly demand below (was MANUAL until 2026-11-08) | VLOC; or redraw to the next fresh zone | Restricts | `G3.test_price_inside_a_tested_monthly_demand_redraws_from_the_next_fresh_zone` | **USER_APPROVED 2026-11-08 (redraw). Earlier: still open; not covered by approved R4** |
| P-G8-1 | RB RF7 (line 606) | Leg-out not closing beyond the leg-in extreme -> RF7 MANUAL | Automate "reaction zone" detection | Restricts | `G8` | Keep manual |
| D40 | Official circulars; D30 | Calendar 2021-2025 in use; 20 Jan 2024 hours inferred from NSE/CMTR/41180 | Reject the inference -> that date UNRESOLVED | Calendar decides gaps (G0) and HTF candles | `test_nse_calendar_data` | Review wording and the inference; approve or mark the date UNRESOLVED |
| B9 | RB 2010-2022, 2097-2110 | Ranges over every applicable tier (P-LVL-1) | One buffer rule | Scanner: R:R may be MANUAL (DEPENDS). Backtest: **cannot run without a choice** | `G7`, `Levels` | Choose a backtest buffer rule (only needed for backtests) |
| B12 | RB 2141; RB 2530-2538 (cancel before trigger when a pre-trade check fails) | Backtest refuses to run without fills, same-bar, expiry, costs, slippage. Since 2026-11-06, a later scan that drops the zone cancels a pending order (`CANCELLED_SETUP_INVALID`, scan times only). With a calendar, expiry counts verified sessions and data holes fail closed (D42) | Any user model | Backtest only | `test_research_backtest.Model`, `AuditRegressions20261106` | Supply an execution and cost model from official schedules (costs, slippage; B9 baseline) |
| M4b | audit M4b; D16 | WIT BLOCKED everywhere | Approve a 75/125-minute session and gap design | No WIT output | `Wit`, q7, e2e | Decide when intraday data (B6) is available |
| P-RISK-1 | RB 41, 53-59, 1029, 2208-2220; also RB 3949 ("risking 2% when your stage says 1%" is a red line: recalculate), which the earlier wording "no line says above the band = reject" omitted | `risk.assess_config`: RPT above the declared stage's maximum, or above 2% with no stage declared, is FAIL; below the band or no stage is MANUAL | MANUAL instead of FAIL | Risk plan only (never a gate or candidate status) | `test_research_risk` Config, AuditRegressions | **USER DECISION REQUIRED** (reading labelled in the code) |
| B12-CAP | RB 2392, 2400, 2408, 2414-2415 | Backtest cap counts trades at FILL; selection is fill order (the Rulebook's "best 10" stays human); a cap above 10 is allowed but labelled MONTHLY_CAP_ABOVE_RULEBOOK | Count at order placement; refuse caps above 10 | Backtest only | `test_research_backtest` Portfolio, CapAuditRegressions | **USER DECISION REQUIRED** with B12 |
| RB-VERSION-1 | Root PDF `340fe490-..._Trading_Rulebook.pdf` (136 pages, SHA-256 e41cd0e7...) vs protected Markdown (SHA-256 039883be...) | Code cites the protected Markdown line numbers; both files are hash-pinned and unchanged | Declare the PDF or the Markdown the authoritative revision | MIT: none found (completed-candle rule is D23; the 3.4 exception exempts MIT). WIT: the G1 recency source (RB 1786-1803) exists only in the Markdown; WIT stays BLOCKED | `test_repo` pins both hashes | **USER DECISION REQUIRED.** **Disputed premise (2026-11-03 / 2026-11-06):** `release/OWNER_DECISION_PACK.md` section 1 reports that PDF page 62 visibly contains RB 1772-1813. The 2026-11-06 audit could not re-extract the PDF (no PDF tool installed), so neither reading is independently confirmed here. The source-of-record choice remains the owner's. Found 2026-11-02 by a stdlib text extraction of the PDF compared line by line with the Markdown: the PDF has no text for RB 1784 ("Leg-out is CLOSED" requirement row), section 3.4 "LTF Proximity Rule" (RB 1786-1803) or the RB 1809 / 1813 Chapter 4.1 wording. All other differences found were bold-font extraction artefacts. Which file is newer is not known |

## 1A. Raised by the 2026-11-06 multi-agent audit

| ID | Source | Current behaviour | Question | Effect | Tests |
|---|---|---|---|---|---|
| D42 | Owner task brief, 2026-11-06 | **USER_STATED** (see `DECISION_LOG.md` D42): 10 simultaneous positions enforced in the journal, labelled in the backtest; pending-order revalidation; 10-session expiry labelled | Confirm the wording, and whether the backtest should refuse (not only label) models above the limits | Journal / backtest only | `test_research_store.JournalAuditRegressions20261106`, `test_research_backtest.AuditRegressions20261106` |
| PINE-ONLY-1 | D12 / PR1 ("Pine-only path goes to manual review where it would change a zone or score") | `EngineResult.pine_only_zones` is read only by `refcheck`; an opposing Pine-only supply inside the G5 bands or below the G7 target does not affect G5/G7 | Should an opposing Pine-only zone make G5/G7 MANUAL? | Could turn some ACTIONABLE into MANUAL_REVIEW; no current output is loosened | none yet (repro: audit Agent 3 D2) |
| CAP-IST-1 | Owner pack section 4 | Backtest counts the month from `fill_time[:7]`, journal from the timestamp's year/month; candle times are naive exchange time | Confirm month boundaries are exchange-local (Asia/Kolkata) and that the cap spans the whole trading book | None while all times are naive IST | `Portfolio`, `Journal` |
| UNDATED-ERR-1 | audit Agent 3 D4 / Agent 6 #10 | An undated ERROR finding (malformed CSV row, bhavcopy input error) blocks every as-of, including earlier ones | Accept as fail-closed, or date such findings | Restrictive only | `test_research_lookahead` |

## 2. Engineering items (adopt on approval; no rule changes)

| ID | Current behaviour | Recommendation | Tests |
|---|---|---|---|
| P-LOC-3, P-LVL-2, P-CONF-1 | Unknown-freshness boundary / target, or a measuring-point disagreement, -> MANUAL | Keep (they only restrict) | `G3`, `G7`, `G5` |
| P-CAL-1 | No calendar -> G0 MANUAL | Keep | `G0`, e2e `test_no_calendar_is_never_actionable` |
| P-LVL-1 | Tier union over PL and both DLs, edges inclusive | Keep until B9 | `Levels` |
| P-LVL-3 | Invalid levels (SL <= 0, inverted geometry, non-finite) -> G7 MANUAL, no R:R or quantity | Keep | `Levels.test_invalid_levels_are_reported_not_computed` |
| P-CA-1 | A price-scale corporate action inside the replayed history -> G0 MANUAL; nothing adjusted | Keep until B7 is decided | `test_research_data.CorporateActions` |
| P-DQ-1 | Findings dated after as_of are not read by an earlier scan | Keep | lookahead `FutureDataQuality` |
| P-CA-2 | A PREVCLOSE discontinuity inside the history makes G0 MANUAL; a backtest trade alive across one is excluded from metrics | Keep until B7 | `test_research_data.PrevcloseDiscontinuity`, `test_research_backtest` |
| P-REF-1 | Zone references matched by timeframe, side and creation period; prices exact | Confirm against the first real TradingView references | `test_research_data.ZoneReference` |
| P-BT-1 | Backtest: every execution assumption a required input; signals from point-in-time scans; one order per zone | Keep | `test_research_backtest` |
| M1 | Open leg-out window labelled in the fresh-zone report (`LEGOUT_WINDOW_OPEN`); the engine is unchanged | Accept the report label; engine status unchanged | e2e `test_before_the_leg_out_closes...` |
| L5-L9, audit rows 13 and 31 | As in `PHASE1_CORRECTNESS_AUDIT.md` (L7 is SESSION_TIMES_ASSUMED on every record; L9 truncation is visible) | Accept or defer each | audit |

## 3. Evidence items (external)

| ID | Needed | Unblocks | Next action |
|---|---|---|---|
| EOD range | Official bhavcopies 2021-01-01 to the scan date (inventory: 699 sessions missing for a 2024-01-31 scan); UDiFF sample for dates after the switch (B18) | Real-data G3-G7, history sufficiency | `python3 -m nse.research.cli inventory --as-of <date>`; approve the download |
| B7 | Corporate-action records for scanned symbols | Removing CORPORATE_ACTIONS_UNVERIFIED | Choose a source; fill `nse/research/corporate_actions.py` format |
| B8, B10, B17 | TradingView observations: `nse/data/reference/tradingview_checks.template.csv`, OHLC and zone reference files | Reference validation | Record the 12 calendar checks, W/M OHLC, and zones for INFY |
| B11 / D1 | Nifty 100 constituents with dates | Universe; survivorship control | Supply NSE Indices files |
| B6 | Intraday source | WIT (with M4b) | Kite verification (D17) |
