# Technical Specification: NSE GTF Demand & Supply Swing-Trading Research System

---

## A. Files Inspected

| File | Type | Size | Role |
|---|---|---|---|
| `Trading Rulebook 341a82c22ebf8056a235c9695e1c0d87.md` | Markdown | 326 KB | **Primary source of truth.** Complete GTF methodology across 6+ sections: pre-trade checklist, zone scoring, TDA, MTFA, execution mechanics, and special strategies. |
| `Demand&Supply Indicator.pine` | PineScript v6 | ~2,750 lines | **Indicator implementation.** Automated zone detection, multi-TF display, scoring, trend engine, and HTF conflict detection. Not to be modified. |
| `README.md` | Markdown | ~210 lines | Describes Jake Schincariol's day-trading ORB skill repo. Separate strategy. Not used as a source for this system. |
| `trader-scanner/SKILL.md` through `trader-pelosi/SKILL.md` (11 files) | Markdown | Variable | Documents the repo's ORB day-trading tools. Separate strategy. Referenced only to identify the existing repo's architecture for use as a software scaffold. |

**Source-of-truth hierarchy:**
1. Trading Rulebook (explicit written rules)
2. Indicator behavior (where it implements a rule, it is treated as intentional)
3. This specification (records both; never invents a rule not present in either source)

---

## B. Existing Indicator Behavior

### B.1 Candle Classification

The indicator classifies every confirmed candle into one of three categories before any zone logic runs.

```
body_size     = abs(close - open)
total_range   = max(high - low, syminfo.mintick)
body_ratio    = body_size / total_range

is_base        = body_ratio ≤ i_base_threshold          (default 0.50)
is_strong_bull = is_bull AND (body_ratio > i_legout_threshold OR close > high[1])   (default 0.50)
is_strong_bear = is_bear AND (body_ratio > i_legout_threshold OR close < low[1])
```

A candle is "strong" if its body ratio exceeds the leg-out threshold **or** if its close breaks beyond the prior candle's extreme: the second condition captures momentum achievement independently of candle shape.

---

### B.2 Zone Detection Algorithm: Daily Timeframe

**Phase 1: Cluster (base) accumulation**

A cluster starts on the first `barstate.isconfirmed` base candle that immediately follows a strong candle (within 3 bars). The strong candle becomes the **leg-in**. The cluster then accumulates base candles up to `i_max_base_candles` (default 3), as long as `f_cluster_can_continue()` returns true:

```
inside_wick    = high ≤ cluster_wick_high AND low ≥ cluster_wick_low
is_transition  = inside_wick AND body_ratio ≤ i_base_threshold × 1.5
breaks_out     = close > cluster_wick_high OR close < cluster_wick_low
continues      = (is_base AND NOT breaks_out) OR is_transition
```

Each additional base candle extends the cluster's wick envelope (`cluster_wick_high`, `cluster_wick_low`) and body envelope (`cluster_body_high`, `cluster_body_low`). The final base candle's body and wick boundaries are separately tracked as `last_base_body_*` and `last_base_wick_*`.

**Phase 2: Leg-out detection**

When a candle ends the cluster (not a base, or cluster is at max), it is tested as a potential leg-out:

```
is_legout_bull = is_bull AND (body_ratio > i_legout_threshold OR close > cluster_wick_high)
is_legout_bear = is_bear AND (body_ratio > i_legout_threshold OR close < cluster_wick_low)

combined_high  = max(legin_high, cluster_wick_high)
combined_low   = min(legin_low, cluster_wick_low)

legout_achieved_bull = close > combined_high   ← "achievement" check
legout_achieved_bear = close < combined_low
```

**Pattern classification (direction of leg-in → direction of leg-out):**

| Leg-In | Leg-Out | Pattern | Zone Type |
|---|---|---|---|
| Bear (down) | Bull (up) | DBR: Drop-Base-Rally | Demand (reversal) |
| Bull (up) | Bull (up) | RBR: Rally-Base-Rally | Demand (continuous) |
| Bull (up) | Bear (down) | RBD: Rally-Base-Drop | Supply (reversal) |
| Bear (down) | Bear (down) | DBD: Drop-Base-Drop | Supply (continuous) |

A zone is created **only if both the leg-out direction matches the pattern AND achievement is satisfied** (close beyond `combined_high` or `combined_low`).

**Phase 3: Deferred achievement (pending zones)**

If the leg-out candle has the correct direction but fails achievement (does not close beyond the combined extreme), the indicator sets `pending_left = 2` and looks ahead up to 2 more confirmed candles for a strong candle that achieves. If achievement occurs within 2 bars, the zone is created using the boundaries from the original cluster. If not, the pending state clears.

**Phase 4: Zero-base DBR / RBD zones**

As a separate path, if two consecutive strong candles form in opposite directions with no base candles between them (`zero_base_dbr` or `zero_base_rbd`), a zone is created with `base_count = 0`.

**Phase 5: Additional leg-out tracking**

After each zone is created, the indicator tracks up to 3 additional bars following the zone's creation bar. Any strong candle in the matching direction increments `zone_legout_count` up to a maximum of 5.

---

### B.3 Proximal Line (PL) and Distal Line (DL) Calculation

Two methods, selectable via `i_zone_method`:

**"Body to Wick" (default):**

| Zone Type | Proximal Line | Distal Line (normal) | Distal Line (exceptional) |
|---|---|---|---|
| Demand | Top of base body envelope (`cluster_body_high`) | Lowest wick of base candles (`cluster_wick_low`) | `min(legin_low, cluster_wick_low, legout_low)` |
| Supply | Bottom of base body envelope (`cluster_body_low`) | Highest wick of base candles (`cluster_wick_high`) | `max(legin_high, cluster_wick_high, legout_high)` |

For reversal patterns (DBR, RBD), the exceptional DL also includes `legin_low` / `legin_high`.
For continuous patterns (RBR, DBD), only `cluster_wick_*` and `legout_*` are considered.

**"Wick to Wick":**
PL uses the wick extreme of the cluster (highest wick for demand, lowest wick for supply) instead of the body. DL calculation is the same as above.

**Exceptional flag:**
`is_exceptional = (demand: distal < cluster_wick_low) OR (supply: distal > cluster_wick_high)`
This is true when the DL is extended beyond the base-only wick to include the leg-in or leg-out extreme.

