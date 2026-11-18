# Implementation Blockers

**Project:** NSE GTF Demand & Supply Swing-Trading Research System
**Version:** 2.2, dated 2026-10-26. It updates v2.1 for user decisions D21–D23 (B13 and B14 resolved; B8 approach decided, verification open).
**References:** `RB n` = Trading Rulebook line; `PS n` = Pine Script line; D*/S* = `DECISION_LOG.md`; PR*/RC* = `SOURCE_COVERAGE_REPORT.md`.

**Repository layout (since 2026-10-26):** everything for this project lives under `nse/`. The two reference sources are in `nse/sources/` (kept byte-for-byte; their SHA-256 hashes are pinned by `tests/test_repo.py`). The four current documents are in `nse/docs/`, the two superseded audit reports in `nse/docs/archive/`, and the Zone Engine in `nse/zone-engine/zone_engine.py` (tests in `tests/`).

**"Blocks" column:** **Doc** = documentation · **Scanner** = scanner implementation · **Validation** = historical validation / backtesting.

**Status: the scanner is NOT implementation-ready.** The documentation is internally consistent; no blocker stops it.

---

## Part 1: Resolved (kept for traceability)

| ID | Former blocker | Resolution |
|---|---|---|
| B1 | Pine vs rulebook precedence | **D12** rulebook-strict. The per-item outcomes table is in DECISION_LOG D12. Ambiguous items → manual review (Part 4B). |
| B2 | Zero-base base component | **D13**: Pine reference with the `ZB-PINE-REF` trace tag; rulebook does not define it |
| B3 | Trend quantification | **D14 + D21**: Weekly (gate) + Monthly (context) clock for daily execution; ambiguous bands → manual |
| B4 | Tested HTF zones in context | **D15** (coinciding: DL untouched) and **D12** (conflict: tested opposing zones → manual) |
| B5 | Trade-type scope | **D16**: MIT + WIT (75/125) |
| B13 | Role of Monthly trend for MIT | **D21** (Option A): Weekly = gate; Monthly = mandatory context; Weekly opposing Monthly location bias → RB 1232 "extreme caution" → manual review; no new hard rejection |
| B14 | WIT trend checks | **D22** (Option C): rulebook's generic matrix with WIT roles (RB 1370, 1574, 1668); Daily is the only trend gate; no added gates; underspecified cases → manual. **Finding:** the rulebook has no separate WIT matrix |
| B16 | HTF freshness from finer candles | **Implemented** (`nse/mtf-freshness/`) under D24-D28, corrected by D33-D34 and D36-D39 after the Phase 1 correctness audit. Real-data and TradingView validation are still open (B6, B7, B8, B10, B17, B18) |

---

## Part 2: Remaining blockers

| ID | Blocker | Why it matters | Source evidence | Affected component | Blocks | Needed to resolve |
|---|---|---|---|---|---|---|
| **B6** | **Kite Connect capabilities unverified** (D10, D17) | The data layer cannot be built on unverified assumptions about history depth, intervals, adjustment, limits or licence. WIT needs session-aligned intraday data that can build exact 75/125-min candles. | D10, D17 | Market data (§9.2); candle construction (§9.3) | **Scanner**, **Validation** | Read current official documentation. User confirms subscription and access outside the repo. Confirm intervals that divide 75 and 125 minutes and align to 09:15. Decide a fallback source if needed. |
| **B7** | **Corporate-action adjustment** | Unadjusted splits and bonuses create false zones and false breaches | Data integrity (no rulebook coverage) | Data validation; candles | **Scanner**, **Validation** | Adjusted data source or corporate-action feed; method; validation on known split/bonus dates |
| **B8** | **HTF candle verification against TradingView** (approach decided by D23: calendar-aligned Y/HY/Q) | Calendar boundaries, OHLC aggregation, listing-period candles and minimum-history behaviour are specified, but whether they match TradingView's `3M`/`6M`/`12M` bars (used by the Pine EMA/SMA at PS 295–297, 312–316) is **unverified** | D23; RB 1104–1179; PS 295–297, 312–316 | Candle construction; TDA steps 1–3; HTF trend and EMA context | **Scanner** (validation of output), **Validation** | Recorded comparisons for agreed symbols: boundaries, OHLC values, holiday periods, listing period, split/bonus stock, SMA/EMA values. **Open until recorded.** |
| **B10** | **Pine parity reference outputs** | The Python engine cannot claim to match Pine without references. D12 makes some outputs intentionally differ (PR1, PR4, PR5, PR8), so the indicator must be configured to match (e.g. max base candles = 5) and the differences asserted. Needed for daily, weekly, monthly, **75-min and 125-min** charts. | Spec §10 | Zone detection acceptance | **Scanner** (acceptance), **Validation** | User records indicator outputs on TradingView for the agreed test set (spec §10.2). TradingView's session alignment for NSE 75/125-min bars must be verified. |
| **B9** | **Deterministic entry/SL buffer values** | Only ranges exist (D7). Tier edges overlap. The price that selects the tier is unstated. Volatility adjustment is +50–100%. A backtest needs one price per trade. | RB 305, 332, 351, 2010–2022, 2097–2110 | Backtest fills | **Validation** (the scanner reports ranges) | A user-defined backtest rule, recorded as a user decision, or reporting at both range bounds |
| **B11** | **Point-in-time Nifty 100 membership; delisted/merged data** | Survivorship bias | D1 | Universe; validation | **Validation** | Dated membership from NSE Indices announcements; history for removed securities |
| **B12** | **Backtest execution assumptions** | The rulebook is silent on gap fills, same-bar entry/SL, costs, price bands | RB 2141 only | Validation engine | **Validation** | User-approved modelling assumptions; costs sourced from official schedules |
| **B15** | **Intraday history depth for WIT validation** | Validating WIT needs long 75/125-min history. Vendor intraday depth is unverified. | D16, D17 | WIT validation | **Validation** | Confirm available intraday history; set the validation window accordingly |
| **B17** | **Validated NSE trading calendar** | Without it, D28 applies: a period completes only when the next period's data arrives (one session late), and every missing weekday is an unverified gap, so zones spanning holidays become UNKNOWN_DATA_GAP (measured in the Phase 1 audit: no untouched W/M zone stays fresh on synthetic data with ~15 weekday holidays a year). Weekday Muhurat and shortened sessions are undetectable without it (D33). Holiday and special-session handling is unvalidated. | D28 (A5); RB 186, 3323 | Candle construction, period completion, data-gap detection | **Scanner** (production use), **Validation** | Obtain an official NSE holiday/session calendar; validate boundaries and holidays against exchange data and TradingView. Not production-ready until done |
| **B18** | **NSE CM EOD file formats unconfirmed** (added 2026-10-27) | Column names, date formats, series values and the timestamp convention of the legacy CM bhavcopy (`cmDDMMMYYYYbhav.csv.zip`) and of the UDiFF common bhavcopy (reported from 2024-07-08, unverified) are unconfirmed (`DATA_REQUIREMENTS.md` §2.1). No EOD loader can be built before the formats are reported (D31), and every D/W/M candle depends on daily data. | D31; `DATA_REQUIREMENTS.md` §2 | EOD loader; daily candles and everything built from them | **Scanner**, **Validation** | One sample file per format, stored with SHA-256, and its actual header and sample rows documented. The legacy format alone suffices for the bounded 2022-2023 experiment; UDiFF is needed after the legacy-to-UDiFF switch (reported as 2024-07-08, but unverified). **Legacy-format evidence recorded for 2022-01-03 and 2023-12-29 (`EOD_FORMAT_EVIDENCE.md`, `nse/data/eod/manifest.csv`); provenance of the two original ZIP archives is user-confirmed (official NSE website, downloaded 2026-10-27), not independently authenticated; the user accepted this two-sample evidence with limitations (2026-10-27). Still open: format continuity across 2022-2023 is not proven by two samples; UDiFF and its switch date are unverified; no Muhurat sample; no independent cross-check (B8, B10); prices unadjusted (B7).** |

