# Audit Validation Report
## Independent Validation of STRATEGY_SPECIFICATION_AUDIT.md

**Date:** 2026-10-25
**Sources validated against:**
- Primary: `Trading Rulebook 341a82c22ebf8056a235c9695e1c0d87.md` (326 KB, ~8,500 lines)
- Reference implementation: `Demand&Supply Indicator.pine` (~2,750 lines, PineScript v6)
- Subject of audit: `STRATEGY_SPECIFICATION_AUDIT.md`

**Methodology:** Both source files read independently. Rulebook treated as source of truth; Pine Script treated as reference implementation. Where both agree, claim is confirmed. Where they disagree, the disagreement is reported without resolution unless the code provides unambiguous implementation evidence.

---

## Section 1. Confirmed Rules

The following first-audit claims are confirmed as accurate by independent reading of both sources.

**Core Strategy Structure**
- GTF Demand & Supply zone methodology confirmed throughout rulebook.
- MIT framework (Monthly Location → Weekly Trend → Daily Execution) confirmed as mandatory TDA sequence.
- Minimum R:R = 2:1 to structural target. Confirmed in Section 5 and reiterated across multiple sections.
- Position size formula: units = RPT ÷ (Entry − SL), RPT = 0.5–1% of capital. Confirmed.
- SL is set permanently once triggered; never moved to breakeven before minimum target. Confirmed.

**Candle Classification**
- Strong candle: body ≥ 60% of range. Confirmed in rulebook and Pine Script (`body_ratio >= 0.6`).
- Weak candle: body < 40% of range. Confirmed (`body_ratio < 0.4`).
- Intermediate: 40–60%. Confirmed.
- Doji: body ≤ 10% or open == close. Confirmed.

**Pattern Types**
- DBR: Drop-Base-Rally (demand zone). Confirmed.
- RBR: Rally-Base-Rally (demand zone). Confirmed.
- RBD: Rally-Base-Drop (supply zone). Confirmed.
- DBD: Drop-Base-Drop (supply zone). Confirmed.
- Base = consolidation of 1–3 weak/doji candles between two strong candles. Confirmed.

**Core Scoring Structure**
- Freshness: 3 (fresh) / 1.5 (tested once) / 0 (tested twice+). Confirmed (rulebook C5 and scoring table).
- Leg-out Strength: 2 (single explosive) / 1.5 (two moderate) / 1 (weak). Confirmed.
- Base Count: 2 (1–3 candles) / 1 (4–5 candles). Confirmed. No score assigned for 0 base candles.
- Maximum core score = 7. Confirmed.
- Minimum to proceed = 7/7 core for standard entry. Confirmed (with exceptions documented in Section 3 below).

**Freshness Rules**
- Proximal line must never have been touched after zone formation. Confirmed as "100% fresh" requirement.
- First test drops score from 3.0 to 1.5. Confirmed.
- A tested-once zone CANNOT reach 7/7 core (max possible = 3.5 + 2 + 2 = 5.5 if gap adds 0.5, or 1.5 + 2 + 2 + 0.5 = 6.0). Confirmed by arithmetic.

**Achievement Check for Regular Zones**
- Leg-out must close beyond `combined_high` (bull) or `combined_low` (bear), where `combined_high = max(legin_high, cluster_wick_high)`. Confirmed in Pine Script lines 1434–1463.
- Pending window: 2 bars. Confirmed (Pine Script lines 1544–1565, `pending_left := 2`).

**Time Score (Confluence)**
- 0–3 bars: 2 points. Confirmed.
- 4–7 bars: 1.5 points. Confirmed.
- 8–15 bars: 1 point. Confirmed.
- 16+ bars: 0.5 points. Confirmed.

**Zone Invalidation: Daily**
- Zone is invalidated when price closes BEYOND the distal line (confirmed in both rulebook and Pine Script).
- Pine Script implementation: permanently deletes the zone from all arrays (lines 2605–2656). See Section 3 for critical detail absent from first audit.

