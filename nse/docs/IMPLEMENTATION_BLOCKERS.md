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
- **B18:** NSE CM EOD file formats (legacy and UDiFF): legacy-format evidence recorded for two dates (`EOD_FORMAT_EVIDENCE.md`); provenance of the two original ZIP archives is user-confirmed (official NSE website, downloaded 2026-10-27), not independently authenticated; the user accepted this two-sample evidence with limitations (2026-10-27). **Update 2026-10-28:** the strict loader (`nse/eod/nse_bhavcopy.py`, which refuses any deviation from the recorded format) also accepts all 61 official Q1 2022 files (working-tree manifest). **Still open:** format continuity for the rest of 2022-2023 is not proven; UDiFF and its switch date are unverified; no Muhurat sample; no independent cross-check (B8, B10); prices unadjusted (B7). UDiFF: no sample inspected. Separate from B6, which covers Kite Connect capabilities only.
- **B17:** NSE trading calendar: **loader built and tested** (`nse/calendar/nse_calendar.py`). **2021-2025 (the whole D29 window) transcribed** from official NSE circulars (D40, proposed wording pending review): 5 base circulars, 4 amendments and 10 session notices, 105 events, in `nse/data/calendar/sources.csv` and `events.csv` (list in `nse/data/calendar/README.md` §1). The circular files are local only and hash-verified. Tests: `tests/test_nse_calendar_data.py` (independent second transcription).
  - 2023 Bakri Id is resolved by NSE/CMTR/57285: 28 June 2023 is a normal session and 29 June a holiday.
  - Special sessions under D30: 20 Jan 2024 and 1 Feb 2025 are regular-hours Saturdays (`NORMAL_SPECIAL`, provisional rule); the 2 March and 18 May 2024 DR-switch sessions are shortened and excluded; five Muhurat sessions (2021-2025) are excluded.
  - Q1 2022 (2022-01-03 to 2022-03-31) reconciles cleanly with the 61 official EOD files. **Its manifest rows are in the working tree, not committed**, so on a checkout without them the reconciliation test reports a missing prerequisite instead of running.
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
| P-LOC-2 | Price inside tested HTF demand: VLOC or redraw | `structure.build_curve` | Curve location at an in-progress tested boundary remains ambiguous | MANUAL | Separate user decision; not covered by R4 DL invalidation | `G3.test_price_inside_a_tested_monthly_demand_needs_review` | OPEN-DECISION, RESTRICTED |
| R7 | History depth: Y needs 3 completed years, HY/Q 3 periods, the Weekly trend 55 weeks | data | Nothing can be ACTIONABLE on short history | G5 DATA_INSUFFICIENT or MANUAL; G4 MANUAL | Approval to download 2021-2025 EOD files (D31); UDiFF sample (B18) | `run_all` local_data reconciliation, then a scan | OPEN-EVIDENCE, RESTRICTED |
| R8 | Nifty 100 constituent file and history (D1, B11) | `universe.py` | Wrong or survivorship-biased universe | Every scan is UNIVERSE_UNVERIFIED | Official NSE Indices files with dates | `test_research_reports.Universe`, then a scan with `--universe` | OPEN-EVIDENCE |
| R9 | Corporate actions (B7) | data | False zones and breaches around splits and bonuses | CORPORATE_ACTIONS_UNVERIFIED on every record; manual checklist item | Adjustment source and convention | Known split or bonus dates compared before and after adjustment | OPEN-EVIDENCE |
| R10 | Score /14 extras: EMA20, crossover, RSI/Stochastic, gap application (spec 5.1) | `confluence.py` | A provisional point could be read as judged | Display only, PROVISIONAL / NOT_EVALUATED labels; no gate reads it | TradingView EMA comparison (B8) | `test_research_confluence` | IMPLEMENTED (display), RESTRICTED |
| R11 | WIT weekly DZ vs Monthly SZ (RB 1402) branch untested | `_g5` | Mistake hidden while WIT is blocked | WIT BLOCKED | Test once M4b is approved | Unit test with a 75m snapshot | DEFERRED |
| R12 | Intraday 75/125-minute session and gap design (audit M4b) | overlay, WIT | Wrong intraday freshness | WIT BLOCKED everywhere | User approval of a design | Synthetic, then TradingView (B10) | DEFERRED |
| R13 | Backtesting: fills, costs, outcome evaluation (B9, B12) | not built | No performance evidence | `scan_history` gives signals only; no metrics | User-approved execution and cost model | Reproducible run on point-in-time data (B11) | DEFERRED |
| RB-VERSION-1 | The root Rulebook PDF and the protected Markdown are different revisions (PDF lacks RB 1784 and RB 1786-1803, section 3.4) | Methodology sources; WIT G1 recency | A rule cited from one revision may not exist in the other | Code cites the Markdown; WIT BLOCKED; no MIT gate depends on the differing text | Owner states which revision is authoritative | Re-run the PDF/Markdown comparison after any new export | OPEN-DECISION |
