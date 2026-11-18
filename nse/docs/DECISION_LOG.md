# Decision Log

**Project:** NSE GTF Demand & Supply Swing-Trading Research System
**Version:** 3.0, dated 2026-11-02. v3.0 records product-owner-approved M1 decisions R1-R6; D41 remains proposed for readings not covered by those approvals. v2.9 added D41 (research-pipeline interpretations; `PROPOSED`, pending review). v2.8 added D40 (official calendar tables 2021-2025, B17; `PROPOSED`, pending review). v2.7 added D39 (per-date calendar ambiguity, audit L10 option B). v2.6 records the user's approval of P1-P3 as D36-D38 and the provisional approval of the D30 special-session rule (§1E). v2.5 added D33-D35 from the Phase 1 correctness audit (`PHASE1_CORRECTNESS_AUDIT.md`). v2.4 adds user-approved decisions D29-D32 (§1D) for the external-validation phase. v2.3 added D24-D28 (§1C) for HTF freshness (B16). v2.2 added D21-D23 (§1B), resolving B13 and B14 and deciding the B8 approach. v2.1 added D12-D17 (§1A). v2.0 replaced v1; §4 maps old IDs to new.

**Current-status note (2026-11-11):** the version sentence above is the 2026-11-02 record. Sections 1F-1H are the later record through D61. D40 is `USER_APPROVED` in section 1F. D41 is `USER_APPROVED` only for the readings section 1F names. D42 remains `USER_STATED`. Do not treat a fixed number in another document as proof that D61 is still the last entry; read this file.

**ID note:** D18–D20 are not reused. They appear in the v1 history table (§4) with different meanings, so the new decisions start at D21.
**References:** `RB n` = Trading Rulebook line; `PS n` = Pine Script line. Blocker IDs (B*, N*) are defined in `IMPLEMENTATION_BLOCKERS.md`.

**Repository layout (since 2026-10-26):** everything for this project lives under `nse/`. The two reference sources are in `nse/sources/` (kept byte-for-byte; their SHA-256 hashes are pinned by `tests/test_repo.py`). The four current documents are in `nse/docs/`, the two superseded audit reports in `nse/docs/archive/`, and the Zone Engine in `nse/zone-engine/zone_engine.py` (tests in `tests/`).

**Status tags**

| Tag | Meaning |
|---|---|
| `USER_APPROVED` | Explicit user decision. Authoritative. It is never reclassified as unresolved. |
| `SOURCE_DEFINED` | Stated explicitly in the Rulebook. |
| `PINE_DEFINED` | Observed Pine behaviour where the Rulebook is silent. Used only if it does not conflict with an explicit rule (D12). |
| `USER_STATED` | Recorded owner instruction that is an operating constraint within its exact wording and scope. Binding for that scope. Not a Rulebook rule, not a methodology change, and not interchangeable with `USER_APPROVED`. It does not override an explicit Rulebook requirement. |
| `OPEN` | Needs a user decision. Listed in `IMPLEMENTATION_BLOCKERS.md`. |
| `WITHDRAWN` | A v1 decision that was unsupported or rejected by the user. |

---

## 1. User-approved decisions (authoritative)

### D1. Stock universe: Nifty 100
- **Status:** `USER_APPROVED`
- **Evidence:** User decision. Consistent with RB 3684–3685 (watchlist built from Nifty 50 and Nifty Next 50) and RB 3702 (liquidity: "stick to Nifty 50 / Next 50").
- **Approved behaviour:**
  - Phase 1 scans the current Nifty 100 constituents.
  - The list comes from the official NSE Indices constituent file. The exact source location is to be confirmed at implementation; nothing was downloaded during this task.
  - The list is versioned with an effective date and refreshed when NSE Indices announces constituent changes. Periodic reviews and ad-hoc replacements are both covered; the review cadence is to be verified from NSE Indices methodology.
- **Consequences:**
  - A universe-manager component (spec §9.1) with symbol ↔ ISIN ↔ data-vendor instrument mapping.
  - Symbol changes, mergers and delistings must be handled.
- **Remaining uncertainty:**
  - **The current list is not a valid historical universe.** A point-in-time membership history plus data for removed or delisted securities is a separate requirement (**B11**). It blocks historical validation only.
  - Any backtest run on today's constituents must be labelled *survivorship-biased* and must not be cited as validation.

### D2. Long-only CNC equity swing trades
- **Status:** `USER_APPROVED`
- **Evidence:** User decision. Consistent with RB 2262 (no F&O substitute for cash shorts) and RB 2260 (beginners: cash equity only).
- **Approved behaviour:**
  - Detect demand **and** supply zones on every timeframe.
  - Only fresh **demand** zones on the execution TF may become actionable long candidates.
  - Supply zones are used as resistance, HTF context (Curve top, HTF conflict, obstacle map) and target information (structural target = PL of the nearest fresh ITF supply, RB 551–558).
  - **No short candidates are generated.**
- **Consequences:** Only the long rows of the curve and MTFA tables apply (RB 439–443, 1887–1903). HOC/VHOC locations reject longs (RB 1600–1601, 1901).
- **Remaining uncertainty:** None.

### D3. Tested zones are never used for entries and are excluded from scanner results
- **Status:** `USER_APPROVED`
- **Evidence:** User decision. Supported by RB 264, 272, 289, 600, 619 (Essential Check 3), 1515–1520 (zone death: "remove from active consideration"). Conflicting passages are overridden: RB 291, 676, 826, 1011, 1920, 2688, 3269 (see SOURCE_COVERAGE_REPORT RC2).
- **Approved behaviour:**
  1. Freshness is tracked faithfully: `test_count` updated on every completed candle per the touch rule (RB 683–697). Breaches are tracked faithfully too.
  2. A **separate eligibility filter** then excludes every zone with `test_count ≥ 1` from the scanner's **displayed zone results** and from **actionable candidates**. Tested zones are **not** listed as flagged rows.
  3. There is **no Type 2 tier and no tested-zone tier**.
  4. The Pine indicator's own chart display (yellow/grey tested zones, PS 41–45, 860–863) is **unchanged**.
- **Consequences:**
  - Tested zones exist only as internal state.
  - Context use of that state is settled by D15 (coinciding: an HTF zone qualifies while its DL is untouched) and D12 (HTF conflict: tested opposing HTF zones → manual review).
  - The 1.5 and 0.0 freshness values never appear in scanner output.
- **Remaining uncertainty:** None for the entry rule. Context handling is in D12 and D15.

### D4. Pre-entry score is out of 14; post-entry Pattern point is separate
- **Status:** `USER_APPROVED`
- **Evidence:**
  - Arithmetic: core 3 + 2 + 2 = 7 (RB 826–829); confluence factors 1–5 = 2 + 2 + 1 + 1 + 1 = 7 (RB 996–1000); **total 14 = RB 1001** and RB 653.
  - The "/15" headings and tables (RB 988, 1009–1012, 1029, 1070–1078, 2436, 3727, 3799) add the post-entry "Pattern confirms post-entry → +1" (RB 1068), which is defined nowhere else.
  - Part B's "MAXIMUM 8" (RB 845) equals 7 + Pattern. **The component arithmetic reconciles cleanly with /14. No component value was changed.**
- **Approved behaviour:**
  - Display the pre-entry total as `X/14`.
  - Never display `/15`.
  - Record the Pattern point only as a post-entry journal field. Never use it for pre-trade qualification.
- **Consequences:**
  - Part E categories (RB 1027–1033) are written on a /15 scale. The scanner applies the category thresholds to the /14 pre-entry value. The maximum attainable is 14, inside the "12–15 Exceptional" band.
  - Alert-note fields use /14 (the rulebook template shows X/15).
  - Unevaluated components (sector, D6) are shown as *not evaluated*, with an upper bound (spec §5.3).
- **Remaining uncertainty:**
  - The informal "/10" (RB 602, 2727, 3001) and "/8" (RB 489, 853, 891, 2858) references are unreconciled. RF3's "10/10 score" override condition is therefore ambiguous; RF3 overrides are Manual.
  - The Window-gap double count between Strength and CF4 is unresolved (N6).

### D5. Zero-base zones remain eligible for assessment
- **Status:** `USER_APPROVED`
- **Evidence:** Pine zero-base path PS 1717–1762 (daily), 2135–2176 (weekly), 2549–2590 (monthly); score PS 594–602; full trace in SOURCE_COVERAGE_REPORT §5.
- **Approved behaviour:**
  - Zero-base zones are detected and assessed like any other zone.
  - They are never rejected solely for `base_count = 0`.
  - They are never treated as automatically exceptional (Pine sets `is_exceptional = false`, PS 1736/1755).
  - No lower-timeframe base candles are invented.
- **Exact Pine score:**
  - **At creation:** freshness 3.0 + strength (1.0 without window gap / 2.0 with `low > high[1]`) + base component 2.0 = **6.0 / 7.0**.
  - **Later changes:** +1 `legout_count` per confirmed strong same-direction bar in bars 1–3 after creation, *only while it is the most recent zone* (no-gap 6.0 → 7.0). Tests reduce freshness. DL close-breach deletes the zone. **No time decay.**
- **Consequences:** Assessment proceeds. Scoring follows **D13**: Pine's zero-base scoring is the initial reference, and it is labelled as not defined by the rulebook.
- **Remaining uncertainty:** Revisit if source validation (parity tests, B10) shows a conflict (D13).

### D6. Sector scoring deferred
- **Status:** `USER_APPROVED`
- **Evidence:** RB 484–499, 851–895, 2854–2949. Pine's alignment label (PS 2949–2983) is display-only and uses a different method (SOURCE_COVERAGE_REPORT P20).
- **Approved behaviour:**
  - Sector alignment is **not evaluated** in Phase 1.
  - No points are awarded or deducted for it.
  - No proxy is computed, and Pine's label is not used.
  - The score shows the component as `not evaluated (max +2)`, **never `0`**.
- **Consequences:** Wherever a rule requires sector support, the candidate status is **Manual review: sector not evaluated**. It is not a pass and not a fail. Affected rules:
  - MTFA "LOC + Sideways + 7/7 + Sector support" (RB 1895) and scenario B/C caution cases (RB 1657, 1824);
  - Priority Rank 1 "Sector supports" and Rank 3 "sector +2" (RB 1009, 1011);
  - RF3 override (RB 602);
  - HOC buy exception (RB 1600);
  - tie-breaker 1 (RB 1019);
  - the aggressive-stance table (RB 1493).

  DIT/HIT, where sector is mandatory (RB 873, 2948), are out of scope.
- **Remaining uncertainty:** None for Phase 1 behaviour.

### D7. Entry and stop-loss buffers: rulebook methodology preserved
- **Status:** `USER_APPROVED`
- **Evidence:** Entry tiers RB 2016–2020; SL tiers RB 2097–2102; "guidelines, not rigid rules" RB 2022; volatility adjustment RB 2108–2110; summary ranges RB 305, 332, 351, 2010–2011.
- **Approved behaviour:**
  - The tiers are transcribed exactly (spec §6.2).
  - No midpoint, no minimum, no fixed percentage, no ATR multiplier, no other formula.
  - The scanner reports the buffer **range** and the resulting entry/SL/R:R/quantity **ranges**.
- **Consequences:**
  - The 2:1 check is reported as *pass at every buffer choice / fail at every choice / depends on buffer choice (manual)*.
  - Deterministic backtesting of fills and stops is **blocked (B9)**.
  - The midpoint table in v1 is withdrawn.
- **Remaining uncertainty:** B9 (tier-edge overlap at ₹100/₹500/₹2,000; which price selects the tier; volatility adjustment; inconsistent summary ranges).

### D8. Explosive leg-out follows source-defined rules; qualitative parts are manual
- **Status:** `USER_APPROVED`
- **Evidence:**
  - Pine: body threshold `0.5` default (PS 12), strict `>` (PS 332, 1436).
  - Achievement: demand `close > max(legin_high, cluster_wick_high)`, supply `close < min(legin_low, cluster_wick_low)` (PS 1434–1439); same for pending (PS 1588, 1591) and W/M (PS 1985–1990, 2399–2404).
  - Rulebook: body > 50% (RB 402); four-factor test (RB 736–741).
- **Approved behaviour:**
  - The body/range threshold and price-achievement condition are applied as in Pine.
  - The rulebook's relative-size and context criteria are **not** converted into a numeric multiplier. Each candidate carries a **manual-review item: "confirm leg-out is visibly larger than surrounding candles and breaks the prior range"**, with the evidence shown (leg-out range, base ranges, prior swing extremes).
- **Consequences:**
  - No candidate is fully automated. Every actionable candidate carries this manual check.
  - Pine's extra strong-candle path (`close > high[1]` without body > 50%, PS 332) is a rulebook/Pine disagreement (PR1). Under **D12** it is not used; affected cases → manual review.
