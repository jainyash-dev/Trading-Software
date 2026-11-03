# Decision Register (human decisions outstanding)

**Dated 2026-11-02.** Open items and approved methodology decisions that change what the system may conclude.

## Product-owner approvals (M1, 2026-11-02)

The following R1-R6 decisions are **USER_APPROVED** and authoritative. Approval is limited
to these six decisions; D41 and its other readings remain PROPOSED unless separately listed
here.

| ID | Approved behaviour | Implementation / test trace |
|---|---|---|
| R1 | Curve position uses CMP only. Execution PL does not affect curve classification. HOC at CMP applies even if execution PL is LOC. | `_g3`; G3 and end-to-end tests |
| R2 | 12 o'clock / Extreme Uptrend maps to `STRONG_UP` for eligibility and matrix evaluation; preserve the original label in reports and diagnostics. | `trend.READINGS`; trend and report tests |
| R3 | Coinciding means actual price-range overlap between demand zones on different timeframes. Aggressive remains separate; a zone merely above the HTF PL is not Coinciding. Preserve applicable D15 tested-zone / DL-untouched requirements. | `structure.coinciding`; overlap, non-overlap, D15 and G6 tests |
| R4 | A completed candle close beyond a demand zone's DL invalidates it under D24. A wick / temporary breach alone is not invalidation or a bounce. An active-trade SL touch is recorded separately from zone invalidation. Apply approved timeframe rules consistently. | Zone Engine, MTF overlay and backtest event tests |
| R5 | HOC + Up + demand long is REJECT; HOC + Sideways is MANUAL pending sector support; HOC + Down follows RF3, with no invented exception. Keep the outcomes explicit. | `matrix_long`, `_g3`, `_g8`; matrix and qualification tests |
| R6 | Known absence of a qualifying HTF zone passes G6 as Standard; unknown freshness / DL status is MANUAL. G3 independently determines whether a curve exists. G6 PASS is not overall qualification. | `_g6`; G3 / G6 regression tests |

The earlier P-LOC-2 reading about price inside a tested HTF demand is not the same decision
as this approved R4 DL-invalidation rule. It remains separately unresolved.

**Detailed review:** `DECISION_REVIEW.md` has, for each item, verbatim Rulebook quotes, the
alternatives, the gate outcomes and tests that would change, and a recommendation.
- **Approved in M1:** R1-R6 above (P-LOC-1, P-TREND-1, P-COIN-1, P-MAT-1, P-MAT-2,
  P-COIN-2, plus the distinct DL-invalidation rule R4).
- **Rulebook-supported recommended defaults still awaiting approval:** P-CONF-1 (entry,
  RB 1302), P-G8-1 (as now).
- **USER DECISION REQUIRED:** P-LOC-2, D40 (20 Jan 2024), B9, B12
  (including the RB 2392 monthly cap in backtests), M4b, RB-VERSION-1 (which Rulebook revision
  is authoritative). Nothing
here is approved by being listed. "Type": **TRADING** (a strategy rule; only the user
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
| P-LOC-2 | RB 1587, 1597, 1617-1622 | Price inside a tested HTF demand -> MANUAL | VLOC; or redraw to the next fresh zone | Restricts | `G3.test_price_inside_a_tested_monthly_demand...` | **Still open; not covered by approved R4** |
| P-G8-1 | RB RF7 (line 606) | Leg-out not closing beyond the leg-in extreme -> RF7 MANUAL | Automate "reaction zone" detection | Restricts | `G8` | Keep manual |
| D40 | Official circulars; D30 | Calendar 2021-2025 in use; 20 Jan 2024 hours inferred from NSE/CMTR/41180 | Reject the inference -> that date UNRESOLVED | Calendar decides gaps (G0) and HTF candles | `test_nse_calendar_data` | Review wording and the inference; approve or mark the date UNRESOLVED |
| B9 | RB 2010-2022, 2097-2110 | Ranges over every applicable tier (P-LVL-1) | One buffer rule | Scanner: R:R may be MANUAL (DEPENDS). Backtest: **cannot run without a choice** | `G7`, `Levels` | Choose a backtest buffer rule (only needed for backtests) |
| B12 | RB 2141 only | Backtest refuses to run without fills, same-bar, expiry, costs, slippage | Any user model | Backtest only | `test_research_backtest.Model` | Supply an execution and cost model from official schedules |
| M4b | audit M4b; D16 | WIT BLOCKED everywhere | Approve a 75/125-minute session and gap design | No WIT output | `Wit`, q7, e2e | Decide when intraday data (B6) is available |
| P-RISK-1 | RB 41, 53-59, 1029, 2208-2220 (the stage table prints bands; no line says "above the band = reject") | `risk.assess_config`: RPT above the declared stage's maximum, or above 2% with no stage declared, is FAIL; below the band or no stage is MANUAL | MANUAL instead of FAIL | Risk plan only (never a gate or candidate status) | `test_research_risk` Config, AuditRegressions | **USER DECISION REQUIRED** (reading labelled in the code) |
| B12-CAP | RB 2392, 2400, 2408, 2414-2415 | Backtest cap counts trades at FILL; selection is fill order (the Rulebook's "best 10" stays human); a cap above 10 is allowed but labelled MONTHLY_CAP_ABOVE_RULEBOOK | Count at order placement; refuse caps above 10 | Backtest only | `test_research_backtest` Portfolio, CapAuditRegressions | **USER DECISION REQUIRED** with B12 |
| RB-VERSION-1 | Root PDF `340fe490-..._Trading_Rulebook.pdf` (136 pages, SHA-256 e41cd0e7...) vs protected Markdown (SHA-256 039883be...) | Code cites the protected Markdown line numbers; both files are hash-pinned and unchanged | Declare the PDF or the Markdown the authoritative revision | MIT: none found (completed-candle rule is D23; the 3.4 exception exempts MIT). WIT: the G1 recency source (RB 1786-1803) exists only in the Markdown; WIT stays BLOCKED | `test_repo` pins both hashes | **USER DECISION REQUIRED.** Found 2026-11-02 by a stdlib text extraction of the PDF compared line by line with the Markdown: the PDF has no text for RB 1784 ("Leg-out is CLOSED" requirement row), section 3.4 "LTF Proximity Rule" (RB 1786-1803) or the RB 1809 / 1813 Chapter 4.1 wording. All other differences found were bold-font extraction artefacts. Which file is newer is not known |

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