**Entry Types**
- Type 1: Set & Forget, requires 7/7 pristine zone. Confirmed.
- Type 2: 6/7 core. Type 3: 5/7 core. Both explicitly documented.
- Rulebook author statement: "I never use Entry Type 2 or 3, and neither should you." Confirmed in Section 5.
- 10-trade monthly ceiling. Confirmed; stated as a ceiling, not a target.

**Timeframes**
- NSE session = 375 minutes. 375 ÷ 3 = 125min; 375 ÷ 5 = 75min. Confirmed as preferred execution timeframes.
- These are preferred over 60min/240min, which do not divide cleanly. Confirmed.

**HTF Trend Detection**
- SMA-50 direction determines trend on each timeframe. Confirmed.
- Ranging detected via multiplicative dead band: `sma50 > sma50[1] * (1 + ranging_pct/100)` for bullish, `sma50 < sma50[1] / (1 + ranging_pct/100)` for bearish. Confirmed (Pine Script lines 252–291). This is NOT a simple comparison.

**Sector Alignment**
- Nifty 50 and sector index alignment is MANDATORY for DIT/intraday entries, HIGH priority for swing entries. Confirmed in rulebook.

**WIT (Weekly/Intraday/Trading) Rules**
- 75min/125min execution zones must be formed within the last 8–10 candles. Confirmed (Section 3 of rulebook).

---

## Section 2. Verified Pine Script Behaviour

Behaviours confirmed by direct reading of the Pine Script source code. Where these diverge from the rulebook, they are separately flagged in Section 3 or 4.

**Zone Creation Logic (lines 1386–1419)**
- Leg-in detection uses two paths: (1) `bar_index - last_strong_index <= 3` (primary), (2) fallback re-evaluation of `bar[1]` (secondary). Maximum window = 3 bars. Rulebook does not specify this window.
- `barstate.isconfirmed` used throughout: all zone creation and test detection runs only on confirmed (closed) bars. No look-ahead bias from this mechanism.

**Zero-Base Zones (lines 1717–1762)**
- DBR zero-base: previous bar is strong bear, current bar is strong bull, `not in_cluster`.
- RBD zero-base: previous bar is strong bull, current bar is strong bear, `not in_cluster`.
- `zone_base_count` set to 0. `is_exceptional` set to false. No achievement gate applied.
- `legout_count` initialised to 1 on creation.
- Gap detection: `has_gap = low > high[1]` (bull), `has_gap = high < low[1]` (bear).
- Initial core score: 6.0 (no gap) or 7.0 (with gap), because the scoring function adds 0.5 for gap and `time_score = 2.0` but base_count=0 yields 0 points from H2.
- Proximal line for DBR: `math.max(math.min(open[1],close[1]), math.min(open,close))`: higher of the two lower body edges.

**Legout Count Tracking (lines 1765–1775)**
- Additional legout detection fires only when `bars_since >= 1 and bars_since <= 3` (bars AFTER zone creation bar). Does not fire on bar 0 (creation bar itself). Correct initial count of 1 is set during zone creation, not via this block.

**Conflict Check (lines 801–852, 896–900)**
- `f_check_zone_conflict` applies to ALL daily zones: both demand zones (checked against opposing weekly/monthly supply) and supply zones (checked against opposing weekly/monthly demand). Called from `f_update_zone_visibility` which iterates all zones.

**DL Breach (lines 2605–2656)**
- Trigger: `close < bot` (demand) or `close > top` (supply) on a confirmed bar.
- Effect: zone is PERMANENTLY DELETED from all arrays via `array.remove` on all zone attribute arrays.
- Test increment does NOT occur. Deletion is unconditional once the close crosses the distal line.
- This is separate from the test detection path (`low <= proximal`).

**Weekly Zone Invalidation (lines 2658–2689)**
- Trigger fires only on `w_bar_change` (first bar of a new weekly candle).
- Close used: `w_close1`: the PREVIOUS completed week's close. Not the current bar's close.
- Consequence: a zone invalidated by weekly close is processed on the Monday open, not at the moment the Friday close happens.