- **Remaining uncertainty:** None beyond the manual-review routes in D12 (PR1, PR3).

### D9. Weekly trailing stop not automated
- **Status:** `USER_APPROVED`
- **Evidence:** RB 2314–2329, 2768–2853. "Quality weekly DZ" is undefined beyond the descriptive criteria at RB 2798.
- **Approved behaviour:**
  - No trailing algorithm.
  - Where data allow, the scanner may list the distal lines of fresh weekly demand zones above the entry, labelled **"Reference only: not an automatically updated stop."**
- **Consequences:** ATH or overhead-clear candidates (RB 113, 2318–2320) have no automated target. They are reported as Manual, with the 2:1 mathematical target (RB 2308) shown as a reference only.
- **Remaining uncertainty:** None for Phase 1.

### D10. Zerodha Kite Connect is the data-source option to investigate
- **Status:** `USER_APPROVED` (as an option to investigate; **nothing confirmed**)
- **Evidence:** User decision.
- **Approved behaviour:**
  - The research-only scanner does no order placement and no broker execution.
  - No connection, credential or API call was made during the documentation phase.
  - Before implementation, verify against current official documentation: subscription status; historical intervals and lookback per interval; corporate-action adjustment; rate limits; licensing for storing data.
- **Consequences:**
  - The data layer must sit behind a vendor-neutral interface, so another source can be swapped in (e.g. NSE bhavcopy for daily EOD, availability to be verified).
  - Credentials, when they exist, must never be committed to the repository.
  - Verification scope is extended by **D17**.
- **Remaining uncertainty:** **B6** (all Kite capabilities unverified).

### D11. Full timeframe hierarchy preserved
- **Status:** `USER_APPROVED`
- **Evidence:** RB 125–132, 1104–1115, 1525–1530. Essential Check 1 omits HY (RB 617); D11 overrides that omission.
- **Approved behaviour:**
  - TDA covers **Yearly → Half-Yearly → Quarterly → Monthly → Weekly → execution TF**, never shortened.
  - Q/HY/Y zone detection is a Python extension of the Pine algorithm. Pine draws no Q/HY/Y zones (it only computes their EMA20 at PS 295–297 and SMA50 trend at PS 312–316), so no Pine parity is possible for those zones.
- **75/125-minute role (verified):**
  - WIT execution TF (RB 180, 1396, 1768, 3610);
  - DIT trend TF (RB 181, 1412, 1669);
  - HIT location TF (RB 182, 1430, 1576);
  - refinement / hidden-LOTL checks (RB 383, 818–820, 2762);
  - recency rule: last 8–10 candles for WIT/DIT execution zones (RB 1403, 1788–1803), MIT exempt (RB 1803);
  - candle alignment: 375-min session ÷ 125 = 3, ÷ 75 = 5 (RB 186–193).
- **Consequences:**
  - Phase 1 includes WIT (75/125 execution) per **D16**.
  - Q/HY/Y candles are calendar-aligned, with minimum-history rules (**D23**). TradingView verification stays open (B8 validation, B10).
  - For daily execution, Weekly **and** Monthly trend are both evaluated (**D14**). The general hierarchy does not replace those checks.
- **Remaining uncertainty:** TradingView parity of the D23 candles (B8 validation, B10).

---

## 1A. User-approved decisions added in v2.1

### D12. Source precedence: rulebook-strict
- **Status:** `USER_APPROVED` (resolves former B1)
- **Approved behaviour:**
  1. Explicit rulebook rules take precedence.
  2. Pine behaviour is used **only** where the rulebook is silent **and** the behaviour does not conflict with an explicit rulebook requirement.
  3. Where they conflict, or the rulebook is ambiguous: document the exact discrepancy and route the **affected decision** to manual review. The scanner computes the rulebook-strict result and shows the Pine result beside it.
  4. No invented rules. The Pine Script is not modified. Source references are kept.
- **Consequences for each recorded discrepancy** (SOURCE_COVERAGE_REPORT §6):

