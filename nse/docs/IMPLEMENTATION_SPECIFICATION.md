# Implementation Specification: Phase 1
## NSE GTF Demand & Supply Swing-Trading Research System

**Version:** 2.3, dated 2026-11-02. It incorporates product-owner approvals R1-R6 in addition to D12-D17 and D21-D23.
**Status:** Research implementation exists. External data, source validation and trading-performance validation remain incomplete; see `IMPLEMENTATION_BLOCKERS.md`.

**Sources (both fully audited; see `SOURCE_COVERAGE_REPORT.md`)**

**Repository layout (since 2026-10-26):** everything for this project lives under `nse/`. The two reference sources are in `nse/sources/` (kept byte-for-byte; their SHA-256 hashes are pinned by `tests/test_repo.py`). The four current documents are in `nse/docs/`, the two superseded audit reports in `nse/docs/archive/`, and the Zone Engine in `nse/zone-engine/zone_engine.py` (tests in `tests/`).
- `Trading Rulebook 341a82c22ebf8056a235c9695e1c0d87.md`: 4,029 lines. **Takes precedence (D12).**
- `Demand&Supply Indicator.pine`: 3,271 lines. Used only where the rulebook is silent and Pine does not conflict with it. **Not to be modified.**

**Labels used in this document**

| Label | Meaning |
|---|---|
| **[USER]** | Approved user decision (D1–D17 in `DECISION_LOG.md`) |
| **[RB]** | Explicit rulebook rule, with line cited |
| **[PINE]** | Pine behaviour used because the rulebook is silent and it does not conflict (D12) |
| **[PROPOSED]** | Implementation or reporting proposal. **Not** a trading rule. Needs acceptance |
| **[OPEN]** | Unresolved; blocker ID given |
| **[MANUAL]** | The scanner shows evidence, both rulebook and Pine results where they differ; a human decides |

`RB n` = rulebook line; `PS n` = Pine Script line.

---

## 1. Phase 1 scope (approved decisions)

| ID | Decision | Effect on Phase 1 |
|---|---|---|
| D1 | Universe = **Nifty 100** | Current constituents for live scans. Historical universe → B11 |
| D2 | **Long-only CNC** | Only fresh execution-TF demand zones can become candidates. Supply = resistance and targets. No shorts |
| D3 | **Tested zones never used for entry** | Excluded from displayed zone results and candidates. No Type 2 / tested tier. Pine visuals unchanged |
| D4 | Pre-entry score **/14** | `X/14`; never `/15`. Post-entry Pattern point separate |
| D5 | Zero-base zones **eligible for assessment** | Never rejected for 0 bases |
| D6 | Sector **deferred** | "Not evaluated", never 0. Sector-dependent rules → manual |
| D7 | Buffers = rulebook tiers | Ranges reported; no midpoint, formula or ATR |
| D8 | Explosive leg-out | Objective source criteria; relative size/context → manual |
| D9 | No trailing-stop automation | Weekly DZ distal lines as "Reference only" |
| D10 / D17 | Kite Connect = **pending investigation** | Not approved or verified. No credentials, connection or orders |
| D11 | Full TF hierarchy | Y → HY → Q → M → W → execution TF |
| D12 | **Rulebook-strict precedence** | Rulebook wins. Pine only where silent and non-conflicting. Conflicts or ambiguities → documented + manual review |
| D13 | Zero-base scoring | Pine reference with the `ZB-PINE-REF` trace tag; not rulebook-defined |
| D14 | Daily execution trend | **Weekly and Monthly** trends both evaluated |
| D15 | Coinciding HTF zone | Counts while the HTF zone exists and its **DL is untouched**; separate from entry eligibility |
| D16 | **MIT + WIT** | MIT: M location → W trend → D execution. WIT: W location → D trend → **75/125-min** execution |
| D21 | MIT trend roles | **Weekly = gate**; **Monthly = mandatory context**, never a gate. Weekly opposing Monthly location bias → "extreme caution" (RB 1232) → [MANUAL]; no new rejection |
| D22 | WIT trend | Rulebook's generic matrix with WIT roles (Daily = the only trend gate); no added Weekly/Monthly gates; underspecified cases → [MANUAL] |
| D23 | HTF candles | **Calendar-aligned** Y/HY/Q; documented boundaries; incomplete data never used; "insufficient history" reported; TradingView parity **not yet verified** |

## 2. What must NOT be implemented in Phase 1
1. Order placement or modification, broker execution, or any broker order endpoint.
2. A broker connection, API call or credential use during documentation; credentials committed to the repository (D17).
3. Short-trade candidates (D2).
4. A tested-zone tier, Type 2/3 entries, or tested zones in zone results (D3).
5. A sector score or proxy, including Pine's dashboard label (PS 2949–2983) (D6).
6. A weekly trailing-stop algorithm (D9).
7. Midpoint, minimum, percentage or ATR-derived buffers (D7).
8. A numeric "relative size" multiplier (D8).
9. Any invented tolerance or threshold (e.g. the withdrawn ±1% coinciding rule).
10. `/15` display, or using the post-entry Pattern point before entry (D4).
11. Automation of the 6/7 override, RF3 override, Confirmation Entry, LOTL entry selection or ATA.
12. DIT/HIT trade types.
13. **60- or 120-minute candles as substitutes for 75/125-minute candles** (D16).
14. Presenting the zero-base base score as rulebook-defined (D13).
15. Any change to `Demand&Supply Indicator.pine`. Parity tests may use its existing input options (e.g. max base candles = 5) without editing the code.

