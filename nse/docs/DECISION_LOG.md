# Decision Log

**Project:** NSE GTF Demand & Supply Swing-Trading Research System
**Version:** 3.0, dated 2026-11-02. v3.0 records product-owner-approved M1 decisions R1-R6; D41 remains proposed for readings not covered by those approvals. v2.9 added D41 (research-pipeline interpretations; `PROPOSED`, pending review). v2.8 added D40 (official calendar tables 2021-2025, B17; `PROPOSED`, pending review). v2.7 added D39 (per-date calendar ambiguity, audit L10 option B). v2.6 records the user's approval of P1-P3 as D36-D38 and the provisional approval of the D30 special-session rule (§1E). v2.5 added D33-D35 from the Phase 1 correctness audit (`PHASE1_CORRECTNESS_AUDIT.md`). v2.4 adds user-approved decisions D29-D32 (§1D) for the external-validation phase. v2.3 added D24-D28 (§1C) for HTF freshness (B16). v2.2 added D21-D23 (§1B), resolving B13 and B14 and deciding the B8 approach. v2.1 added D12-D17 (§1A). v2.0 replaced v1; §4 maps old IDs to new.

**ID note:** D18–D20 are not reused. They appear in the v1 history table (§4) with different meanings, so the new decisions start at D21.
**References:** `RB n` = Trading Rulebook line; `PS n` = Pine Script line. Blocker IDs (B*, N*) are defined in `IMPLEMENTATION_BLOCKERS.md`.

**Repository layout (since 2026-10-26):** everything for this project lives under `nse/`. The two reference sources are in `nse/sources/` (kept byte-for-byte; their SHA-256 hashes are pinned by `tests/test_repo.py`). The four current documents are in `nse/docs/`, the two superseded audit reports in `nse/docs/archive/`, and the Zone Engine in `nse/zone-engine/zone_engine.py` (tests in `tests/`).

**Status tags**

| Tag | Meaning |
|---|---|
| `USER_APPROVED` | Explicit user decision. Authoritative. It is never reclassified as unresolved. |
| `SOURCE_DEFINED` | Stated explicitly in the Rulebook. |
| `PINE_DEFINED` | Observed Pine behaviour where the Rulebook is silent. Used only if it does not conflict with an explicit rule (D12). |
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
- **Status:** `PROPOSED`, 2026-10-28. **Pending the user's review of this wording.** The user approved the underlying decisions on 2026-10-28:
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
    - 20 Jan 2024 (NSE/MSD/60340) withdraws the DR-switch session announced in NSE/MSD/59999 and holds "regular trading sessions ... as per regular market timings", without printing the times. *Proposed:* record 09:15-15:30 from NSE/CMTR/41180, so it is also `NORMAL_SPECIAL`. This is the one session whose hours come from a second circular.
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
- **Status:** `PROPOSED` as an umbrella, 2026-10-29; **partially superseded by USER_APPROVED M1 decisions R1-R6, 2026-11-02**. The remaining D41 readings are not approved. The approvals are recorded in `DECISION_REGISTER.md` and do not approve unrelated D41 items.
- **Proposed behaviour:** the fourteen readings P-TREND-1, P-LOC-1 to P-LOC-3, P-MAT-1, P-MAT-2, P-COIN-1, P-COIN-2, P-CAL-1, P-LVL-1, P-LVL-2, P-CONF-1, P-G8-1 and P-DQ-1, listed with their effect and code location in `RESEARCH_PIPELINE.md` section 4.
  - **Approved in M1:** P-LOC-1 / R1 (CMP only); P-TREND-1 / R2 (12 o'clock maps to STRONG_UP, label retained); P-COIN-1 / R3 (actual demand-range overlap; Aggressive remains distinct); P-MAT-1 and P-MAT-2 / R5 (approved HOC/EQB outcomes); P-COIN-2 / R6 (known absence passes G6 as Standard, unknown remains MANUAL).
  - The separate R4 approval confirms D24's own-timeframe completed-close invalidation and requires SL-hit events to remain separate from zone invalidation events.
  - Other D41 readings remain PROPOSED, including P-LOC-2 (price inside tested HTF demand), P-LOC-3, P-CAL-1, P-LVL-1 to P-LVL-3, P-CONF-1, P-G8-1, P-DQ-1, P-CA-1/2, P-REF-1, P-BT-1 and M1 reporting.
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

The full remaining list is in `IMPLEMENTATION_BLOCKERS.md` Part 4 ("Decisions still required before reliable implementation"). None of it reopens D1–D17 or D21–D39 (D40 is proposed, pending review).

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