---

## Part 3: Not blocking (manual-review treatment defined)

| ID | Issue | Phase 1 treatment |
|---|---|---|
| N1 | Sector alignment (D6) | *Not evaluated (max +2)*; sector-dependent rules → manual. Never a silent pass. |
| N2 | Weekly trailing (D9) | Reference distal lines only |
| N3 | HTF conflict 5–10% band; Weekly/Yearly/tested opposing zones (D12, PR11) | Manual-review evidence |
| N4 | Coinciding "touching" tolerance; aggressive achievement (D15) | Manual |
| N5 | HTF EMA20, crossover, gap application, RSI/Stochastic | Provisional or not evaluated; manual |
| N6 | Window-gap double count (Strength vs CF4) | Provisional; unresolved |
| N7 | Explosive relative size and context (D8) | Manual item on every candidate |
| N8 | Authenticity, garbage chart, "came from", LOTL, Confirmation Entry | Evidence shown; manual |
| N9 | MTFA matrix missing cells | Manual |
| N10 | Target quality, target buffer, Weekly vs Monthly target | Manual |
| N11 | Insufficient-history trends | "Insufficient history"; manual |
| N12 | High-priority "2+ failures → reconsider" | Count shown; manual |
| N13 | Rulebook editorial errors | Documented |
| N14 | Pine realtime / drawing-limit behaviour | Completed candles only; compare values |

---

## Part 4: Decisions still required before reliable implementation

### 4A. Decisions requiring the user's input
1. **B9:** a backtest buffer rule (only if deterministic historical validation is wanted).
2. **B12:** backtest execution assumptions.

No other user decision is outstanding. B13 and B14 were resolved by D21 and D22; the B8 approach was decided by D23.

### 4B. Source ambiguities requiring manual review
These are not blockers; the scanner flags them per case (D12).
- **Candle and zone mechanics:**
  - candle strong only via `close > high[1]` (PR1);
  - transition-candle base count changing the score band (PR4);
  - non-consecutive or frozen leg-out counts (PR5);
  - gap meaningfulness (PR6);
  - PL touch inside the pending window (PR10);
  - pending zone whose failed first leg-out may count as a second explosive candle (PR18, `PENDING_LEGOUT_COUNT_AMBIGUOUS`);
  - non-achieving patterns used as HTF context (PR3).
- **Trend:**
  - clock bands "1", "2", "2–3" and "3–4" where the matrix outcome depends on them (D14);
  - insufficient history on a **gating** trend (MIT Weekly, WIT Daily);
  - RB 1232 "extreme caution" cases, and whether Sideways or ambiguous Weekly readings "oppose" the Monthly location bias (D21);
  - WIT cases that rest on matrix rows phrased around Monthly/Quarterly zones or Daily charts (RB 1892, 2593–2598) (D22).
- **HTF candles:** zones or trends that depend on a `partial_listing_period` candle (D23).
- **HTF conflict:** 5–10% band; Weekly, Yearly and tested opposing zones (PR11).
- **Coinciding:** LTF PL above HTF PL; aggressive achievement; coinciding zone ≠ curve boundary (D15).
- **WIT:** recency 9+ candles; weekly DZ near a Monthly SZ; simultaneous 75/125 candidates (D16).
- **Scoring context:** sector-dependent rules (D6); explosive relative size and context (D8); matrix gaps (N9); target quality and target buffer (N10); RF3 "10/10" override; 6/7 override; authenticity, garbage chart, LOTL, "came from" (N8).