**HTF Test Detection (weekly/monthly)**
- Uses `w_low1`/`w_high1` for weekly test, `m_low1`/`m_high1` for monthly test: previous completed period OHLC. Not the current incomplete candle.

**Sector Inputs**
- `i_nifty_symbol` and `i_sector_symbol` exist as input fields (lines 74–77) but are never referenced in zone creation, scoring, or trend detection logic. They are UI-only placeholders. Sector alignment scoring is NOT implemented in the indicator.

**Ranging Threshold**
- `_dash2_ranging_mult = 1.0 + i_dash2_ranging_pct / 100.0` creates a dead band. A Python port must replicate this multiplicative comparison, not a simple slope sign.

**Scoring Function (lines 594–602)**
- `f_calc_core_score(freshness, strength, base_count, has_gap)` confirmed correct as documented in first audit.
- Gap bonus (+0.5) is applied inside this function when `has_gap` is true.

---

## Section 3. Corrections to the First Audit

These are items where the first audit (`STRATEGY_SPECIFICATION_AUDIT.md`) states something that is incorrect or incomplete based on independent reading of the sources.

### Correction 1: DL Breach Behaviour Is Entirely Absent from the First Audit

**First audit claim:** Not discussed. Decision E.5 asks "if price closes below DL, treat as tested-2+ or invalidate?"
**Actual Pine Script behaviour:** The indicator PERMANENTLY DELETES the zone from all arrays when `close < bot` (demand) or `close > top` (supply). There is no "mark as tested-2+" path for DL breach. The zone is gone.
**Rulebook:** Confirms zone invalidation when price closes beyond the distal line, but does not specify the data-structure treatment.
**Impact on E.5:** Option A (treat as tested-2+) is contradicted by the reference implementation. The correct behaviour is deletion, not incremented test count. This is not an open decision: it is answered by the code.

### Correction 2: `f_check_zone_conflict` Applies to All Daily Zones, Not Demand Zones Only

**First audit claim (B.9):** "Applied to daily demand zones only."
**Actual Pine Script behaviour:** `f_check_zone_conflict` handles both demand and supply zones. The function checks whether a daily demand zone has an opposing weekly/monthly supply above it AND whether a daily supply zone has an opposing weekly/monthly demand below it. It is called from `f_update_zone_visibility` which iterates all daily zones without filtering by direction.
**Impact:** The first audit's description of the conflict-check scope is incorrect. Both directions are checked symmetrically.

### Correction 3: Maximum Scoring Total Is 14, Not 15

**First audit claim (B.12):** "5 confluence factors. Maximum total = 15."
**Actual rulebook (Part C table):** "MAXIMUM TOTAL = 14." Confluence factors: Sector (+2), EMA (+2), Cross (+1), Gap (+1), RSI (+1) = max 7. Core max = 7. Total = 14.
**Contradiction within rulebook:** The Quick Scoring Reference section states "/15" and lists 6 confluence factors, adding "Pattern confirms post-entry → +1." This factor is not described anywhere in Part B or the main confluence scoring section. It appears only in the Quick Reference table.
**Impact:** The "15" figure in the first audit comes from the Quick Reference, which is inconsistent with the Part C table. The Part C table is the primary scoring documentation and should be treated as authoritative. The "+1 Pattern" factor is undocumented.

### Correction 4: The "Hard 7/7 Minimum" Has Explicit Documented Exceptions

**First audit claim:** "7/7 core is non-negotiable minimum."
**Actual rulebook:** Three documented exceptions exist in the same rulebook:
1. **6/7 override** (Section 2): A zone scoring 6/7 with a single but violently explosive leg-out can be traded as 7/7: for experienced traders after 100+ trades only.
2. **Trade Selection Priority Framework** (Section 2, Rank 3rd): "Conservative with Strong Confluence: 6/7 core, 9–10/15 total, sector +2, manage with reduced RPT (0.75%)": explicitly listed as tradeable.
3. **Entry Type 2** (Section 5): 6/7 core is a documented entry type, then immediately qualified with "I never use Entry Type 2 or 3."
**Impact:** The "7/7 is a hard minimum" is accurate for standard automated screening but should not be presented as having no exceptions. For the Python research tool, the default threshold should be 7/7, but the screen should optionally surface 6/7 zones with a clear label.