## 3. Source hierarchy (D12)
1. **[USER]** decisions override conflicting source passages. Each override is documented.
2. **[RB]** explicit rules govern.
3. **[PINE]** fills gaps only where the rulebook is silent **and** Pine does not conflict with an explicit rule.
4. Conflict or ambiguity → the discrepancy is documented. The scanner computes the rulebook-strict result, shows the Pine result where different, and marks the affected decision **[MANUAL]**.
5. A **[PROPOSED]** item is never presented as an existing rule.

---

## 4. Zone detection

The same algorithm runs on every TF: Y, HY, Q, M, W, D, 125-min and 75-min.

### 4.1 Candle classification
```
body_ratio      = |close − open| / max(high − low, tick)
is_strong_bull  = close > open AND body_ratio > 0.50          # [RB 402]
is_strong_bear  = close < open AND body_ratio > 0.50
is_base         = body_ratio <= 0.50                          # [PINE PS 11, 335] (rulebook silent)
pine_only_break = close > open AND body_ratio <= 0.50 AND close > high[1]   # PR1 → [MANUAL] if it changes an outcome
```
- **[RB 402, 738]** Explosive = body > 50%. Pine's alternative `close > high[1]` path (PS 332–333) conflicts, so it is **not** used. Where it would create a zone, a leg-in or a leg-out count that the rulebook definition does not, the case is shown as [MANUAL].
- **[MANUAL] (D8)** Relative size and context (RB 740–741).
- Detection never depends on display settings or chart TF (PR12, PR17).

### 4.2 Leg-in, base cluster, leg-out
1. **Cluster start [PINE PS 1386–1419].** A base candle starts a cluster if a strong candle (body > 50%) occurred ≤ 3 bars earlier (the leg-in). Otherwise bar[1] is checked as the leg-in. Single-candle leg-in and the 3-bar window are Pine (rulebook silent).
2. **Continuation [PINE PS 487–491].** Base candle not closing outside the cluster wick range, or a transition candle (inside the wicks, body ≤ 0.75).
   - **Max base candles = 5** (Pine option, PS 10), so the rulebook's 4–5-base score exists (RB 786, D12/PR4). 6+ bases form no zone (RB 787 "reject").
   - **Base count:** report `base_count_pine` (base candles only) and `base_count_incl_transitions`. If they fall in different score bands → [MANUAL] (RB 404, 739, 769).
3. **Leg-out.** Strong candle (body > 50%) in either direction.
4. **Achievement [PINE PS 1434–1439], used as the objective minimum for RB 739.** Demand: `close > max(legin_high, cluster_wick_high)`; supply mirrored. Failure → not explosive, so the zone cannot be an execution candidate (RB 730). The pattern is kept as **HTF context only, [MANUAL]** (RB 1639, PR3).
5. **Pattern.** DBR / RBR / RBD / DBD by leg-in and leg-out direction.
6. **Pending [PINE PS 1544–1715, 1799–1930].** Deferred achievement: **1 later bar** on chart TFs (D, 125m, 75m), because Pine's daily block counts down on the same bar; **2 later bars** on W/M and the Q/HY/Y extension (SOURCE_COVERAGE_REPORT P8). A PL touch between the original leg-out and the achievement bar → [MANUAL] (PR10).

### 4.3 PL / DL: [PINE PS 1464–1511] · [RB 337–339, 542–544]
- Body to Wick (the rulebook names the method without defining it; PR16).
- Demand PL = highest body in the cluster.
- Normal DL = lowest cluster wick.
- Exceptional DL: reversal `min(leg-in, cluster, leg-out lows)`; continuous `min(cluster, leg-out lows)`.
- **[RB 544]** PL never changes.
- **[PROPOSED]** Store both DLs (RB 2112–2129 gives the trader the SL-type choice).

### 4.4 Zero-base zones: [PINE PS 1717–1762, 2135–2176, 2549–2590] · D5, D13
- Two consecutive strong candles in opposite directions (**both body > 50%**, D12), not in a cluster.
- DBR: PL = `max(min(open[1],close[1]), min(open,close))`, DL = `min(low[1], low)`.
- `base_count = 0`, `legout_count = 1`, `gap = low > high[1]`, not exceptional.
- W/M versions also require no pending zone.
- Never rejected for 0 bases. Never auto-exceptional. No invented lower-TF bases.
- Scoring per §5.2, tagged `ZB-PINE-REF`.