### 4C. External technical checks
- **B6 Kite Connect:** history depth per interval; supported intervals; access requirements; adjustment; rate limits; storage licence; reliable construction of 75/125-min candles (granularity, 09:15 alignment, session completeness). No credentials or connections until the user explicitly approves implementation.
- **B7:** corporate-action adjustment source.
- **B8:** TradingView verification of D23 calendar boundaries and HTF candle values (open until comparisons are recorded).
- **B10:** TradingView parity references, including NSE 75/125-min bar alignment on TradingView.
- **B18:** NSE CM EOD file formats (legacy and UDiFF): legacy-format evidence recorded for two dates (`EOD_FORMAT_EVIDENCE.md`); provenance of the two original ZIP archives is user-confirmed (official NSE website, downloaded 2026-10-27), not independently authenticated; the user accepted this two-sample evidence with limitations (2026-10-27). **Update 2026-10-28:** the strict loader (`nse/eod/nse_bhavcopy.py`, which refuses any deviation from the recorded format) also accepts all 61 official Q1 2022 files (manifest committed in 9e302df). **Still open:** format continuity for the rest of 2022-2023 is not proven; UDiFF and its switch date are unverified; no Muhurat sample; no independent cross-check (B8, B10); prices unadjusted (B7). UDiFF: no sample inspected. Separate from B6, which covers Kite Connect capabilities only.
- **B17:** NSE trading calendar: **loader built and tested** (`nse/calendar/nse_calendar.py`). **2021-2025 (the whole D29 window) transcribed** from official NSE circulars (D40, proposed wording pending review): 5 base circulars, 4 amendments and 10 session notices, 105 events, in `nse/data/calendar/sources.csv` and `events.csv` (list in `nse/data/calendar/README.md` §1). The circular files are local only and hash-verified. Tests: `tests/test_nse_calendar_data.py` (independent second transcription).
  - 2023 Bakri Id is resolved by NSE/CMTR/57285: 28 June 2023 is a normal session and 29 June a holiday.
  - Special sessions under D30: 20 Jan 2024 and 1 Feb 2025 are regular-hours Saturdays (`NORMAL_SPECIAL`, provisional rule); the 2 March and 18 May 2024 DR-switch sessions are shortened and excluded; five Muhurat sessions (2021-2025) are excluded.
  - Q1 2022 (2022-01-03 to 2022-03-31) reconciles cleanly with the 61 official EOD files. Its manifest rows are committed (9e302df; this note said "working tree, not committed" until 2026-11-06). The raw archives themselves are local files, so a checkout without them reports a missing prerequisite instead of running.
  - **Still open:**
    - TradingView boundary and holiday validation (with B8).
    - Normal hours 09:15-15:30: provisional, from NSE/CMTR/41180 (2019) and corroborated by NSE/CMTR/65729 (2024); no systematic review of timing circulars in between.
    - Completeness: a missed amendment or session is caught only by reconciliation with EOD files, which exist for Q1 2022 and 2023-12-29 only.
  - The official Nifty 100 constituent file: not yet obtained.

### 4D. Historical-data and backtesting validation
- **B11:** point-in-time Nifty 100 membership and delisted/merged history.
- **B15:** intraday history depth for WIT.
- **B9, B12:** buffer determinism and fill/cost assumptions.
- Any backtest on today's constituents is survivorship-biased and is **not** validation evidence.

---

## Part 5: Readiness summary

| Area | Status |
|---|---|
| Documentation | ✅ D1–D17 and D21–D39; D40 remains proposed, pending review (D30 special-session rule approved provisionally; two regular-hours Saturdays are registered from official circulars, none verified against EOD files or TradingView); M1 R1-R6 approved 2026-11-02 |
| Scanner implementation | **Built 2026-10-29 (`nse/research/`), software-tested, outputs not externally validated.** Needs B6 (data source), B18 (EOD file formats), B7 (adjustment), B8 + B10 (TradingView verification) and B17 (validated NSE calendar) before outputs can be trusted. B16 is implemented. M1 R1-R6 are approved and have focused regression coverage; other D41 readings remain as listed in the Decision Register. |
| Historical validation | ⛔ **Not ready.** Additionally needs B9, B11, B12, B15. |

**Implementation status (2026-10-28):** Phase 1 in progress; external validation pending.
- **Zone Engine** (`nse/zone-engine/zone_engine.py`, 64 synthetic tests in `tests/test_zone_engine.py`): single-timeframe detection, scoring, freshness, invalidation and zone-level eligibility. All 13 audit mutations and the P12 ambiguity are caught; the M3 ambiguity is recorded for manual review (D35). Input validation gaps L1-L3 fixed 2026-10-28 (working tree).
- **HTF freshness orchestrator** (`nse/mtf-freshness/mtf_freshness.py`, 43 synthetic tests in `tests/test_mtf_freshness.py`): implements B16 under D24-D28, D33-D34 and D36-D39. It applies completed finer candles to W/M/Q/HY/Y and D zones (D from an intraday base, or from a daily base under D38); it never adds eligibility, only removes it (`eligible_after_overlay`). 18 original targeted mutations and 15 from the correctness audit are caught.
- **Phase 1 correctness audit:** `PHASE1_CORRECTNESS_AUDIT.md`. Verdict: NOT READY TO DECLARE COMPLETE. The remediation is committed (`b7a51cc`, `bdaa09d` for L4/L10; calendar infrastructure in `d72415f`). Candidates must come from `eligible_after_overlay`, never from the engine's `eligible` alone (audit M4); `tests/test_repo.py` now fails if any other NSE module reads the engine's `eligible` or imports network code.
- **Real-data pipeline check (working tree):** the 61 official Q1 2022 bhavcopies, the official calendar and the orchestrator replay INFY with no gap, and all 61 daily bars match the recorded Yahoo Finance reference (`tests/test_nse_replay.py` `RealInfyQ1Of2022`). Yahoo republishes exchange data, so this checks transcription and the pipeline; it is not independent or TradingView validation.
- Neither component is validated against TradingView (B8, B10) or on corporate-action-adjusted data (B7), and the calendar is not externally validated (B17).

