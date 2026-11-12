# Decision Review: unresolved strategy and engineering decisions

**Original review dated 2026-10-29.** This review covers items in `DECISION_REGISTER.md` (D40,
D41's readings, R1-R6, the backtest decisions and the audit items).

**Status update 2026-11-02:** Product owner approved R1-R6. The controlling decisions are
in the `Product-owner approvals` section of `DECISION_REGISTER.md`; they supersede any
conflicting alternatives and recommendations below. The earlier P-LOC-2 question about
price inside a tested HTF demand remains open and is distinct from the approved DL
invalidation rule R4.

- Quotes are verbatim from the Trading Rulebook (RB line), except that its em dashes are written as hyphens (repository text rule).
- "Tests that change" names the tests whose expected outcome would move if the alternative
  were adopted.
- A **Recommended default** appears only where the Rulebook itself supports it. Everything
  else is marked **USER DECISION REQUIRED**.
- Items not covered by the approved R1-R6 remain open or PROPOSED as indicated in the register.

## A. Trading rules

### A1. P-TREND-1: 12 o'clock "Extreme Uptrend" in matrix rows written for "Strong Up"
- **Source:** RB 1688 "Rising very steeply | 12 o'clock | Extreme Uptrend | ... | Aggressively hunt for Demand Zone entries"; RB 1689 "Rising steeply | 12-1 o'clock | Strong Uptrend". The matrix rows say "Strong Up" (RB 1889-1897). RB 1232: "Use clock method (12-3 = up, 3-6 = down)".
- **Current:** 12 o'clock maps to {STRONG_UP} (`trend.READINGS`).
- **Alternatives:**
  - (a) As now.
  - (b) Extreme is its own reading, absent from the matrix, so MANUAL.
- **Consequence of (b):** every setup with a 12 o'clock Weekly trend leaves ACTIONABLE for MANUAL REVIEW. That includes the e2e reference candidate (`test_research_e2e.Reference`), `Trend.test_matrix_rows` and the ideal-scenario gate tests.
- **Recommended default: (a).** RB 1688's action for 12 o'clock is stronger than RB 1689's for Strong ("aggressively" vs "confidently"), and RB 1232 groups 12-3 as up. Approval is still needed, because the matrix wording does not name Extreme.

### A2. P-MAT-1: EQB with a Down trend, for a long
- **Source:** RB 1599: "**EQB** ... | **TREND ONLY** | ONLY trade in the direction confirmed by the ITF Trend. If ITF is up → buy. If ITF is down → sell. If ITF is sideways → DO NOTHING. | Do NOT take counter-trend trades here." Spec 7.6 has no EQB + Down row for longs ("Not listed → [MANUAL]").
- **Current:** REJECT (G4 FAIL).
- **Alternative:** MANUAL (spec 7.6).
- **Consequence of the alternative:** `Trend.test_matrix_rows` (EQB + DOWN) changes FAIL to MANUAL. The status changes REJECTED to MANUAL_REVIEW only where RF3 (G8) does not already reject.
- **Recommended default: as now.** RB 1599 is explicit, and the Rulebook outranks the spec table (D12).

### A3. P-MAT-2: HOC
- **Source:** RB 1600: "**HOC** ... Do NOT buy unless extreme circumstances (VLOC-quality confirmation + massive sector support)". RB 1901: "HOC | Up | Any demand | - | ❌ **REJECT.**"
- **Current:** HOC + any Up reading is REJECT. HOC + Sideways or Down is MANUAL; sector is not evaluated (D6).
- **Alternative:** HOC always REJECT, because sector support cannot be shown.
- **Consequence:** the HOC + Sideways matrix test would move from MANUAL to FAIL.
- **Recommended default: as now.** The REJECT is the literal RB 1901 row. The MANUAL is spec 7.2's treatment of RB 1600's exception, which needs sector (D6).

### A4. P-COIN-1 / R3: execution zone above the HTF location zone's PL
- **Source:**
  - RB 1833 "Your LTF execution zone's Proximal Line sits INSIDE or directly TOUCHING the HTF Location zone's Proximal Line area."
  - RB 1854 "LTF zone is inside HTF area but above HTF PL, AND has 7/7 + achievement | **Aggressive**".
  - RB 1855 "... WITHOUT achievement | **REJECT**".
  - The matrix has rows that need neither: RB 1894 "LOC | Moderate Up | 7/7 | Standard", RB 1897 "EQB | Strong Up | 7/7 | Standard". RB 1893 "LOC | Strong Up | 7/7 Coinciding".
  - Spec 7.5: "LTF PL above the HTF PL → [MANUAL]".
- **Current:** G6 is MANUAL whenever the execution PL is above the qualifying HTF PL, in every matrix row.
- **Alternatives:**
  - (a) As now.
  - (b) A numeric "touching" tolerance, or an extent for "HTF area". None exists in the Rulebook.
  - (c) Apply the coinciding/aggressive classification only in rows that name it (VLOC rows; LOC + Strong Up). Standard rows (LOC + Moderate Up, EQB + Strong Up) pass G6 when no HTF zone contains the execution PL.
- **Consequence:**
  - (c) would let standard-row setups reach ACTIONABLE. LOC + Strong Up would then *require* Coinciding, which is stricter than spec 7.6's "Pass".
  - Tests that change: `G6.test_above_the_htf_pl_needs_review`; e2e `test_unresolved_rule_keeps_the_restriction` (k = 1.75, LOC + Strong Up, would stay MANUAL or become FAIL under (c)); `Trend.test_matrix_rows` for LOC + Strong Up.
- **USER DECISION REQUIRED.** The Rulebook gives no tolerance. Reading (c) follows the matrix's Entry Type column but contradicts spec 7.5/7.6 as written.

### A5. P-COIN-2 / R6: no qualifying HTF location zone at all
- **Source:** D15 "A lower-TF setup may receive coinciding-trade confluence from a relevant HTF zone when that zone exists and price has not touched its distal line since creation." The Rulebook does not cover the case where no such zone exists.
- **Current:** G6 PASS ("standard setup").
- **Alternative:** MANUAL.
- **Consequence:** `G6.test_no_qualifying_zone_is_a_standard_setup` changes. In practice it is rare: a fresh curve bottom is always a qualifying zone, so G3 already fails without one.
- **USER DECISION REQUIRED.**

### A6. P-LOC-1 / R1: which price reads the curve
- **Source:** RB 1591 "Read your current position | Where is CMP relative to these lines?" The entry sits at the PL plus a buffer (RB 2010).
- **Current:** positions are computed at both the current price and the execution PL. If they differ and that changes the outcome, the result is MANUAL.
- **Alternatives:**
  - (a) As now.
  - (b) Current price only (RB literal).
  - (c) Execution PL only.
- **Consequence:** (b) would remove MANUAL where the two disagree. `G3.test_current_price_and_entry_pl_disagreeing_goes_to_review` would then follow the price: 1300 is HOC, so FAIL with Strong Up.
- **Recommended default: (b), the current price**, as RB 1591 states. Approval is needed before the code changes.

### A7. P-LOC-2 / R4: price inside a tested HTF demand zone
- **Source:** RB 1587 "Must be FRESH (PL untouched). Tested zones create false boundaries." RB 1597 "VLOC ... INSIDE the HTF Demand Zone itself". RB 1617-1622: "Your Monthly Demand (bottom of Curve) gets tested - price touches its PL and bounces ... REDRAW the Curve."
- **Current:** MANUAL (`PRICE_INSIDE_TESTED_HTF_DEMAND`).
- **Alternatives:**
  - (a) As now.
  - (b) VLOC while price is still in the zone that its first touch made tested.
  - (c) Redraw at once to the next fresh zone below.
- **Consequence:** `G3.test_price_inside_a_tested_monthly_demand_needs_review` changes. Under (b) the best matrix rows (VLOC) become reachable; under (c), LOC or EQB with the lower boundary.
- **Resolved 2026-11-08: USER_APPROVED (c), redraw from the next fresh Monthly demand below** (DECISION_LOG 1F; the test is now `G3.test_price_inside_a_tested_monthly_demand_redraws_from_the_next_fresh_zone`). Original note: RB 1587 and 1597 pull in opposite directions while the touch is in progress. RB 1617 describes the redraw only after a bounce.

### A8. P-CONF-1: where the HTF conflict distance is measured
- **Source:** RB 1302 "Is there a Monthly Supply Zone within 5-10% above your buy entry?" Spec 7.4: "Distances are reported from both the PL and the entry range (the rulebook measures from the entry; Pine from the PL)."
- **Current:** bands are measured from the PL, the entry minimum and the entry maximum. If they differ and that changes the outcome, MANUAL.
- **Alternative:** decide on the entry range only, and report the PL distance as evidence.
- **Consequence:** `G5.test_the_measuring_point_can_decide` and e2e `test_higher_timeframe_conflict` change. A supply 4.5% above the entry maximum but 5.1% above the PL would REJECT instead of MANUAL. The entry range itself still depends on B9, so MANUAL remains where the bounds disagree.
- **Recommended default: the entry**, as RB 1302 and spec 7.4 both say. Approval is needed.

### A9. P-G8-1: RF7, reaction zone with poor closing
- **Source:** RB 606 "DZ2 formed right above DZ1, AND leg-out failed to close strongly."
- **Current:** MANUAL when the leg-out does not close beyond the leg-in extreme.
- **Alternative:** automate "formed right above DZ1". This needs a distance rule the Rulebook lacks.
- **Recommended default: as now**, because RF7 needs both conditions and only one is objective.

### A10. D40: calendar tables, especially 20 January 2024
- **Source:** NSE/MSD/60340 says "regular trading sessions ... as per regular market timings" and prints no times. The hours are taken from NSE/CMTR/41180 (09:15-15:30, effective 3 Jun 2019).
- **Current:** NORMAL_SPECIAL; a bar is expected that day.
- **Alternatives:**
  - (a) Accept the inference.
  - (b) Mark that date UNRESOLVED (D39). Every period containing it is then truncated: W 2024-W03, M 2024-01, Q1, H1 and Y 2024.
- **Consequence of (b):** every 2024 scan that needs those periods becomes UNVERIFIED_SESSION or truncated. `test_nse_calendar_data` changes.
- **USER DECISION REQUIRED.** The whole D40 wording also awaits your review. A TradingView check of 20 Jan 2024 (`tradingview_checks.template.csv` TV-CAL-09) would add evidence, but not settle the hours.

### A11. B9: which buffer within the printed ranges (backtests only)
- **Source:** RB 2017-2020, the price tiers. RB 2022: "**These are guidelines, not rigid rules.** Use common sense." RB 2109: "Volatile, news-driven market | Increase buffer by 50-100%".
- **Current:** the scanner reports ranges over every tier that could apply (P-LVL-1). The backtest refuses to run without `entry` and `stop` choices.
- **USER DECISION REQUIRED.** The Rulebook explicitly declines a fixed value.

### A12. B12: execution assumptions (backtests only)
- **Source:** RB 2141 "**Exit on TOUCH, not on CLOSE**". RB 2139 "**Once the trade triggers, SL is PERMANENTLY LOCKED**". RB 2392: "a MAXIMUM of 10 trades per month".
- **Already consistent with the Rulebook:**
  - the stop exits on touch;
  - levels are fixed at the signal.
- **USER DECISION REQUIRED:**
  - gap fills;
  - same-bar stop and target;
  - order expiry;
  - cancel-if-target-first;
  - costs and slippage.

  None appears in the Rulebook.
- The 10-trades-a-month cap is enforced in the backtest when `monthly_trade_cap` is set, counted at fill in fill order (`apply_portfolio_rules`); the Rulebook's "best 10" selection stays a user decision (B12-CAP). *(Corrected 2026-11-06: this line used to say the cap was not enforced.)*

### A13. M4b: intraday (WIT) session and gap design
- **Current:** WIT is BLOCKED everywhere.
- **USER DECISION REQUIRED**, together with an intraday data source (B6, D32).

## B. Engineering readings (adopt or reject; no trading rule changes)

| ID | Current | Effect | Recommendation |
|---|---|---|---|
| P-LOC-3 | A curve boundary of unknown freshness stops the search (MANUAL) | Restricts | Keep |
| P-LVL-1 | Union of the tiers of the PL and both DLs, edges inclusive | Wider ranges, more MANUAL | Keep until B9 |
| P-LVL-2 | Target: nearest FRESH supply above the entry maximum; tested skipped (RB 557 "Identify nearest FRESH opposing zone"; RB 2286); unknown freshness stops | Restricts | Keep |
| P-LVL-3 | Invalid levels make G7 MANUAL; no R:R | Restricts | Keep |
| P-CAL-1 | No calendar makes G0 MANUAL | Restricts | Keep |
| P-CA-1 | A recorded price-scale action in the history makes G0 MANUAL | Restricts | Keep until B7 |
| P-CA-2 (new) | A PREVCLOSE discontinuity in the history makes G0 MANUAL (`PRICE_DISCONTINUITY_IN_HISTORY`); a backtest trade across one is excluded | Restricts | Keep until B7 |
| P-DQ-1 | Findings dated after as_of are not read by an earlier scan | Neutral | Keep |
| P-REF-1 | Zone match key: timeframe, side, creation period | Comparison only | Confirm on the first real references |
| P-BT-1 | Backtest needs a full user execution model; one order per zone from its first allowed signal | Neutral | Keep |
| M1 | `LEGOUT_WINDOW_OPEN` report label; engine unchanged | Report only | Accept |
| L5 | Engine minimum 3 candles; zero-base needs 4 | Edge case | Accept as documented |
| L6 | `Rules` overrides not validated | Only via code | Add validation if overrides are ever exposed |
| L7 | Daily close assumed at 15:30 (SESSION_TIMES_ASSUMED on every record) | Visible | Accept |
| L8 | Supply zones' manual flags hidden under CONTEXT_ONLY | Supply is context only | Accept; reconsider if supply ever gates |
| L9 | One missing session ends the HTF series | Visible (`truncated_at`) | Accept; segmenting would be a design change |
| Audit rows 13, 31 | Wick-to-Wick PL/DL; dropping a timeframe in a 6+ base mess: not implemented | Not built | Defer (USER DECISION REQUIRED to build) |

## C. What changes once you decide

For each item, the change is limited to the function named under "Current" and the tests
named under "Consequence". Every test that changes would be updated in the same change,
with the decision recorded as `USER_APPROVED` in `DECISION_LOG.md`. Nothing is promoted
without that record.