### 4.5 Leg-out count: D12/PR5
- Starts at 1.
- Each subsequent strong candle (body > 50%) in the zone's direction within bars 1–3 after creation adds 1 (3-bar window: [PINE PS 1764–1775]).
- Counted **per zone** (RB 728). Pine counts only for the most recent zone.
- Interrupted or non-consecutive sequences, or a count that differs from Pine's → [MANUAL].

### 4.6 Zone state
- **Test [RB 264, 683–697].** Any wick or body touch of the PL after the leg-out; gap-through counts.
  - Updated on **every completed candle of the finest TF processed** (daily; 75/125-min where WIT data exist), including for HTF zones (RB 292, 1508; PR8).
- **Breach [PINE PS 2613; RB 1627, 1741].** Close beyond the DL invalidates the zone permanently. HTF zones are breached by their own TF's close (rulebook silent on which close).
- **DL touch** (wick reaches the DL without a close beyond it) is recorded separately for D15.
- **Approved R4:** a wick or temporary move beyond the DL is not itself invalidation and is not a bounce. Preserve D24: the zone's completed own-timeframe close controls permanent invalidation; an interim lower-timeframe close beyond an HTF DL remains pending until that HTF period resolves.
- If an active trade's SL is touched, record a `STOP_LOSS_HIT` trade event separately from any `ZONE_INVALIDATED` zone event. Either, both, or neither may occur on the same completed candle, according to the selected stop and the DL close.
- **[PROPOSED]** Per-zone event log: created, leg-out increment, test, DL touch, invalidated. This allows point-in-time reconstruction.

### 4.7 Timeframes
| TF | Role | Parity basis |
|---|---|---|
| Y, HY, Q | TDA steps 1–3, conflict (Q/HY) | No Pine reference for zones (Python extension, D11). Calendar candles per D23 (§9.3); TradingView verification open (B8) |
| M | MIT location; conflict; WIT monthly-structure check; D14 trend | Pine W/M engine (PS 2191–2603), adjusted per D12 |
| W | MIT trend and target; WIT location; D14 trend | Pine engine (PS 1777–2189), adjusted per D12 |
| D | MIT execution; WIT trend and target | Pine daily engine, adjusted per D12 |
| 125-min, 75-min | **WIT execution** (D16) | Pine run on TradingView 75/125-min charts (B10) |

For any parity test, D12 differences (PR1, PR4, PR5, PR8) are asserted rather than ignored.

---

## 5. Scoring

### 5.1 Reconciliation

| Component | Rulebook definition | Pine implementation | Phase 1 decision | Source reference |
|---|---|---|---|---|
| **Freshness** (core 3) | 3 / 1.5 / 0. Any touch; gap-through counts | `test_count` from `low ≤ PL` | Faithful tracking, updated per finest completed candle. **Only `test_count = 0` zones are output (D3)** | RB 663–715 · PS 595, 2648–2654 |
| **Strength** (core 2) | 2+ explosive, or 1 + gap = 2; 1 = 1; weak = 0 | `legout_count`, `has_gap` | Pending zones: a reading that also counts the failed first leg-out (body > 50%); a score difference → [MANUAL] `PENDING_LEGOUT_COUNT_AMBIGUOUS` (PR18). Body > 50% candles only, counted per zone (D12). Pine difference → [MANUAL]. Gap meaningfulness [MANUAL]. Relative size/context [MANUAL] (D8) | RB 716–772 · PS 596–600, 1764–1775 |
| **Base count** (core 2) | 1–3 = 2; 4–5 = 1; 6+ = 0. 0 undefined | `base_count` (transitions excluded); default max 3 | Max 5; both counts reported; band disagreement → [MANUAL]. 0 bases → Pine 2.0 tagged `ZB-PINE-REF` (D13) | RB 773–821 · PS 10, 601 |
| **Core gate** | 7/7 for Type 1 | `X/7` display | **7/7 required** | RB 661, 829 |
| **Gap treatment** | Strength gap (type unstated); CF4 any valid application; ignore negligible gaps | Window gap, any size | Gap size shown; meaningfulness [MANUAL]; CF4 provisional; double count unresolved (N6) | RB 728, 934–964 · PS 1523–1525, 1739 |
| **Sector** (+2) | All three aligned +2; two +1 | Display-only proxy | **Not evaluated (D6)** | RB 484–499, 851–895 |
| **HTF EMA 20** (+2) | 2+ in zone +2; 1 → +1; trending TFs | Levels only | Provisional count; trending condition [MANUAL] | RB 500–516, 896–918 |
| **Crossover** (+1) | EMA20 × EMA50 inside zone, trending | "Minor" cross labels | Provisional; [MANUAL] | RB 565–573, 919–933 |
| **RSI / Stochastic** (+1) | Stoch ≈ ≤ 20 or RSI divergence at zone | RSI display only | Not evaluated pre-entry; [MANUAL] | RB 574–583, 965–987 |
| **Pre-entry max** | 7 + 7 = **14** (RB 1001, 653) | - | `X/14` (D4) | - |
| **Pattern** (post-entry +1) | RB 1068 only | - | Journal field only (D4) | RB 1068 |
| **Time decay** | None | None | None | PS 594–602 |