**Update 2026-10-29: research pipeline built (post-Phase-1 work requested in `CLAUDE.md`).**
- Trend, location, HTF conflict, coinciding, trade levels and R:R, G0-G8, the scanner, reports and a validation runner now exist: `nse/research/`, `nse/validation/`.
  - Architecture, commands and the PROPOSED interpretations (D41): `RESEARCH_PIPELINE.md`.
  - Rule-to-test mapping: `TRACEABILITY.md`.
- They are software-tested only: synthetic gate, integration, lookahead and adversarial tests, plus one run on the official Q1 2022 files. **Their outputs are restricted:** no status approves a trade, every record carries NOT_EXTERNALLY_VALIDATED, and WIT is BLOCKED.
- The external blockers above (B6-B12, B15, B17, B18) are unchanged. Phase 1 acceptance is unchanged (`PHASE1_EXIT_CHECKLIST.md`).

## Part 6: Research-pipeline items (2026-10-29)

**Second pass, 2026-10-29.** The full human decision register is `DECISION_REGISTER.md`.
- R7: the history needed per as-of is now measured by `cli inventory`.
- R9: an interface exists. A corporate action inside the history makes G0 MANUAL.
- R13: backtest infrastructure exists. It needs a user execution model before any run.
- The real-replay gap is closed: `test_research_e2e` reaches ACTIONABLE on synthetic data.

Readiness: **USER_APPROVED** (methodology approved), **IMPLEMENTED** (code and focused tests present), **OPEN-DECISION** (user decision needed), **OPEN-EVIDENCE** (external data or records needed), **DEFERRED** (out of scope), **RESTRICTED** (code keeps the output from passing until resolved).

| ID | Issue | Component | Consequence if wrong | Current restriction | Evidence or decision needed | Validation method | Readiness |
|---|---|---|---|---|---|---|---|
| R1 | CMP alone determines curve position (P-LOC-1) | `_g3`, `_g4` | Execution PL could otherwise move the matrix row | HOC at CMP applies even if PL is LOC | Owner approved 2026-11-02 | `G3`, e2e | USER_APPROVED, IMPLEMENTED |
| R2 | 12 o'clock maps to STRONG_UP; preserve Extreme Uptrend label (P-TREND-1) | `trend.READINGS`, `trend_for`, reports | Extreme trend could pass a Strong Up row | Label remains visible in diagnostics/reports | Owner approved 2026-11-02 | Trend, gate, report tests | USER_APPROVED, IMPLEMENTED |
| R3 | Coinciding uses inclusive actual price-range overlap; Aggressive is distinct (P-COIN-1) | `structure.coinciding`, `_g6` | PL-only comparison conflates overlapping and above-PL cases | Aggressive remains MANUAL pending its distinct Rulebook conditions | Owner approved 2026-11-02 | overlap / non-overlap / D15 tests | USER_APPROVED, IMPLEMENTED |
| R4 | Completed own-timeframe close beyond DL invalidates; record active-trade SL separately | Zone Engine, MTF overlay, backtest | Wick, invalidation and SL events could be conflated | Wick-only remains non-invalidating; SL and zone events separate | Owner approved 2026-11-02; consistent with D24 | invalidation, MTF and backtest tests | USER_APPROVED, IMPLEMENTED |
| R5 | HOC + Up rejects; HOC + Sideways is manual; HOC + Down follows RF3 | `matrix_long`, `_g3`, `_g8` | HOC exception could be invented or RF3 bypassed | Sector exception remains unevaluated | Owner approved 2026-11-02 | matrix and final-status tests | USER_APPROVED, IMPLEMENTED |
| R6 | Known absence passes G6 as Standard; unknown remains manual; G3 stays independent | `_g6`, `_g3` | G6 pass could be mistaken for overall qualification | G3 and final status remain authoritative | Owner approved 2026-11-02 | G3/G6 tests | USER_APPROVED, IMPLEMENTED |
| P-LOC-2 | Price inside tested HTF demand: VLOC or redraw | `structure.build_curve` | Curve location at an in-progress tested boundary remains ambiguous | Monthly: redraw from the next fresh Monthly demand below; unknown boundary MANUAL; W and supply MANUAL | Resolved: USER_APPROVED 2026-11-08 (redraw; DECISION_LOG 1F) | `G3.test_price_inside_a_tested_monthly_demand_redraws_from_the_next_fresh_zone`, `G3.test_redraw_*` | RESOLVED, RESTRICTED |
| R7 | History depth: Y needs 3 completed years, HY/Q 3 periods, the Weekly trend 55 weeks | data | Nothing can be ACTIONABLE on short history | G5 DATA_INSUFFICIENT or MANUAL; G4 MANUAL | Approval to download 2021-2025 EOD files (D31); UDiFF sample (B18) | `run_all` local_data reconciliation, then a scan | OPEN-EVIDENCE, RESTRICTED |
| R8 | Nifty 100 constituent file and history (D1, B11) | `universe.py` | Wrong or survivorship-biased universe | Every scan is UNIVERSE_UNVERIFIED | Official NSE Indices files with dates | `test_research_reports.Universe`, then a scan with `--universe` | OPEN-EVIDENCE |
| R9 | Corporate actions (B7) | data | False zones and breaches around splits and bonuses | CORPORATE_ACTIONS_UNVERIFIED on every record; manual checklist item | Adjustment source and convention | Known split or bonus dates compared before and after adjustment | OPEN-EVIDENCE |
| R10 | Score /14 extras: EMA20, crossover, RSI/Stochastic, gap application (spec 5.1) | `confluence.py` | A provisional point could be read as judged | Display only, PROVISIONAL / NOT_EVALUATED labels; no gate reads it | TradingView EMA comparison (B8) | `test_research_confluence` | IMPLEMENTED (display), RESTRICTED |
| R11 | WIT weekly DZ vs Monthly SZ (RB 1402) branch untested | `_g5` | Mistake hidden while WIT is blocked | WIT BLOCKED | Test once M4b is approved | Unit test with a 75m snapshot | DEFERRED |
| R12 | Intraday 75/125-minute session and gap design (audit M4b) | overlay, WIT | Wrong intraday freshness | WIT BLOCKED everywhere | User approval of a design | Synthetic, then TradingView (B10) | DEFERRED |
| R13 | Backtesting: fills, costs, outcome evaluation (B9, B12) | not built | No performance evidence | `scan_history` gives signals only; no metrics | User-approved execution and cost model | Reproducible run on point-in-time data (B11) | DEFERRED |
| RB-VERSION-1 | The root Rulebook PDF and the protected Markdown are different revisions (PDF lacks RB 1784 and RB 1786-1803, section 3.4) | Methodology sources; WIT G1 recency | A rule cited from one revision may not exist in the other | Code cites the Markdown; WIT BLOCKED; no MIT gate depends on the differing text | Owner states which revision is authoritative | Re-run the PDF/Markdown comparison after any new export | OPEN-DECISION |