| ID | Discrepancy | Resolution under D12 |
|---|---|---|
| PR1 | Pine counts `close > high[1]` as strong without body > 50% | **Rulebook:** strong/explosive requires body > 50% (RB 402). The Pine-only path is not a strong candle. Where it would change a zone or score → manual review. Applies to leg-in, leg-out, zero-base and leg-out counting. |
| PR3 | Pine makes close-beyond-(leg-in + base)-extreme mandatory for creation | The rulebook requires "price achievement" for an explosive leg-out (RB 739) but gives no numeric test. **Pine's condition is used as the objective minimum test** (silent, no conflict). Leg-outs failing it cannot score strength (RB 730) and are not execution candidates. Patterns failing it are kept as **manual-review HTF context only**, because HTF location zones may have weak leg-outs (RB 1639). |
| PR4 | Pine default max 3 bases; transitions not counted | **Rulebook** scores 4–5 bases (RB 786), so detection uses Pine's existing option `max base candles = 5` (PS 10). 6+ bases form no zone, consistent with "reject" (RB 787). Counting transition candles is ambiguous: the rulebook calls a big-bodied candle inside the range "functionally a base candle" (RB 404, 739, 769). **Both counts are reported**, and manual review applies if the score band differs. Parity tests must configure the indicator with max = 5. |
| PR5 | Pine leg-out count: any strong bar in bars 1–3, latest zone only | Count is **per zone** (the rulebook counts the candles moving away from that zone's base, RB 728). Only body > 50% candles count (PR1). The 3-bar window is Pine (rulebook silent). Non-consecutive or interrupted sequences → manual review. Where Pine's latest-zone freeze gives a different count → difference shown, manual review. |
| PR6 | Pine counts gaps of any size | The rulebook requires a meaningful gap (RB 941, 2974) with no numeric test → gap size shown, manual review. |
| PR8 | Pine tests HTF zones only at the next HTF bar | **Rulebook:** any candle touch, updated every session (RB 264, 292, 683, 1508). HTF freshness is updated on every completed candle of the finest TF processed (daily, or 75/125-min for WIT). |
| PR10 | Pine tests pending zones from the bar after the achievement bar | Rulebook: from the candle after the leg-out (RB 682). Which candle is the leg-out in a pending case is ambiguous → a touch between the original leg-out and the achievement bar → manual review. |
| PR18 | Pending zone: Pine counts one leg-out from the achievement bar (PS 688, 1646), though the failed first leg-out also had body > 50% | Ambiguous: RB 728 counts "2+ explosive candles", but RB 739 also asks for price achievement. The engine keeps Pine's count as the primary reading, adds a reading that also counts the first leg-out, and raises `PENDING_LEGOUT_COUNT_AMBIGUOUS` (manual review) when the two give different scores. An alternative 7/7 never makes a zone eligible (found by the Zone Engine audit, P12). |
| PR11 | Conflict scope and threshold | **Rulebook:** opposing Monthly, Quarterly and Half-Yearly zones (RB 1302–1304, 1158). Inside an opposing zone or within 5% → conflict (both readings of "5–10%" agree). 5–10% → manual. Pine's Weekly check and the Yearly check are not in the rulebook list → manual-review evidence, not auto-reject. Tested opposing HTF zones (Pine counts `test_count < 2`; rulebook ambiguous, RB 1639) → manual-review evidence. |
| PR12, PR17 | Display toggles / chart TF gate detection | Detection is independent of display (no rulebook basis for gating) |
| PR13 | Trend quantification | See D14 |
| PR16 | PL/DL marking method | Rulebook names it without defining it → Pine "Body to Wick" (PS 1470–1490) |
| - | Leg-in window (3 bars), pending window (1 later bar on chart TFs D/125m/75m; 2 on W/M and the Q/HY/Y extension; SOURCE_COVERAGE_REPORT P8), base threshold ≤ 50%, transition ≤ 75% inside wicks | Pine (rulebook silent, no conflict) |

- **Remaining uncertainty:** each manual-review route above is a **source ambiguity**, listed in `IMPLEMENTATION_BLOCKERS.md` Part 4.

### D13. Zero-base scoring: Pine reference, explicitly not rulebook-defined
- **Status:** `USER_APPROVED` (resolves former B2)
- **Approved behaviour:**
  - Zero-base zones remain eligible for assessment (D5).
  - Pine's zero-base scoring (PS 594–602, 1717–1762) is the **initial implementation reference**:
    - base component 2.0 for `base_count = 0`;
    - strength from `legout_count` and the leg-in/leg-out gap;
    - freshness as normal.
  - Every zero-base score carries the trace tag **`ZB-PINE-REF: base component for 0 bases is Pine-defined (PS 601); the rulebook table starts at 1 base (RB 785–787)`**.
  - Zero-base zones may be actionable on this basis.
- **Interaction with D12:**
  - Both zero-base candles must satisfy body > 50% (PR1); a Pine-only close-break candle → manual review.
  - The gap must be meaningful (PR6, manual).
  - Leg-out counting follows PR5.
- **Remaining uncertainty:** Revisit if parity or source validation shows a conflict. The tag keeps every affected result identifiable.

### D14. Trend for Daily execution: evaluate Weekly and Monthly
- **Status:** `USER_APPROVED` (narrows former B3; Monthly role set by **D21**)
- **Approved behaviour:**
  - For any trade with Daily execution (MIT), evaluate the **Weekly and Monthly** trends. Both are mandatory.
  - The Y → HY → Q → M → W → execution hierarchy (D11) is kept and does not replace these checks.
- **Method (only as far as the sources support):**
  - SMA-50 clock (RB 1672–1711; SMA for the first 100 trades, RB 1748) on completed Weekly and Monthly candles.
  - The rulebook gives no numeric angle, so Pine's clock formula is the numeric reference (silent, no conflict): `pct = (SMA50 − SMA50[5]) / SMA50 × 100`, thresholds ±0.1 / 0.4 / 1.0 / 2.0 (PS 252–291).
- **Mapping to rulebook readings** (RB 1686–1695):

| Pine position | Rulebook reading | Status |
|---|---|---|
| 12 | Extreme up | Clear |
| 1 | Between "12–1 strong" and "1–2 moderate" | Up is clear; strong vs moderate ambiguous |
| 2 | Between "1–2 moderate" and "2–3 mild" | Up is clear; strength ambiguous |
| 2–3 | Mild up; "any doubt → sideways" (RB 1708) | Ambiguous (up or sideways) |
| 3 | Sideways | Clear |
| 3–4 | Mild down; "any doubt → sideways" | Ambiguous (down or sideways) |
| 4, 5, 6 | Down | Clear |

  Ambiguity matters only where it changes the matrix outcome (e.g. EQB needs Strong Up; VLOC + Moderate is absent). In those cases → manual review.
- **Roles:**
  - **Weekly** = ITF trend in the MTFA matrix (RB 1378, 1667).
  - **Monthly** trend: the rulebook gives it no gating role (only RB 1193 and RB 1232: "if weekly trend opposes your monthly location bias, proceed with extreme caution"). It is **reported for every daily-execution candidate**. Its role is settled by **D21**: mandatory context, not a gate. (The v2.1 proposed flag "Monthly down → manual review" is withdrawn.)
- **Insufficient history:** the clock needs SMA50 now and 5 candles earlier, i.e. ≥ 55 completed candles of that TF (D23) → otherwise "insufficient history". Never "Ranging". For Weekly (the gate) this → manual review. For Monthly (context) it is reported only.
- Pine's dead-band Up/Down/Ranging method (PS 304–316) is reported as secondary context only.

### D15. Coinciding confluence from higher-timeframe zones
- **Status:** `USER_APPROVED` (user-stated rule; resolves the coinciding part of former B4)
- **Approved behaviour:**
  - A lower-TF setup may receive coinciding-trade confluence from a relevant HTF zone when that zone **exists** and **price has not touched its distal line** since creation. A wick touch of the DL disqualifies it.
  - A PL touch alone (a "tested" zone) does **not** disqualify it for coinciding evidence.
- **Separation from entry rules:**
  - D3 is unchanged. Tested zones are never entry zones and never appear in displayed zone results or candidate lists.
  - A tested-but-DL-intact HTF zone may appear **only as cited evidence** inside a candidate's coinciding classification.
- **Relevant HTF zone:** the HTF **location** zone for the trade type: Monthly demand for MIT, Weekly demand for WIT (RB 1574, 1394).
- **Geometry** (rulebook):
  - LTF PL inside the HTF zone (between its PL and DL) → Coinciding (RB 528, 1833, 1853).
  - LTF zone below the HTF DL → Invalid (RB 1856).
  - LTF PL above the HTF PL → **manual review**: "directly touching" has no tolerance.
  - Aggressive classification needs "achievement" (RB 1847) → manual review.
- **Note:** the Curve still uses **fresh** HTF zones only (RB 445, 1215, 1587). The coinciding zone and the curve boundary can differ; if the outcome depends on the difference → manual review.
- **Remaining uncertainty:** The rule above is recorded exactly as stated. Any case it does not determine is flagged for manual review rather than guessed.

### D16. Phase 1 covers MIT and WIT
- **Status:** `USER_APPROVED` (resolves former B5)

| | MIT | WIT |
|---|---|---|
| HTF location (Curve) | Monthly (RB 1377, 1573) | **Weekly**, curve between fresh weekly D/S zones (RB 1394, 1574) |
| ITF trend | Weekly + Monthly evaluated (D14) | **Daily** (RB 1395, 1668) |
| LTF execution | Daily | **75-min and 125-min** (RB 1396, 1768, 3610); 125-min preferred (RB 1404) |
| Core | 7/7 | 7/7 (RB 1396) |
| Extra checks | - | Weekly location must not conflict with Monthly structure; "a perfect weekly DZ inside a Monthly SZ is toxic" (RB 1402). Execution zone recency: last 8–10 candles (RB 1403, 1788) |
| Structural target | Nearest fresh opposing Weekly zone PL (RB 557) | Nearest fresh opposing **Daily** zone PL (ITF, RB 551–558) |

- **Rules flagged for manual review (source ambiguous):**
  - Recency band: formed within the last 8 candles → passes under every reading. 9–10 → manual. >10 → manual, and >20 must re-verify HTF conditions (RB 1788 vs 1797–1801, RC8).
  - Weekly DZ **near** (not inside) a Monthly SZ → manual. Inside → reject.
  - Both 75 and 125 candidates at the same price area → reported separately with the 125 preference noted; no combination rule exists.
  - The rulebook's "after 50+ successful MIT trades" prerequisite (RB 180, 3556, 3615) is a trader-progression rule. It is shown as an informational note; it does not gate.
- **WIT trend handling:** settled by **D22** (rulebook matrix with WIT roles; no added Weekly/Monthly trend gates).
- **Candles:**
  - 75-min boundaries: 09:15, 10:30, 11:45, 13:00, 14:15 → 15:30.
  - 125-min boundaries: 09:15, 11:20, 13:25 → 15:30.
  - Built only from session-aligned finer data (e.g. 1- or 5-minute; 15-minute does not divide 125). **Never substituted with 60- or 120-minute candles** (RB 184–193).
  - Incomplete or special-session candles are flagged and excluded.

### D17. Kite Connect: pending investigation (extends D10)
- **Status:** `USER_APPROVED`
- **Approved behaviour:**
  - Kite Connect is **not** an approved or verified integration.
  - No credentials are requested, stored or used. No broker connection. No orders.
  - Before implementation relies on it, verify: historical-data coverage (depth per interval); supported intervals; access requirements (subscription, authentication flow); data adjustment; rate limits; storage licence; and **whether 75/125-minute candles can be built reliably** (interval granularity, session alignment at 09:15, completeness of each session).
- **Remaining uncertainty:** B6.

---

## 1B. User-approved decisions added in v2.2

### D21. MIT trend roles: Weekly gates, Monthly is mandatory context (B13, Option A)
- **Status:** `USER_APPROVED` (resolves B13)
- **Rationale:**
  - The rulebook names Weekly as the MIT ITF trend (RB 1378, 1667, 1232: "For MIT trades, the weekly trend is your ITF confirmation").
  - It gives Monthly trend no gating rule. The only related rule concerns Weekly trend vs Monthly **location**: "If weekly trend opposes your monthly location bias, proceed with extreme caution" (RB 1232).
- **Approved behaviour:**
  1. The **Weekly** trend is the primary trend gate in the MTFA matrix (RB 1887–1903).
  2. The **Monthly** trend is always evaluated and reported as mandatory context (D14). It is never a gate, and it alone never causes rejection or manual review. Where it disagrees with the trade direction, it is listed under *evidence against*.
  3. **Weekly trend opposing the Monthly location bias** (bias = buy at VLOC/LOC, RB 1597–1598):
     - the candidate gets the rulebook's **"extreme caution" (RB 1232)** treatment, i.e. status `MANUAL REVIEW: extreme caution (RB 1232)`;
     - no new hard rejection is created;
     - an explicit matrix rejection still applies (e.g. LOC + Down → reject, RB 1896). Caution never turns a matrix rejection into a pass.
- **Consequences:**
  - Removes the v2.1 proposed "Monthly down → manual review" flag.
  - Monthly trend that cannot be computed is reported as "insufficient history" without blocking.
- **Remaining ambiguity (→ manual review):**
  - "Extreme caution" has no operational definition (sizing, extra checks) → manual.
  - Weekly *Sideways* or ambiguous clock bands vs a buy bias: the rulebook does not say whether that "opposes" the bias → manual.
  - EQB has no location bias, so RB 1232 does not apply.

### D22. WIT trend handling follows the rulebook's matrix, no added gates (B14, Option C)
- **Status:** `USER_APPROVED` (resolves B14)
- **Source finding:**
  - The rulebook contains **no separate WIT-specific trend matrix**.
  - It has one **generic MTFA alignment matrix** (RB 1883–1904), written in terms of Location (HTF), Trend (ITF) and Zone Quality (LTF), and states that only the timeframes filling those roles change by trade type (RB 1370).
  - The role tables assign WIT: location = **Weekly** (RB 1574), trend = **Daily** (RB 1668), execution = **75/125-min** (RB 1768); also RB 180, 1394–1396, 3608–3610.
- **Approved behaviour:**
  1. WIT candidates are evaluated with the rulebook's matrix, using the roles the rulebook assigns to WIT. This applies the rulebook's own role mapping; it is **not** the MIT configuration transplanted onto WIT.
  2. The **Daily** trend is the only WIT trend gate.
  3. **No** Weekly or Monthly trend gate is added for WIT. Weekly/Monthly trend may be shown as context only.
  4. WIT-specific rulebook checks stay as specified in D16:
     - Weekly location vs Monthly structure (RB 1402);
     - recency (RB 1403, 1788);
     - 125-min preference (RB 1404);
     - Monthly curve "for context" (RB 1393).
- **Remaining ambiguity (→ manual review, with source reference):**
  - Whether every matrix row applies identically to WIT. The matrix's worked examples and the Confirmation Entry it references (RB 1892, 2593–2598) are phrased with Monthly/Quarterly zones and Daily charts → any WIT case resting on those rows → manual.
  - Clock-band ambiguities on the Daily trend (D14 table) → manual where they change the outcome.
  - Cells missing from the matrix (RC12) → manual.

### D23. Higher-timeframe candle construction: calendar-aligned (B8)
- **Status:** `USER_APPROVED` (decides the B8 approach). **TradingView parity is NOT verified.**
- **Rationale:** The rulebook does not define period boundaries (RB 1104–1179). Calendar alignment is expected to match TradingView's `3M`/`6M`/`12M` resolutions used by the Pine Script (PS 295–297, 312–316). That expectation is an assumption until compared.
- **Approved behaviour [PROPOSED construction details, pending TradingView validation]:**

| TF | Calendar boundaries (IST, NSE trading sessions only) |
|---|---|
| Yearly | 1 Jan – 31 Dec |
| Half-Yearly | 1 Jan – 30 Jun; 1 Jul – 31 Dec |
| Quarterly | Jan–Mar; Apr–Jun; Jul–Sep; Oct–Dec |
| Monthly | Calendar month |
| Weekly | Trading sessions Monday–Friday of the same calendar week |

  - **OHLCV aggregation:** open of the first session, max high, min low, close of the last session, summed volume. Built from corporate-action-adjusted daily candles (B7).
  - **Completion:** a period candle is used only after the last NSE trading session of that period has closed. The in-progress period is never used for zones, tests, trends or conflict.
  - **Data gaps:** a candle missing any trading session (checked against the NSE calendar) is **incomplete** and is never used. No candles are fabricated or interpolated.
  - **Listing period:** the first candle after listing covers only part of the period. It is tagged `partial_listing_period` and kept for TradingView comparison. Any zone or trend that depends on it → manual review.
  - **Minimum history:** if the completed candles are too few for a calculation, the result is **"insufficient history"**, never a default value. The count of completed candles is always shown.

| Calculation | Completed candles needed | Approx. history: Y / HY / Q / M / W |
|---|---|---|
| SMA-50 clock (`SMA50` vs `SMA50[5]`, PS 252) | 55 | 55 y / 27.5 y / 13.75 y / 4.6 y / ~1.1 y |
| Pine dead-band trend (`SMA50` vs `SMA50[1]`, PS 304–316) | 51 | 51 y / 25.5 y / 12.75 y / 4.25 y / ~1 y |
| HTF EMA-20 (confluence, provisional) | ≥ 20; seed and convergence to be checked against TradingView | 20 y / 10 y / 5 y / 20 m / 20 w |
| Zone detection | ≥ 2 (zero-base) / ≥ 3 (leg-in, base, leg-out). "No fresh zone found" is reported with the candle count | - |

  - Execution TFs: Daily needs 55 sessions for the clock. 75-min needs 55 candles ≈ 11 sessions; 125-min needs 55 ≈ 18.3 sessions.
- **Consequences:**
  - Yearly and Half-Yearly SMA-50 trends will be "insufficient history" for essentially all Nifty 100 stocks; Quarterly for many. These trends are context only; no rule gates on them.
  - Zone detection on Y/HY/Q still runs on whatever completed candles exist.
  - The full hierarchy (D11) is unchanged: every level is evaluated or reported as insufficient.
- **Remaining validation (open, B8/B10):** compare period boundaries and OHLC values against TradingView for agreed symbols:
  - quarter/half/year starts;
  - holiday weeks and months;
  - listing-period candles;
  - a split/bonus stock;
  - EMA/SMA values.

  Not validated until those comparisons are recorded.

---

## 1C. User-approved decisions added in v2.3 (HTF freshness, B16)

These record the answers to design questions A1-A5 (approved 2026-10-26). They are implemented in `nse/mtf-freshness/mtf_freshness.py`.

### D24. HTF invalidation (A1)
- **Status:** `USER_APPROVED`
- **Approved behaviour:**
  - A **completed** higher-timeframe candle closing beyond the distal line invalidates the zone permanently (PS 2667, 2718; RB 1627, 1741).
  - A base-candle close beyond it is evidence only. Status `BASE_CLOSE_BEYOND_DL_PENDING` (manual review, never fresh) until that higher-timeframe period completes.
  - If the period then closes back inside, the zone is `TESTED`, with `BASE_CLOSE_BEYOND_DL_RESOLVED_NOT_INVALIDATED` kept for review.

### D25. Touch-count granularity (A2)
- **Status:** `USER_APPROVED`
- **Approved behaviour:**
  - Both counts are kept: `base_touch_count` (one per touching base candle) and `htf_test_count` (the Zone Engine / Pine reference view).
  - Only fresh vs tested gates eligibility (RB 264, D3).
  - No new scoring rule.

### D26. Finest reliable base series (A3)
- **Status:** `USER_APPROVED`
- **Approved behaviour:**
  - Touches come from the finest reliable completed series supplied (`D`, or an intraday interval that divides 375 minutes).
  - Every event records `source_tf`, candle start and candle end. A daily base gives day-level timing only.
  - The 75m and 125m execution analyses stay independent.

### D27. Data gaps (A4)
- **Status:** `USER_APPROVED`
- **Approved behaviour:**
  - A missing or partial session after a zone became knowable, and before any touch, makes the zone `UNKNOWN_DATA_GAP`: not fresh context, requiring repair or manual review.
  - A known gap inside a period also ends that timeframe's series (`HTF_SERIES_TRUNCATED_AT_GAP`).
  - Freshness is never inferred from missing candles.
- **Amended by D34:** gaps count from the zone's first formation period, not only after it became knowable.

### D28. Calendar fallback (A5)
- **Status:** `USER_APPROVED` (temporary)
- **Approved behaviour:** without a validated NSE calendar:
  - a period is complete only when a later period's data exists;
  - every missing weekday is an unverified gap;
  - every snapshot carries `CALENDAR_UNVALIDATED`.
- **Production readiness:** not production-ready until calendar boundaries and holidays are validated (**B17**).

---

## 1D. User-approved decisions added in v2.4 (external-validation phase)

### D29. Validation window
- **Status:** `USER_APPROVED`
- **Approved behaviour:**
  - The initial window is 2021-01-01 to 2025-12-31.
  - A test that needs an event outside it is proposed, with a reason, before the window is extended.

### D30. Trading calendar source and special sessions
- **Status:** `USER_APPROVED`
- **Approved behaviour:**
  - The calendar comes only from official NSE capital-market (CMTR) circulars for each year, plus their amendments, with source reference, circular date, year and any unresolved ambiguity recorded (`nse/calendar/nse_calendar.py`, `nse/data/calendar/`).
  - Muhurat and shortened sessions are flagged and **excluded from normal candle construction** until a documented rule is approved.
- **Orchestrator behaviour:** D33.
- **Special sessions on regular hours: `USER_APPROVED` (provisional), 2026-10-27.**
  - A special session may be classified `NORMAL_SPECIAL` (a normal trading day, flagged as special) **only** when official source data verifies that it is a genuine trading session with regular 09:15-15:30 hours.
  - In code (`nse_calendar.py` `session_type`), this requires a `CONFIRMED` `SPECIAL_SESSION` row whose source circular is present and hash-verified, with exactly 09:15-15:30.
  - An unverified source or an `UNRESOLVED` row raises `CalendarAmbiguityError`; it is never guessed. Any other hours give `EXCLUDED_SHORTENED`.
  - "Flagged as special" lives in the calendar (`flagged_dates()`); the orchestrator's snapshot does not carry it.
- **Provisional approval is not external verification.** No special session has been verified. For the 1 Feb 2025 budget session, all of these are outstanding (B6, B8, B17):
  - the official circular (number unconfirmed);
  - its exact hours;
  - the `events.csv` row;
  - end-of-day data availability;
  - TradingView's candle treatment.

### D31. Local files only
- **Status:** `USER_APPROVED`
- **Approved behaviour:**
  - Daily data comes from local NSE end-of-day files and TradingView exports.
  - Loaders record provenance, download date and SHA-256.
  - No network-fetching code.
  - File formats are reported to the user before any loader is built.

### D32. No broker API for intraday data yet
- **Status:** `USER_APPROVED`
- **Approved behaviour:**
  - No connection to Kite Connect or any broker API.
  - Intraday requirements and local-export options are established first (`DATA_REQUIREMENTS.md` §4).
  - If they are insufficient, a separate recommendation goes to the user for explicit approval.

---

## 1E. Decisions from the Phase 1 correctness audit (v2.5)

### D33. Excluded and unclassifiable sessions (audit H1)
- **Status:** `USER_APPROVED`
- **Approved behaviour** (`mtf_freshness.py` `_classify`, `_overlay`):
  - Session classification runs before gap detection, aggregation and freshness.
  - Every set-aside candle is listed in `excluded_candles` with its classification. Nothing is dropped silently.
  - A candle on a calendar-excluded session (`EXCLUDED_MUHURAT`, `EXCLUDED_SHORTENED`) never enters an HTF candle or the touch count.
  - If such a candle reaches a zone's proximal or distal line after creation, the zone needs manual review (`EXCLUDED_SESSION_TOUCH`) and is not usable as fresh.
  - A candle whose session cannot be classified is also kept out. That covers:
    - a weekend date without a calendar (`UNVERIFIED_SESSION`);
    - an intraday candle outside 09:15-15:30 (`UNVERIFIED_SESSION`, or `OUTSIDE_REGULAR_HOURS` with a calendar);
    - a candle on a day the calendar says is closed.
  - Every zone whose span from formation to as-of contains such a date gets status `UNVERIFIED_SESSION` (never fresh).
  - An intraday candle wholly outside the session is classified, not a crash. One straddling 09:15 or 15:30 is still rejected as malformed.
- **Known limit:** without a calendar, a weekday Muhurat or shortened session with regular timestamps is undetectable. Only `CALENDAR_UNVALIDATED` marks it (B17).

### D34. Data gaps from formation (audit H2)
- **Status:** `USER_APPROVED`
- **Approved behaviour:**
  - Gaps count from the first day of the zone's first formation period (leg-in, else base) through as-of, in both calendar and no-calendar modes.
  - Any such gap makes an untouched zone `UNKNOWN_DATA_GAP`.
  - Missing periods are never silently bridged.
- **Measured consequence:** without a calendar, synthetic data with about 15 weekday holidays a year left no untouched W/M zone fresh, before or after this change. B17 is effectively mandatory for real data.

### D35. Base candle closing outside a full cluster (audit M3)
- **Status:** `USER_APPROVED` (option c)
- **Approved behaviour:**
  - When a cluster already holds the maximum 5 bases, a further base candle (body ≤ 50%) that closes outside the cluster is **not** classified as a 6th base (garbage area) and not dismissed.
  - The engine records the event `BASE_CLOSED_OUTSIDE_CLUSTER` and a `rejected_patterns` entry with disposition `MANUAL_REVIEW`. The entry carries the cluster start, the candle index, the base count, the cluster high/low and the close.
  - No zone is created from that cluster.
  - The Rulebook question stays open: RB 787 (6+ base candles) vs RB 802 (6+ *overlapping* base candles).

These three were proposed as P1-P3 after the second-pass review of D33 and D34. Each closes a counterexample documented and tested in `PHASE1_CORRECTNESS_AUDIT.md` §4A.

### D36. Unresolved flags are never reported FRESH (was P1)
- **Status:** `USER_APPROVED`, 2026-10-27
- **Approved behaviour:**
  - An untouched zone with any unresolved manual-review flag reports `MANUAL_REVIEW`, not `FRESH`. Today those flags are `EXCLUDED_SESSION_TOUCH` and `PARTIAL_FIRST_PERIOD`.
  - Status precedence: INVALIDATED > BASE_CLOSE_BEYOND_DL_PENDING > TESTED > UNVERIFIED_SESSION > UNKNOWN_DATA_GAP > MANUAL_REVIEW > FRESH.
- **Nature:** implementation safety and reporting. Eligibility was already blocked; no trading rule changes.

### D37. No stitching across a wholly missing period (was P2)
- **Status:** `USER_APPROVED`, 2026-10-27
- **Approved behaviour:**
  - In calendar mode, a wholly missing expected trading period truncates the affected higher-timeframe series (`HTF_SERIES_TRUNCATED_AT_GAP`, `truncated_at`), as a partly missing one already does under D27. Candles are never stitched across a missing period.
  - This includes missing periods after the last period with data. Before the fix found on 2026-10-27, that case reported no truncation, though the zone was still `UNKNOWN_DATA_GAP` under D34.
  - Without a calendar (D28), missing weekdays are unverified. The series is not truncated, but D34 keeps every affected zone from being fresh.
- **Nature:** implementation safety, extending D27 consistently.

### D38. Daily zones over a daily base (was P3)
- **Status:** `USER_APPROVED`, 2026-10-27
- **Approved behaviour:**
  - `replay(..., base_tf="D", htf=("D",))` is permitted. Daily zones then receive session validation (D33), data-gap checks (D34, D37) and the freshness overlay (`eligible_after_overlay`).
  - This replaces the original replay contract that each timeframe must be coarser than the base. One committed test assertion was changed accordingly.
- **Nature:** an interface change for implementation safety; no trading rule changes.
- **Limits:**
  - A daily base gives no earlier touch timing than the engine itself.
  - Without a calendar, the newest daily candle completes only when the next day's candle exists (D28).
  - 75m/125m zones still have no equivalent path (audit M4b).

### D39. Ambiguous calendar dates are handled per date (audit L10, option B)
- **Status:** `USER_APPROVED`, 2026-10-27
- **Approved behaviour:**
  - Missing calendar coverage (no verified BASE circular for a year) stays a fatal setup error.
  - A date the calendar cannot classify (`NseCalendar.UNRESOLVED_ERRORS`: `CalendarAmbiguityError`, i.e. an `UNRESOLVED` row or an unverified event source) is handled per date. The rest of the replay is not aborted.
  - Candles on that date are set aside as `CALENDAR_UNRESOLVED`.
  - The date never creates a gap, but it still blocks affected zones: every zone whose formation-to-as-of span contains it is `UNVERIFIED_SESSION`.
  - Every higher-timeframe period containing it is truncated (`HTF_SERIES_TRUNCATED_AT_UNRESOLVED_CALENDAR`).
- **Nature:** implementation safety. No trading rule changes, and no calendar fact is inferred.
- **Applied literally:** a period is truncated even when the ambiguous date is after as-of or before the first candle (`PHASE1_CORRECTNESS_AUDIT.md` §4C).

### D40. Official calendar tables 2021-2025; special sessions recorded under D30 (B17)
- **Status:** `USER_APPROVED` 2026-11-08 (section 1F), with the escalated discrepancy D40-Q1 about 20 Jan 2024. Originally `PROPOSED`, 2026-10-28, pending the user's review of this wording. The user approved the underlying decisions on 2026-10-28:
  - keep the supplied 2022 file name;
  - record the archive URL with a byte-identity note, and `downloaded_on=UNKNOWN`;
  - register the 2022 Muhurat notice as confirmed, keeping D30's exclusion;
  - use NSE/CMTR/41180 provisionally for normal hours;
  - register the 2023 circulars, confirming the revised Bakri Id date only on official evidence;
  - keep the circular files local.

  The implementation choices marked *proposed* below were not part of those decisions.
- **Proposed behaviour** (`nse/data/calendar/sources.csv`, `events.csv`; list in `nse/data/calendar/README.md` §1):
  - **Scope: the whole D29 window, 2021-2025.** 19 official NSE sources: 5 base holiday circulars, 4 amendments, 9 session notices and the normal-hours circular NSE/CMTR/41180; 105 events. Every file is held locally and matches its recorded SHA-256. Claude checked every row against the extracted text, and the base circulars and every timing table also on the rendered pages (2026-10-28); the user has not checked them independently.
  - **Bakri Id 2023 is resolved by NSE/CMTR/57285** (2023-06-27, "Change in Trading Holiday", partial modification of NSE/CMTR/54757): 28 June 2023 is a normal session and 29 June a holiday. NSE serves this circular only as a ZIP (circular plus the Maharashtra notification); the ZIP is stored and hashed as served.
  - **Added holidays:** 22 Jan 2024 (NSE/CMTR/60338), 20 May 2024 (NSE/CMTR/61518), 20 Nov 2024 (NSE/CMTR/64960).
  - **D30 is unchanged.** Five Muhurat sessions (2021-2025, Normal Market times from each notice) are `CONFIRMED` `MUHURAT_SESSION` rows and stay `EXCLUDED_MUHURAT`; their candles never enter HTF construction or touch counts (D33). The 2025 session (13:45-14:45) lies inside regular clock hours and is excluded by the calendar, not by the clock. No rule for using Muhurat data is approved.
  - **Shortened sessions:** the DR-switch Saturdays of 2 Mar 2024 (NSE/MSD/60677) and 18 May 2024 (NSE/MSD/61893) had two Normal Market windows, 09:15-10:00 and 11:30-12:30. The schema holds one start and end per row, so each row spans 09:15-12:30 and its note says the session was not continuous. Both are `EXCLUDED_SHORTENED`.
  - **Regular-hours Saturdays (D30 provisional rule):**
    - 1 Feb 2025 (NSE/CMTR/65729) prints Normal Market 09:15-15:30 "as per the standard market timings": `NORMAL_SPECIAL`.
    - 20 Jan 2024 (NSE/MSD/60340) withdraws NSE/MSD/59999, 60300 and 60318 *(correction 2026-11-08: their contents are not held, so the earlier wording "the DR-switch session announced in NSE/MSD/59999" is not verified)* *[2026-11-09: now held and hash-registered; 59999 did announce the two-window DR session, which 60340 withdrew before the day. See the D40 evidence-trail note in section 1F.]* and holds "regular trading sessions ... as per regular market timings", without printing the times. *Proposed:* record 09:15-15:30 from NSE/CMTR/41180, so it is also `NORMAL_SPECIAL`. This is the one session whose hours come from a second circular.
  - The supplied 2022 copy keeps its file name `NSE_CMTR_50560_2022_trading_holidays.pdf.pdf` with `downloaded_on=UNKNOWN`, never inferred from file times. Its archive URL is recorded because the copy Claude retrieved there on 2026-10-28 is byte-identical (`nse/data/calendar/README.md` §1, §4). This shows the content is identical; it does not show where or when the original copy was downloaded.
  - **Normal hours 09:15-15:30** (`REGULAR_OPEN`/`REGULAR_CLOSE`, `mtf_freshness.SESSION_OPEN`/`SESSION_CLOSE`) are provisionally evidenced by NSE/CMTR/41180 (31 May 2019, effective 3 Jun 2019), registered as a 2019 `SESSION_NOTICE` with no events, and corroborated by NSE/CMTR/65729 (2024-12-23), which calls them the standard market timings. No systematic review of the timing circulars in between has been made, so this aspect is **not validated**.
- **Proposed schema changes** (`nse_calendar.py`; tested):
  - `sources.csv` `downloaded_on` may be `UNKNOWN`, as in the EOD manifest.
  - An `events.csv` row may leave `source_ref` empty **only** when its status is `UNRESOLVED`, and it still needs a note. A `CONFIRMED` row must cite a registered source. No current row uses this.
- **Not complete:** B17 stays open and Phase 1 is not complete. Outstanding:
  - TradingView holiday and boundary validation (with B8);
  - the systematic normal-hours review;
  - completeness of the event list: reconciliation with official EOD files covers Q1 2022 only.

### D41. Research-pipeline interpretations (scanner, G0-G8)
- **Status:** `USER_APPROVED` 2026-11-08 for the readings section 1F names. History: `PROPOSED` as an umbrella, 2026-10-29; **partially superseded by USER_APPROVED M1 decisions R1-R6, 2026-11-02**. A reading this entry still marks `PROPOSED`, and that section 1F does not name, stays proposed. The register does not approve a reading the log does not.
- **Proposed behaviour:** the fourteen readings P-TREND-1, P-LOC-1 to P-LOC-3, P-MAT-1, P-MAT-2, P-COIN-1, P-COIN-2, P-CAL-1, P-LVL-1, P-LVL-2, P-CONF-1, P-G8-1 and P-DQ-1, listed with their effect and code location in `RESEARCH_PIPELINE.md` section 4.
  - **Approved in M1:** P-LOC-1 / R1 (CMP only); P-TREND-1 / R2 (12 o'clock maps to STRONG_UP, label retained); P-COIN-1 / R3 (actual demand-range overlap; Aggressive remains distinct); P-MAT-1 and P-MAT-2 / R5 (approved HOC/EQB outcomes); P-COIN-2 / R6 (known absence passes G6 as Standard, unknown remains MANUAL).
  - The separate R4 approval confirms D24's own-timeframe completed-close invalidation and requires SL-hit events to remain separate from zone invalidation events.
  - Other D41 readings remain PROPOSED, including P-LOC-2 (price inside tested HTF demand), P-LOC-3, P-CAL-1, P-LVL-1 to P-LVL-3, P-CONF-1, P-G8-1, P-DQ-1, P-CA-1/2, P-REF-1, P-BT-1 and M1 reporting. This bullet is the 2026-10-29 proposed set. Section 1F is the later record: a reading named there, including P-LOC-2 and P-LOC-3 under "Other approvals" and the D41 policy list in that section, is approved within that wording. This bullet does not keep a named reading proposed.
- **Added 2026-10-29 (second pass), also PROPOSED:**
  - P-LVL-3: invalid levels make G7 MANUAL with no R:R. Invalid means SL <= 0, inverted zone geometry or a non-finite price.
  - P-CA-1: a price-scale corporate action inside the replayed history makes G0 MANUAL; nothing is adjusted (B7).
  - P-REF-1: the matching key for zone references.
  - P-BT-1: backtests need a complete user-supplied execution model (B9, B12).
  - M1: the fresh-zone report labels an open leg-out window; this is a report label only.
  - P-CA-2 (third pass): a PREVCLOSE discontinuity inside the replayed history makes G0 MANUAL; a backtest trade alive across one is excluded from metrics.
  - The full register, with alternatives and effects, is `DECISION_REGISTER.md`.
- **Consequence while PROPOSED:** unapproved readings stay research output. Every record carries NOT_EXTERNALLY_VALIDATED and the manual checklist; no candidate status approves a trade.
- **Not changed:** D1-D40; the Rulebook and the Pine Script; WIT stays BLOCKED (audit M4b).

### D42. Owner-stated portfolio and pending-order policy (task brief, 2026-11-06)
- **Status:** `USER_STATED`, 2026-11-06; owner-approved operating constraints 2026-11-08 (D46, section 1F, which also supersedes the labelling below with D45 refusals and IST month counting). The owner's task instruction for the multi-agent audit states these as requirements. They are implemented only where they restrict output; no requirement here loosens a gate.
- **Stated requirements and implementation:**
  - **Maximum 10 simultaneous positions, independent of the RB 2392 monthly maximum of 10 trades.** This is not a Rulebook rule. `models.OWNER_MAX_OPEN_POSITIONS`.
    - `store.journal_event` refuses a TRIGGERED event while 10 positions are open (`MAX_OPEN_POSITIONS`). An exit at the same time counts as open.
    - The backtest keeps `max_open_positions` as a model input. It labels `MAX_OPEN_POSITIONS_ABOVE_OWNER_LIMIT` (or `PORTFOLIO_CONCURRENCY_NOT_MODELLED`) instead of refusing, so sensitivity runs stay possible.
  - **Pending orders do not fill once a pre-trade condition is invalid (RB 2530-2538).**
    - Backtest: every later point-in-time scan known before a bar opens must still list the zone in an allowed status. Otherwise the order is `CANCELLED_SETUP_INVALID`, and the result carries `REVALIDATION_AT_SCAN_TIMES_ONLY`.
    - Journal: a TRIGGERED event is refused when a stored scan strictly before it no longer lists the zone (`ZONE_NO_LONGER_CANDIDATE`).
  - **Ten verified-session expiry.** `models.OWNER_ENTRY_EXPIRY_SESSIONS`.
    - With a calendar, the backtest counts verified sessions. A missing, excluded or unclassifiable session ends the record (`DATA_MISSING_SESSION` / `DATA_EXCLUDED_SESSION` / `DATA_UNVERIFIED_SESSION`, no R).
    - A model whose expiry is not 10 is labelled `ENTRY_EXPIRY_NOT_OWNER_POLICY`.
  - **Missing point-in-time evidence stays MANUAL or DATA_INSUFFICIENT.** This is already implemented (P-DQ-1, D27).
    - Added: an in-progress candle that has reached a fresh zone's PL makes G1 MANUAL (`INCOMPLETE_CANDLE_TOUCH`).
    - Added: an incomplete bar inside a backtest window ends that record (`DATA_INCOMPLETE_CANDLE`).
  - **WIT remains BLOCKED** (unchanged, M4b).
- **Not decided here:**
  - B9 (entry/stop baseline) and the B12 cost/slippage values.
  - Counting the monthly cap in IST.
  - P-LOC-2, P-RISK-1 and RB-VERSION-1. These remain as in `DECISION_REGISTER.md`.

---

## 1F. Owner-approved decisions (owner task brief, 2026-11-08)

The owner's task brief of 2026-11-08 (the `autonomous-gtf-project-council` activation)
lists the decisions below as binding and not to be reopened. They are recorded here as
`USER_APPROVED`, except D42's constraints, which D46 keeps as `USER_STATED` owner-approved
operating constraints (they are not Rulebook rules). Engineering choices made while
implementing them are in `ENGINEERING_DECISIONS.md` (ED-1 onwards) and are not owner
decisions. Nothing here changes the Rulebook or the Pine Script.

### D42 (status update). Portfolio and pending-order constraints
- **Status:** `USER_STATED`, owner-approved operating constraints (D46), 2026-11-08. The wording question raised on 2026-11-06 is closed by the brief, which restates them:
  - 10 simultaneous open positions;
  - 10 trades per IST calendar month, counted by the first fill/trigger time converted to IST, months running from 00:00 IST on day 1 to the end of the last day;
  - pending orders revalidated before filling;
  - expiry after 10 verified NSE sessions, which missing or unclassifiable sessions never extend;
  - WIT BLOCKED.
- **Implementation:**
  - `models.ist_month` is used by `store.journal_event` (ceiling), `store.journal_summary` and `backtest.apply_portfolio_rules`.
  - `backtest` refuses a run without a calendar (expiry must count verified sessions).
  - D45 refuses limits above these values.
- **Tests:**
  - `test_research_execution_policy.IstMonth`, `D45Refusals`
  - `test_research_store.JournalIstMonth20261108`

### D43. Opposing Pine-only zones in G5 / G7 (was PINE-ONLY-1)
- **Status:** `USER_APPROVED`, 2026-11-08.
- **Decision:** a relevant opposing Pine-only zone that cannot be validated independently makes G5 / G7 MANUAL. It is never silently ignored and never used as an automatic target.
- **Implementation:**
  - `zone_engine` Pine-only records now carry Pine's own `invalidated_index` and `test_count`.
  - `structure.pine_only_zones` drops only a zone Pine itself deleted (completed close beyond DL; PS 2613, RB 1313). A record without the field counts as unbroken.
  - **G5:** a Pine-only supply on a G5 timeframe (MIT: M, Q, HY reject; W, Y evidence; Pine-only zones exist only on M, W, D) whose band is not CLEAR for PL or either entry bound turns PASS into MANUAL (`PINE_ONLY_ZONE_REVIEW`). It never turns into FAIL and never softens one.
  - **G7:** a Pine-only supply on the target timeframe above the entry minimum and below the structural target (or anywhere above when there is none) makes G7 MANUAL. A zone Pine recorded as touched is excluded, because a tested zone cannot be the fresh target (RB 551-558, as `levels.select_target`; ED-4).
- **Tests:** `test_research_gates.PineOnlyD43`; `test_research_adversarial.CouncilRegressions20261108`; scenario `mit_aggressive_zone_above_monthly_demand` (G5 now MANUAL).

### D44. Point-in-time evidence and undated errors (was UNDATED-ERR-1)
- **Status:** `USER_APPROVED`, 2026-11-08.
- **Decision:**
  - Later verified evidence must not affect earlier historical scans.
  - Undated errors are never silently ignored. If their impact cannot be bounded, the affected analysis is MANUAL or DATA_INSUFFICIENT.
  - Unaffected periods are not contaminated.
- **Implementation:**
  - `marketdata._bad_date`: a CSV row with an unreadable date is dated at the previous valid row's date (inclusive) when its neighbouring valid rows are in order and the file has no OUT_OF_ORDER or DUPLICATE_DATE finding anywhere. Only scans on or after that date are blocked. The finding is `verified=False`, and an undated `ERROR_DATE_BOUND_INFERRED` warning makes the inference visible.
  - Without a previous row, or with out-of-order neighbours, the finding stays undated and blocks every scan.
  - Whole-input errors (`BAD_HEADER`, `NO_INPUT_FILE`, `NO_BARS`, `BHAVCOPY_INPUT`) stay unbounded.
  - Dated findings were already filtered by `Finding.known_at` (P-DQ-1).
- **Tests:** `test_research_lookahead.FutureDataQuality.test_d44_*`.
- **Not implemented, recorded for owner visibility (ED-6):**
  - `recorded_on` columns (universe, corporate actions, instruments) are not read by the loaders. Filtering records by when they were *entered* would loosen G0 for earlier scans (a split with ex-date before as_of would vanish), so the restrictive behaviour is kept.
  - A per-file bhavcopy error is still whole-input (backlog).

### D45. Hard rejection of backtest configurations above owner limits
- **Status:** `USER_APPROVED`, 2026-11-08.
- **Implementation:** `backtest.ExecutionModel.__post_init__` raises `ValueError` for:
  - `max_open_positions` or `monthly_trade_cap` that is None (unlimited) or above 10;
  - `entry_expiry_sessions` above 10.

  Both caps now default to 10. Stricter values are allowed; an expiry other than 10 keeps the `ENTRY_EXPIRY_NOT_OWNER_POLICY` label. The 2026-11-02 labels `MONTHLY_CAP_ABOVE_RULEBOOK` and `MAX_OPEN_POSITIONS_ABOVE_OWNER_LIMIT` can no longer occur, and nothing about the limits is only a warning.
- **Tests:** `test_research_backtest.Portfolio`, `CapAuditRegressions`; `test_research_execution_policy.D45Refusals`; adversarial `test_dataclasses_replace_cannot_bypass_the_d45_limits`.

### D46. D42 recorded as USER_STATED owner-approved operating constraints
- **Status:** `USER_APPROVED`, 2026-11-08.
- **Decision:** D42 keeps `USER_STATED` (not a Rulebook rule, not a methodology change) and is enforced in the journal, pending-order and backtest workflows.

### Other approvals in the 2026-11-08 brief
- **P-LOC-2** `USER_APPROVED`:
  - Monthly determines curve and VLOC; Daily identifies and executes.
  - When a Monthly demand holding CMP is TESTED, the curve is redrawn from the next valid fresh Monthly demand below (RB 1621).
  - Missing or unknown boundaries are MANUAL.
  - `structure.build_curve` applies this to Monthly demand only. A tested Weekly zone or a tested supply holding price stays MANUAL. A fresh zone also holding price stays the bottom.
  - G3 evidence `redrawn_past_tested`.
  - Tests: `G3.test_price_inside_a_tested_monthly_demand_redraws_from_the_next_fresh_zone`, `test_redraw_*`. The earlier MANUAL test was replaced, as a specification correction.
- **P-LOC-3** `USER_APPROVED`: unknown, missing or unverified Monthly boundary freshness is MANUAL. This was already implemented; the redraw keeps it (`test_redraw_stops_at_a_boundary_of_unknown_freshness`).
- **P-RISK-1** `USER_APPROVED`:
  - above the declared stage maximum: FAIL;
  - below the minimum: MANUAL;
  - no stage: MANUAL;
  - no stage and above 2%: FAIL;
  - inside the inclusive range: PASS;
  - no automatic stage promotion.

  `risk.assess_config` already matches every branch (council audit 2026-11-08); no change.
- **B9** `USER_APPROVED`:
  - the original Rulebook price-tier ranges;
  - the PL / normal-DL / exceptional-DL tier union;
  - inclusive shared boundaries;
  - predeclared sensitivity scenarios;
  - no automatic buffer selection.

  `levels` (P-LVL-1) was unchanged. `execution_policy.owner_grid` requires the (entry, stop) scenarios to be declared before the run and selects nothing.
- **B12** `USER_APPROVED`:
  - manual Kite/GTT execution only, no broker integration;
  - ten verified-session expiry;
  - STOP_FIRST baseline and EXCLUDE sensitivity;
  - AT_OPEN gap proxy;
  - slippage 0.05%, 0.10% and 0.20% per side;
  - a separate dated, instrument-specific Zerodha cost model.

  Implemented in `nse/research/execution_policy.py` (`owner_grid`, `CostSchedule`). No Zerodha figures exist in the repository, so the schedule is a user-supplied file and no cost is defaulted. Flat per-order charges are not modelled (`flat_charges_modelled: false`).
- **B12-CAP / CAP-IST-1** closed by D42 / D46: the cap counts the first fill time, IST month.
- **D40** `USER_APPROVED`: the approved calendar tables and special-session handling are kept as recorded. **Escalated discrepancy D40-Q1 (not reconciled):**
  - The brief describes "the January 20, 2024 two-part primary/DR normal-market sessions; one trading date for expiry; do not create candles across the break or discard valid observations".
  - The registered evidence says otherwise: NSE/MSD/60340 withdrew three earlier circulars (contents not held at the time; held since 2026-11-09) and held regular trading from the primary site (`events.csv` row 61, NORMAL_SPECIAL). The two-window primary/DR sessions are **2 Mar 2024** (NSE/MSD/60677) and **18 May 2024** (NSE/MSD/61893), which D30 excludes from candle construction (`EXCLUDED_SHORTENED`).
  - The calendar data and code are unchanged. The backtest still ends a record that meets an excluded session (`DATA_EXCLUDED_SESSION`), which is fail-closed.
  - Owner action: say whether the instruction refers to 2 Mar / 18 May 2024 and, if so, whether D30's exclusion should change for them.
  - **Resolved by evidence, later 2026-11-08** (`REAL_DATA_READINESS.md` §1). Two independent council reviews extracted the held circulars, hash-verified against `sources.csv`, and agreed on every point:
    - 20 Jan 2024 was a regular session from the primary site only (NSE/MSD/60340).
    - The two-window primary/DR sessions are 2 Mar and 18 May 2024 (NSE/MSD/60677, 61893).
    - So the owner's instruction describes those two dates. The approval is kept as given; the correction is factual only.
  - **Implemented (ED-10):**
    - the two dates stay `EXCLUDED_SHORTENED`, so no candle is built across the break (D30);
    - each counts as one trading date for expiry;
    - its daily bar is used only as a bound (nothing is discarded).
  - **Calendar correction:** `events.csv` row 61 no longer says the withdrawn NSE/MSD/59999, 60300 and 60318 announced a DR-switch session; those circulars were not held at the time, so their content was not verified. *[2026-11-09: now held and hash-registered; 59999 did announce the two-window DR session, which 60340 withdrew before the day. See the D40 evidence-trail note in section 1F.]*
  - **Still unverified:** the 20 Jan 2024 hours (from NSE/CMTR/41180).
  - **Evidence trail closed, 2026-11-09 (MP1; factual, not a new decision).** The three withdrawn circulars are now held and hash-registered in `nse/data/calendar/sources.csv`. One independent investigator and the Chair both extracted their text:
    - **NSE/MSD/59999** (28 Dec 2023) announced a "Special Live trading session on Saturday, January 20, 2024 with intra day switch over to DR site": 09:15-10:00 on the primary site, 11:30-12:30 on the DR site, closing session 12:40-12:50.
    - **NSE/MSD/60300 and 60318** (18 and 19 Jan 2024) only updated ENIT and member-portal timings for that plan.
    - **NSE/MSD/60340** (19 Jan 2024) withdrew all three and held "regular trading sessions ... from primary site ... as per regular market timings".

    So the owner's wording describes the plan of 59999, which was withdrawn before the day. The two-window sessions that actually took place are 2 Mar and 18 May 2024. The owner approval above is unchanged. Calendar classifications and code are unchanged. The only data change is the `events.csv` 2024-01-20 note, which now states what 59999 said. Tests: `test_nse_calendar_data.Tables.test_d40_twentieth_january_is_one_primary_session_not_the_withdrawn_dr_plan`.
  - **Still open:** no official text prints the 20 Jan 2024 clock times; 09:15-15:30 remains an inference from "regular market timings" and NSE/CMTR/41180.
- **D41** `USER_APPROVED` as a whole:
  - the calendar, level, target, geometry, HTF-conflict, weak-close, data-quality, corporate-action and exact-price-match policies, including P-CAL-1, P-LVL-1 to P-LVL-3, P-CONF-1, P-G8-1, P-DQ-1, P-CA-1/2, P-REF-1, P-BT-1 and the M1 report label;
  - every one as already implemented; no code change.
- **RB-VERSION-1** `USER_APPROVED`:
  - The supplied Rulebook PDF is canonical.
  - The protected Markdown is its immutable, line-indexed citation companion; citations stay `RB <line>`.
  - Substantive discrepancies are escalated, never silently reconciled.
  - The open extraction dispute (RB 1784 and 1786-1803 present in the PDF or not) affects only WIT, which stays BLOCKED.
- **Instrument identity** `USER_APPROVED`:
  - inclusive listing intervals;
  - effective-date semantics;
  - successors distinct;
  - unknown or conflicting identity unresolved.

  Already implemented and tested (`test_research_instruments`). It is not yet wired into the scanner (backlog). *[2026-11-09: wired into every bhavcopy input, ED-21; this implements the approval, it does not change it.]*
- **Deferred / manual, unchanged:**
  - Aggressive setups (G6 MANUAL);
  - automatic wick-to-wick selection (not implemented; G7 takes both DLs);
  - automatic timeframe descent in 6+ candle bases (no zone is formed);
  - calendar-gap truncation (disclosed limitation);
  - WIT intraday BLOCKED.

---

## 1G. Owner decisions on Master Prompt 1 (2026-11-09)

All `USER_APPROVED`, 2026-11-09, given in response to the MP1 report. They are recorded in the owner's terms. How each is implemented is in `ENGINEERING_DECISIONS.md` ED-25 to ED-32.

### D47. Scripted backfill of the missing 2021-2025 NSE EOD files
- **Status:** `USER_APPROVED`.
- **Approved:** a scripted download of the missing 2021-2025 files identified by `acquire-plan`, from the verified official NSE URLs it prints.
- **Conditions:**
  - rate limiting, retries and resumable downloads;
  - verify integrity, source URL, content hash and expected format;
  - preserve raw files and never silently replace one;
  - no unauthorised sources and no paid data;
  - quarantine malformed or conflicting files;
  - a complete acquisition and validation report.
- **Scope:** this backfill only. It is not unrestricted future downloading, and it does not cover 2016-2020 EOD files.

### D48. Ten-year window: calendar and data readiness extended to 2016-2020
- **Status:** `USER_APPROVED`. It extends D29's 2021-2025 window.
- **Conditions:**
  - authoritative NSE holiday and special-session circulars only;
  - verify trading dates and session information;
  - never infer a holiday or session; keep unresolved dates flagged;
  - preserve the verified 2021-2025 calendar.

### D49. Historical Nifty 100 transcription, approved with review
- **Status:** `USER_APPROVED`.
- **Approved:** prepare the membership dataset from the official baseline list and reconstitution notices, with:
  - every addition and removal, with its effective date;
  - ad-hoc changes, including the Jio Financial spin-off where applicable;
  - ISINs and identity verified;
  - independent agent cross-checks.
- **Counts:** officially documented temporary counts such as 101 are accepted; the count is never forced to 100.
- **Review gate:** a human review of the completed transcription is required before the universe is marked verified. Until it is reviewed and accepted, results stay `UNIVERSE_UNVERIFIED` and are never presented as research-ready.

### D50. Corporate-action policy
- **Status:** `USER_APPROVED`.
- **Canonical prices:** raw, unadjusted OHLC.
- **Events:** verified corporate-action events and their terms are stored separately.
- **No silent adjustment:** prices are never adjusted silently, and unverified ratios are never used in zone detection, scanning or backtesting.
- **Derived series:** any adjusted series must be separate, traceable and governed by a documented adjustment policy.

### D51. Historical identity continuity
- **Status:** `USER_APPROVED`.
- **Join rule:** renamed companies are connected only through verified ISIN continuity and effective dates.
- **Never joined:** two companies are never joined because they share a ticker or a similar name.
- **Fallback:** if continuity cannot be established, the existing DATA_INSUFFICIENT restriction stays.

**Standing instruction (2026-11-09):** do not claim DATA_READY until the historical files, the calendar, universe membership and the required identity evidence have passed validation. No commit or push.

---

## 1H. Owner decisions on the D47-D51 follow-up (2026-11-09)

All `USER_APPROVED`, 2026-11-09, recorded in the owner's terms. Implementation: `ENGINEERING_DECISIONS.md` ED-33 onwards.

### D52. DQ-1: PREVCLOSE discontinuity across an excluded session, approved with strict safeguards
- **Status:** `USER_APPROVED`.
- **When it counts as an explained calendar gap:** only when all three hold:
  - an authoritative NSE calendar or circular confirms the excluded or special session;
  - the session is explicitly recorded as excluded from the accepted EOD dataset;
  - no EOD file is expected for it under the approved acquisition policy.
- **Must not:**
  - classify this discontinuity alone as a split, bonus or other corporate action;
  - fabricate an OHLC candle;
  - suppress independent corporate-action or identity warnings;
  - make a candidate ACTIONABLE merely because this discontinuity is explained.
- **Must:**
  - preserve the missing-session marker and provenance in scan inputs and manifests;
  - audit every downstream calculation that assumes consecutive daily candles or uses the missing session's price action;
  - return MANUAL or DATA_INSUFFICIENT where the missing candle could materially affect a calculation or decision.
- **Regression tests:** confirmed excluded sessions, unconfirmed sessions, genuine corporate actions and sequence-dependent calculations.

### D53. B11-R: Nifty 100 transcription, conditional acceptance
- **Status:** `USER_APPROVED` (process), not acceptance of the data.
- **Approved:** independent verification of every addition, removal, effective date, symbol and ISIN against authoritative NSE evidence.
- **Jio Financial:** the symbol discrepancy is resolved from official evidence; an inference is never accepted as fact.
- **Counts:** documented 101-member periods are preserved.
- **Review gate:** the universe stays unverified until the human review is complete and the review file holds the explicitly accepted rows. Nothing is marked accepted automatically, and no evidence is manufactured.

### D54. CAL-2: Dhanteras dates remain UNRESOLVED
- **Status:** `USER_APPROVED`.
- **Approved:**
  - no inference of session status or hours;
  - seek authoritative NSE evidence;
  - keep the dates flagged;
  - never treat them as verified sessions;
  - they must not block daily readiness that does not require them.

### D55. DATA-2: official NSE EOD backfill 2016-2020, approved
- **Status:** `USER_APPROVED`.
- **Approved:** a resumable, rate-limited download of the missing 2016-2020 official files, with the D47 safeguards:
  - verified official URLs only;
  - no overwriting;
  - verify source, hash, format, parsing and EQ-row validity;
  - quarantine malformed or conflicting files;
  - preserve raw files and provenance;
  - report downloaded, parsed, validated and accepted coverage separately.
- **Readiness:** none is claimed until the calendar and data validation pass.

### D56. B7-C / B11-I: corporate-action and identity evidence, approved
- **Status:** `USER_APPROVED`.
- **Approved:**
  - collection of official NSE corporate-action records for all relevant historical Nifty 100 members;
  - verification of event dates, types, terms, ratios and instrument identity;
  - investigation of the 13 unresolved ISIN changes from official evidence.
- **Rules:**
  - join only through verified identity continuity and effective dates, never through similar names or reused tickers;
  - raw unadjusted OHLC stays canonical;
  - any derived adjusted series is separate, traceable and documented;
  - missing or ambiguous evidence stays DATA_INSUFFICIENT or MANUAL.

### D57. Local-first web application
- **Status:** `USER_APPROVED` (owner instruction, 2026-11-09). **Historical record preserved.**
- **Commercial production supersession (2026-11-18):** For commercial production architecture, **OD-BP-001** is the newer controlling owner decision and explicitly supersedes D57. D57 is not deleted. Local-first loopback remains a development, testing, migration or engineering baseline where useful; it is not the target commercial production deployment model. See OD-BP-001 below and [ADR_OD-BP-001.md](../../docs/product-blueprint/ADR_OD-BP-001.md).
- **Decision (historical text, 2026-11-09):** The GTF Trading Intelligence Platform is a local-first web application opened in a browser. It is not a Tauri, Electron, or AppKit application.
- **Initial deployment (historical):** one Mac. The API and the UI bind to loopback only. No public exposure. No cloud service is required for core use. No paid provider is enabled by this decision.
- **Later deployment (historical):** frontend and backend may be hosted on cloud infrastructure. Environment-specific configuration stays outside business logic. Persistence and provider interfaces stay replaceable. This decision does not authorise creating that infrastructure or spending on it.
- **Session (still applicable to local/dev mode):** HttpOnly cookie, `SameSite=Strict`, host and origin checks, and a custom request header. The session value is not placed in localStorage, a URL, browser logs, or frontend source. The withdrawn Tauri inherited-token design is not reused.
- **Unchanged:** the research pipeline remains the only eligibility authority. Live fills, journal mutations, and unresolved trade-plan identity keep their existing restrictions. No broker integration. Desktop shells remain excluded.
- **Records:** [API contracts](../../docs/architecture/API_CONTRACTS.md) section 1, [system architecture](../../docs/architecture/SYSTEM_ARCHITECTURE.md) process model, AR-2 and AR-3 in [decisions](../../docs/product/DECISIONS_AND_OPEN_QUESTIONS.md).

### D58. CAL-2: Dhanteras dates confirmed as regular equity sessions (option A)
- **Status:** `USER_APPROVED` (owner instruction, 2026-11-10). Supersedes D54 for these four dates only.
- **Decision:** the existing `SPECIAL_SESSION` rows for 2016-10-28 (NSE/CMTR/33442), 2017-10-17 (NSE/CMTR/36003), 2018-11-05 (NSE/CMTR/39215) and 2019-10-25 (NSE/CMTR/42455) change from `UNRESOLVED` to `CONFIRMED`. Each keeps its 09:15-15:30 regular equity hours, so the calendar classifies it `NORMAL_SPECIAL`. The Gold ETF/SGB-only evening extension stays in the row's note and builds no candle.
- **Evidence:** the four circulars, read in full and hash-matched to `sources.csv` ("Regular Market Timing (there is no change to this)"), and a normal bhavcopy held for each date. See [T-002 evidence report](../../docs/product-discovery/phase-01/T002_DHANTERAS_EVIDENCE_REPORT.md).
- **Effect:** the ED-44 history cut no longer applies. No UNRESOLVED calendar row remains, and the ED-31 / ED-42 / ED-44 rules stay in force for any future one.
- **Not decided here:** any other calendar date, T-001 membership, identity, or readiness gates. DATA_READY is not claimed.

### D59. Provisional Nifty 100 membership research window
- **Status:** `USER_APPROVED` (owner instruction, 2026-11-10).
- **Decision:** membership-based Nifty 100 research uses 2020-12-31 onward. This is a research-window restriction. It is not membership certification.
- **Conditions:** every membership period still needs a human review and a matching source hash. An unverified period stays `UNIVERSE_UNVERIFIED`. An unresolved identity stays `DATA_INSUFFICIENT` or the existing fail-closed status. Corporate-action coverage still has to satisfy G0. A later constituent list is not used to reconstruct 2016-2020 membership. No pre-2020 baseline is invented. EOD before 2020-12-31 may warm indicators and other uses that are not represented as a survivorship-controlled Nifty 100 study.
- **Effect:** a non-ad-hoc universe scan or backtest whose as-of is before 2020-12-31 carries `MEMBERSHIP_BEFORE_PROVISIONAL_WINDOW`. Dates on or after 2020-12-31 do not carry that label. They remain `UNIVERSE_UNVERIFIED` until the review rows are accepted. `DATA_READY` is not claimed.

### D60. Twenty-five Nifty 100 count calculations, arithmetic only
- **Status:** `USER_APPROVED` (owner Yash Jain, 2026-11-11).
- **Approved:** the derived member-count arithmetic on the 25 `exception:` rows of `nse/data/universe/nifty100_review.csv`, whose keys and SHA-256 values are the rows of `nifty100_count_exceptions.csv`. The review stores this as `count_approval` `APPROVED`, reviewer `Yash Jain`, `reviewed_on` `2026-11-11`. Twenty of those dates derive to 101 and five derive to 100.
- **Not approved:** any constituent, any dummy seat (`DUMMYREL`, `DUMMYITC`, `DUMMYSIEMS`, `DUMMYTATAM`, `DUMMYHDLVR`), any inferred ISIN, any membership period, and any historical Nifty 100 certification. `decision` stays blank on these rows. Count approval does not verify a period.

### D61. Ten E03 membership mappings, direction only
- **Status:** `USER_APPROVED` (owner Yash Jain, 2026-11-11).
- **Approved:** the symbol and the direction of the ten `change:E03:` rows transcribed from `ind_prs23082021.pdf` page 5 section 3 (NIFTY 100). Page 1 dates the change effective 30 September 2021. Exclusions: ABBOTINDIA, ALKEM, MRF, PETRONET, UBL. Inclusions: BANKBARODA, CHOLAFIN, JINDALSTEL, PIIND, SAIL. The review stores this as `mapping_approval` `APPROVED`, reviewer `Yash Jain`, `reviewed_on` `2026-11-11`.
- **Not approved:** the membership period those rows would start or end. In particular the open periods BANKBARODA `INE028A01039` from 2021-09-30 and CHOLAFIN `INE121A01024` from 2021-09-30 are not certified. `decision` stays blank. Mapping approval does not verify a period.

### D62. Corporate-action evidence tiers (OD-CA-1, partial)
- **Status:** `USER_APPROVED` (owner, session instruction 2026-11-13, Decision 1).
- **Approved:** three evidence levels: `CA_COMPLETENESS_VERIFIED`, `CA_RESPONSE_PRESENT_NOT_COMPLETE` and `CORPORATE_ACTIONS_UNVERIFIED`. A non-empty, hash-verified response that parsed (no unparsed price subject), on a symbol-date that passes the price-integrity checks, may carry the second, weaker tier. That tier may be used only for clearly labelled exploratory research.
- **Not approved:** the weaker tier does not pass the corporate-action certification gate, does not enter the certified research universe, and does not remove `CORPORATE_ACTIONS_UNVERIFIED` from a record. Completeness is not inferred from previous-close checks. No existing certification requirement is weakened. No claim of complete historical corporate-action coverage. Response integrity is not response completeness.
- **Implemented by:** ED-51.

### D63. P0 data certification uses six data gates
- **Status:** `USER_APPROVED` (owner, session instruction 2026-11-13, Decision 2).
- **Approved:** P0 data certification is independent of GTF strategy qualification. The certification builder evaluates six data gates: membership, security identity, trading calendar, raw OHLC integrity (EOD), corporate-action coverage, price continuity. It does not run the trading qualification pipeline for every historical member-date. No duplicate gate architecture.
- **Not approved:** a data-certified symbol-date is not GTF trade eligibility, and outputs must say so. Candidates still come only from the canonical pipeline. Nothing here changes a qualification gate, a zone rule or a risk limit.
- **Implemented by:** ED-51.

### D64. R-12 investigation and fix authorised; T-001 batch 2 held
- **Status:** `USER_APPROVED` (owner, session instruction 2026-11-13, Decisions 3 and 4).
- **Approved:** a separate R-12 batch. Prevent unexplained corporate-action-related price discontinuities from silently entering GTF zone detection, fail closed where the price history cannot be resolved, keep raw unadjusted OHLC, add split, bonus, rights and demerger regressions using the TATASTEEL 1:10 example. Keep R-12 separate from the certification-builder and T-001 changes.
- **Not approved:** any change to the Rulebook, the Pine Script, unrelated methodology, or zone eligibility rules. No T-001 batch 2 decision is written: the 17 rows wait for an explicit owner answer, and the recommendation to accept is not authorisation.
- **Implemented by:** ED-52.
- **Superseded in part (2026-11-13):** the batch 2 hold ended with D65. The rest of D64 stands.

### D65. T-001 batch 2: 17 membership rows accepted
- **Status:** `USER_APPROVED` (owner, session instruction 2026-11-13; reviewer recorded as `Yash Jain`, following batch 1).
- **Approved:** `decision` `ACCEPTED` on exactly the 17 rows of the five evidence cards in `docs/product-discovery/p0/P0_T001_BATCH2_OWNER_PACKAGE.md`:
  - G-E04, all 10 rows, effective 2022-03-31;
  - G-E05, all 4 rows, effective 2022-08-08;
  - `change:I-2022-04-20-JUBLFOOD:ISIN_CHANGE:JUBLFOOD:INE797F01020`;
  - `change:I-2022-07-29-TATASTEEL:ISIN_CHANGE:TATASTEEL:INE081A01020`;
  - `change:I-2022-09-14-BAJAJFINSV:ISIN_CHANGE:BAJAJFINSV:INE918I01026`.
  The owner wrote "ACCEPT"; the ledger's schema token is `ACCEPTED`.
- **Not approved:** any other row or group; GRASIM, BAJFINANCE, the dummy seats and the other insufficient-evidence groups; any change to count or mapping approvals; corporate-action completeness (OD-CA-1 stays open). Membership acceptance does not certify a member-date.
- **Result:** 140 rows `ACCEPTED`, 131 blank. 85 of 185 periods verified (14 more). 0 member-dates certified.

### D66. OD-CA-1: corporate-action completeness acceptance standard (Option A)
- **Status:** `USER_APPROVED` (owner, session instruction 2026-11-15).
- **Approved:** corporate-action completeness for a symbol and date window requires two independent official sources, reconciled event by event. Both sources must have verified SHA-256 hashes. Their provenance and independence must be established. The reconciliation must identify missing, additional, conflicting and differently represented events. The owner approval for each completeness window must explicitly identify the symbol, the date window, both source hashes and the reconciliation record. Any unresolved discrepancy, missing source, hash mismatch, insufficient coverage, ambiguous provenance or unparsed event fails closed. A single source, even if hash-verified and individually approved, never establishes corporate-action completeness.
- **Not approved:** acquiring or downloading any source; any particular source file or completeness record; any `completeness.csv` row; certification of any historical member-date. D62's three evidence tiers are unchanged.

### D67. Queue V3 answers: 91 membership rows accepted; identity kept unjoined; ED-57 authorised
- **Status:** `USER_APPROVED` (owner, session instructions 2026-11-15; reviewer recorded as `Yash Jain`, following D65).
- **Approved:**
  - Q3: `decision` `ACCEPTED` on exactly the 91 evidence-sufficient rows of `docs/product-discovery/p0/P0_MEMBERSHIP_OWNER_DECISION_FILE_PROPOSED.csv` (named `P0_MEMBERSHIP_DECISION_FILE_PROPOSED.csv` in the instruction; it is the only proposal file), after the pre-write checks in `P0_91_MEMBERSHIP_DECISION_AUDIT.md` passed.
  - Q5 BAJFINANCE and Q6 GRASIM: Option 1, keep the old and new ISINs unjoined; no listing end; no identity-record change. NSE/CML/33154 and NSE/CML/33327 are held as evidence only.
  - Q4: the seven optional rows (JIOFIN, ITCHOTELS x2, ENRIN x2, TMCV x2) are deferred.
  - Q2: a BSE enquiry only (no purchase, subscription, payment, commitment or bulk acquisition).
  - Q11: retrieval of the official CGPOWER 2016 scheme terms only (no inferred ratio, price adjustment, parser change or exception closure).
  - ED-57: exact-rational support for fractional face-value splits (VBL 2024-09-12), with tests and independent review.
- **Not approved:** Q7 (OD-PX-4), Q8 (OWN-1), Q9 (OD-PX-3), Q10 (OD-MEM-2/3), Q12 (TV-1), Q13 (R-5) remain pending. Any corporate-action completeness window, any `completeness.csv` row, any production rebuild, P5, broker work. Membership acceptance does not certify a member-date.
- **Result:** 231 rows `ACCEPTED`, 40 blank. Certified member-dates remain 0 (D66).
- **Disclosure recorded after the write (independent review, 2026-11-15):** one of the 91 rows, `change:I-2024-09-12-VBL:ISIN_CHANGE:VBL:INE200M01039`, carries a contrary advisory verdict in `P0_MEMBERSHIP_ROW_RECOMMENDATIONS.csv` (`INSUFFICIENT_EVIDENCE`). The reason given is that the cited NSE API record's own `isin` field is the older INE200M01013, while the bhavcopies show INE200M01021 -> INE200M01039. ED-37 does not use that field ("it often holds an older ISIN"). The INE200M01013 -> INE200M01021 step is itself an accepted row (`change:I-2023-06-15-VBL`). The acceptance proposal did not disclose this verdict. The row was written because D67 names the exact 91 rows. The owner may revisit this row; see `P0_91_MEMBERSHIP_DECISION_AUDIT.md`.

### D68. Queue V4 answers: D66 source enquiries; OD-PX-4 declined; dummy seats Option A; ED-57 expectations approved
- **Status:** `USER_APPROVED` (owner, session instruction 2026-11-15).
- **Approved:**
  - D66 source path, Decision 1: a **written enquiry only** to BSE about corporate-action event coverage, historical periods, event types, provenance and upstream sources, independence from NSE data, sample records, and subscription and licensing terms. No purchase.
  - D66 source path, Decision 2: a **free CDSL coverage test** on the 15 known in-window splits, documenting notices found and not found, event types, historical availability, ISIN-change requirements and limitations. The test is not proof of complete corporate-action coverage.
  - Q7 (OD-PX-4): **DECLINED.** The 700 shortened-session price exceptions stay excluded until an adequately supported rule exists.
  - Q10 (OD-MEM-2/3): **Option A.** Dummy seats are excluded from security-level calculations; index counts are reported separately.
  - ED-57: the two changed synthetic test expectations ("Rs 10 -> Rs 3" read exactly as `SPLIT 3:10`) are approved.
  - `change:I-2024-09-12-VBL:ISIN_CHANGE:VBL:INE200M01039`: **keep ACCEPTED**, retaining the disclosure of the contrary advisory verdict (D67).
  - Q8: BRITANNIA 2021-05-25 and TVSMOTOR 2025-08-25 stay unparsed. Q9: ADANIENSOL 2024-11-21 stays excluded. CGPOWER demerger representation rule: deferred.
- **Not approved / pending:** Q12 (TradingView exports) and Q13 (R-5 precedence wording) stay pending. No BSE purchase or subscription. **No certification approval**: D66 and every other applicable gate must pass independently first. No completeness window, `completeness.csv` row or approval marker.

### OD-BP-001. Commercial production architecture is browser-based cloud SaaS (supersedes D57 for production)
- **Status:** `USER_APPROVED` (product owner, 2026-11-18).
- **Decision:** For GTF commercial production architecture, OD-BP-001 supersedes D57. The commercial GTF product shall be a browser-based, cloud-hosted, multi-tenant SaaS web application. Customers access GTF through supported web browsers. A desktop application or mandatory desktop installation is not part of the commercial product scope.
- **Local-first retention:** Local-first / loopback execution may be retained as a development, testing, migration or engineering baseline. It is not the target commercial production deployment model. Remaining local-first requirements are classified as development/testing compatibility requirements, not commercial production architecture requirements.
- **Confirmed product boundaries:** NSE cash equities; initial research universe Nifty 100; individual traders; positional and swing trading; cloud-hosted browser SaaS; manual execution through external broker platforms; tenant-isolated customer data; broker order routing not authorised; desktop shells excluded from the commercial product.
- **Architectural implications (target, not a technology lock):** browser React/TypeScript frontend; cloud-hosted backend APIs; multi-tenant identity and authorisation; tenant-isolated customer data; shared market reference data where legally permitted; managed production database; background workers; secure object storage; cloud networking, TLS and edge protection; monitoring and observability; backup, recovery and deployment processes; subscription and entitlement enforcement. Specific technologies and providers remain subject to architecture review and separate approval.
- **Does not authorise:** cloud infrastructure purchases; deployment or migration; database migration; API or schema changes; external provider commitments; broker integration or order execution; removal of local development/testing capabilities; any change to D66 or historical data certification; any change to Rulebook or research-engine decisions. D57 historical text is preserved, not rewritten away.
- **Implementation authorisation:** No commercial cloud implementation is authorised by this decision alone. The W0 foundation specifications (MS-016, MS-017, MS-018 and related foundation specs) are **authorised for specification only**. Cloud spending, provider selection and production deployment require separate approvals.
- **Records:** [ADR_OD-BP-001.md](../../docs/product-blueprint/ADR_OD-BP-001.md), [00_MASTER_PRODUCT_BLUEPRINT.md](../../docs/product-blueprint/00_MASTER_PRODUCT_BLUEPRINT.md), [13_OWNER_DECISION_REGISTER.md](../../docs/product-blueprint/13_OWNER_DECISION_REGISTER.md), [07_TECHNOLOGY_DECISION_REGISTER.md](../../docs/product-blueprint/07_TECHNOLOGY_DECISION_REGISTER.md).

**Standing instruction (2026-11-09):**
- DATA_READY is not claimed until the acceptance criteria pass.
- Engineering completion, data readiness and research validation are kept distinct.
- No change to the Pine indicator or the Rulebook.
- No staging, commit or push.

**Implementation record (2026-11-09; engineering, not owner decisions):**

| Decision | Implemented by | Data state |
|---|---|---|
| D52 | ED-33, ED-34 | 12 excluded-session files held |
| D53 | ED-35 | human review pending |
| D54 | ED-31, ED-42 | 4 dates UNRESOLVED; confirmed by D58 (2026-11-10) |
| D55 | ED-38, ED-41 | 2,466 of 2,466 equity sessions accepted after D58 (2,462 before the four Dhanteras dates were confirmed) |
| D56 | ED-37, ED-39 | 145 symbols covered; 27 of 30 ISIN changes evidenced |
| D59 | ED-47 | provisional membership research from 2020-12-31; not certified |
| D60 | ED-48 | 25 count rows: `count_approval` APPROVED; `decision` blank; no period verified |
| D61 | ED-48 | 10 E03 rows: `mapping_approval` APPROVED; `decision` blank; no period verified |
| D62 | ED-51 | 108,325 member-dates `CA_RESPONSE_PRESENT_NOT_COMPLETE`; exploratory-only 68,143 at D62, 73,368 after D65; 0 certified |
| D63 | ED-51 | builder evaluates six data gates; `gtf_trade_eligibility` NOT_EVALUATED on every output row |
| D64 | ED-52 | G0 holds on an unexplained price-scale gap; batch 2 rows held until D65 |
| D65 | ledger, no ED | 17 rows `ACCEPTED` 2026-11-13; 85 of 185 periods verified; 0 certified |

Details: `IMPLEMENTATION_BLOCKERS.md` Part 11.

---

## 2. Source- and Pine-defined specifications (verified)

| ID | Item | Status | Evidence |
|---|---|---|---|
| S1 | Strong-candle body threshold > 50% | `SOURCE_DEFINED` (RB 402) + `PINE_DEFINED` (PS 12, 332) | The Pine-only close-break path is not used; it routes to manual review (D12, PR1) |
| S2 | Base-candle threshold body ≤ 50%; transition ≤ 75% inside wicks | `PINE_DEFINED` (PS 11, 335, 489) | The rulebook has no explicit base threshold |
| S3 | Core score: freshness 3/1.5/0; strength 2/1/0; base 2/1/0 | `SOURCE_DEFINED` (RB 675–677, 728–730, 785–787) and `PINE_DEFINED` (PS 594–602) | No 1.5 strength value and no time decay exist in either source |
| S4 | 7/7 core required for Type 1 | `SOURCE_DEFINED` (RB 661, 829, 995) | - |
| S5 | DL close-breach permanently deletes the zone | `PINE_DEFINED` (PS 2613–2647, 2667–2699, 2718–2750) and consistent with RB 1627, 1741 | HTF zones are breached only by their own TF close (PS 2667, 2718) |
| S6 | Leg-in window 3 bars + bar[1] fallback; single-candle leg-in | `PINE_DEFINED` (PS 1390–1419) | Rulebook silent |
| S7 | Pending achievement window: 1 later bar (daily engine, same-bar countdown PS 1546 then 1584); 2 later bars (W/M engines, PS 1799 before 2097) | `PINE_DEFINED` | Rulebook silent. Corrected in v2.2 (earlier versions said 2 bars for all TFs) |
| S8 | Exceptional DL: reversal = leg-in/base/leg-out extreme; continuous = base/leg-out | `SOURCE_DEFINED` (RB 337–339, 542–544) and `PINE_DEFINED` (PS 1473–1490) | - |
| S9 | Zero-base `is_exceptional = false` | `PINE_DEFINED` (PS 1736, 1755) | DL already = `min(low[1], low)` |
| S10 | HTF conflict applies to daily demand **and** supply zones | `PINE_DEFINED` (PS 801–852) | Rulebook TFs and band govern (D12, PR11) |
| S19 | Max base candles = 5 (Pine option) so 4–5-base zones are scored | `SOURCE_DEFINED` (RB 786) via a `PINE_DEFINED` option (PS 10) | D12, PR4 |
| S11 | Freshness touch rule (wick or body touch, gap-through counts) | `SOURCE_DEFINED` (RB 683–697) | Pine `low ≤ PL` (PS 2651) |
| S12 | Curve 0 / 33.33 / 66.66 / 100 from fresh DZ PL to fresh SZ PL | `SOURCE_DEFINED` (RB 1195–1209, 1584–1601) | Not in Pine |
| S13 | Position size `floor(RPT ÷ (Entry − SL))` | `SOURCE_DEFINED` (RB 42, 2162; floor implied by RB 2203–2204) | - |
| S14 | Structural target = PL of nearest fresh ITF opposing zone; R:R ≥ 2 | `SOURCE_DEFINED` (RB 81–90, 551–559, 2278–2300) | "Quality" ambiguous (N10) |
| S15 | Type 1 only; Types 2/3 not used | `SOURCE_DEFINED` (RB 2357–2374) | - |
| S16 | Max 10 trades per month (journal) | `SOURCE_DEFINED` (RB 2392) | - |
| S17 | SMA-50 clock is the Phase 1 trend method (ATA after 100 trades) | `SOURCE_DEFINED` (RB 1748, 3007) | Weekly (gate) + Monthly (context) per D14/D21; ambiguous bands → manual |
| S18 | Scoring applies to execution-TF zones only; HTF location zones are not graded | `SOURCE_DEFINED` (RB 647, 1270–1274, 1631–1640) | - |

---

## 3. Status of former open decisions

| ID | Topic | Status |
|---|---|---|
| B1 | Detection precedence | **Resolved by D12** |
| B2 | Zero-base base component | **Resolved by D13** |
| B3 | Trend quantification | **Resolved by D14 + D21.** Mapping ambiguities → manual review |
| B13 | Monthly trend role (MIT) | **Resolved by D21** (Option A) |
| B14 | WIT trend checks | **Resolved by D22** (Option C) |
| B4 | Tested HTF zones in context | **Resolved:** coinciding by D15; conflict by D12 (manual review) |
| B5 | Trade-type scope | **Resolved by D16** (MIT + WIT) |
| B8 | Q/HY/Y alignment | **Decided by D23** (calendar alignment). **TradingView boundary/value verification still open** |
| B9 | Deterministic buffers | **Open** (needed only for historical validation) |

The full remaining list is in `IMPLEMENTATION_BLOCKERS.md` Part 4 ("Decisions still required before reliable implementation"). None of it reopens D1–D17 or D21–D39. D40 is `USER_APPROVED` in section 1F (2026-11-08). An older note that called D40 proposed is not the status.

---

## 4. v1 → v2 mapping

| v1 ID | v1 decision | v2 disposition |
|---|---|---|
| D1 | 50% thresholds, "SOURCE_DEFINED" | S1/S2 (body > 50% is in the rulebook; the base threshold is Pine-defined) |
| D2 | Core formula | S3 (verified) |
| D3 | **/15** | **WITHDRAWN** → D4 (/14) |
| D4 | Tested-once flagged in output | **WITHDRAWN** → D3 |
| D5 | Zero-base 6.0 / 7.0 | D5 (arithmetic kept, last-zone caveat added, base component → B2) |
| D6 | DL breach deletion | S5 |
| D7 | 3-bar leg-in, "SOURCE_DEFINED" | S6 (`PINE_DEFINED`) |
| D8 | Conflict both directions | S10 |
| D9 | Q/HY/Y detection in Python | D11 |
| D10 | Supply zones informational | D2 |
| D11 | **Sector score = 0** | **WITHDRAWN** → D6 (not evaluated) |
| D12 | **Midpoint buffers** | **WITHDRAWN** (rejected by the user) → D7 |
| D13 | Explosive check = indicator definition | D8 |
| D14 | Zero-base not exceptional | S9 |
| D15 | Weekly trailing deferred | D9 |
| D16 | Universe UNRESOLVED | **Resolved** → D1 (Nifty 100) |
| D17 | Kite approved as primary, limits stated | **Revised** → D10 (investigate only; limits unverified) |
| D18 | Tested-once in zone inventory | **WITHDRAWN** → D3 |
| D19 | WIT/DIT 8–10 candle recency | Retained as source rule (RB 1788); applies to WIT (D16), with the ambiguous band → manual |
| D20 | **Coinciding within ±1%** | **WITHDRAWN** (invented threshold) → N4 |