### 5.2 Zero-base score (Pine reference, D13)
| State | Freshness | Strength | Base | Core |
|---|---|---|---|---|
| Created, no gap | 3.0 | 1.0 | 2.0 `ZB-PINE-REF` | 6.0 |
| Created, gap (`low > high[1]`) | 3.0 | 2.0 (gap meaningfulness [MANUAL]) | 2.0 `ZB-PINE-REF` | 7.0 |
| No gap + 1 further strong candle (body > 50%) in bars 1–3 | 3.0 | 2.0 | 2.0 `ZB-PINE-REF` | 7.0 |
| PL touched | - | - | - | Excluded from output (D3) |
| Close beyond DL | - | - | - | Deleted |

There is no time decay. The rulebook does not define the base component for 0 bases (RB 785–787). Every result carries the tag so it can be revisited.

### 5.3 Score display [PROPOSED]
```
Core: 7/7 (Freshness 3 · Strength 2 · Base 2)            [ZB-PINE-REF if zero-base]
Pre-entry: 9/14 evaluated; provisional: EMA20 +2 (manual), gap +0
           not evaluated: Sector (max +2), RSI/Stoch (max +1)
           upper bound: 12/14
Post-entry Pattern: journal only
```
The Part E category (RB 1027–1033) is shown for the evaluated value, and also for the upper bound if it differs.

---

## 6. Entry, stop-loss, target, R:R, position size

### 6.1 Rules [RB]
- Entry = PL + buffer (limit order) (RB 298, 2010).
- SL = DL − buffer; locked after trigger; exit on touch (RB 321, 2139–2141).
- SL types: Normal / Exceptional / Shri Krishna (RB 2116–2128).
- R:R ≥ 2 (RB 82). Targets per RB 2268–2328.
- `Qty = floor(RPT ÷ (Entry − SL))` (RB 42, 2162, 2203–2204). Capital and RPT are user inputs.

### 6.2 Buffer tiers (transcribed exactly; no value chosen): D7
| Stock price range (as printed) | Entry buffer (RB 2016–2020) | SL buffer (RB 2097–2102) |
|---|---|---|
| Below ₹100 | ₹0.25 − ₹0.50 | ₹0.50 − ₹1 |
| ₹100 − ₹500 | ₹0.50 − ₹2 | ₹1 − ₹3 |
| ₹500 − ₹2,000 | ₹2 − ₹5 | ₹3 − ₹8 |
| Above ₹2,000 | ₹5 − ₹10 | ₹8 − ₹15 |

Related source statements:
- "Guidelines, not rigid rules" (RB 2022).
- SL buffer +50–100% in volatile, news-driven markets (RB 2108–2110).
- Differing summary ranges: RB 305, 332, 351 ("scale to … ATR", no formula), 2010.

**Unresolved (B9):** overlapping tier edges; which price selects the tier; qualitative volatility condition. This blocks deterministic backtests only.

### 6.3 Range reporting [PROPOSED]
- **Entry range:** `[PL + min, PL + max]`, over every tier that could apply.
- **SL ranges:** for the normal and exceptional DL. The volatility adjustment is listed as a manual consideration and not applied numerically.
- **R:R range and quantity range.**
- **2:1 status:**
  - `PASS (all buffer choices)`;
  - `FAIL (all)` → reject (RF8);
  - `DEPENDS ON BUFFER` → [MANUAL].
- **Shri Krishna SL:** location-zone DL shown as a reference [MANUAL].

### 6.4 Targets [RB] + [MANUAL]
- **MIT:** PL of the nearest **fresh** Weekly supply above entry (RB 557). Monthly supply PL as reference (RB 1386).
- **WIT:** PL of the nearest **fresh** Daily supply above entry (ITF per RB 551–558).
- No target buffer; it appears only in an example (RB 2287).
- "Quality" of the opposing zone → [MANUAL].
- No fresh supply above / ATH: 2:1 mathematical target shown as a reference only; status [MANUAL] (D9). Weekly DZ distal lines labelled **"Reference only: not an automatically updated stop."**

---

## 7. TDA and MTFA

### 7.1 TDA (D11)
For Y, HY, Q, M, W and the execution TF: report the nearest fresh demand zone below and fresh supply zone above, or "insufficient history" (D23), always with the count of completed candles. Also report the TDA-statement fields (RB 1449–1471).

### 7.2 Location / Curve [RB 1195–1218, 1578–1628]
- **MIT:** Monthly curve. **WIT:** Weekly curve (RB 1394).
- Bottom and top = PLs of the nearest **fresh** DZ below and SZ above.
- Levels 0 / 33.33 / 66.66 / 100%. Positions VLOC / LOC / EQB / HOC / VHOC.
- **Approved R1:** classify curve position at CMP only. Execution PL and its buffer do not influence G3/G4 location. If CMP is HOC, apply HOC rules even when execution PL is LOC.
- Redraw when a boundary zone is tested or broken.
- ATH → no curve; follow trend; demand only (RB 1609).
- Longs: HOC → reject unless "extreme circumstances" with sector support (RB 1600) → [MANUAL] (sector not evaluated). VHOC → reject (RB 1601).