---

### B.4 Zone Properties Stored Per Zone

| Property | What It Records |
|---|---|
| `zone_tops`, `zone_bottoms` | Top and bottom price of the zone box |
| `zone_is_demand` | True = demand, false = supply |
| `zone_test_count` | 0 = fresh, 1 = tested once, 2+ = tested multiple |
| `zone_last_test_bar` | Bar index of last test (prevents double-counting same bar) |
| `zone_is_exceptional` | Whether DL was extended to extreme wick |
| `zone_strong_closing` | True if leg-out closed beyond leg-in extreme (demand: `close > legin_high`; supply: `close < legin_low`) |
| `zone_has_gap` | Window gap present: demand = `legout_low > cluster_wick_high`; supply = `legout_high < cluster_wick_low` |
| `zone_pattern_type` | "DBR", "RBR", "RBD", or "DBD" |
| `zone_base_count` | Number of base candles (0 for zero-base zones) |
| `zone_legout_count` | Number of strong leg-out candles tracked (1–5) |
| `zone_bar` | Bar index when zone was created |
| `zone_origin_enabled` | True when an origin sub-zone is drawn (only when base_count > 1) |

---

### B.5 Origin Zones

Each zone with `base_count > 1` has an associated origin sub-zone drawn at:
- Origin PL = last base candle body high (demand) or body low (supply)
- Origin DL = min/max of last base wick and leg-out wick

Origin zones show the most concentrated institutional origin within a multi-base cluster. For single-base zones, the origin coincides with the main zone and is not drawn separately.

---

### B.6 Zone Test Detection

Executed on every `barstate.isconfirmed` bar:

```
Daily:   tested = (is_demand AND low  ≤ proximal) OR (is_supply AND high ≥ proximal)
Weekly:  tested = (is_demand AND w_low1  ≤ proximal) OR (is_supply AND w_high1 ≥ proximal)
Monthly: tested = (is_demand AND m_low1  ≤ proximal) OR (is_supply AND m_high1 ≥ proximal)
```

For Weekly and Monthly, the indicator uses the **previous** completed period's wick extremes (`[1]` lookback), ensuring only fully closed bars are assessed.

To prevent a single volatile bar from incrementing `test_count` more than once: `array.set(zone_test_count, i, test_count + 1)` only when `bar_index != last_test_bar`.

---

### B.7 Zone Visual States and Coloring

| State | Daily color | Weekly color | Monthly color |
|---|---|---|---|
| Fresh demand | `i_demand_color` (default: green, 80% transparent) | `i_weekly_demand_color` (blue) | `i_monthly_demand_color` (purple) |
| Fresh supply | `i_supply_color` (red) | `i_weekly_supply_color` (orange) | `i_monthly_supply_color` (maroon) |
| Fresh exceptional | Separate configurable colors | Same pattern | Same pattern |
| Tested once | `i_tested_once_color` (yellow, 70% transparent): shared across all TFs | ← same | ← same |
| Tested 2+ | `i_tested_color` (gray, 70% transparent): shared across all TFs | `i_tested_weekly_color` | `i_tested_monthly_color` |
| HTF conflict | Fuchsia border override on daily zone | - | - |

---

### B.8 Zone Score Display

Each zone label shows:
```
[PATTERN] [SCORE]/7 [CLOSE_FLAG] [GAP_FLAG] [TEST_FLAG]
PL: [proximal price]
DL: [distal price]
R:  [PL-DL distance]
⚠ [W SZ @ X.XX] if HTF conflict
```

Score formula (`f_calc_core_score`):

```python
freshness  = 3.0 if test_count == 0 else (1.5 if test_count == 1 else 0.0)
strength   = 2.0 if (legout_count >= 2 or (legout_count >= 1 and has_gap)) else (1.0 if legout_count >= 1 else 0.0)
time_score = 2.0 if base_count <= 3 else (1.0 if base_count <= 5 else 0.0)
core_score = freshness + strength + time_score
```

Notes:
- `base_count = 0` scores `time_score = 2.0` (falls in the "≤ 3" bucket)
- `legout_count` is initialized to 1 at zone creation and may increment to 5
- `has_gap` = window gap flag (not gap type)
- The displayed score is **core score only** (out of 7). The 8-point confluence score is not computed by the indicator.

---

### B.9 HTF Conflict Detection (`f_check_zone_conflict`)

Applied to daily demand zones only:
- Scans all active weekly and monthly zones
- Flags a conflict if an opposing zone (supply for a demand zone) has `test_count < 2` AND its proximal line is within `i_conflict_distance_pct` (default 5%) above the daily demand zone's proximal line
- Monthly conflicts override weekly in the displayed label
- Conflict border: fuchsia, width max(border_width, 2)

---

### B.10 Trend Engine