## Part 7: Evidence blocker status (council audit 2026-11-08)

Inventory read from the local files; nothing was downloaded. SHA-256 values were computed on
2026-11-08. Synthetic tests are not evidence for any of these blockers.

| ID | Held now | Missing | Readiness | Smallest owner action |
|---|---|---|---|---|
| B18 (UDiFF) | 64 files in `nse/data/eod/raw`: Jan-Mar 2022 legacy bhavcopies plus cm29DEC2023 (csv and zip); `manifest.csv` sha256 `6bb670706d643ab77a61ce0cdae9aa536c107d9e660547269158648e97880189` | Legacy files Apr 2022 - Nov 2023; any UDiFF sample; an official source for the switch date | BLOCKED (no UDiFF parser evidence) | Place one official UDiFF CM bhavcopy from after the switch, the NSE page or circular naming the switch date, and the remaining 2022-2023 legacy ZIPs in `nse/data/eod/inbox` |
| B11 (constituents, identity history) | Nothing (no membership or instrument-record file) | Dated Nifty 100 membership; delistings, mergers, symbol changes | BLOCKED; scans are labelled UNIVERSE_UNVERIFIED / SURVIVORSHIP_UNCONTROLLED | Supply the NSE Indices reconstitution notices for the window and a membership CSV citing them (`universe.py` format) |
| B7 (corporate actions) | No corporate-actions file; PREVCLOSE discontinuities are detected (one in Q1 2022, SETFGOLD, unverified) | Split / bonus records with ex-dates; an adjustment policy | BLOCKED; G0 MANUAL when a price-scale event is inside the history (P-CA-1/2) | Supply NSE corporate-action records (ex-date, ratio, source document) for the scanned symbols |
| B8 / B10 / B17 (TradingView parity) | Templates only; `INFY/ohlc_reference.csv` (sha256 `09bed3ef2f12b554204638d5ac30f3ff149edc36c4c42b03189eaa3258e0549d`) is transcribed from Yahoo screenshots with adjustment UNKNOWN, so it is not independent. Calendar `sources.csv` `726bec6521671a0590ed6f944a28bbfb6a036f23d5d5a87da5fe15c841435185`, `events.csv` `e05a87a9c8ce30dff64503e1c3f0fecacba75d91d2250b08793f604994933a12` (after the 2026-11-08 row-61 note correction; was `4fcc32bb...0a850a72`) | Any recorded TradingView OHLC, trend or zone observation | NOT EXTERNALLY VALIDATED | Record TradingView D/W/M/3M/6M/12M OHLC and indicator zones for INFY 2022 into the reference templates (`REFERENCE_VALIDATION_PLAN.md`) |
| B6 / B15 (intraday, WIT) | Nothing | Intraday data; Kite interval and history-depth evidence | BLOCKED (WIT stays BLOCKED, M4b) | Confirm the Kite subscription and the supported intervals / history depth from the official documentation; no credentials in the repository |
| D40-Q1 | Calendar evidence above | Contents of the withdrawn NSE/MSD/59999, 60300, 60318 | RESOLVED by evidence (`REAL_DATA_READINESS.md` §1) | Optionally hold those three circulars to close the 20 Jan 2024 trail |

## Part 8: Real-data readiness milestone (2026-11-08)

Full detail and the acquisition priority list: `REAL_DATA_READINESS.md`.

| ID | Status after the milestone | Evidence added | Next owner action |
|---|---|---|---|
| EOD range | BLOCKED for any full-year window: 62 of 492 trading days in 2022-2023 are held; 430 missing (2022-04-01 to 2023-12-28) | `eod-coverage` report: 64 / 64 files load; 2 identical duplicates; 0 invalid records | Place the 430 legacy bhavcopies in `nse/data/eod/inbox` |
| B18 | BLOCKED | Requirements for one sample and the acceptance checks (`REAL_DATA_READINESS.md` §4) | One official UDiFF sample + the switch-date circular |
| B11 | BLOCKED | Reconstitution schema and validation rules (§5); overlapping membership is now refused and members without data are reported (ED-13) | NSE Indices notices + one baseline list |
| B8 / B10 / B17 | BLOCKED | INFY observation matrix P1-P10 and the Pine settings list (§6) | TradingView exports for INFY Q1 2022 |
| D40-Q1 | RESOLVED (factual correction) | Two independent hash-verified reviews | none required |
| Costs (B12) | Structure documented; percentages only | Gap report (§8); realism gaps on every result (ED-12) | A dated Zerodha schedule with sources; a decision on RPT / capital in backtests |