### 7.3 Trend (D14, D21; WIT per D16, D22)
| Trade type | Trend TFs evaluated | Gating role |
|---|---|---|
| MIT (Daily execution) | **Weekly and Monthly** (D14) | **Weekly = the trend gate** (ITF in the matrix; RB 1232, 1378, 1667). **Monthly = mandatory context** (D21): always computed and reported; disagreement listed as evidence against; never rejects or flags on its own. **Weekly trend opposing Monthly location bias** (buy bias at VLOC/LOC) → `MANUAL REVIEW: extreme caution (RB 1232)`. A matrix rejection (e.g. LOC + Down) still applies |
| WIT (75/125 execution) | **Daily** (RB 1395) | **Daily = the only trend gate** (D22; RB 1395, 1668). No Weekly or Monthly trend gate. Those trends may be shown as context only |

- **Method:** SMA-50 clock on completed candles (RB 1672–1711, 1748).
- **Numeric reference [PINE]:** `pct = (SMA50 − SMA50[5]) / SMA50 × 100`; thresholds ±0.1 / 0.4 / 1.0 / 2.0 (PS 252–291).
- **Mapping to rulebook readings** (D14 table):
  - 12 = Rulebook label **Extreme Uptrend**, mapped to `STRONG_UP` for eligibility and matrix evaluation (approved R2). Preserve both the original clock position and label in diagnostics and reports.
  - 1 and 2 = up, with strong vs moderate ambiguous;
  - 2–3 and 3–4 = ambiguous with sideways ("any doubt → sideways", RB 1708);
  - 3 = sideways;
  - 4–6 = down.
- Ambiguity → [MANUAL] **only where it changes the matrix outcome**.
- Fewer than 55 completed candles of that TF (SMA50 now and 5 candles earlier, D23) → "insufficient history". For a **gating** trend (MIT Weekly, WIT Daily) → [MANUAL]. For **context** (MIT Monthly; Q/HY/Y) → reported only.
- [MANUAL] also where it is unclear whether a reading "opposes" the location bias, e.g. Weekly Sideways or ambiguous bands vs a buy bias (D21).
- Pine's dead-band method (PS 304–316): secondary context only.

### 7.4 HTF conflict (D12, PR11)
| Finding | Status |
|---|---|
| Daily (MIT) or 75/125 (WIT) DZ PL **inside** an opposing Monthly, Quarterly or Half-Yearly zone, or that zone's PL ≤ 5% above | **Conflict** → reject (RF2, RB 601, 1302–1304), unless the opposing zone is broken (RB 1313) |
| Opposing M/Q/HY PL > 5% and ≤ 10% above | [MANUAL] |
| Opposing **Weekly** or **Yearly** zone within 10%; any **tested** (DL-intact) opposing HTF zone within 10% | [MANUAL] evidence (not in the rulebook list, or ambiguous) |
| WIT only: weekly location DZ inside a Monthly SZ | Reject ("toxic", RB 1402) |
| WIT only: weekly location DZ near a Monthly SZ | [MANUAL] |

Distances are reported from both the PL and the entry range (the rulebook measures from the entry; Pine from the PL).

### 7.5 Coinciding (D15)
- **Relevant HTF location zone:** Monthly DZ (MIT) or Weekly DZ (WIT). It qualifies if it exists and **its DL has never been touched** since creation. A PL touch does not disqualify it.
- A tested HTF zone used here appears only as cited evidence. It never appears in zone results (D3).
- **Approved R3:** Coinciding means that the inclusive price ranges of the execution demand and qualifying HTF demand overlap. Use both actual zone boundaries, `[min(PL, DL), max(PL, DL)]`; an exact shared boundary counts as overlap.
- Example: Daily demand ₹100-₹110 and Weekly demand ₹105-₹115 overlap and are Coinciding.

| Geometry | Classification |
|---|---|
| Execution demand range overlaps a qualifying HTF demand range | **Coinciding** (approved R3; D15 DL condition still applies) |
| Execution demand range is wholly above the HTF demand range | **Aggressive**, separate from Coinciding; G6 stays [MANUAL] until the distinct Rulebook conditions can be verified (RB 1843-1847, 1854-1855) |
| Execution demand range is wholly below the HTF DL | **Invalid** (RB 1856) |
| Relevant zone freshness or DL status is unknown | [MANUAL]; unknown is not known absence |
| No qualifying HTF location demand zone is known | G6 **PASS as Standard** (approved R6); G3 independently decides whether a curve exists |
| Coinciding zone differs from the fresh curve boundary and the outcome depends on it | [MANUAL] |

### 7.6 Alignment matrix, long rows (RB 1883–1904)

**Source finding (D22).** The rulebook has **one generic matrix** written in Location (HTF) / Trend (ITF) / Zone Quality (LTF) terms. It states that only the timeframes in those roles change by trade type (RB 1370). Roles from RB 1573–1574, 1667–1668, 1767–1768:
- **MIT:** Monthly location / Weekly trend / Daily execution.
- **WIT:** Weekly location / Daily trend / 75–125-min execution.