### Correction 5: Zero-Base Zone Initial Core Score Is 6.0, Not 7.0 (Without Gap)

**First audit implication:** Zero-base zones start at 7/7.
**Actual indicator behaviour:** `legout_count = 1` on creation, `base_count = 0`, `has_gap` depends on whether a gap exists between the two candles. Without a gap, `f_calc_core_score` returns: freshness(3.0) + strength(2.0, single strong leg-out at count=1) + base(0, because H2 table starts at 1 candle) + gap(0) = **5.0 core**. Adding time_score=2.0 (0–3 bars), total = **7.0**. WITH a gap: 5.0 + 0.5 (gap bonus) + 2.0 (time) = **7.5**.
**Clarification:** The "core" (parts A+B) of a zero-base zone = 5.0. The time score (part C) pushes the total to 7.0 (no gap) or 7.5 (with gap). The first audit's treatment did not distinguish core from total for zero-base zones.

---

## Section 4. Genuine Contradictions and Missing Specifications

These are issues where the rulebook itself contains an internal inconsistency, or where the rulebook does not specify behaviour that the Pine Script implements.

### Contradiction 4.1. Tested-Once Zone: Proceed or Reject?

**Source A (Section 1, 10 Essential Checks, #3):** "Is this zone 100% FRESH?": YES is required. A tested zone would fail this check.
**Source B (Section 2, Freshness scoring):** "TESTED ONCE = 1.5. Only proceed if all other factors are exceptionally strong."
**Source C (Section 2, Core Score Summary):** "Must score 3 for Type 1 entry. 1.5 only with exceptional confluence."
**Source D (Section 2, Trade Selection Priority, Rank 3rd):** "Conservative with Strong Confluence: 6/7 core": this can only be a tested-once zone (since a tested-once zone cannot reach 7/7 core).
**Nature:** Genuine internal contradiction. Essential Check #3 says reject. The scoring system provides a score for tested-once zones. Priority Rank 3rd makes it tradeable.
**Resolution required:** User must decide whether the Python tool should surface tested-once zones or filter them out at the screening stage.

### Contradiction 4.2. Maximum Score Is 14 or 15?

**Source A (Part C table):** Maximum = 14. Five confluence factors.
**Source B (Quick Scoring Reference):** Maximum = 15. Six confluence factors (adds "Pattern confirms post-entry → +1").
**Nature:** Internal rulebook inconsistency. The "+1 Pattern" factor is not described elsewhere.
**Resolution required:** User must declare which total to use. Recommendation: use 14 as the denominator; treat the Pattern factor as a post-entry confirmation, not a pre-entry scoring input.

### Missing Specification 4.3: Zero-Base Zone Scoring

The rulebook's H2 table starts at "1–3 base candles = 2 points." It does not mention 0 base candles. The Pine Script assigns `base_count = 0` for zero-base zones, which yields 0 points from the H2 table. This is implemented behaviour with no rulebook definition.

### Missing Specification 4.4: Leg-In Detection Window

The rulebook defines patterns by visual description (the leg-in strong candle, then base, then leg-out) but does not specify the maximum number of bars allowed between leg-in and base start, or between base end and leg-out. The Pine Script uses a 3-bar window (`bar_index - last_strong_index <= 3`). This is implemented behaviour with no rulebook definition.

### Missing Specification 4.5: Sector Alignment in Algorithmic Scoring

The rulebook requires sector alignment and awards up to +2 points for it (Part C: "Sector aligned with Nifty 50 and sector index = +2"). The Pine Script has sector symbol input fields but implements no sector alignment logic: it is a UI placeholder only. The +2 points are never computed by the indicator.
**Impact:** Any Python implementation that aims to replicate the indicator's actual scoring will NOT include sector scores. Implementing sector scoring requires a separate data feed and logic not present in the reference implementation.

### Missing Specification 4.6: "Explosive" Relative Size Check

The rulebook defines explosive as: body > 50% of range AND price achievement AND **relative size (visually larger than surrounding candles)** AND context. The Pine Script checks body ratio and `close > combined_high` but has no candle-size comparison to surrounding bars. The relative size criterion is unimplemented in the reference.

### Missing Specification 4.7: Weekly Trailing Stop-Loss

The rulebook references trailing SL management at weekly levels but provides no algorithmic rule for when or how to trail. This is acknowledged as requiring discretionary judgment. No Pine Script implementation exists.

---

## Section 5. All 10 Decisions: Evidence and Recommendations

Each decision from Section E of the first audit is reviewed with evidence from both sources and a recommendation.

---

### E.1. Tested-Once Zones: Filter or Surface?

**First audit claim:** Tested-once zones cannot reach 7/7 core; the audit recommends filtering them out by default.
**Rulebook evidence:**
- Essential Check #3: "Is this zone 100% FRESH?": YES required. Tested zones fail.
- Freshness table: tested-once = 1.5. "Only proceed if all other factors are exceptionally strong."
- Trade Selection Priority Rank 3rd: 6/7 core is explicitly listed as tradeable with sector +2 and reduced RPT.
- Entry Type 2: 6/7 core is documented, then immediately discouraged for beginners.

**Pine Script evidence:** The indicator assigns freshness=1.5 to tested-once zones and continues to display and score them. It does not automatically hide or reject them.

**Status:** Genuine rulebook contradiction. The 7/7 filter is the correct default for Type 1 screening. However, the rulebook does not prohibit surfacing tested-once zones as a separate category.

**Recommendation:** Implement two tiers. Tier 1: fresh zones meeting 7/7 core (standard screen). Tier 2: tested-once zones with total ≥ 9/14, sector aligned, flagged explicitly as "Tested-Once / Type 2 only." Default view shows Tier 1 only.

**User decision required:** Confirm whether Tier 2 should be implemented at all, or whether the screen should hard-filter tested-once zones.

---

### E.2. Zero-Base Zone Scoring and Eligibility

**First audit claim:** Zero-base zones are not defined in the rulebook. Treat as a special case.
**Rulebook evidence:** No mention of zero-base zones. H2 table starts at 1–3 base candles = 2 points.
**Pine Script evidence:** Zero-base zones are fully implemented. base_count=0 → 0 H2 points. Core = 5.0. With time_score=2.0 and gap bonus=0.5, total can reach 7.5. Without gap, total = 7.0 (which meets the 7/7 threshold only because time score is included in the total).

**Status:** Unspecified in rulebook. Implemented in indicator. The indicator treats zero-base zones as valid, eligible zones once time_score pushes total to ≥ 7.

**Recommendation:** Follow the indicator's treatment. Accept zero-base zones with total score ≥ 7.0 (including time score). Flag them as "Zero-Base" in output: they are structurally stronger (two consecutive strong candles) but weaker by base scoring. Require the gap bonus for initial 7.0+ on creation, or accept time decay to 1.5 which drops total to 6.5 (below threshold).

**User decision required:** Confirm whether zero-base zones without a gap should be considered eligible when their total = 7.0 at creation (time_score=2.0), and whether they become ineligible as time_score decays below 2.0.

---

### E.3. Buffer/Tolerance on Zone Entry

**First audit claim:** 0.1–0.2% buffer is a guideline; no hard rule.
**Rulebook evidence:** Buffer figures appear as examples and guidelines, not fixed rules.
**Pine Script evidence:** The indicator draws zone boundaries but does not implement entry buffer logic: it is a charting tool, not an order-management system.

**Status:** Guideline, not a rule. Implementation decision only.

**Recommendation:** Use 0.1% as the default entry trigger threshold for scanning (price within 0.1% of proximal line). Make this configurable. Do not treat it as a strategy rule.

**User decision required:** Confirm default buffer percentage for scanning.

---

### E.4. "Explosive" Leg-Out: Relative Size Check

**First audit claim:** The indicator checks body ratio and price achievement. Relative size is unimplemented.
**Rulebook evidence:** Explosive requires body > 50% of range AND structural achievement AND relative size (visually larger than surrounding candles) AND context. The rulebook explicitly states: "A candle with a big body that stays WITHIN the range of surrounding candles achieves nothing."
**Pine Script evidence:** Checks `body_ratio >= 0.5` and `close > combined_high`. No comparison to surrounding candle ranges. Relative size criterion is absent.

**Status:** Genuine gap. The reference implementation is less strict than the rulebook definition.

**Recommendation:** For the Python tool, implement the indicator's definition (body > 50% + price achievement) as the minimum bar. The relative size check is a qualitative criterion; a proxy implementation could compare the leg-out candle's range to the average range of the preceding 5 candles (e.g., range ≥ 1.2× average). This is an approximation. Flag these for manual review rather than treating them as automatic pass/fail.

**User decision required:** Confirm whether to implement a relative-size proxy, and if so, what multiplier to use.

---

### E.5. DL Breach: Delete or Mark as Tested-2+?

**First audit claim:** Open question. Two options presented.
**Rulebook evidence:** Zone is invalid once price closes beyond the distal line.
**Pine Script evidence:** Lines 2605–2656: zone is **permanently deleted** from all arrays when close crosses distal. Not marked as tested-2+. The deletion is unconditional.

**Status:** RESOLVED. The reference implementation is unambiguous. DL breach = permanent deletion.

**Decision:** Not open. Match the indicator: delete zones on DL breach (close beyond distal). Do not carry them forward as tested-2+.

**No user decision required.** Implement as permanent deletion.

---

### E.6. Leg-In Detection Window

**First audit claim:** 3-bar window is implemented. Rulebook silent.
**Rulebook evidence:** No specification of the detection window.
**Pine Script evidence:** `bar_index - last_strong_index <= 3` plus a secondary fallback evaluating `bar[1]`. Confirmed 3-bar maximum.

**Status:** Unspecified in rulebook. Implemented in indicator. 3-bar window is the reference implementation.

**Recommendation:** Use 3-bar window as the default. This is the reference implementation's value and is consistent with the visual definition of a pattern (leg-in, then immediately base, then leg-out without large gap in between).

**No user decision required.** Use 3 bars.

---

### E.7. Weekly Trailing Stop-Loss Algorithm

**First audit claim:** Unspecified algorithmically. Defer.
**Rulebook evidence:** References trailing SL at weekly structure levels but provides no algorithmic rule.
**Pine Script evidence:** Not implemented in the indicator.

**Status:** Genuinely unspecified. Cannot be automated without user-defined rules.

**Recommendation:** Defer to Phase 2. The scan tool's purpose is zone identification and scoring, not trade management. SL management is a per-trade decision. Note in the tool's output the weekly proximal/distal levels that a user could use as trailing SL reference points.

**No blocking decision required.** Defer.

---

### E.8. Long-Only vs Bidirectional (NSE CNC Constraint)

**First audit claim:** NSE CNC does not permit overnight short positions. Supply zones are informational only.
**Rulebook evidence:** Strategy is bidirectional on paper (supply zones scored symmetrically). NSE CNC delivery mechanism prevents short selling.
**Pine Script evidence:** Indicator scores and displays both demand and supply zones symmetrically.

**Status:** Operational constraint, not a strategy rule. The Pine Script cannot know whether the user is trading CNC or F&O.

**Recommendation:** Implement both zone types in scoring. In trade output, tag supply zones as "F&O only / Not eligible for CNC short." Allow a configuration flag to suppress supply zone alerts for users trading CNC-only accounts.

**User decision required:** Confirm whether the initial implementation should suppress supply zone alerts entirely, or display them with a CNC-ineligible tag.

---

### E.9. Stock Universe and Filtering

**First audit claim:** Implementation decision, not a strategy rule.
**Rulebook evidence:** No specific stock universe defined. Sector alignment required for trade qualification.
**Pine Script evidence:** Single-symbol indicator. No universe logic.

**Status:** Pure implementation decision.

**Recommendation:** Start with Nifty 50 + Nifty Next 50 as the initial scanning universe. Add filtering for minimum average daily volume (e.g., ≥ 500K shares) and price range (e.g., ≥ INR 100). These are operational constraints, not strategy constraints.

**User decision required:** Confirm universe and liquidity filters for the initial build.

---

### E.10. Data Source for NSE Historical Data

**First audit claim:** Implementation decision.
**Rulebook evidence:** Not applicable.
**Pine Script evidence:** Not applicable (TradingView handles data internally).

**Status:** Pure implementation decision.

**Recommendation:** Zerodha Kite API (historical data endpoint) is the natural choice given the broker. For backtesting, NSE bhavcopy or Zerodha's historical API provides daily OHLC. For intraday candles (75min/125min), Zerodha's historical API supports 1-min granularity that can be resampled. Confirm API rate limits before designing the scanning loop.

**User decision required:** Confirm whether Zerodha Kite API is the approved data source, and whether a paid NSE data subscription is available as an alternative.

---

## Section 6. Technical Risks Requiring Validation

**Risk T1: Candle Resampling for 75min/125min**
Standard resampling from 1-min data to 75min or 125min must align candle boundaries exactly with NSE session start (09:15 IST). A misaligned resample produces candles that span two sessions or cut candles short. Validate: the first candle of each day starts at 09:15 and each candle closes at exactly 09:15 + N×75 (or N×125).

**Risk T2: `barstate.isconfirmed` Replication**
The Pine Script runs all logic on confirmed (closed) bars only. In a Python live scan, "confirmed bar" means a candle whose period has closed. Scanning on the last bar of a 75-min candle before close would produce look-ahead bias. Implementation must only process fully closed candles.

**Risk T3: SMA-50 Ranging Dead Band**
The ranging threshold is `sma50 > sma50[1] * (1 + pct/100)`. A Python port that uses `sma50 > sma50[1]` (simple comparison) will classify many ranging markets as trending. The multiplicative dead band is essential to replicate.

**Risk T4: Sector Alignment Scoring Gap**
The +2 sector confluence score requires live Nifty 50 and sector index data alongside stock data. The Pine Script does not implement this. A Python tool that includes sector scoring will diverge from the reference implementation's actual scores. If sector scoring is included, it must be clearly marked as an extension beyond the indicator.

**Risk T5: Zone Deletion on DL Breach Is Irreversible**
The indicator permanently deletes zones on DL breach. A Python implementation using a database or dataframe must handle deletion correctly: not just flag the zone as invalid. If the data store is append-only (e.g., a log), a separate invalidation record must be maintained and the active zone list must exclude invalidated zones.

**Risk T6: Weekly Invalidation Timing**
Weekly zone invalidation uses the previous week's close (`w_close1`) and fires on the first bar of the new week. In a Python implementation, this means weekly zone checks must run at Monday's first 75min/125min candle open, using Friday's closing price. Running the check at any other time would produce different invalidation behaviour.

**Risk T7: Zero-Base Zone Score Decay**
Zero-base zone scores start at 7.0 (no gap) or 7.5 (with gap). As time passes, the time_score component decays: 0–3 bars → 2.0, 4–7 bars → 1.5, 8–15 bars → 1.0, 16+ bars → 0.5. A zero-base zone without a gap that has aged past 7 bars falls to total 6.5: below the 7/7 threshold. The scoring must be recomputed on each scan iteration, not stored as a fixed value at creation.

**Risk T8: HTF Data Alignment**
Weekly and monthly zone detection uses previous completed period OHLC (`w_low1`, `w_high1`, `m_low1`, `m_high1`). In Python, fetching HTF data must correctly identify the previous completed period, not the current in-progress period. Using the wrong period is a form of look-ahead bias.

---

## Section 7. Pre-Implementation Blockers

These items must be resolved before implementation begins. Items are ordered by dependency.

**Blocker B1: Scoring Denominator: 14 or 15?**
The Part C table says 14. The Quick Reference says 15. The tool cannot display a score without declaring a denominator. The unseen "+1 Pattern" factor is post-entry, not pre-entry.
**Required action:** User declares "use 14" or "use 15 with Pattern as a defined post-entry factor."

**Blocker B2: Tested-Once Zone Treatment**
Essential Check #3 says filter. Priority Rank 3rd says surface. The scan tool cannot implement both simultaneously at the filtering stage.
**Required action:** User declares default filter behaviour (hard filter at 7/7 vs. two-tier output).

**Blocker B3: Zero-Base Zone Eligibility Threshold**
Zero-base zones have core = 5.0 (no H2 points). They meet 7.0 total only via time_score=2.0 (0–3 bars). Once the zone is older than 3 bars, total falls to 6.5 (time_score=1.5 at 4–7 bars), then 6.0, then 5.5. The time window during which a zero-base zone is eligible is very short.
**Required action:** User confirms whether zero-base zones without a gap are eligible only in their first 3-bar window, or whether a lower threshold (e.g., 6.5) applies to zero-base zones specifically.

**Blocker B4: Sector Scoring Implementation Decision**
The indicator does not implement sector scoring. Including it in Python requires a separate Nifty 50 and sector index data feed and logic that does not exist in the reference implementation.
**Required action:** User declares whether Phase 1 includes sector scoring (with custom implementation) or defers to Phase 2.

**Blocker B5: Zerodha Kite API Access Confirmed**
The data source affects every downstream technical decision (rate limits, candle granularity, historical depth, authentication).
**Required action:** User confirms Kite API credentials are available and the historical data endpoint is accessible at the required granularity (1-min minimum for 75min/125min resampling).

**Blocker B6: Supply Zone Treatment for CNC Accounts**
Scoring supply zones requires the same logic as demand zones. But if the implementation is CNC-only, surfacing supply zones as actionable alerts is incorrect.
**Required action:** User declares whether supply zones appear in output (with CNC-ineligible label) or are suppressed entirely in Phase 1.

---

## Section 8. Recommended Next Step

**Immediate action:** Resolve Blockers B1 through B6 above. These are brief decisions that unblock all downstream design work.

**Suggested format:** Review each blocker and provide a one-line decision:
- B1: Score /14 or /15?
- B2: Hard filter at 7/7, or two-tier output including tested-once?
- B3: Zero-base zones eligible only in first 3 bars (no-gap case), or lower threshold?
- B4: Sector scoring in Phase 1 (custom implementation) or deferred?
- B5: Kite API confirmed available?
- B6: Supply zones shown with label, or suppressed in Phase 1?

Once blockers are resolved, the recommended build sequence is:

1. **Data layer:** Kite API wrapper → fetch 1-min OHLC → resample to 75min/125min → resample to daily, weekly, monthly. Validate candle alignment against known NSE session times.
2. **Candle classifier:** Port `f_classify_candle` (strong/weak/doji by body ratio) to Python. Unit test against known candles.
3. **Trend engine:** Port SMA-50 with multiplicative ranging dead band. Validate against indicator output on the same chart.
4. **Zone engine:** Port pattern detection (DBR/RBR/RBD/DBD + zero-base), scoring function, pending window, DL breach deletion, test count increment. Unit test each pattern type independently.
5. **HTF conflict check:** Port `f_check_zone_conflict` for weekly/monthly opposing zones. Validate that it applies to both demand and supply daily zones.
6. **Scanner loop:** Iterate the stock universe, apply zone engine per symbol, filter by score threshold, output ranked list.
7. **Output layer:** Format results for review. Tag zone type, score, freshness, time decay status, and CNC eligibility.

Phase 2 (deferred): Sector alignment scoring, trailing SL management, Zerodha order placement integration, backtesting harness.

---

*This report is a validation document only. No existing files were modified. All findings are traceable to specific line numbers in the Pine Script or specific sections of the Trading Rulebook as cited above.*