## Part 9: Master Prompt 1 (real NSE data readiness), 2026-11-09

The status classes are the prompt's own:

| Class | Meaning |
|---|---|
| ENGINEERING_COMPLETE | the code is built and tested |
| EVIDENCE_BLOCKED | waiting for documents |
| DATA_INSUFFICIENT | waiting for market data |
| MANUAL | a human must review |
| LIVE_VALIDATION_PENDING | needs a check against live or external tools |

Evidence paths: `nse/data/eod/evidence/`, `nse/data/universe/evidence/`, `nse/data/calendar/circulars/`, `nse/data/corporate_actions/raw/`.

| ID | Status | Exact missing evidence | Why it is needed | Affected capability | Current limitation | What closes it | Engineering continues? |
|---|---|---|---|---|---|---|---|
| B18 (UDiFF) | ENGINEERING_COMPLETE for the switch and the two observed schemas (ED-20) | When UDiFF was first published (circulars 61787, 62142, 59694 not read). Continuity on unsampled dates | A third header variant would be refused | EOD ingestion after 2024-07-08 | Any unseen header is refused and quarantined (fail-closed) | One sample of each new variant, if one appears | Yes |
| DATA-1 (EOD backfill, D31) | DATA_INSUFFICIENT | 1,171 of 1,233 trading days in 2021-2025 have no accepted file: 247 in 2021, 186 in 2022, 244 in 2023, 246 in 2024, 248 in 2025 | Zones, the Weekly/Monthly curve and SMA-50 need continuous history | scans, scan history, backtest | `research_ready` is false; 62 accepted dates (5.03%) | Owner downloads the listed files into `nse/data/eod/inbox` and runs `acquire-ingest` (list: `acquire-plan`; names per ED-20) | Yes |
| CAL-1 (calendar before 2021) | EVIDENCE_BLOCKED and owner decision (D29 window) | The NSE holiday circulars for 2016-2020 and any special-session notices | Ten-year history cannot classify a date without them; a weekday is never assumed to trade | coverage, acquisition plan, replay before 2021 | Dates before 2021 are `CALENDAR_UNVALIDATED` and never called missing | Owner approves extending the D29 window; the circulars are added to `nse/data/calendar/` | Yes |
| B11 (Nifty 100 history) | EVIDENCE_BLOCKED (partial evidence held), then MANUAL | Held: the dated list as of 31 Mar 2022 (100 symbols, no ISINs) and 10 releases from Feb 2021 to Aug 2025. Missing: a human-reviewed transcription; the Aug 2021 list (image-only PDF); ad-hoc changes (e.g. the Jio Financial spin-off, 2023); 2016-2020 releases; an ISIN for every member | Survivorship-free universe at each date | universe, scan history, backtest | Every scan is `UNIVERSE_UNVERIFIED` | Transcribe the baseline and changes in the `membership.py` schema (declare the Aug 2023 count of 101), review against the PDFs, convert, then hash-check | Yes (converter built, ED-22) |
| B7 (corporate actions) | EVIDENCE_BLOCKED and owner decision | Held: NSE corporate-action API responses for INFY and RELIANCE, 2016-2025. Missing: records for every universe symbol, a completeness check, structured ratios (the API gives free text), and an adjustment policy | Raw prices are unadjusted; a split inside a history distorts zones | G0 corporate-action handling | `CORPORATE_ACTIONS_UNVERIFIED`; a PREVCLOSE discontinuity is flagged; G0 MANUAL when a recorded action falls inside the history | Per-symbol records (ex-date, ratio, source) in the `corporate_actions.py` format; an owner decision on adjustment | Yes (raw OHLC preserved) |
| B8 / B10 / B17 (TradingView parity, INFY) | LIVE_VALIDATION_PENDING and EVIDENCE_BLOCKED | Any TradingView export: INFY D/W/M/3M OHLC for Q1 2022 and 2023-12-29, SMA-50, and indicator zones, with chart settings (`REAL_DATA_READINESS.md` §6, P1-P10) | External check of candles, trend and zones | reference comparison | `TRADINGVIEW_PARITY_UNVERIFIED` on every result; no comparison exists | Owner exports from TradingView (Claude never reads values off a chart) | Yes |
| D40-Q1 | RESOLVED by evidence (trail closed 2026-11-09) | Only the printed 20 Jan 2024 clock times (inferred as 09:15-15:30) | Normal-hours classification of that day | calendar | None in practice: the day is a regular session (D30 provisional rule) | None needed | Yes |
| B6 / B15 (intraday, WIT) | EVIDENCE_BLOCKED (unchanged) | Intraday data and Kite interval evidence | WIT | WIT stays BLOCKED | - | Owner (D32) | Yes |

**MP1 limits on what was verified.**
- **EOD (ED-23):** every EOD sample and circular is official and hash-recorded, but none has been compared with an independent source (TradingView, a broker or a vendor).
- **Universe:** the extracted content in `nse/data/universe/evidence/sources.csv` is labelled unreviewed.
- **Corporate actions:** the API responses cannot be re-fetched byte-identically, so their URL is the one the retrieving agent reported.

## Part 10: After the owner decisions D47-D51 (2026-11-09)