There is **no separate WIT matrix**. Applying this table to WIT uses the rulebook's role mapping, not MIT settings. WIT cases that rest on rows phrased around Monthly/Quarterly zones or Daily charts (the Confirmation Entry row, RB 1892, 2593–2598) → [MANUAL].

| Location | ITF trend | Rulebook | Phase 1 |
|---|---|---|---|
| VLOC | Strong Up | Execute | Pass |
| VLOC | Sideways | Execute if coinciding | Pass if Coinciding; else [MANUAL] |
| VLOC | Down | Confirmation Entry only | [MANUAL] (deferred strategy) |
| LOC | Strong / Moderate Up | Execute | Pass |
| LOC | Sideways | 7/7 + **sector support** | [MANUAL]: sector not evaluated |
| LOC | Down | Reject | Reject |
| EQB | Strong Up | Buy | Pass |
| EQB | Down | Sell only; no long | Reject long (approved R5; RB 1599) |
| EQB | Sideways | Do nothing | Reject |
| HOC | Up | Reject demand long | Reject (approved R5; RB 1901) |
| HOC | Sideways | Sector-supported exception only | [MANUAL] pending sector support (approved R5; D6) |
| HOC | Down | Apply RF3; no invented exception | RF3 outcome (approved R5) |
| VHOC | any | No buy | Reject |
| Not listed, or trend reading ambiguous where it matters | - | - | [MANUAL] |

### 7.7 WIT-specific rules (D16)
| Rule | Source | Treatment |
|---|---|---|
| Execution TF 75-min **and** 125-min; 125 preferred | RB 1396, 1404, 1768 | Scan both. Simultaneous candidates in the same area → reported separately, preference noted, [MANUAL] |
| Weekly location must not conflict with Monthly structure | RB 1402 | §7.4 |
| Execution zone recency | RB 1403, 1788–1801 | Formed ≤ 8 candles ago → pass. 9–10 → [MANUAL]. >10 → [MANUAL]; >20 must also re-verify HTF conditions |
| 7/7 core | RB 1396 | Gate |
| Target = nearest fresh Daily supply | RB 551–558 | §6.4 |
| "After 50+ successful MIT trades" | RB 180, 3556, 3615 | Informational note (trader progression); not a gate |
| Session-aligned candles; no 60/120 substitution | RB 184–193 | §9.3 |

---

## 8. Eligibility and qualification pipeline (long-only; MIT and WIT)

| Gate | Check | Outcome on failure | Source |
|---|---|---|---|
| G0 | Completed candles only; history adequate; intraday sessions complete (WIT) | `DATA INSUFFICIENT` | §11 |
| G1 | Execution-TF **demand** zone, not breached, **`test_count = 0`**; WIT recency | Not listed (D3) / recency [MANUAL] | D2, D3, D16 |
| G2 | Core **7/7** under D12 definitions | Reject. D12 discrepancies → [MANUAL] | §5 |
| G3 | CMP-only location (curve) | Reject / [MANUAL] | §7.2, §7.6; approved R1 |
| G4 | Trend: MIT Weekly gate + Monthly context + RB 1232 caution (D21); WIT Daily gate only (D22) | Reject (matrix) / [MANUAL] | §7.3 |
| G5 | HTF conflict | Reject / [MANUAL] | §7.4 |
| G6 | Actual range overlap / separate Aggressive / known absence | Invalid below HTF DL → reject; Aggressive or unknown → [MANUAL]; known absence → PASS as Standard | §7.5; approved R3/R6 |
| G7 | Entry / SL / target / R:R (RF8) | `FAIL all` → reject; `DEPENDS` → [MANUAL] | §6 |
| G8 | Red flags and Essential Checks | Per item | RB 594–631 |

**Statuses.** The scanner never auto-approves a trade.
- `REJECTED`: an automated gate failed, with source reference.
- `MANUAL REVIEW`: at least one gate is inconclusive. Each [MANUAL] item is listed with both rulebook and Pine results where they differ.
- `ACTIONABLE CANDIDATE: MANUAL CHECKS PENDING`: every automated gate passed. Always carries the checklist:
  - explosive relative size/context (D8);
  - gap meaningfulness;
  - authenticity;
  - garbage chart;
  - LOTL;
  - "came from";
  - target quality;
  - buffer selection;
  - `ZB-PINE-REF` note if zero-base;
  - trader-state items (RF5, RF9, RF10, Essential Check 10).

**Sector** is never a silent pass. Any rule needing it → `MANUAL REVIEW: sector not evaluated` (D6).

---

## 9. Proposed architecture [PROPOSED]

**Update 2026-10-29:** built as `nse/research/` (section 7-8 gates, scanner, reports) and `nse/validation/`; see `RESEARCH_PIPELINE.md`. 9.1 has a loader but no constituent data (B11); 9.10 is not built.

Cross-cutting rules:
- Completed candles only.
- Point-in-time reconstructable state.
- Read-only; no broker order endpoints in the codebase.
- Secrets outside the repository; none requested now (D17).
- No Pine-parity claim until §10 passes.