**SMA 50 Clock (current-TF):**
```
sma50             = ta.sma(close, 50)
sma50_change_pct  = (sma50 - sma50[i_clock_lookback]) / sma50 * 100
```
Maps to 8 clock positions (12, 1, 2, 2-3, 3, 3-4, 4, 5, 6 o'clock) based on percentage thresholds.

**HTF SMA 50 trend (Dashboard 2):**
Fetched via `request.security` for D, W, M, 3M, 6M, 12M with `barmerge.lookahead_off`. Shows UP/DOWN/RANGING for each timeframe.

**EMA 20/50/200 on current TF:**
- EMA 20, EMA 50: standard EMAs
- EMA 200: user-selectable EMA or SMA (default SMA, to match institutional "200 DMA")

**HTF EMA 20 horizontal levels:**
Fetched for W, M, 3M, 6M, 12M via `request.security`. Displayed as horizontal dotted lines extending across the chart.

**EMA cross signals:**
- Major: EMA 50 × EMA 200 (Golden / Death Cross)
- Minor: EMA 20 × EMA 50

---

### B.11 Weekly and Monthly Zone Detection

**Trigger:** `w_bar_change` and `m_bar_change` (when the weekly or monthly bar closes).

Weekly and monthly zones use an **identical algorithm** to the daily zones, but operating on previous-period OHLC data:
- Weekly: `w_open1, w_high1, w_low1, w_close1` (previous week's closed bar, fetched via `request.security`)
- Monthly: `m_open1, m_high1, m_low1, m_close1` (previous month's closed bar)

Each runs the same cluster → leg-in → base → leg-out → achievement logic. The same `i_base_threshold`, `i_legout_threshold`, `i_max_base_candles` inputs apply to all three timeframes. Weekly zones have a dashed PL/DL style; monthly zones have a dotted style.

**Additional leg-out tracking** (`zone_legout_count` increments within 3 subsequent week/month bars) mirrors the daily logic but is index-tracked via `w_seq` and `m_seq` counters rather than `bar_index`.

---

### B.12 What the Indicator Does NOT Display

| Not in indicator | Where it is documented |
|---|---|
| Quarterly and Half-Yearly zone detection | Rulebook Section 3, TDA Steps 2–3 |
| Curve position (VLOC / LOC / EQB / HOC / VHOC) | Rulebook Section 4, Chapter 1 |
| Zone authenticity (authentic vs non-authentic) | Rulebook Section 2, H6 |
| Gap type (Novice / Pro / Window) beyond a boolean flag | Rulebook Section 2, L3 and Section 6 |
| Confluence score (up to +8 points) | Rulebook Section 2, Part B |
| Full 15-point score | Rulebook Section 2, Part C |
| Coinciding vs. Aggressive classification | Rulebook Section 4, Chapter 4 |
| Entry, SL, target, or position-sizing calculations | Rulebook Section 5 |
| Sector / Nifty D&S zone drawing (only symbol input exists) | Rulebook Section 2, M1 |

---

## C. Trading Rules Explicitly Documented in the Rulebook

### C.1 Critical Pre-Trade Rules (Hard Gates)

**C1: Position sizing:** `Quantity = RPT ÷ (Entry − SL)`. RPT = 0.5–1% capital (learning), 1–1.5% (intermediate), 1.5–2% (professional).

**C2: Minimum R:R:** Every trade must offer ≥ 2:1 Risk-to-Reward. Entry-to-target distance ÷ entry-to-SL distance ≥ 2.

**C3: TDA completed:** Full top-down scan from Yearly → Half-Yearly → Quarterly → Monthly → Weekly → Daily must be done before every trade. Cannot be skipped for any trade type.

**C4: MTFA aligned:** All three components: HTF Location (Curve position), ITF Trend (SMA 50 clock or ATA), LTF Execution zone: must point in the same direction.

**C5: Zone is 100% fresh (for Type 1 entry):** Proximal Line has never been touched by any wick or body after the leg-out candle closed.

**C6: Entry outside the zone with buffer:** Entry placed above PL (demand) or below PL (supply). Never inside the zone. Never at the DL. Always limit orders.

**C7: SL beyond DL with meaningful buffer:** SL placed below DL (demand) or above DL (supply). Hard order in broker system, immediately upon entry. Permanently locked after trigger.

### C.2 High-Priority Rules

**H1: Minimum 1–3 base candles (ideal):** Score 2 pts. 4–5 bases = 1 pt. 6+ = garbage area, reject.

**H2: Explosive leg-out:** Body > 50% of range AND price achievement (close beyond combined_high/low). Score 2 pts for 2+ or 1+gap; 1 pt for 1 candle; 0 pts = reject.

**H3: ITF trend confirmation:** ITF SMA 50 clock (12–3 = uptrend, 3–6 = downtrend) or ATA must support trade direction.

**H4: Curve position aligned:** VLOC/LOC for longs; HOC/VHOC for shorts; EQB = trend-only.

**H5: Closing concept:** Leg-out candle closes beyond leg-in extreme (demand: close > legin_high; supply: close < legin_low).

**H6: Zone authenticity:** Authentic zone formed independently. Non-authentic zones (formed by bouncing off a prior zone) require exceptional closing + violent momentum to override.

### C.3 Medium-Priority Confluence Factors (Add-on Points)

**M1: Sector + Nifty alignment:** Stock + Sector + Nifty all at aligned D/S zones = +2 pts. Any two = +1 pt. Mandatory for DIT/HIT.

**M2: HTF EMA 20 in zone:** 2+ HTF EMA 20 lines running through execution zone = +2 pts. 1 = +1 pt.

**M3: Coinciding vs Aggressive:** Coinciding (LTF PL aligns with HTF PL) is Priority Rank 1. Aggressive (inside HTF area but floating away from PL) requires 7/7 + achievement.

**M4: Exceptional marking:** For reversal patterns, DL may be expanded to include extreme wicks of leg-in/leg-out. PL never changes.

**M5: Structural target at ITF opposing zone:** Set target at nearest fresh opposing zone PL on ITF, not arbitrary 2× calculation.

### C.4 Low-Priority Confluence Factors

**L1: Golden/Death cross inside zone:** +1 pt if valid cross occurs inside a pre-existing zone in a trending market.

**L2: RSI divergence or Stochastic OS/OB:** +1 pt. Check, note, then remove indicator from chart.

**L3: Gap application:** +1 pt. Novice Gap (trend direction), Pro Gap (counter-trend), Window Gap (between base and leg-out). Only Window Gap has execution implications (adjust entry upward if close to PL).

### C.5 Absolute Rejection Red Flags

**RF1**: Zone tested 2+ times. **RF2**: LTF zone inside opposing HTF zone (use Confirmation Entry or reject). **RF3**: ITF trend strongly against trade AND not at VLOC/VHOC. **RF4**: Garbage area (6+ bases, unclear structure). **RF5**: Emotional state (FOMO, revenge, boredom). **RF6**: F&O lot size forces risk beyond RPT. **RF7**: Reaction zone with poor closing. **RF8**: No 2:1 R:R available to nearest structural target. **RF9**: Mental state compromised. **RF10**: Trading with scared money.

### C.6 Multi-Timeframe Workflow (MIT Focus)

| Step | Timeframe | Purpose |
|---|---|---|
| TDA 1 | Yearly | Grand structural context |
| TDA 2 | Half-Yearly | Major macro barriers |
| TDA 3 | Quarterly | Key obstacle map |
| TDA 4 | **Monthly → HTF Location** | Draw Curve, determine VLOC/LOC/EQB/HOC/VHOC |
| TDA 5 | **Weekly → ITF Trend** | SMA 50 clock or ATA, intermediate momentum |
| TDA 6 | **Daily → LTF Execution** | Fresh 7/7 zone, entry/SL/target calculation |

NSE-specific: 375-minute session; preferred timeframes for WIT/DIT execution are **125min** (375÷3=3 perfect candles) and **75min** (375÷5=5 perfect candles).

### C.7 Entry Types

| Type | Name | Zone Score Required | Method |
|---|---|---|---|
| Type 1 | Set & Forget | 7/7 (pristine) | Limit order at PL + buffer; SL at DL − buffer; walk away. Zero screen time after placement. |
| Type 2 | Wait for Close | 6/7 (documented but discouraged) | Wait for first candle to close inside zone, second candle to open inside zone, enter on second open. |
| Type 3 | Confirmation on Zone | 5/7 (documented but discouraged) | As Type 2 plus price must break back above PL before entry. |

**Author's stated recommendation:** *"I never use Entry Type 2 or 3, and neither should you."* Types 2 and 3 are documented for educational understanding but not recommended in practice.

### C.8 Buffer Sizing Guidelines (from Rulebook, Section 5, Chapter 1)

**Entry buffer (above PL for demand / below PL for supply):**

| Stock Price Range | Buffer |
|---|---|
| Below ₹100 | ₹0.25 – ₹0.50 |
| ₹100 – ₹500 | ₹0.50 – ₹2 |
| ₹500 – ₹2,000 | ₹2 – ₹5 |
| Above ₹2,000 | ₹5 – ₹10 |

**SL buffer (below DL for demand / above DL for supply):**

| Stock Price Range | Buffer |
|---|---|
| Below ₹100 | ₹0.50 – ₹1 |
| ₹100 – ₹500 | ₹1 – ₹3 |
| ₹500 – ₹2,000 | ₹3 – ₹8 |
| Above ₹2,000 | ₹8 – ₹15 |

The rulebook states explicitly: *"These are guidelines, not rigid rules."*

### C.9 Stop Loss Rules

Three SL placement approaches:
1. **Normal SL:** DL − buffer. Standard zones, calm market.
2. **Exceptional SL:** Most extreme wick of leg-in / leg-out − buffer (for zones with extreme wicks beyond the base). Applied automatically when `is_exceptional = true` in the indicator.
3. **Shri Krishna SL:** HTF Location zone's DL − buffer. Sideways or highly volatile markets.

**Absolute SL rules:**
- Hard order in broker system on entry: never a mental note
- SL PERMANENTLY LOCKED after trade triggers: no widening, no moving to break-even
- Exit on **touch**, not on candle close
- Never average down

### C.10 Target Rules

Priority order:
1. **Structural target:** PL of nearest fresh opposing zone on ITF. Often 3:1 to 10:1+.
2. **Minimum mathematical target:** Entry + 2 × (Entry − SL). Exactly 2:1.
3. **Weekly Demand Trailing:** No fixed target; trail SL below each new Weekly DZ's DL as price rises. Used at ATH or when all overhead supply is broken/garbage.

### C.11 SL on Touch vs Zone Break on Close

These two rules are distinct and apply in different contexts:

- **SL exit: touch**: When price hits your stop-loss order, exit immediately. Do not wait for the candle to close. (Execution mechanics, Chapter 2)
- **Zone break for ATA trend analysis: close**: A zone is broken for trend-determination purposes only when a candle CLOSES beyond the DL, not just a wick. (MTFA, Chapter 2)

These do not conflict; they operate in separate domains.

### C.12 10-Trade Monthly Limit

Maximum 10 trades per month. This is a ceiling, not a target. 0–5 per month is explicitly acceptable. Reaching 10 by mid-month means stopping for the rest of the month.

---

## D. Differences Between Indicator and Rulebook

| # | Area | Rulebook Rule | Indicator Behavior | Gap Type |
|---|---|---|---|---|
| D1 | Quarterly / Half-Yearly zones | Required in TDA (Steps 2–3) | Not drawn. Only Daily, Weekly, Monthly. | Missing feature |
| D2 | Curve position | Explicitly required: VLOC/LOC/EQB/HOC/VHOC determination | Not calculated or displayed | Missing feature |
| D3 | Full 15-point score | 7-point core + 8-point confluence = 15 max | Only core score shown (out of 7) | Missing feature |
| D4 | Sector / Nifty alignment score | +2 pts; mandatory for DIT | Symbol inputs exist; no zone detection or alignment scoring on those symbols | Partial implementation |
| D5 | Gap type | Novice, Pro, Window gap: each with distinct meaning | Single boolean `has_gap` = Window gap only (leg-out low > cluster wick high) | Partial implementation |
| D6 | "Achievement" qualitative check | "Price moves meaningfully away, breaks prior structure": size and context required | Body ratio threshold + close-beyond-combined-high check. No "relative to surrounding candles" check. | Simplified implementation |
| D7 | Zone authenticity | Non-authentic zones require exceptional closing to override | Not detected or flagged | Missing feature |
| D8 | Coinciding vs. Aggressive | Must classify each setup; coinciding = Priority 1 | Not computed or displayed | Missing feature |
| D9 | Zero-base zones (base_count=0) | Scoring table starts at "1–3 base candles = 2 points"; no explicit rule for 0 base candles | `base_count = 0` scores `time_score = 2.0` (since 0 ≤ 3) | Minor ambiguity (see Section E) |
| D10 | "Wick to Wick" zone method | Only "Body to Wick" method is described in the rulebook | "Wick to Wick" is an available option in the indicator | No rulebook conflict; indicator extends the documented method |
| D11 | SMA 50 clock ranging threshold | "Any doubt → classify as sideways" | Configurable numeric threshold (default 0.1% change per `lookback` bars) | Implementation detail |
| D12 | LTF proximity rule for WIT/DIT | "Only last 8–10 candles on execution TF are valid" | No recency filter on zone display | Missing filter (applies only to WIT/DIT, not MIT) |

---

## E. Ambiguous or Conflicting Rules Requiring Your Decision

These items require explicit decisions before any implementation proceeds. They are listed as separate concerns:
zone classification, numerical scoring, and trade-entry eligibility are treated as distinct questions.

---

### E.1 Tested-Once Zones: Entry Eligibility Contradiction

**The tension:**

The rulebook contains three separate instructions that partially conflict:

| Source | Instruction |
|---|---|
| Section 1 (C5) | "The zone's Proximal Line must NEVER have been touched. Tested once = score drops from 3 to 1.5. Proceed only with exceptional HTF backing." |
| Section 2 (Core Score) | Tested once = 1.5 points → Core total max = 1.5 + 2 + 2 = **5.5 / 7**. Since 5.5 < 7, a tested-once zone mathematically **cannot reach the 7/7 threshold** for Type 1 Set & Forget entry. |
| Section 1 (10 Essential Checks, #3) | *"Is this zone 100% FRESH?"*: implies only fresh zones are valid for any entry. |

**What the scoring system implies:** A tested-once zone can never score 7/7 Core, so it is automatically ineligible for Type 1 entry. The only entries available would be Type 2 or Type 3: which the author then explicitly says to never use.

**What the C5 text implies:** "Proceed only with exceptional HTF backing": some door is left open for tested-once zones under exceptional conditions.

**The decision needed from you:**

> For this research system: Should a tested-once zone (core score max 5.5/7) ever generate a paper-trading entry signal: under any conditions (e.g., score ≥ 5.5/7 AND VLOC AND sector +2 AND EMA +2 = total ≥ 9.5/15)?
>
> **Option A:** No. A tested-once zone never produces an entry signal. It is classified, scored, and displayed but marked "entry ineligible." (Consistent with the 7/7 hard minimum and the Essential Check #3.)
>
> **Option B:** Yes, under exceptional conditions. Specify the minimum total score and required confluence factors for a tested-once zone to qualify. (Consistent with C5's "proceed with exceptional HTF backing" text.)

**What the indicator currently does:** Displays tested-once zones in yellow and scores them at 1.5 freshness. Makes no entry eligibility decision: that logic is outside the indicator. This behavior is preserved regardless of which option you choose.

---

### E.2 Zero-Base Zones: Scoring Interpretation

**The tension:**

The Core Score table in Section 2 states: *"1–3 base candles = 2 points."* The indicator creates zones with `base_count = 0` (two consecutive strong candles in opposite directions with no base between them), and scores them at `time_score = 2.0` because `0 ≤ 3`.

The rulebook's scoring section does not explicitly mention zero-base zones. The phrase "1 to 3 base candles" is the stated range. Zero is not addressed.

**The decision needed from you:**

> Should a zero-base zone (DBR or RBD with no base candles) score `time_score = 2.0` (as the indicator does), or should it be treated as a special case requiring a separate rule?

**Options:**
- **Option A:** 0 base candles = 2 points. Consistent with the indicator and with the principle that "fewer bases = faster institutional victory = stronger zone."
- **Option B:** 0 base candles = an exceptional category with its own score or handling (e.g., requires the strong_closing flag to be true to validate the zone).

---

### E.3 Buffer Amounts: Objectivity for Backtesting

**The tension:**

The rulebook provides price-tier ranges (e.g., "₹2–₹5 for ₹500–₹2,000 stocks") but explicitly states: *"These are guidelines, not rigid rules."* A backtesting system cannot use a range: it needs a single deterministic value.

**The decision needed from you:**

For the backtesting and paper-trading system, should buffers be:

> **Option A:** Mid-point of each tier (e.g., ₹500–₹2,000 stocks → ₹3.50 entry buffer, ₹5.50 SL buffer). Simple and defensible.
>
> **Option B:** A fixed percentage of the stock price (e.g., entry buffer = 0.3% of price, SL buffer = 0.5% of price). More objective and scales naturally across all price levels.
>
> **Option C:** A multiple of ATR(N): e.g., entry buffer = 0.25 × ATR(14), SL buffer = 0.50 × ATR(14). Most statistically defensible but requires ATR data.
>
> **Option D:** Use the rulebook tier exactly as written; always apply the minimum of the range for conservative simulation.

---

### E.4 "Explosive" Leg-Out: Achievement Objectivity

**The tension:**

The rulebook states achievement requires the leg-out to close "meaningfully away" and "stands out visually." The indicator operationalizes this as `close > combined_high` (close beyond the combined wick of leg-in + cluster). This is objective and binary.

However, the rulebook also says: *"A big-bodied candle inside the range of surrounding candles achieves nothing: it's functionally a base candle despite the math."*

The indicator does NOT check whether the leg-out candle is visually larger than surrounding candles, only that it closes beyond the combined high/low.

**The decision needed from you:**

> Is the indicator's achievement check (`close > combined_high`) sufficient as the "explosive" definition for the research system: or should an additional filter be added (e.g., leg-out body size > average body size of the last N candles)?

If you want an additional filter, specify the exact condition.

---

### E.5 DL Breach: Zone Permanence

**The tension:**

The rulebook's test-count logic (0 = fresh, 1 = tested, 2+ = dead) handles PL touches. But if price closes **below the DL** of a demand zone (the zone is "broken" structurally), the rulebook does not give an explicit rule for what happens to the zone's status.

The indicator keeps the zone displayed and increments `test_count` each time the PL is touched, but does not have a "DL breach = zone deleted" flag.

**The decision needed from you:**

> If price closes below a demand zone's DL (or above a supply zone's DL), should the zone be:
>
> **Option A:** Treated as "tested 2+" (test_count ≥ 2): existing indicator logic handles this if the breach causes the PL to be crossed twice.
>
> **Option B:** Permanently invalidated with a separate flag (`zone_breached = true`) and excluded from all future signals, regardless of test count.

---

### E.6 Leg-In Detection Window

**The tension:**

The indicator allows a base candle to start a cluster if a strong candle appeared within the last 3 bars (`bar_index - last_strong_index ≤ 3`). The rulebook describes the leg-in as the candle immediately preceding the base, but does not specify an exact number of allowed intervening bars.

**The decision needed from you:**

> Is the indicator's 3-bar window for leg-in detection correct for your methodology, or should it be stricter (1 bar: immediate predecessor only) or more flexible (5 bars)?

This only matters if you want the backtesting zone detection to be intentionally stricter or looser than the indicator.

---

### E.7 Weekly Trailing SL Algorithm

**The tension:**

The rulebook describes trailing the SL below "each new quality Weekly Demand Zone's DL" as price rises. The phrases "each new" and "quality" are not precisely defined. This method is documented in principle but has no algorithmic specification.

**The decision needed from you:**

> For the paper-trading / signal system, should weekly trailing SL be implemented? If yes, what defines "a new quality Weekly DZ" for trailing purposes? (e.g., any newly formed weekly demand zone with score ≥ X?)

If not needed in the initial build, this can be deferred.

---

## F. Proposed System Architecture

All components are strictly separated. No component reaches across boundaries except through defined interfaces.

```
┌─────────────────────────────────────────────────────────────┐
│                     MARKET DATA LAYER                       │
│  NSE OHLCV (Daily, Weekly, Monthly, 125min, 75min)          │
│  Corporate action adjustments (splits, bonuses, dividends)  │
│  Nifty 50 + Sector index data                               │
│  Outputs: Adjusted price series per symbol                  │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                ZONE DETECTION ENGINE                         │
│  Ports the indicator's algorithm to Python                  │
│  Inputs: Adjusted OHLCV series per TF per symbol            │
│  Outputs per symbol + TF: List of zones with:               │
│    - PL, DL, zone type, pattern, is_exceptional             │
│    - base_count, legout_count, has_gap, strong_closing      │
│    - core_score, test_count (as of each bar)                │
│    - formation_bar, last_test_bar                           │
│  Runs daily after each session close                        │
│  Zone state is time-indexed: reproducible at any past bar   │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│             MULTI-TIMEFRAME ANALYSIS ENGINE                  │
│  Inputs: Zone lists (Daily, Weekly, Monthly) per symbol     │
│          SMA 50 per timeframe                               │
│  Outputs per symbol per bar:                                │
│    - SMA 50 clock angle (ITF = Weekly for MIT)              │
│    - ITF trend direction (UP/DOWN/RANGING)                  │
│    - Curve position (VLOC/LOC/EQB/HOC/VHOC)                │
│      [requires nearest fresh Monthly DZ and SZ]             │
│    - HTF conflict flag for each daily zone                  │
│    - Coinciding vs Aggressive classification                │
│  All calculations use barstate.isconfirmed equivalent       │
│  (only confirmed past bars, never current forming bar)      │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│              TRADE QUALIFICATION ENGINE                      │
│  Inputs: Zone data, MTFA outputs, confluence inputs         │
│  For each candidate zone, computes:                         │
│    - Core score (already in zone data)                      │
│    - Confluence score: sector alignment, HTF EMA 20 in zone │
│      gap type, RSI/Stoch state, EMA cross in zone           │
│    - Total score (out of 15)                                │
│    - Pre-trade checklist (10 essential checks)              │
│    - Entry eligibility (fresh 7/7+ Type 1 only, pending     │
│      your decision on E.1)                                  │
│    - Entry, SL, target prices (with buffer rules)           │
│    - R:R calculation (must be ≥ 2:1)                        │
│  Outputs: Qualified trade proposals with full reasoning      │
│  Manual review required for: confluence score inputs,        │
│    sector alignment, EMA 20 in zone, gap type, RSI/Stoch    │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│           RISK MANAGEMENT & POSITION SIZING                  │
│  For each qualified trade proposal:                         │
│    - Quantity = RPT ÷ (Entry − SL), floor to whole shares  │
│    - Validates: R:R ≥ 2:1, Quantity ≥ 1 share               │
│    - Validates: max open risk (sum of all active trade SLs) │
│    - Validates: monthly trade count ≤ 10                    │
│    - Validates: no F&O lot-size issues                      │
│  Outputs: Sized orders with risk amount, R:R, quantity      │
└───────────────────────────┬─────────────────────────────────┘
                            │
        ┌───────────────────┼──────────────────────┐
        │                   │                      │
┌───────▼──────┐  ┌─────────▼────────┐  ┌─────────▼──────────┐
│  HISTORICAL  │  │  PAPER TRADING   │  │  TRADE JOURNAL &   │
│  BACKTESTING │  │  SIGNAL SYSTEM   │  │  PERFORMANCE RPT   │
│              │  │                  │  │                    │
│  Replays all │  │  Daily output:   │  │  Inputs: all       │
│  layers over │  │  today's entry   │  │  completed trades  │
│  historical  │  │  alerts, active  │  │  (paper only)      │
│  data.       │  │  positions, and  │  │  Outputs: win rate │
│  No forward  │  │  zone status.    │  │  R:R, max drawdown │
│  data ever   │  │  No orders       │  │  score vs outcome  │
│  used.       │  │  placed. Read-   │  │  correlation, etc  │
│              │  │  only research.  │  │                    │
└──────────────┘  └──────────────────┘  └────────────────────┘
```

**Layer isolation rules:**
- Market Data layer never calls Zone Detection; it only exports cleaned price series.
- Zone Detection has no knowledge of MTFA or trade qualification.
- Trade Qualification reads zone data and MTFA output; it never modifies them.
- Risk Management reads trade proposals; it never reads raw price data.
- Backtesting and Paper Trading are separate modes of the same pipeline. Backtesting runs offline; Paper Trading runs daily after market close.
- **No component connects to Zerodha or any broker API at this stage.**

---

## G. Historical Data Requirements for NSE Stocks

### G.1 What is needed

| Data Type | Granularity | Lookback Required | Purpose |
|---|---|---|---|
| NSE equity OHLCV | Daily bars | 10+ years (2014–present minimum) | Monthly/Weekly zone detection, TDA, backtesting |
| NSE equity OHLCV | 125-minute bars | 5+ years | WIT execution zone detection |
| NSE equity OHLCV | 75-minute bars | 5+ years | WIT/DIT execution zone detection (if needed) |
| Nifty 50 index OHLCV | Daily | Same as equity | Sector/curve context |
| Sector indices (Bank Nifty, Nifty IT, Nifty Auto, Nifty Pharma, Nifty Metal) | Daily | Same | Sector alignment scoring |
| Corporate actions | Adjustments file | Full history | Adjust OHLCV for splits, bonuses, rights issues, dividends |
| NSE symbol universe | Current + historical | Full history | Survivorship-bias-free backtest universe |

### G.2 NSE-Specific Data Considerations

**Trading hours:** 9:15 AM – 3:30 PM IST (375 minutes). No pre-market. No after-hours.

**125min bars:** Not directly available from most vendors. Must be constructed from daily or intraday data:
- 3 bars per day: 9:15–10:20, 10:20–11:25, 11:25–12:30, 12:30–1:35, 1:35–2:40, 2:40–3:30: **wait**: 375 ÷ 125 = 3 bars exactly. Bars: 9:15–11:20, 11:20–1:25, 1:25–3:30.

**75min bars:** 5 bars per day: 9:15–10:30, 10:30–11:45, 11:45–1:00, 1:00–2:15, 2:15–3:30.

**Corporate actions (CRITICAL):** NSE stocks frequently undergo bonuses (e.g., 1:1 bonus doubles shares, halves price), splits, and rights issues. Unadjusted price data will show artificial price gaps that falsely create "zone" patterns at the adjustment date. All OHLCV must be back-adjusted before zone detection is run.

**Delisted stocks (survivorship bias):** A significant number of NSE stocks get delisted, suspended, or merged every year. Any dataset that only contains currently listed stocks will exclude these, inflating backtest win rates by removing stocks that may have crashed to zero.

### G.3 Practical Data Sources

| Source | Type | Coverage | Notes |
|---|---|---|---|
| Zerodha Kite Connect API | Official broker API | Daily: up to 2,000 days; 1-min: up to 60 days | Requires Kite Connect subscription (~₹2,000/month) + trading account. High quality, adjusted data available. |
| NSE official website (Bhavcopy) | Free EOD | Daily only, full history | No intraday. Good for Daily/Weekly/Monthly zone detection. |
| Upstox API / Angel One SmartAPI | Broker APIs | Similar to Kite | Alternatives if Kite unavailable. |
| Refinitiv / Bloomberg | Institutional | Full history, survivorship-bias-free | Expensive (₹50,000+/year). Most accurate for professional backtesting. |
| Quandl / Nasdaq Data Link | Data vendor | Indian EOD available via some subscriptions | Verify adjustment methodology. |

**Minimum viable data path for Phase 1 (research/paper trading):**
1. NSE Bhavcopy (free, daily OHLCV) for backtesting Daily/Weekly/Monthly zones.
2. Zerodha Kite Connect for current paper-trading data, once you decide to connect.

**What is NOT available for free and cannot be assumed:**
- Tick data
- Survivorship-bias-free intraday history
- Pre-2010 intraday data for most stocks

---

## H. Backtesting Risks

### H.1 Look-Ahead Bias

**Risk level: Very High if not carefully managed.**

| Scenario | How Look-Ahead Enters | Prevention |
|---|---|---|
| Zone detection | A zone forms on bar N. If the system "knows" this zone when evaluating bar N−1, it has used future information. | Use only `barstate.isconfirmed` logic. A zone is only "known" from the bar after its leg-out candle confirmed. |
| Monthly/Weekly zones | A Monthly zone closes on the last trading day of the month. It must not be visible to any daily bar within that same month. | Run monthly zone detection only after the month-end bar is fully closed. Apply the zone starting from the first bar of the next month. |
| SMA 50 / trend | Current-bar SMA 50 uses the current close. | Use only `sma50[1]` (previous bar's SMA) as the trend reading when making bar-N decisions. |
| Freshness status | A zone's test count on any given bar must only reflect touches up to and including that bar. | Zone test_count must be a time-indexed series, not a scalar. |
| "Pending" zone creation | The indicator may create a zone on bar N+1 or N+2 based on future achievement. | This is a form of look-ahead. In backtesting, a pending zone must not be "known" until the achievement bar is confirmed. |

### H.2 Survivorship Bias

**Risk level: High for any NSE dataset that is not explicitly survivorship-bias-free.**

A standard NSE equity dataset will likely contain only stocks that are currently traded and have not been delisted. In a 10-year backtest, stocks that were suspended, went bankrupt, or were merged out of existence will be absent. These stocks were often in long downtrends, meaning the backtest never encounters a losing trade from holding them. This inflates win rates.

**Mitigation:** Use a point-in-time snapshot of the NSE universe that includes all stocks that were listed at each historical date, including those later delisted.

### H.3 Corporate Actions

**Risk level: High if adjustments are not applied.**

A 2:1 bonus issue causes the stock price to halve overnight. Without adjustment, the indicator will detect this as a massive downward gap: a false "explosive bear candle" that creates a phantom supply zone. Every zone formed before the adjustment date and every test count is distorted.

**All OHLCV data must be adjusted backward using the official NSE corporate action file before any zone detection is run.**

### H.4 Slippage and Order Fill Assumptions

| Order Type | Realistic Assumption | What NOT to Assume |
|---|---|---|
| Entry limit order (at PL + buffer) | Fills when `bar.low ≤ limit price` (for demand). If the open gaps below limit, fills at the open price. | Do not assume 100% fill rate. If the open gaps above limit and never touches it, no fill. |
| Stop-loss order (at DL − buffer) | Worst-case: fills at the SL price. If the next-day open gaps below SL, fills at the open. | Do not assume the SL always fills at exactly the SL price. Gap risk is real, especially post-earnings. |
| Market slippage | Add 0.05%–0.10% to entry and exit prices for mid-cap/small-cap stocks. Large-cap stocks (Nifty 50 constituents): 0.01%–0.02%. | Do not assume zero slippage. |

### H.5 Transaction Costs (NSE Equity Delivery)

For multi-day swing trades on NSE (CNC / delivery product type):

| Cost | Rate |
|---|---|
| Zerodha brokerage | ₹0 for equity delivery |
| STT (Securities Transaction Tax) | 0.1% on sell side only |
| Exchange transaction charge (NSE) | ~0.00335% per side |
| SEBI turnover charge | 0.0001% per side |
| Stamp duty | 0.015% on buy side |
| GST (18% on brokerage + transaction charge) | ~18% × exchange charges |
| Total estimated round-trip cost | ~0.12% – 0.15% of trade value |

This must be applied to every simulated trade in the backtest.

### H.6 Unrealistic Fill Scenarios to Exclude

- Partial fills during illiquid sessions (some NSE mid-caps have very low volume; a large position may not fill entirely at limit)
- Circuit breaker hits: NSE upper/lower circuits (5%/10%/20% limits) can prevent any fills for multiple sessions
- T+1 settlement: delivery positions settle in T+1 on NSE (changed from T+2 in 2023). No intraday cash flow impact but relevant for margin considerations

### H.7 Short Selling Limitations

On NSE, equity short selling in the cash (CNC) segment is only available intraday (MIS product type). Overnight short positions require Futures (F&O). Since your rulebook explicitly prohibits F&O for beginners and requires the position-sizing formula (which F&O lot sizes break), **supply zone sell setups cannot be implemented as overnight swing trades in the cash segment**.

**This means:** For this research system, unless F&O is explicitly opted in, only demand zone long setups can be backtested or paper-traded as swing positions.

---

## I. Prioritized Implementation Plan

### Phase 0: Decisions Required First
No implementation until Section E decisions are made (E.1 through E.7). Decisions block the zone detection engine's output schema and the trade qualification logic.

### Phase 1: Data Foundation
1. Download NSE Bhavcopy historical daily OHLCV for Nifty 500 stocks (free from NSE website).
2. Download corporate actions file (NSE NSEIndia/historical data section).
3. Write a Python data pipeline that applies corporate action adjustments and outputs a clean, adjusted OHLCV series per symbol.
4. Verify adjustment correctness on 2–3 stocks with known corporate action dates.
5. Construct 125min and 75min bars from daily data (requires intraday data source).
6. **No broker connection. No API keys. Paper only.**

### Phase 2: Zone Detection Engine
1. Port the indicator's zone detection algorithm to Python, function by function.
2. Implement in this exact order:
   a. Candle classification (`is_base`, `is_strong_bull/bear`)
   b. Cluster accumulation logic
   c. Zone creation with PL/DL for both methods (Body to Wick and Wick to Wick)
   d. Exceptional zone flag
   e. Pattern classification (DBR/RBR/RBD/DBD)
   f. Zero-base zone path
   g. Pending zone (2-bar deferred achievement)
   h. Additional leg-out tracking
   i. Core score calculation (already a 4-line formula)
   j. Test count increment logic (using wick extremes)
3. Run on 5 test stocks, compare output visually against the TradingView indicator on the same data. Output must match before proceeding.
4. All outputs are time-indexed (zone known only from its leg-out bar onward). No future data.
5. **Do not implement Weekly/Monthly zone detection until Daily is validated.**

### Phase 3: MTFA Engine
1. SMA 50 clock computation (percentage-based, matching indicator's formula).
2. HTF SMA 50 trend direction (Daily, Weekly, Monthly, Quarterly).
3. Curve position: compute nearest fresh Monthly DZ below and SZ above current price; divide space into VLOC/LOC/EQB/HOC/VHOC.
4. HTF conflict detection: port `f_check_zone_conflict` to Python.
5. Coinciding vs. Aggressive classification: check if Daily DZ PL is within a defined tolerance of the Monthly DZ PL.

### Phase 4: Trade Qualification Engine
1. Automated checks: core score ≥ 7/7, freshness (per E.1 decision), R:R ≥ 2:1, trend alignment, curve position.
2. Buffer application (per E.3 decision) to compute Entry, SL, Target prices.
3. The 10 pre-trade essential checks.
4. Manual-review flags for: sector alignment score, HTF EMA 20 in zone, RSI/Stoch state (these require human judgment until automated sources are integrated).

### Phase 5: Risk and Sizing Engine
1. `Quantity = floor(RPT ÷ (Entry − SL))`
2. Monthly trade counter (≤ 10 ceiling)
3. Open trade risk accumulator (sum of all active SLs vs. capital)

### Phase 6: Historical Backtesting
1. Walk-forward backtest: train on 2014–2020, validate on 2021–present.
2. Apply transaction costs (0.12–0.15% round-trip).
3. Apply realistic fill logic (limit order fills on wick touch; gap fill at open).
4. Log every trade: entry date, exit date, PL price, DL price, entry price, SL price, target price, quantity, result (SL hit / target hit / open), R multiple, score at entry.
5. Report: win rate, average R multiple, max drawdown, monthly distribution.
6. **Never show P&L projections. Only statistical distributions from historical data.**

### Phase 7: Paper Trading Signal System
1. Daily pipeline running after NSE market close.
2. Updates zone state for all tracked stocks.
3. Outputs: new entry alerts, active position updates, zone-tested alerts.
4. Alert format matches the rulebook's template: stock, score, type, location, trend, sector, entry type, action, note.
5. **No orders. No broker connection. Read-only research.**

### Phase 8: Trade Journal
1. Manual entry of paper trades taken.
2. Records: full pre-trade checklist answers, entry/SL/target/quantity, reason for taking.
3. Post-trade: result, rule-based vs. lucky classification, lesson.
4. Performance aggregation: score vs. outcome correlation, win rate by curve position, by trend direction, by pattern type.

---

## Decisions Needed Before Implementation

| # | Question | Where It Blocks |
|---|---|---|
| **E.1** | Can a tested-once zone (max core 5.5/7) generate any entry signal under exceptional conditions, or is it always entry-ineligible? | Trade qualification engine entry filter |
| **E.2** | Should a zero-base zone (base_count=0) score time_score=2.0 (as the indicator does) or be treated differently? | Zone detection scoring |
| **E.3** | Which buffer formula to use for backtesting? Mid-point of tier, fixed %, ATR multiple, or tier minimum? | Entry/SL price calculation in trade qualification |
| **E.4** | Is the indicator's achievement check (close > combined_high/low) sufficient for "explosive" leg-out, or should an additional filter be added? | Zone detection creation gate |
| **E.5** | If price closes below a demand zone's DL: mark as tested-2+, or add a separate permanent "breached" flag? | Zone state management |
| **E.6** | Is the 3-bar leg-in detection window correct, or should it be stricter / more flexible? | Zone detection cluster start condition |
| **E.7** | Should Weekly Demand Trailing be implemented in Phase 1, or deferred? If implemented, what defines "a new quality Weekly DZ" for trailing? | Trade qualification target-setting logic |
| **E.8** | Should supply zone sell setups be included in backtesting despite NSE CNC overnight short-selling restrictions? (If yes, this requires either simulating F&O or noting that these signals are informational only.) | Backtest universe and position type |
| **E.9** | What is the target NSE stock universe for backtesting? Nifty 50, Nifty 500, or a custom list? | Data requirements and backtest scope |
| **E.10** | Do you have a Zerodha Kite Connect subscription, or should the system be designed around NSE Bhavcopy + a different data provider for Phase 1? | Data pipeline architecture |

**Please provide decisions on these 10 questions. No implementation will begin until you approve.**