| ID | Status | Exact missing evidence | Why it is needed | Affected capability | Current limitation | What closes it | Engineering continues? |
|---|---|---|---|---|---|---|---|
| DATA-1 (EOD 2021-2025) | **CLOSED for EOD files (D47, ED-25)** | none for 2021-2025 | - | scans, history, backtest | 210 non-EQ rows isolated in 112 files (ED-30) | - | Yes |
| DATA-2 (EOD 2016-2020) | DATA_INSUFFICIENT | 2016-2020 bhavcopies. D47 covers 2021-2025 only, and D48 extends calendar and readiness work, not downloads | Ten-year history; Monthly / Yearly context before 2021 | Monthly zones, SMA-50 clock, `inventory` M/Q/HY/Y readiness | `inventory` reports Monthly not ready for 2021-2022 as-of dates | An owner approval extending D47's download scope to 2016-2020 | Yes |
| CAL-1 (calendar 2016-2020) | **ENGINEERING_COMPLETE (D48, ED-26)**, 4 dates MANUAL | none, apart from CAL-2 | - | calendar | Pre-2021 dates not reconciled with EOD files (DATA-2) | - | Yes |
| CAL-2 (Dhanteras 2016-2019) | **CLOSED 2026-11-10 by D58** (was MANUAL, owner decision) | A ruling on 2016-10-28, 2017-10-17, 2018-11-05, 2019-10-25: regular 09:15-15:30 plus an evening session for Gold ETFs / SGBs only | No event type describes an instrument-limited session | calendar answers for those 4 dates | Closed by D58. No UNRESOLVED row remains. ED-31 and ED-44 still apply to any future unresolved date | Owner chooses NORMAL_SPECIAL, or no row, for equities | Yes |
| B11-R (Nifty 100 review) | MANUAL (D49 human review) | One ACCEPTED row in `nse/data/universe/nifty100_review.csv` covering the current file hashes | D49 review gate | universe | 171 periods UNVERIFIED; every scan `UNIVERSE_UNVERIFIED` | Review per `nse/data/universe/README.md` | Yes |
| B11-I (identity gaps) | EVIDENCE_BLOCKED | Official evidence linking old and new ISINs for 13 members (HAL, TATASTEEL, DRREDDY, VBL, KOTAKBANK, NESTLEIND, BAJFINANCE, CANBK, NAUKRI, SHRIRAMFIN, JUBLFOOD, ADANIPOWER, BAJAJFINSV); listing records for 4 no longer listed (HDFC, MINDTREE, PEL, TATAMTRDVR) | D51: continuity only through verified ISIN evidence | identity with `--instruments` | DATA_INSUFFICIENT from the first unexplained date | NSE ISIN-change or corporate-action records (ex-dates) for those symbols, with source files | Yes |
| B11-P (pre-2021 membership) | EVIDENCE_BLOCKED | 2016-2020 releases and a dated baseline (official dated lists exist for Mar 2019 to Mar 2022) | Survivorship-free universe before 2021 | universe | Membership starts 2020-12-31 | Transcribe 2016-2020 under D49 (the converter rolls forward from an earlier baseline) | Yes |
| B7 (corporate actions) | PARTIAL (D50 policy implemented, ED-28) | Event records for every member (held: INFY, RELIANCE) | Price-scale events inside histories | G0 MANUAL coverage | `CORPORATE_ACTIONS_UNVERIFIED` except for held records; prices never adjusted | Approval to collect NSE corporate-action records for the universe (not covered by D47) | Yes |
| B8 / B10 / B17 | LIVE_VALIDATION_PENDING | TradingView exports | external parity | reference comparison | unchanged | Owner exports | Yes |
| DQ-1 (Muhurat PREVCLOSE) | MANUAL (owner decision) | A rule for discontinuities explained only by an excluded session | Detector cannot tell a Muhurat close from a corporate action | G0 for every real-data history since Nov 2021 | Every such G0 MANUAL (fail-closed); nothing ACTIONABLE on real data | Owner decision DQ-1 (`DECISION_REGISTER.md`) | Yes |

**DATA_READY: not claimed.** EOD files 2021-2025 and the 2016-2025 calendar have passed validation. The universe is unreviewed (B11-R) and identity has documented gaps (B11-I). That is the owner's standing condition of 2026-11-09.

## Part 11: After the owner decisions D52-D56 (2026-11-09)

Supersedes the Part 10 rows it names. Three kinds of status are kept apart: engineering (code and tests), data (evidence held and accepted) and research validation (none claimed).