| # | Component | Responsibility | Key rules / dependencies |
|---|---|---|---|
| 9.1 | Universe manager (Nifty 100) | Official constituent file; versioned with effective dates; refresh on NSE Indices announcements; symbol ↔ ISIN ↔ vendor mapping; corporate events | D1; B11 for history |
| 9.2 | Market-data acquisition and validation | Vendor-neutral adapter (Kite pending, D17); daily and **intraday** raw data; provenance; checks vs NSE calendar; OHLC sanity; gaps in intraday sessions | B6, B7 |
| 9.3 | Session-aware candle construction | Daily (09:15–15:30 IST, 375 min, RB 186); weekly; monthly; **Q/HY/Y calendar-aligned per D23** (Q: Jan–Mar, Apr–Jun, Jul–Sep, Oct–Dec; HY: Jan–Jun, Jul–Dec; Y: Jan–Dec), from adjusted daily candles; incomplete periods never used; listing period tagged `partial_listing_period`; TradingView parity to verify (B8/B10); **75-min** (09:15, 10:30, 11:45, 13:00, 14:15 → 15:30); **125-min** (09:15, 11:20, 13:25 → 15:30); built from finer session-aligned data that divides both periods (e.g. 1- or 5-min) | No 60/120 substitution. Incomplete or special sessions flagged and excluded (RB 190–193). Candle usable only after it closes |
| 9.4 | Zone detection | §4 on all TFs; event log; both DLs; DL-touch tracking | D12, D13, D23 |
| 9.5 | HTF trend and conflict | D14 + D21 (MIT), D16 + D22 (WIT) trend; conflict §7.4. HTF zone freshness comes from the orchestrator (`nse/mtf-freshness/`, D24-D28), not from the engine's own HTF view | D21, D22, D24-D28 |
| 9.6 | Fresh-zone eligibility filter | Zone results = `test_count = 0`, non-breached; supply labelled *context: not a candidate*; tested zones internal only (D15 evidence use excepted) | D2, D3, D15 |
| 9.7 | Qualification and scoring | §5, §7, §8 | D4–D8, D12–D16 |
| 9.8 | Entry / SL / target / R:R / size | §6 ranges | D7, D9, B9 |
| 9.9 | Reporting | §12 schema; evidence for and against with RB/PS references; alert-note fields (/14) | D4 |
| 9.10 | Paper-trade journal and validation | Journal per RB 3713–3741 + post-entry Pattern field; monthly metrics (RB 3762–3775); 10-trade cap (RB 2392); validation only after B9, B11, B12, B15 | - |

---

## 10. Pine parity testing

### 10.1 Principle
Parity is tested against the unmodified indicator, configured through its existing inputs (max base candles = 5, PR4). Where D12 makes Phase 1 differ intentionally (PR1, PR4 counting, PR5, PR8), the test asserts the documented difference. No parity claim is made until the tests pass.

### 10.2 Test cases (the user supplies TradingView references, B10; daily, weekly, monthly, 75-min and 125-min charts)
1. DBR with 1–3 bases, immediate achievement.
2. RBR with exceptional DL.
3. Pending achieved on the next bar (daily) or within 2 bars (weekly); pending expired; touch inside the pending window.
4. Cluster with a transition candle (both base counts).
5. 4- and 5-base zones (max = 5); 6th base → no zone.
6. Zero-base: no gap (6.0), gap (7.0), increment to 7.0, Pine latest-zone freeze vs per-zone count.
7. Candle with body exactly 50%; small-body close-break candle (PR1 manual flag).
8. PL wick touch; gap-through; near miss; DL wick touch (D15) vs DL close (deletion).
9. Weekly/monthly zone creation timing; HTF test timing (PR8 difference).
10. Conflict: inside-case, within 5%, 5–10% band, Weekly-only, tested opposing zone.
11. 75/125 session alignment: first candle at 09:15; last ends 15:30; short session excluded.
12. Detection independent of display settings.
13. **D23 HTF candles:** quarter, half-year and year boundaries; OHLC values for agreed symbols; holiday weeks and months; listing-period candle; a split/bonus stock; SMA/EMA values on M/Q/HY/Y. Recorded comparisons are required before D23 counts as validated.

Synthetic-candle unit tests can be written before any market data exists.

---

## 11. Data requirements

| Data | Purpose | Candidate source | Guaranteed? | Blocker |
|---|---|---|---|---|
| Nifty 100 current constituents | Live universe | NSE Indices official file | Not yet obtained | - |
| Nifty 100 point-in-time membership | Validation | NSE Indices announcements | **No** | B11 |
| Daily OHLCV, long history | D/W/M/Q/HY/Y zones; trends | Kite (pending); exchange EOD (to verify) | **No** | B6 (Kite), B18 (EOD formats), B8 |
| **Intraday OHLCV, session-aligned, granularity dividing 75 and 125 min** | WIT execution zones | Kite (pending) | **No** | B6 |
| Long intraday history | WIT validation | To verify | **No** | B15 |
| Corporate actions / adjusted prices | Prevent false zones | Vendor-adjusted or exchange feed | **No** | B7 |
| NSE trading calendar, special sessions | Candle completeness | Exchange circulars | Obtained for 2021-2025 (`nse/data/calendar/`); not externally validated | B17 |
| Delisted / merged history | Validation | To identify | **No** | B11 |
| Cost schedules, price bands | Validation fills | Official schedules | **No** | B12 |

**Kite verification checklist (D17; no calls made, no credentials requested):**
- historical coverage per interval;
- supported intervals;
- access requirements (subscription, authentication);
- adjustment for splits/bonuses;
- rate limits;
- storage licence;
- whether exact 75/125-min candles can be built reliably (granularity, 09:15 alignment, session completeness).

---

## 12. Output schema [PROPOSED]

**Fresh zone results** (tested zones never appear):
- TF, side, pattern, PL, DL (normal and exceptional);
- `base_count_pine` and `base_count_incl_transitions`, zero-base flag (`ZB-PINE-REF`), `legout_count` (rulebook and Pine);
- gap and gap size, strong-closing flag, creation date, DL-touched flag, core `X/7`;
- supply rows labelled *context: not a candidate*.

**Candidate report:**
- **Identification:** symbol; as-of candle; trade type (**MIT** or **WIT-75 / WIT-125**).
- **Zone:** all fresh-zone fields above.
- **Score:** core breakdown; `X/14` evaluated, provisional, not-evaluated and upper bound; Part E category.
- **Context:** TDA table; location (curve, zones used); trend (MIT: Weekly and Monthly; WIT: Daily) with pct, clock and mapped reading; HTF conflict findings; coinciding classification with the HTF zone cited (DL-intact status).
- **WIT only:** recency (candles since formation).
- **Trade levels:** entry range; SL ranges; target and references; R:R range; quantity range; 2:1 status.
- **Evidence:** evidence **for** and **against** with RB/PS references.
- **Decision support:** each [MANUAL] item with rulebook vs Pine values; status; checklist; alert-note fields.

---

## 13. Readiness and decisions still required

**Not ready for implementation.** The full list is in `IMPLEMENTATION_BLOCKERS.md` Part 4.

| Category | Items |
|---|---|
| User input | B9, B12 (only for historical validation). B13 and B14 are resolved (D21, D22); the B8 approach is decided (D23) |
| Source ambiguities → manual review per case | PR1, PR3–PR6, PR10, PR11 items; clock bands; RB 1232 "extreme caution" and what counts as "opposing" (D21); WIT cases on MIT-phrased matrix rows (D22); listing-period candles (D23); coinciding tolerance; WIT recency band; 75/125 overlap; sector-dependent rules; explosive relative size; matrix gaps; target quality |
| External technical checks | B6 Kite (incl. 75/125 construction), **B18 NSE CM EOD file formats (legacy and UDiFF)**, B7 corporate actions, **B8 TradingView verification of calendar boundaries and HTF candle values**, B10 TradingView parity references (incl. 75/125-min alignment), **B17 validated NSE calendar** (official circulars), constituent file |
| Historical data / backtesting | B11 point-in-time universe, B15 intraday depth, B9 buffers, B12 fill/cost assumptions |

**Implementation status (2026-10-28):** Phase 1 in progress; external validation pending.
- **Zone Engine** (`nse/zone-engine/zone_engine.py`): single-timeframe detection, scoring, freshness, invalidation and zone-level eligibility (D12, D13, D35).
- **HTF freshness orchestrator** (`nse/mtf-freshness/mtf_freshness.py`): implements B16 under D24-D28, D33-D34 and D36-D39.
  - It applies completed finer candles to W/M/Q/HY/Y and D zones (D from an intraday base, or from a daily base under D38).
  - It never adds eligibility, only removes it (`eligible_after_overlay`). Candidates must come from it, never from the engine's `eligible` alone (audit M4).
- **NSE calendar** (`nse/calendar/nse_calendar.py`, `nse/data/calendar/`): official circulars for 2021-2025 transcribed and hash-verified; Q1 2022 reconciles with the official EOD files. TradingView validation and a systematic normal-hours review are open (B17).
- **Evidence:** synthetic tests, plus one real-data pipeline check (INFY, Q1 2022, official bhavcopies against a Yahoo Finance reference; not independent validation). Current test counts and mutation results are in `IMPLEMENTATION_BLOCKERS.md` Part 5 and `PHASE1_CORRECTNESS_AUDIT.md`.
- **Not validated:** neither component is validated against TradingView (B8, B10) or on corporate-action-adjusted data (B7); the calendar is not externally validated (B17).
- **Built 2026-10-29, not externally validated:** trend, location, conflict, coinciding, trade levels and R:R, G0-G8, the scanner and its reports (`nse/research/`, `RESEARCH_PIPELINE.md`; interpretations in D41, `PROPOSED`). WIT output is BLOCKED (audit M4b). Not built: the /14 score extras (EMA20, crossover, RSI/Stochastic, gap application), corporate actions (B7) and backtesting (B9, B12).