| ID | Status | Exact missing evidence | Current limitation | What closes it | Engineering continues? |
|---|---|---|---|---|---|
| DQ-1 (excluded-session PREVCLOSE) | **CLOSED (D52; ED-33, ED-34)** | none: NSE serves the 12 Muhurat / DR-switch bhavcopies of 2016-2025, now held as `EXCLUDED_SESSION_D33` | Where such a file is missing, a discontinuity is explained only under the strict D52 conditions; an unobserved excluded session inside a zone's span makes G1 MANUAL | - | Yes |
| DATA-2 (EOD 2016-2020) | **CLOSED (D55)** | none: 2,466 of 2,466 calendar equity sessions 2016-2025 ACCEPTED (2,462 before D58 confirmed the four Dhanteras dates) | 2 files needed exact layout variants (ED-38) | - | Yes |
| CAL-2 (Dhanteras 2016-2019) | **CLOSED 2026-11-10 by D58 (option A: confirmed regular equity sessions).** Before that: UNRESOLVED by owner decision (D54) | none for these four dates. The held circulars print "Regular Market Timing (there is no change to this)" plus a Gold ETF / SGB-only evening session | The four dates are CONFIRMED, 09:15-15:30, `NORMAL_SPECIAL`, and their archives are accepted equity sessions. ED-44 still applies to any future UNRESOLVED date. Before D58 the files stayed VALIDATED and a scan restarted after 2019-10-25 | Closed by D58 | Yes |
| B11-R (Nifty 100 review) | **MANUAL: awaiting human review (D53, ED-35)** | A human decision on each of the 271 rows of `nse/data/universe/nifty100_review.csv`; the verifier's packet (`nifty100_review_packet.csv`) is advisory | 185 periods UNVERIFIED; every scan `UNIVERSE_UNVERIFIED` | Human row-level review (README there) | Yes |
| B11-I (identity gaps) | **CLOSED except three (D56, ED-37)** | Official documents for three ISIN changes: BAJFINANCE 2016-09-09 and GRASIM 2016-10-07 (each split's printed record date is the Saturday after the change, so a date match would be an inference), and YESBANK 2020-03-16 (no official price event held) | Those histories are not joined across the change (`ISIN_CHANGED_WITHOUT_RECORD`, DATA_INSUFFICIENT across it) | Official NSE / exchange documents for those changes | Yes |
| B7 (corporate actions) | **DATA COLLECTED (D56, ED-39); completeness unverified** | An independent check of the NSE API's completeness (R-10) | 47 latest responses are HTTP 200 body `[]` and are not coverage, including `SRTRANSFIN` collected 2026-11-10. 141 symbols have parsed events. 4 more are AGM-only. 10 `UNPARSED_PRICE_EVENT` keep G0 MANUAL. An empty list is not proof that no action occurred | Optional independent source | Yes |
| B11-P (pre-2021 membership) | EVIDENCE_BLOCKED for a pre-2020 baseline. D59 (2026-11-10) limits membership-based research to 2020-12-31 onward without certifying it | 2016-2020 releases and dated lists, if a study before the provisional window is wanted | Membership-based research before 2020-12-31 is labelled `MEMBERSHIP_BEFORE_PROVISIONAL_WINDOW`. EOD before that date may warm indicators. It is not a survivorship-controlled universe | A transcribed official baseline under D49, if the window is to move earlier | Yes |
| B8 / B10 / B17 | LIVE_VALIDATION_PENDING (unchanged) | TradingView exports | no external parity | Owner exports | Yes |

**DATA_READY: not claimed.** EOD 2016-2025 is held and every equity session has an accepted archive. Regenerated `eod-coverage` for 2016-01-01..2025-12-31 on 2026-11-10: 2,466 of 2,466 equity sessions, 12 excluded sessions, `eod_ready` true, `data_ready` false. The acceptance criteria still fail because the universe has no human review (B11-R). Research validation: none; no result is evidence of profitability.

## Part 12: PROMPT-01 certification (2026-11-09)

Gate results: `REAL_DATA_READINESS.md` §0C. **DATA_READY: not claimed. Verdict: PARTIALLY_READY.**

| ID | Severity | What is missing | Why it matters | Evidence or change needed | Responsibility |
|---|---|---|---|---|---|
| B11-R | Blocks Gate C | Human decisions on the 271 rows of `nifty100_review.csv` | No point-in-time universe can be certified | Row-level review (D53) | Owner |
| P01-H1 | HIGH (invariant) | **CLOSED (ED-46).** G0 is MANUAL: `CORPORATE_ACTION_COVERAGE_UNKNOWN` when no coverage is supplied, `CORPORATE_ACTION_COVERAGE_UNVERIFIED` when the replayed span is outside a hash-verified window | An empty event list or an empty official response is not that window. A verified window with no recorded price-scale action can still pass this check. NSE does not adjust PREVCLOSE, so the discontinuity detector stays active | `test_research_gates.G0.test_corporate_action_coverage_unknown_unverified_and_covered` | Prompt 02, directed in the closure review |
| P01-H2 | MEDIUM | **CLOSED (ED-46).** `run_manifest.scan_input_paths` fingerprints `--instruments` and `coverage.csv` beside the corporate-action file | Changing either file changes `dataset_sha256` | `test_research_run_manifest.Manifest.test_identity_and_coverage_files_change_the_dataset_fingerprint` | Prompt 02 |
| P01-H3 | MEDIUM | **CLOSED (ED-46), no behaviour change to ED-33, ED-43 or ED-44.** ED-40's loader is unchanged; its "behaviour unchanged without the flag" clause is superseded only for the G0 result | The four edits still match their recorded decisions. See ED-46 | Code re-read of `scanner.py`, `inputs.py`, `mtf_freshness.py` `_build_series` | Prompt 02 |
| P01-H4 | LOW | **CLOSED (ED-46).** An unverified universe file, not only an ad-hoc list, adds `SURVIVORSHIP_UNCONTROLLED` | A reviewed file with every row verified does not add it | `test_research_backtest.EndToEnd.test_a_synthetic_trade_from_a_point_in_time_signal` | Prompt 02 |
| R-10 / B7 | MEDIUM | CA records for 46 symbols whose official API response is empty (retried; includes live symbols ICICIPRULI, ETERNAL, PAYTM, SWIGGY) | Those symbols are uncovered: no D52 explanation, no proof of absence | Another official NSE CA source (e.g. the corporate announcements archive), approved by the owner | Owner / data workstream |
| B11-I (rest) | Contained | Official documents for BAJFINANCE 2016, GRASIM 2016 and YESBANK 2020 ISIN changes | Those histories are not joined | NSE notices | Owner / data workstream |
| CAL-2 | **Closed (D58, 2026-11-10)** | n/a: the owner classified the four Dhanteras dates as regular equity sessions | The ED-44 cut no longer applies; history from 2016 is used | n/a | n/a |
| PROV-1 | LOW | Download-log entries for 62 archives (Q1 2022 batch, 3 owner files) | Provenance rests on the manifest rows only | none possible retroactively; disclosed | none |
| B11-P | Open (unchanged) | Membership before 2020-12-31 | No universe for 2016-2020 scans | Owner approval to transcribe | Owner |

Fixed in this round, each with a test:
- **Stale universe annotations:** regenerated.
- **Pre-2016 renames carrying today's ISIN:** fixed (`RealIdentityRecords`).
- **Empty-membership universe treated as verified:** fixed.
- **Loader version not bumped for ED-38:** bumped to 2.1.0.
- **CA completeness:** audited (`ca_completeness_audit.py`).
- **Identity builder:** moved into the repository; reproduces its output byte-identical.
- **`collect_corporate_actions.py --retry-empty`:** added; it writes new files and never overwrites.
