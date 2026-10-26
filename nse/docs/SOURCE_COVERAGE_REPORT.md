# Source Coverage Report

**Project:** NSE GTF Demand & Supply Swing-Trading Research System
**Version:** 2.2, dated 2026-10-26. v2.2 adds D21–D23 to §9 and records finding RC14 (no WIT-specific matrix). v2.1 recorded how D12–D17 resolve the discrepancies (§6, §9). The source audit itself is unchanged. v2.0 replaced v1, whose coverage claims were incomplete (§8).
**Companion documents:** `IMPLEMENTATION_SPECIFICATION.md`, `DECISION_LOG.md`, `IMPLEMENTATION_BLOCKERS.md`

**Repository layout (since 2026-10-26):** everything for this project lives under `nse/`. The two reference sources are in `nse/sources/` (kept byte-for-byte; their SHA-256 hashes are pinned by `tests/test_repo.py`). The four current documents are in `nse/docs/`, the two superseded audit reports in `nse/docs/archive/`, and the Zone Engine in `nse/zone-engine/zone_engine.py` (tests in `tests/`).

**Notation**
- **Observed:** what the source text or code literally says or does.
- **Interpretation:** my reading of an observed fact. Each one is labelled where it appears.
- `RB n` is a line in `Trading Rulebook 341a82c22ebf8056a235c9695e1c0d87.md`. `PS n` is a line in `Demand&Supply Indicator.pine`.
- Rule classes: **E** explicit · **D** discretionary · **A** ambiguous · **C** contradictory (with another passage).
- Pine column: **Yes** implemented · **Partial** · **Differs** (implemented differently) · **Display** (shown on chart, not used in any logic) · **No**.
- Phase 1 column: **Implement** · **Report** (computed and shown, not a gate) · **Manual** (manual review is required and the scanner shows the evidence) · **Defer** · **N/A** (trader conduct or psychology; not automatable).

---

## 1. What was inspected

| File | Lines | Coverage in this audit | Status |
|---|---|---|---|
| `Trading Rulebook 341a82c22ebf8056a235c9695e1c0d87.md` | 4,029 (`wc -l` says 4,028 because the file has no trailing newline) | **Read in full, 1–4029.** All 8 sections, every chapter, table, quick reference and appendix-style summary. | ✅ Fully audited |
| `Demand&Supply Indicator.pine` | 3,271 (`wc -l` says 3,270, same reason) | **Read in full, 1–3271.** Inputs, trend engine, all zone engines (D/W/M), scoring, conflict, invalidation, dashboards, plots. | ✅ Fully audited |
| `DECISION_LOG.md` (v1), `SOURCE_COVERAGE_REPORT.md` (v1), `IMPLEMENTATION_SPECIFICATION.md` (v1) | - | Read in full and rewritten (v2) | Corrected |
| `archive/AUDIT_VALIDATION_REPORT.md`, `archive/STRATEGY_SPECIFICATION_AUDIT.md` | - | Searched for the disputed claims (§8.4). They are not used as evidence anywhere in v2. | **Superseded; left unmodified** |
| `README.md`, `trader-*/` | - | Not used. These cover the US ORB day-trading skills and are unrelated to this specification. | Not relevant |

**Integrity check.** I recorded SHA-256 hashes before editing any document and rechecked them afterwards (§10). The Pine Script, the Rulebook and all application files are unchanged.

**External sources.** None were consulted. Kite Connect documentation, NSE Indices constituent files and TradingView behaviour notes were not accessed. No network calls, credentials or broker connections were used. Every statement here about those systems is marked *to be verified*.

---

## 2. Trading Rulebook: coverage table

### Section 1: Pre-Trade Rulebook (RB 3–642)

| Section / heading | Lines | Relevant rule | Class | Pine | Phase 1 |
|---|---|---|---|---|---|
| How to use | 3–8 | Any Critical failure → reject. 2+ High failures → "seriously reconsider". | E / D | No | Implement Critical gates. Report High-priority failures; "reconsider" → Manual |
| Foundational Laws | 9–32 | Principles; the 50%-accuracy-at-2:1 maths | E (context) | No | N/A |
| C1 Position sizing | 37–76 | `Qty = RPT ÷ (Entry − SL)`. RPT 0.5–1% (learning), 1–1.5%, 1.5–2% | E (formula); D (RPT within range) | No | Implement the formula. Capital and RPT are user inputs |
| C2 Minimum 2:1 R:R | 77–114 | R:R ≥ 2 or reject. Target priority: structural → 2:1 → weekly trailing. ATH → trailing | E; A (target "quality") | No | Implement where entry/SL/target are determinable (see B9). ATH → Manual (D9) |
| C3 Top-Down Approach | 115–156 | Mandatory Y→HY→Q→M→W→Execution. TDA statement | E | Partial (W/M zones; Q/HY/Y trend + EMA only) | Implement all six steps (D11). Q/HY/Y zones are a Python extension |
| C4 MTFA | 157–259 | Location + Trend + Execution aligned. Trade-type TF table. 375-min session (125/75 rationale). Curve table. Clock table. ATA table. IF→THEN rules | E / A | Partial (clock on chart TF; no curve) | Implement curve and SMA clock (D14). ATA Deferred. 75/125 → WIT execution (D16) |
| C5 Zone 100% fresh | 260–293 | PL never touched by body or wick after leg-out closed. Binary. Line 291: "tested once … proceed only with exceptional HTF backing" | E; **C** (272 vs 291) | Yes (`test_count`; HTF timing differs, §6 PR8) | Implement status. **D3:** tested zones excluded from display and candidates |
| C6 Entry outside zone | 294–316 | Entry = PL + small buffer ("₹0.50 to ₹2-5", 305). Limit orders | E rule; D buffer | No | Report the buffer range only. Deterministic value unresolved (B9) |
| C7 SL beyond DL | 317–355 | SL = DL − meaningful buffer ("₹1-5+", 332). Exceptional DL (337–339). Shri Krishna SL (343). "Scale buffer to … ATR" with no formula (351). SL locked (352) | E rule; D / **C** buffer | Exceptional DL: Yes. Buffer: No | Report ranges. No ATR formula. SK SL → Manual reference |
| High priority gate | 356–359 | Fail 2+ → reconsider | D | No | Report; Manual |
| H1 Base candles | 360–384 | 1–3 = 2, 4–5 = 1, 6+ = 0 (reject). Drop to a lower TF if messy | E; **0 bases undefined** | Differs (max 3 by default; transitions not counted) | Max 5; both base counts reported (D12). Zero-base → D13. Refinement → Manual |
| H2 Explosive leg-out | 385–407 | 2+ explosive or 1 + gap = 2; 1 = 1; weak = 0. Explosive = body > 50% **and** achievement **and** not within surrounding range | E / A | Partial | Pine mechanics. Relative size/context → Manual (D8) |
| H3 ITF trend | 408–427 | Aligned or at least sideways. SMA clock or ATA | E / A | Partial | MIT: Weekly + Monthly clock (D14); WIT: Daily (D16). ATA Deferred |
| H4 Curve position | 428–446 | Buy/sell matrix. Curve **between FRESH zones only** (445) | E | No | Implement (long side only) |
| H5 Closing concept | 447–462 | Leg-out should ideally close beyond the leg-in extreme. HTF achievement extension | E (preference) | Differs (Pine makes it mandatory for zone creation) | Report flag. Pine achievement used as objective minimum (D12, PR3) |
| H6 Authenticity | 463–479 | Reaction zones are weaker; strong closing overrides | D | No | Manual |
| M1 Sector & market | 484–499 | Stock + Sector + Nifty at aligned zones: +2; any two: +1. Mandatory for DIT/HIT | E score; D "aligned zones" | Display (different method, §4 P22) | **Not evaluated (D6)** |
| M2 HTF EMA 20 | 500–516 | 2+ HTF EMA20 inside zone: +2; 1: +1. Trending TFs only | E / A | Display (levels only) | Report as provisional; trending condition → Manual |
| M3 Coinciding vs aggressive | 517–532 | Coinciding = inside or touching HTF PL. Aggressive needs 7/7 + achievement. Prefer coinciding | E / A (no tolerance) | No | "Inside" → Implement. "Touching" and achievement → Manual (N4) |
| M4 Exceptional marking | 533–546 | Reversal: leg-in/base/leg-out extreme. Continuous: base/leg-out. PL never changes | E | Yes | Implement (Pine) |
| M5 Structural target | 547–560 | Target = PL of nearest FRESH opposing ITF zone. ≥2:1 or use the 2:1 minimum or reject | E / A ("quality", 2278) | No | Implement nearest fresh Weekly SZ PL. "Quality" → Manual |
| L1 Golden/Death cross | 565–573 | EMA20 × EMA50 on execution TF, inside an existing zone, trending market: +1 | A | Display (Pine's "minor" cross) | Provisional + Manual |
| L2 RSI / Stochastic | 574–583 | Stochastic OS/OB or RSI divergence at the zone: +1 | A | Display (RSI 14 value only) | Not evaluated pre-entry; Manual |
| L3 Gap analysis | 584–593 | Novice/Pro/Window gaps; 4 applications; window-gap entry tweak | A | Partial (window gap boolean) | Provisional + Manual |
| Red flags RF1–RF10 | 594–610 | Absolute rejects. RF3 override needs "10/10 score" (602) | E (RF1, RF8); D (others) | RF1 partial | RF1, RF8 Implement. RF2 partial (conflict). RF3 Implement. RF4, RF7 Manual. RF5/6/9/10 N/A (RF6 moot: cash only) |
| 10 Essential checks | 611–631 | All YES or no trade. Check 1 omits Half-Yearly (617) | E; **C** (617 vs 125–132) | No | Checks 1–4, 8, 9 automated or partial. 5–7 computed where determinable. 10 N/A |
| Pre-trade affirmation | 632–642 | Trader commitment | - | No | N/A |

### Section 2: Scoring (RB 643–1079)

| Section / heading | Lines | Relevant rule | Class | Pine | Phase 1 |
|---|---|---|---|---|---|
| Section intro | 643–656 | Score **execution-TF zones only**. "Complete **14**-Point Scoring Table" (653) | E; **C** (vs 988) | - | Score execution zones only |
| Part A header | 657–662 | **Minimum 7/7 core for Type 1, no negotiation** (661) | E | Displays `/7` | Implement gate |
| Freshness | 663–715 | 3 / 1.5 / 0. Wick touch counts; a 2–3 pt near miss does not; gap-through counts | E | Yes | Implement status; D3 filter |
| Strength | 716–772 | 2 / 1 / 0. Four-factor explosive test (body, achievement, relative size, context). Achievement levels. Leg-out must be a closed candle | E / A | Partial (`legout_count`, window gap) | Pine count; Manual for relative size and context (D8) |
| Time at base | 773–821 | 1–3 = 2; 4–5 = 1; 6+ = 0. Garbage area. Refinement option | E; 0 undefined | Partial | D12 (max 5, both counts); D13 (zero-base) |
| Core summary + 6/7 override | 822–844 | 7/7 for Type 1. 6/7 override only after 100+ trades with strong HTF backing | E / D; **C** (vs 661) | - | 7/7 gate. Override not automated |
| Part B header | 845–850 | "MAXIMUM **8** ADDITIONAL POINTS" | **C** (the listed factors sum to 7) | No | /14 (D4) |
| CF1 Sector | 851–895 | As M1. Mandatory for "DIT/AIT" (869–873) | E / D | Display | Not evaluated (D6) |
| CF2 HTF EMA 20 | 896–918 | As M2 | E / A | Display | Provisional / Manual |
| CF3 Crossover | 919–933 | As L1 | A | Display | Provisional / Manual |
| CF4 Gap application | 934–964 | Any valid application, **including Window Gap present**: +1. Ignore 5-paisa gaps | A | Partial | Provisional / Manual. Double count with Strength unresolved (N6) |
| CF5 RSI / Stochastic | 965–987 | +1. Divergence wording at 979: "price LOWER LOW, RSI HIGHER HIGH" | A (wording) | Display | Not evaluated; Manual |
| Part C | 988–1002 | Heading "15-POINT" (988). Footer "MAXIMUM TOTAL **14**" (1001) | **C** | No | /14 (D4) |
| Part D Priority framework | 1003–1022 | Ranks 1–4 + rejects. Rank 3 = 6/7 + sector +2. Tie-breakers. Uses /15 | E / D | No | Ranks where determinable. Sector parts "not evaluated" |
| Part E Decision matrix | 1023–1034 | 12–15 / 10–11 / 8–9 / 7 / <7 | E (scale /15) | No | Report category from the /14 evaluated score and its upper bound |
| Quick Scoring Reference | 1035–1079 | Adds "PATTERN: Pattern confirms post-entry? → +1" (1068). TOTAL /15 | **C**; Pattern undefined | No | Pattern = post-entry journal field only (D4) |

### Section 3: Top-Down Approach (RB 1080–1538)

| Section / heading | Lines | Relevant rule | Class | Pine | Phase 1 |
|---|---|---|---|---|---|
| Intro (TDA vs MTFA) | 1080–1101 | TDA first, MTFA second | E | - | Pipeline order |
| 1.1 Six-step process | 1104–1118 | Y, HY, Q, M, W, Execution | E | Partial | Implement (D11) |
| 1.2 Yearly | 1119–1140 | Mark the 1–2 most significant zones; focus on the nearest | D | No zones | Python extension. "Most significant" → Manual. Report nearest above/below |
| 1.3 Half-Yearly | 1141–1159 | Fresh HY zones. Daily zone within **5–10%** of HY supply → reject or Confirmation Entry | E / A | No | Implement detection. Conflict band reporting (N3) |
| 1.4 Quarterly | 1160–1179 | Fresh Q zones; obstacle map | E | No | Implement |
| 1.5 Monthly | 1180–1219 | Fresh M zones. Curve at 0/33.33/66.66/100 from DZ PL to SZ PL. Redraw when tested. ATH/ATL | E | Zones Yes; curve No | Implement |
| 1.6 Weekly | 1220–1251 | Fresh W zones (targets). Trend by SMA50 or ATA. Clumping | E / A | Zones Yes | Implement |
| 1.7 Execution TF | 1252–1277 | Score 7/7. HTF zones may be garbage; LTF must be pristine. "Wick-to-Wick" named but not defined (1263) | E / A | Yes (daily) | Implement |
| 2.1–2.2 Conflict definition | 1280–1306 | Check **Monthly, Quarterly, Half-Yearly** within 5–10% of entry. "Coming from" | E / A | Differs (W/M, 5%, §6 PR11) | Implement + N3 |
| 2.3 Conflict actions | 1307–1315 | Reject or Confirmation Entry. A broken HTF zone resolves the conflict | E | Partial (deleted zones drop out) | Implement. Confirmation Entry → Defer/Manual |
| 2.4 Where price came from | 1316–1333 | Do not buy intermediate zones while price is dropping from M/Q supply | A | No | Report the last HTF zone touched; Manual |
| Ch3 Colour coding | 1334–1367 | Visual convention | D | Pine colours differ | N/A (report labels by TF) |
| 4.1 MIT | 1372–1388 | M / W / D. Target at Weekly **or Monthly** opposing zone. Coinciding is best | E / A | - | Implement (D16) |
| 4.2 WIT | 1389–1405 | W / D / 75–125. Monthly conflict check. Execution zones from the last 8–10 candles. Prefer 125 | E / A | No | Implement (D16); ambiguous items → Manual |
| 4.3 DIT | 1406–1424 | 15-min execution. **Sector mandatory** | E | No | Out of scope (intraday; sector deferred) |
| 4.4 HIT | 1425–1444 | Avoid | E | No | Out of scope |
| Ch5 TDA output | 1449–1473 | Six questions; TDA statement | E | No | Report fields. "Origin" → Manual |
| Ch6 Conservative vs aggressive | 1478–1499 | Context-dependent stance | D / A | No | Report context; Manual |
| Ch7 Maintenance | 1504–1524 | Daily update of execution-zone status. Tested → grey out and remove from active. Redraw curve | E | Greys out tested zones | Implement on every completed candle; D3 |
| Chapter summary | 1525–1538 | Restates the above | - | - | - |

### Section 4: MTFA (RB 1539–1983)

| Section / heading | Lines | Relevant rule | Class | Pine | Phase 1 |
|---|---|---|---|---|---|
| Intro | 1539–1560 | Location → Trend → Execution, in that order | E | - | Pipeline order |
| 1.1–1.2 HTF per trade type | 1563–1577 | MIT = Monthly, WIT = Weekly, etc. | E | - | Implement |
| 1.3 Curve | 1578–1602 | Build from nearest **fresh** DZ (below) and SZ (above). Five positions | E | No | Implement |
| 1.4 Special situations | 1603–1628 | ATH/ATL; redraw when a boundary is tested; full redraw when broken | E | No | Implement. ATH target → Manual (D9) |
| 1.5 HTF quality | 1629–1645 | HTF zones may be garbage, "**slightly tested OK (up to ~25%)**" (1639) | **C** (vs 445, 1215, 1587) | - | Curve uses fresh zones only. "25%" is not measurable. Coinciding per D15; conflict per D12 |
| 2.1 Scenarios A–F | 1648–1662 | Location × trend decisions | E | No | Implement |
| 2.2 ITF per trade type | 1663–1671 | MIT = Weekly | E | - | Implement |
| 2.3 SMA 50 clock | 1672–1711 | Angle read visually. "If ANY doubt → sideways" (1708) | A | Differs (numeric thresholds) | D14: Pine numbers as reference; ambiguous bands → Manual |
| 2.4 ATA | 1712–1754 | Zone-violation trend. SMA for the first 100 trades (1748) | E / A | No | Defer |
| 3.1–3.3 LTF requirements | 1757–1785 | Fresh, strength ≥ 1, base ≤ 5, 7/7, leg-out closed | E | Partial | Implement |
| 3.4 Proximity rule | 1786–1804 | WIT/DIT: last 8–10 candles. >20 candles → re-verify. MIT exempt (1803) | A | No | WIT (D16): ≤ 8 candles pass; 9+ → Manual |
| 4.1–4.2 Mahabharata scenarios | 1807–1826 | A: execute. B: needs achievement. C: needs strong confluence (sector). D: reject | E | No | Implement. C → sector not evaluated |
| 4.3 Coinciding/aggressive | 1827–1859 | Decision table. Zone below HTF DL → INVALID | E / A | No | "Inside" and "below DL" Implement. Rest Manual |
| 5.1 Workflow | 1862–1882 | 10-step process | E | No | Pipeline |
| 5.2 Alignment matrix | 1883–1904 | Location × trend × quality | E / A (missing cells) | No | Implement long rows, generic matrix (MIT roles and WIT roles per RB 1370; D22). Missing cells → Manual (N9). No WIT-specific matrix exists (RC14) |
| 5.3 No alignment | 1905–1929 | 5/7–6/7: skip, or wait for a retest then Confirmation Entry (1920) | E; **C** with D3 | No | Skip. Entry on a retested zone is excluded (D3) |
| 6.1–6.2 TF translation | 1932–1967 | Daily ↔ weekly heuristics | D | - | N/A |
| Chapter summary | 1968–1983 | Restates the above | - | - | - |

### Section 5: Execution Mechanics (RB 1984–2565)

| Section / heading | Lines | Relevant rule | Class | Pine | Phase 1 |
|---|---|---|---|---|---|
| 1.1–1.2 Entry | 1994–2023 | Entry = PL + buffer. Tier table (2016–2020). "Guidelines, not rigid rules" (2022) | E / D / **C** | No | Report ranges only (D7, B9) |
| 1.3 Limit orders | 2024–2033 | Always limit orders | E | No | N/A (no execution) |
| 1.4 Missed entry | 2034–2050 | Never chase | E | No | Paper-journal rule |
| 1.5 Window-gap entry | 2051–2060 | "Within a few points" → adjust; "10+ points" → leave | A | No | Manual |
| 2.1–2.3 SL | 2063–2111 | SL = DL − buffer. Tier table (2097–2102). Volatile market +50–100% (2109) | E / D / **C** | No | Report ranges only (D7, B9) |
| 2.4 SL types | 2112–2131 | Normal / Exceptional / Shri Krishna. Selection by context | D | Exceptional DL computed | Report both DLs + SK reference. Choice → Manual |
| 2.5 Absolute SL rules | 2132–2156 | Hard order; locked; exit on touch | E | No | Paper-trade simulation: SL on touch |
| 3.1–3.2 Formula + examples | 2159–2207 | Example 3: ₹1,000 ÷ ₹3 = 333 shares (rounding down implied) | E | No | Implement with floor |
| 3.3 RPT by stage | 2208–2221 | 0.5–1% / 1–1.5% / 1.5–2% | E / D | No | User input |
| 3.4–3.5 Formula purpose; single pool | 2222–2244 | No capital buckets | E | No | Journal |
| 3.6 F&O | 2245–2265 | No F&O for beginners; no F&O substitute for shorts | E | No | Consistent with D2 |
| 4.1–4.3 Targets | 2268–2313 | Structural (preferred); 2:1 minimum; skip if 2:1 is impossible | E / A | No | Implement |
| 4.4 Weekly trailing | 2314–2329 | Trail below DL of each new **quality** weekly DZ | E / D | No | **Defer (D9)**. Reference only |
| 4.5 Break-even trap | 2330–2346 | No break-even exits; trailing exit is the only early exit | E | No | Journal |
| 5.1–5.3 Entry types | 2349–2387 | Type 1 = 7/7. Types 2/3 taught but "never use" (2370) | E | No | Type 1 only. No Type 2/3 tier (D3) |
| Ch6 10-trade limit | 2388–2417 | Max 10 trades per month | E | No | Paper-journal counter |
| Ch7 Alerts | 2418–2468 | Never naked; note template uses "Score: [X/15]" (2436) | E; C (/15) | No | Report alert-note fields using /14 |
| Ch8 Post-trade | 2469–2529 | Live-trade conduct; recovery protocol | E / D | No | Journal |
| Ch9 Modification | 2530–2549 | Before trigger: adjust or cancel. After trigger: nothing | E | No | Journal |
| Chapter summary | 2550–2565 | Restates the above | - | - | - |

### Section 6: Special Strategies (RB 2566–3024)

| Section / heading | Lines | Relevant rule | Class | Pine | Phase 1 |
|---|---|---|---|---|---|
| Intro | 2566–2573 | Extensions only | - | - | - |
| S1 Confirmation entry | 2574–2689 | Wait for HTF zone entry, NSZ break by a close, enter at the new DZ PL. 1 vs 2 SZ break rule. No-base variant "superior", gap serves as base (2671–2679). Line 2688 mentions "pullback to a **tested** Daily DZ" | E / A; **C** (2688 vs D3) | No | **Defer**. Flag VLOC + down-trend cases as Manual |
| S2 LOTL | 2690–2767 | Stacked zones "within 2–5%". Entry options; **Balanced = midpoint between DZ2 PL and DZ1 PL** (2728). SL below DZ1 DL is non-negotiable. Hidden LOTL on 75/125 | E / A | No | Flag LOTL; Manual. No automated entry choice |
| S3 Weekly trailing | 2768–2853 | Process; exit on touch; large-candle exception | E / D | No | Defer (D9) |
| S4 Sector analysis | 2854–2949 | Three-level check; weightage; rotation; portfolio 12–15 stocks; mandatory for DIT/HIT | E / D | Display | Not evaluated (D6) |
| S5 Gap analysis | 2950–2985 | Gap types, applications, execution rules. Window-gap distance table in absolute "points" | A | Partial | Provisional / Manual |
| S6 ATA operations | 2986–3012 | Close beyond DL; clumping within 1–2% | E / A | No | Defer |
| Strategy summary | 3013–3024 | Index of strategies | - | - | - |

### Section 7: Psychology (RB 3025–3437)

| Section / heading | Lines | Relevant rule | Class | Pine | Phase 1 |
|---|---|---|---|---|---|
| Ch1–Ch3 | 3033–3241 | Knowing-doing gap; conditioning; eight traps | - | No | N/A |
| Ch4 HR Manager | 3242–3283 | Rejection filter order: conflict → location → trend → freshness → quality → closing → R:R. "Proceed with caution if tested once" (3269) | E; **C** (3269 vs D3) | No | Use as the order of rejection reasons. Tested zones excluded (D3) |
| Ch5–Ch8 | 3284–3417 | Capital/fear; daily routine (no trades in the first 30 min, 3329); professional profile; red flags | - | No | N/A |
| Chapter summary | 3418–3437 | Restates the above | - | - | N/A |

### Section 8: Development & Operations (RB 3438–4029)

| Section / heading | Lines | Relevant rule | Class | Pine | Phase 1 |
|---|---|---|---|---|---|
| Ch1 100-trade contract | 3444–3540 | Live trades at 0.5–1% RPT; four phases | E | No | N/A (trader conduct) |
| Ch2 Trade-type progression | 3541–3641 | **MIT only for the first 100 trades** (3550). WIT after 50+ MIT. Trade-type specs | E | No | WIT included (D16); "50+ MIT trades" shown as a note |
| Ch3 Scaling | 3642–3677 | RPT increases | E | No | N/A |
| Ch4 Watchlist | 3678–3706 | Build from Nifty 50 and Nifty Next 50 (3684–3685); liquidity; clean charts | E / D | No | Consistent with D1 (Nifty 100). Clean-chart filter → Manual |
| Ch5 Journal | 3707–3775 | Template columns (3713–3741); monthly metrics (3762–3775) | E | No | Implement journal schema and metrics |
| Ch6 Alerts | 3776–3836 | Alert hierarchy; template "Score: [X/15]" (3799) | E; C | No | Report fields (/14) |
| Ch7–Ch9 | 3837–3927 | Per-stock documentation; reviews; schedules | - | No | N/A |
| Ch10 Risk monitoring | 3928–3952 | Red lines (10% monthly DD, >10 trades, …) | E | No | Journal metrics |
| Ch11 Integration | 3953–4029 | One-page system | - | No | - |

---

## 3. Pine Script: block map (every line accounted for)

| Lines | Block | Kind |
|---|---|---|
| 1–2 | Version, `indicator()` (500 boxes/lines/labels max) | Setup |
| 4–77 | Inputs: zones, exceptional, border, info, score, tested, weekly, monthly, conflict, sector | Inputs |
| 79–208 | Inputs: trend EMAs, crosses, HTF EMA levels, dashboards 1 and 2 | Inputs |
| 209–237 | TF-in-seconds and visibility flags | Logic |
| 239–291 | EMA20/50/200, SMA50, `trend_state`, SMA50 clock | Trend |
| 293–297 | HTF EMA20 for W/M/3M/6M/12M via `request.security` | Trend |
| 299–316 | Dashboard 2 HTF SMA50 trend with ranging multiplier | Trend |
| 318–321 | EMA crosses | Trend |
| 323–339 | Candle classification | Detection |
| 341–352 | HTF OHLC (`[0]`, `[1]`, `[2]`, `[3]`) and W/M bar-change flags | Detection |
| 354–478 | Persistent state for D/W/M clusters and pending zones | Detection |
| 480–491 | Last strong candle; cluster-continuation function | Detection |
| 493–568 | Zone and origin arrays (D/W/M) | State |
| 570–574 | Style helpers | Display |
| 580–603 | Helpers + **`f_calc_core_score`** (594–602) | Scoring |
| 604–654 | HTF EMA line management | Display |
| 656–713 | `f_create_zone`, `f_create_origin_zone` (daily) | Detection / State |
| 715–799 | Daily origin visibility + label (score text) | Display |
| 801–852 | **`f_check_zone_conflict`** | Conflict |
| 854–946 | Daily zone visibility + label (score, conflict) | Display |
| 948–1052 | Weekly/monthly create functions | Detection / State |
| 1054–1384 | Weekly/monthly zone + origin visibility | Display |
| 1386–1583 | **Daily cluster → leg-out → zone creation** | Detection |
| 1584–1715 | **Daily pending (deferred achievement)** | Detection |
| 1717–1762 | **Daily zero-base zones** | Detection |
| 1764–1775 | **Daily additional leg-out tracking** | Scoring input |
| 1777–2189 | **Weekly engine** (pending, cluster, zero-base, leg-out tracking) | Detection |
| 2191–2603 | **Monthly engine** (same structure) | Detection |
| 2605–2656 | **Daily invalidation + test loop** | State |
| 2658–2708 | **Weekly invalidation + test loop** | State |
| 2710–2759 | **Monthly invalidation + test loop** | State |
| 2761–2880 | Dashboard 1 calculations (volume, ATR, RSI, zone counts, distances) | Display |
| 2882–2983 | Dashboard 2 calculations; **Nifty/sector status and alignment label** (2949–2983) | Display |
| 2985–3001 | Table setup | Display |
| 3003–3232 | Last-bar rendering: HTF EMA lines, dashboards 1 and 2 | Display |
| 3234–3271 | Cross labels, EMA plots, background | Display |

---

## 4. Pine Script: verified findings

Each finding states the **observed** behaviour, with interpretation labelled separately.

**P1. Defaults (PS 9–12, 15, 71, 205, 207).** Zone method `"Body to Wick"` (alternative `"Wick to Wick"`). `i_max_base_candles = 3` (options 1–5). `i_base_threshold = 0.5` (options 0.3–0.7). `i_legout_threshold = 0.5` (options 0.5–1.0). Exceptional detection on. Conflict distance 5.0% (1–20). Clock lookback 5 bars. Ranging threshold 0.1%.

**P2. Candle classification (PS 323–335).** `body_ratio = |close − open| / max(high − low, mintick)`.
- `is_strong_bull = close > open AND (body_ratio > 0.5 OR close > high[1])`. Bear is mirrored.
- `is_base = body_ratio <= 0.5`.
- *Observed:* the comparisons are strict `>` for strong and `<=` for base. A candle with body exactly 50% is a base candle and is strong only through the close-break path.
- *Observed:* "strong" and "base" can both be true. A small-bodied candle that closes above the prior high qualifies as both.

**P3. Leg-in and cluster start (PS 480–485, 1386–1419).** A cluster starts on a confirmed base candle when:
- the last confirmed strong candle is ≤ 3 bars back (leg-in = that candle's high/low and direction), or
- otherwise, bar[1] re-tested as strong (leg-in = bar[1]).

Only one candle is treated as the leg-in.

**P4. Cluster continuation (PS 487–491, 1420–1432).** The cluster continues while `cluster_count < i_max_base_candles` AND one of:
- the candle is a base that does not close outside the cluster wick range, or
- it is a "transition": inside the cluster wicks with `body_ratio ≤ 0.75` (`1.5 × base_threshold`).

*Observed:* only `is_base` candles increment `cluster_count`. Transition candles widen the wick/body envelope but are **not counted**.
*Observed consequence:* with the default maximum of 3, no zone ever has `base_count` 4–5, so Pine never produces the 1.0 or 0.0 base-count score at default settings.

**P5. Leg-out, pattern and achievement (PS 1433–1463).**
- `combined_high = max(legin_high, cluster_wick_high)`; `combined_low = min(legin_low, cluster_wick_low)`.
- Leg-out bull = `close > open AND (body_ratio > 0.5 OR close > cluster_wick_high)`.
- A zone is created **only if** `close > combined_high` (demand) or `close < combined_low` (supply).
- Pattern: bear leg-in + bull leg-out = DBR; bull + bull = RBR; bull + bear = RBD; bear + bear = DBD.

**P6. PL/DL (PS 1464–1511).** Body to Wick, demand:
- PL = `cluster_body_high`.
- DL = `cluster_wick_low`, or with exceptional detection: reversal `min(legin_low, cluster_wick_low, legout_low)`; continuous `min(cluster_wick_low, legout_low)`.
- `is_exceptional = DL < cluster_wick_low`.

Supply is mirrored. Wick to Wick uses `cluster_wick_high` / `cluster_wick_low` as PL. *Observed:* only the final DL is stored, so the non-exceptional (cluster-wick) DL is not retained.

**P7. Zone attributes (PS 1512–1543).**
- `strong_closing = close > legin_high` (demand).
- `has_gap = low > cluster_wick_high` (window gap; demand).
- `base_count = cluster_count`.
- An origin sub-zone is created when `base_count > 1` (display only).

*Interpretation:* because creation already requires `close > combined_high ≥ legin_high`, `strong_closing` is always true for cluster-path zones whenever `legin_high` is not `na`. The ✓/✗ closing flag adds no information for those zones.

**P8. Pending zones (PS 1544–1565, 1584–1715).** If the leg-out direction matches but achievement fails, `pending_left = 2`. On each later pending bar:
- the zone is created if `close > open AND (body > 0.5 OR close > cluster_wick_high) AND close > combined_high`;
- the original cluster geometry is used and the leg-out extremes are merged.

`zone_bar` is the achievement bar. *Observed:* during a daily pending window, new daily clusters can still start. Weekly and monthly engines block cluster detection while pending (PS 1932, 2346).

**Correction (found while building the Zone Engine; v2.0–v2.2 said "next 2 bars" for every TF).** The **daily (chart-TF)** pending block (PS 1584) is a top-level `if` that runs on the **same** bar that sets `pending_left := 2` (PS 1546). Its achievement test fails there by construction, because that bar's close already failed it, so the counter drops to 1. **Only one later daily bar can complete a daily pending zone.** The weekly and monthly engines check pending **before** their cluster logic in each bar (PS 1799 vs 2097; 2213 vs 2511), so **two later bars** can complete it. The rulebook is silent, so the Zone Engine reproduces each Pine variant (D12). Synthetic tests cover both.

**P9. Zero-base zones (PS 1717–1762).** See §5 for the full trace.

**P10. Additional leg-out tracking (PS 1764–1775; weekly 2178–2189; monthly 2592–2603).** Only the **last element** of the zone array is examined. If 1 ≤ bars since creation ≤ 3 and `legout_count < 5`, any confirmed `is_strong_bull` (demand) or `is_strong_bear` (supply) bar increments `legout_count`.

*Observed:*
- the strong bars need not be consecutive and need not show further achievement;
- if another zone of either direction is created in that window, tracking moves to the new zone and the earlier zone's count freezes.

**P11. Zone creation is gated by display inputs (PS 657–658, 949–950, 1002–1003).** `f_create_zone` creates a zone only if `(is_demand AND i_show_demand) OR (NOT is_demand AND i_show_supply)` and the bar is confirmed. Every new zone starts with `test_count = 0`, `legout_count = 1`, `zone_bar = bar_index` (weekly/monthly: `w_seq`/`m_seq`).
*Observed consequence:* hiding supply zones removes them from the internal inventory, not just from the chart.

**P12. Core score (PS 594–602).**
- freshness = `3.0 / 1.5 / 0.0` for `test_count` 0 / 1 / ≥2;
- strength = `2.0` if `legout_count ≥ 2 OR (legout_count ≥ 1 AND has_gap)`, `1.0` if `legout_count ≥ 1`, else `0.0`;
- base component (`time_score`) = `2.0` if `base_count ≤ 3`, `1.0` if `≤ 5`, else `0.0`.

The score is **recomputed at display time** from current state (PS 772, 913, 1106, 1191, 1272, 1357). It is shown as `"/7"` (PS 781, 922, 1116, 1201, 1282, 1367). *Observed:* there is no age-based or time-decay term, no 1.5 strength value, and no confluence, `/14` or `/15` score anywhere in the file.

**P13. Daily invalidation and tests (PS 2605–2656).** The loop runs over all daily zones on every bar and is **not gated by `barstate.isconfirmed`**.
- Invalidation (demand): `close < zone bottom` → the zone and its origin are deleted from every array (permanent).
- Otherwise, if `bar_index > created_bar` and `low ≤ PL` (demand) and this bar has not already counted: `test_count += 1`.

*Observed:* every bar that touches counts as a separate test, so a two-bar visit is 2 tests.
*Interpretation:* on historical bars this matches confirmed-bar processing. Realtime intrabar behaviour is not relied on.

**P14. Weekly/monthly engines (PS 1777–2603).** These run only when the chart TF is below W/M (PS 213–214), on the first chart bar of a new period (`w_bar_change` / `m_bar_change`), on confirmed bars. They use `w_open1..w_close1` (the `[1]` HTF candle) with `lookahead_off` (PS 341–349).
*Interpretation:* at that bar, `[1]` is the just-completed HTF candle. So a weekly zone is created at the close of the first daily bar of the following week.

**P15. Weekly/monthly invalidation and tests (PS 2658–2759).** Evaluated only on `w_bar_change` / `m_bar_change`:
- invalidation by `w_close1 < bottom` (the weekly close), not by any daily close;
- test by `w_low1 ≤ PL` (the completed week's low).

*Observed:* an HTF zone touched mid-week is reported as fresh by Pine until the following week's first bar.

**P16. HTF conflict (PS 801–852, called at 896–900 and 935–940; dashboard count 3089–3108).**
- Applies to **daily zones of both directions**.
- Compares against opposing **weekly and monthly** zones with `test_count < 2` (fresh or tested once).
- Demand: conflict if `HTF_PL > daily_PL AND HTF_PL − daily_PL ≤ 5% × daily_PL`. Supply is mirrored.
- Result: a fuchsia border/label and a dashboard count only. It filters nothing.

*Interpretation:* a daily DZ that lies **inside** an HTF supply zone (HTF SZ PL below the daily PL) is **not** flagged, because of the strict `>` test. Quarterly, half-yearly and yearly zones do not exist in Pine and are never checked.

**P17. Trend (PS 243–291, 304–316, 2892–2908, 3214–3232).**
- `trend_state` uses `sma50 > sma50[1]` with no dead band. It drives line colour and background only.
- **Clock:** `pct = (SMA50 − SMA50[5]) / SMA50 × 100` on the chart TF. Thresholds: `>2.0` → 12, `>1.0` → 1, `>0.4` → 2, `>0.1` → 2–3, `>−0.1` → 3, `>−0.4` → 3–4, `>−1.0` → 4, `>−2.0` → 5, else 6.
- **HTF trend (Dashboard 2):** Up if `SMA50 > SMA50[1] × 1.001`, Down if `SMA50 < SMA50[1] / 1.001`, else "Ranging", computed for D/W/M/3M/6M/12M.

*Interpretation:* SMA50 needs 50 bars of that TF (≈12.5 years for 3M, 25 for 6M, 50 for 12M). With less history both comparisons are false and Pine shows **"Ranging"** rather than "insufficient data".
*Observed:* the clock action text (PS 3218–3228) has overlapping conditions:
- flat readings (−0.1 to 0.1) are labelled "Mild UP / Caution";
- −0.4 to −0.1 is labelled "SIDEWAYS: Curve only";
- the final `else` is unreachable.

This is a display-only defect.

**P18. HTF EMA 20 (PS 293–297, 3007–3026).** Horizontal levels for W/M/Q/HY/Y are displayed. There is no zone-overlap test and no scoring.

**P19. Crosses (PS 318–321, 3238–3248).** "Major" = EMA50 × EMA200, where "EMA200" defaults to an **SMA** (PS 101); labels GC/DC. "Minor" = EMA20 × EMA50; labels Golden/Death. Labels only. *Observed:* the rulebook's Golden/Death cross (EMA20 × EMA50, RB 569, 921) is Pine's "minor" cross.

**P20. Sector inputs (PS 74–77, 2949–2983, 3110–3118).** **Correction to v1, which said "never used in logic".**
- Pine fetches Nifty and sector `close`, EMA20 and SMA50 on the chart TF.
- Status: "Bullish" if close > both, "Bearish" if below both, else "Neutral".
- Label: "Aligned ↑/↓ (+2)" when both share a status; "Partial (+1)" when either is Bullish; otherwise "No Alignment (0)".
- *Observed:* the result is a dashboard label only and is added to no score.
- *Observed:* the method (price vs moving averages) differs from the rulebook definition (stock, sector and Nifty all **at aligned D&S zones**, RB 490, 859), and it ignores the stock itself.

**P21. Dashboard 1 (PS 2761–2880, 3032–3118).** Volume, ATR(14), RSI(14) 70/30, fresh-zone counts and nearest fresh-zone distance. Display only.

**P22. Not present in Pine.** Q/HY/Y zone detection, Curve/location, coinciding vs aggressive, authenticity, LOTL, entry, SL, target, R:R, quantity, any confluence score, post-entry pattern, trailing stop, trade-type logic, recency (8–10 candle) filter.

**P23. Confirmed-bar behaviour.** All creation, pending, zero-base and leg-out-tracking blocks require `barstate.isconfirmed` (PS 483, 658, 1386, 1420, 1584, 1724, 1765, 1777, 2191). The three invalidation/test loops do not (PS 2605, 2658, 2710).

**P24. Drawing limits (PS 2).** `max_boxes_count = 500`. *Interpretation:* TradingView may drop the oldest drawings once that limit is exceeded. Parity tests should therefore compare zone values (labels, arrays), not the presence of boxes.

---

## 5. Zero-base trace (exact executed path)

**Daily detection (PS 1717–1723):**
```
zero_base_bull = close>open AND (body_ratio>0.5 OR close>high[1])
prev_zero_bear = close[1]<open[1] AND (prev_body_ratio>0.5 OR close[1]<low[2])
zero_base_dbr  = prev_zero_bear AND zero_base_bull AND NOT in_cluster
```
`in_cluster` is read **after** the cluster block on the same bar, which may have just closed a cluster. The block runs only if `bar_index > 2 AND barstate.isconfirmed` (PS 1724). Unlike the weekly (PS 2139) and monthly (PS 2553) versions, the daily path does **not** check for a pending zone.

**Creation (PS 1725–1743, DBR; RBD mirrored at 1744–1762).**
- Body to Wick PL = `max(min(open[1],close[1]), min(open,close))`.
- DL = `min(low[1], low)`.
- `f_create_zone(true, PL, DL, bar_index−1, is_exceptional=false)` sets `test_count=0`, `legout_count=1` (PS 683, 688).
- Then: `strong_closing = close > high[1]`, `has_gap = low > high[1]`, `pattern = "DBR"`, `base_count = 0` (PS 1735–1742).
- `zone_origin_enabled` stays `false`, so the origin box is never shown.

**Score at creation**, from `f_calc_core_score` (PS 594–602) with `test_count=0`, `legout_count=1`, `base_count=0`:

| Component | Variable and value | Rule applied | Points |
|---|---|---|---|
| Freshness | `test_count = 0` | `== 0 → 3.0` | **3.0** |
| Strength, no gap | `legout_count = 1`, `has_gap = false` | `≥1 → 1.0` | **1.0** |
| Strength, with gap | `legout_count = 1`, `has_gap = true` | `≥1 AND gap → 2.0` | **2.0** |
| Base component | `base_count = 0` | `≤ 3 → 2.0` | **2.0** |
| **Core (no gap / gap)** | | | **6.0 / 7.0** |

**Subsequent changes (exact):**
1. **Bars 1–3 after creation (PS 1765–1775).** Each confirmed `is_strong_bull` bar adds 1 to `legout_count`, **only while this zone is still the last element of the daily arrays**. A no-gap zone therefore goes 6.0 → 7.0 on the first such bar. After bar 3, or once a newer daily zone exists, `legout_count` is frozen.
2. **Any later bar with `low ≤ PL` (PS 2649–2654).** `test_count += 1`, so freshness goes 3.0 → 1.5 → 0.0. Under D3 the zone then leaves scanner output.
3. **Any bar with `close < DL` (PS 2613).** The zone is deleted.
4. **No age-based decay exists.** `base_count` and `has_gap` never change after creation.

**Weekly/monthly zero-base (PS 2135–2176, 2549–2590).** Same logic on `[1]`/`[2]` HTF candles. Additionally requires no pending zone. Leg-out tracking counts HTF candles (`w_seq`, `m_seq`).

**What the rulebook says.**
- The base table covers 1–3, 4–5 and 6+ only (RB 785–787, 1047–1049). **Zero bases is not scored.**
- In the Confirmation Entry context only, "no base candle" bounces are called "superior" and "the gap or empty space between the leg-in and leg-out serves as the 'base'" (RB 2671–2679).
- *Observed:* Pine's zero-base `has_gap` is the gap between leg-in and leg-out. The rulebook's Window Gap is defined as the space between **base** and leg-out (RB 588, 949).
- **Pine's 2.0 base-count points for `base_count = 0` therefore have no explicit rulebook basis.** Resolved by **D13**: Pine's value is the initial reference, tagged `ZB-PINE-REF`.

---

## 6. Rulebook ↔ Pine disagreements

| ID | Topic | Rulebook | Pine | Consequence |
|---|---|---|---|---|
| PR1 | Strong / exciting candle | Body > 50% (RB 402); "significantly" > 50% (738) | Body > 50% **or** close beyond prior high (PS 332–333, 1436–1437) | Pine accepts small-bodied break candles as leg-outs → **D12:** body > 50% required; Pine-only path → Manual |
| PR2 | Explosive relative size / context | Required (RB 740–741, 768–770) | Not checked | Manual review (D8) |
| PR3 | Closing / achievement | H5 closing is "ideally" (RB 451); achievement levels (747–752) | Close beyond leg-in + base extreme is **mandatory** for creation, with a pending grace of 1 later bar (daily) or 2 (weekly/monthly) (PS 1438–1463, 1584–1591) | Pine never creates zones the rulebook would mark as weak-closing → **D12:** Pine test is the objective achievement minimum; non-achieving patterns are HTF context only (Manual) |
| PR4 | Base counting | Count base candles; 4–5 = 1 point (RB 786) | Transitions not counted; default maximum 3 prevents 4–5-base zones (PS 10, 1421–1427) | Different base counts; 4–5-base zones absent → **D12:** max 5; both counts; band disagreement → Manual |
| PR5 | Number of leg-out candles | "2+ explosive candles moving away from the base" (RB 728) | Any strong same-direction bar within 3 bars, latest zone only (PS 1764–1775) | Strength can differ → **D12:** per-zone count, body > 50% only; differences → Manual |
| PR6 | Gap | Any gap type; must be meaningful (RB 941, 960, 2974) | Window gap only, any size (PS 1523–1525) | Strength 2 from tiny gaps → Manual |
| PR7 | Zero-base base score | Undefined | 2.0 (PS 601) | **D13:** Pine reference, `ZB-PINE-REF` tag |
| PR8 | HTF freshness timing | Any candle touch; update every session (RB 264, 683, 292, 1508) | Weekly/monthly tests only at the next period's first bar, using the HTF low (PS 2701–2706, 2752–2757) | Pine shows touched HTF zones as fresh for up to a week/month → **D12:** update on every finest completed candle |
| PR9 | Test counting | "Count HOW MANY times the PL has been touched" (RB 685); visit vs candle not defined | One per touching bar (PS 2651–2654) | Affects 1.5 vs 0 only. Irrelevant under D3 |
| PR10 | Pending-zone test window | From the candle after the leg-out (RB 682) | From the bar after the **achievement** bar (PS 2649 with `zone_bar` = achievement bar) | Touches between the original leg-out and achievement are missed → **D12:** touch in that window → Manual |
| PR11 | HTF conflict | M, Q, HY within **5–10%** above entry; "inside" counts (RB 1158, 1302–1304, 601) | W and M within 5% above daily PL; inside-case missed (PS 821–850) | **D12:** M/Q/HY inside or ≤ 5% = conflict; 5–10%, W, Y and tested opposing zones → Manual |
| PR12 | Zone inventory | Zones exist regardless of how a chart is displayed | Display toggles gate creation (PS 657) | Scanner must detect independently of display |
| PR13 | Trend quantification | Clock read visually; doubt → sideways (RB 1686–1708) | Numeric clock thresholds; separate dead-band method (PS 252–291, 304–316) | **D14** |
| PR14 | Golden cross naming | EMA20 × EMA50 (RB 569) | Pine calls this "minor"; its "Golden Cross" is EMA50 × SMA200 | Naming only |
| PR15 | Sector alignment | Zone-based, three instruments (RB 490, 859–866) | MA-based, two indices (PS 2949–2983) | Pine label must not be used (D6) |
| PR16 | Marking method | "Body to Wick" / "Wick-to-Wick" named but not defined (RB 538, 1263) | Defined in code (PS 1470–1511) | Pine is the only definition; used (D12, rulebook silent) |
| PR17 | HTF zone availability | All HTFs always relevant | Weekly/monthly engines run only when chart TF is below W/M (PS 213–214) | Scanner computes all TFs regardless |
| PR18 | Leg-out count of a pending zone | "2+ explosive candles moving away from the base" (RB 728); explosive needs achievement (RB 739) | `legout_count = 1` at the achievement bar, so the failed first leg-out is never counted (PS 688, 1646) | **D12:** both readings shown; score difference → Manual (`PENDING_LEGOUT_COUNT_AMBIGUOUS`) |

---

## 7. Rulebook-internal contradictions and ambiguities

| ID | Topic | Evidence | Resolution status |
|---|---|---|---|
| RC1 | **Score denominator** | "14-Point" (653); "MAXIMUM 8 ADDITIONAL" (845); "15-POINT" (988); "MAXIMUM TOTAL 14" (1001); Quick Reference adds Pattern +1, TOTAL /15 (1068–1078); /15 also at 482, 596, 1009–1012, 1029, 1874, 2436, 3727, 3799; /10 at 602, 2727, 3001; /8 at 489, 853, 891, 2858 | **D4: pre-entry /14.** The arithmetic reconciles exactly: core 3+2+2 = 7; confluence factors 1–5 = 2+2+1+1+1 = 7; total 14. "8 additional" = 7 + post-entry Pattern. The /10 and /8 references are informal and unreconciled; they are not used. |
| RC2 | **Tested-once zones** | Binary "do NOT trade" (272, 289); "proceed only with exceptional backing" (291, 676, 826); "proceed with caution if tested once" (3269); "wait for retest then Confirmation Entry" (1920); "pullback to a tested Daily DZ" (2688) | **D3** governs the scanner: tested zones excluded. |
| RC3 | **6/7 override** | "No negotiations" (661) vs 6/7 override (831–843) vs Rank 3 "ACCEPTABLE" (1011) vs Type 2 for 6/7 (2354) vs "never use Type 2/3" (2370) | Not automated. 6/7 fresh zones are not actionable. The override needs sector (deferred), 100+ trades and visual judgement. |
| RC4 | **Buffer ranges** | Entry "₹0.50 to ₹2-5" (305) vs "₹0.50 to ₹5" (2010) vs tiers ₹0.25–₹10 (2016–2020). SL "₹1-5+" (332) vs "₹500 stock might need ₹5-10" (351) vs tiers ₹0.50–₹15 (2097–2102). Tier edges ₹100/₹500/₹2,000 belong to two tiers. The price basis (PL, DL, CMP) is not stated | **Unresolved (B9).** Ranges are transcribed exactly in the spec; no value chosen. |
| RC5 | HTF zone quality | "Slightly tested OK (up to ~25%)" (1639) vs curve between FRESH zones only (445, 1215, 1587) | Curve uses fresh zones (explicit, repeated). The "25%" cannot be measured (testing is binary, 289). Context uses: coinciding per D15 (DL untouched); conflict per D12 (tested opposing zones → Manual). |
| RC6 | Half-Yearly in Essential Check 1 | Omitted (617); included at 125–132 and 1104–1115 | D11: full hierarchy. |
| RC7 | Target timeframe and buffer | ITF opposing PL (551–558, 2278); "Weekly or Monthly" (1386); example "PL − small buffer" (2287) | N10: target buffer unresolved; Weekly vs Monthly → Manual. |
| RC8 | LTF recency | 8–10 candles (1788) vs re-verify after 20 (1801) vs risk bands 15–20 / 30+ (1797–1798) | WIT in scope (D16): ≤ 8 candles pass; 9+ → Manual. |
| RC9 | RSI divergence wording | "Price LOWER LOW, RSI HIGHER HIGH" (979) | Recorded, not corrected. Component is manual. |
| RC10 | Cross-references | Confirmation Entry "covered in Section 7" (1312) and trailing "Section 7 (Special Strategies)" (2322): both are Section 6. ATA "Section 5, Chapter 2.4" (2990): it is Section 4. "Sections 1-5 taught…" (1986) is written inside Section 5. | Editorial only. |
| RC11 | Trade-type naming | "DIT/AIT" (869–873, 892, 2942–2948) vs "DIT/HIT" (892, 2940) | Editorial only. Both are out of scope. |
| RC12 | MTFA matrix gaps | No rows for LOC + mild up (2–3 o'clock), EQB + moderate/mild up, VLOC + moderate up, and others (1887–1903) | N9: Manual. |
| RC13 | Gap and strength double count | Strength gives 2 for "1 explosive + gap" (728). CF4 gives +1 for "Window Gap present" (940) | N6: unresolved. Shown as provisional. |
| RC14 | No WIT-specific trend matrix | The only alignment matrix is generic: Location (HTF) / Trend (ITF) / Zone Quality (LTF) (1883–1904). Roles change by trade type (1370; WIT: 1574, 1668, 1768). Some referenced rows are phrased around Monthly/Quarterly zones and Daily charts (1892, 2593–2598) | D22: generic matrix with WIT roles; WIT cases on those rows → Manual. |

---

## 8. Corrections to earlier documents

### 8.1 v1 `SOURCE_COVERAGE_REPORT.md`
| v1 claim | Correction |
|---|---|
| Rulebook "Lines 1–1150 (complete read of Sections 1–3)" | Section 3 ends at line 1538, so 1–1150 did not cover all of Section 3. Sections 4–8 (1539–4029) were unread. **v2 read 1–4029.** |
| Pine "verified (all critical sections)", skipping 650–789, 905–1385, 2750+ | Those ranges contain `f_create_zone` (656–688), which initialises `legout_count = 1` and gates creation by display toggles, and the sector logic (2949–2983). **v2 read 1–3271.** |
| "Sector inputs … never used in logic" | Wrong. PS 2949–2983 compute a display-only alignment label (P20). |
| "~2,750 lines" (v1 spec) | 3,271 lines. |
| B1 resolved as /15 | Superseded by **D4 (/14)**. |
| B2 "tested-once flagged, not actionable", shown in output | Superseded by **D3** (excluded from display). |
| B3 zero-base "eligible, with gap 7.0 / no-gap 6.0" | Arithmetic confirmed, but the base-count component is undefined in the rulebook (now handled by **D13**). The leg-out increment applies only while the zone is the latest zone. |
| B5 "Kite API: approved as primary source" | Superseded by **D10** (option to investigate; nothing confirmed). |
| B7 universe unresolved | Superseded by **D1** (Nifty 100). |
| "Specification is ready for implementation" | **Withdrawn.** See `IMPLEMENTATION_BLOCKERS.md`. |
| T4 "Sector score: 0 (deferred …)" | Replaced by an explicit *not evaluated* status (D6). |

### 8.2 v1 `DECISION_LOG.md`
| v1 entry | Correction |
|---|---|
| D3 "/15", display X/15 | Replaced by **D4 /14**. Pattern is post-entry and separate. |
| D4 + D18: tested-once zones displayed and flagged | Replaced by **D3**: excluded from displayed results and candidates. |
| D11 sector score = 0 | Replaced by **D6**: *not evaluated / manual review*, not 0. |
| D12 midpoint buffers (₹0.375, ₹1.25, …) | **Withdrawn.** The user rejected midpoints (D7). |
| D16 universe UNRESOLVED | Replaced by **D1** (Nifty 100). |
| D17 Kite as primary data source, with unverified limits ("2,000 days", "60 days") | Replaced by **D10**. Limits are *to be verified*; not stated as fact. |
| D20 "Coinciding = within ±1%" | **Withdrawn.** The 1% figure is invented (no source). See N4. |
| D1 / D7 labelled SOURCE_DEFINED | The base threshold (≤ 0.5), 3-bar leg-in window and pending window (1 later bar on daily, 2 on weekly/monthly, P8) are **Pine-defined**; the rulebook is silent. |
| D5 "reaches 7.0 if legout_count increments within 3 bars" | Correct only while the zone is the most recent daily zone (P10). |
| D13 IMPLEMENTATION_CHOICE | Replaced by **D8** (user decision). |

### 8.3 v1 `IMPLEMENTATION_SPECIFICATION.md`
- The /15 table, midpoint buffers, sector "computed as 0", tested-once display, 1% coinciding tolerance, "~2,750 lines" and the Nifty 500 data plan are all removed or corrected.
- Unsupported numbers are removed: transaction cost "~0.12–0.15%", circuit limits "5%/10%/20%", Kite "~₹2,000/month", "2,000 days", "60 days".
- "Explosive check accepted as sufficient (ASSUMPTION)" is replaced by D8 with manual review.

### 8.4 Superseded audits (left unmodified; not evidence)
| File / line | Unsupported claim | Actual source |
|---|---|---|
| `archive/AUDIT_VALIDATION_REPORT.md` 26–28 | Strong ≥ 60%, weak < 40% | 0.5 thresholds (PS 11–12; RB 402) |
| same, 40 | Strength 2 / **1.5** / 1 | 2 / 1 / 0 (PS 596–600; RB 728–730) |
| same, 54–58 | "Time Score" by bar age (2 / 1.5 / 1 / 0.5) | Base-count score 2 / 1 / 0 by `base_count` (PS 601); no time decay anywhere |
| same, 391, 411 | Zero-base starts at 7.0 / 7.5, decays to 6.5; core 5.0 | 6.0 / 7.0 at creation; no decay (§5) |
| same, 238 | Two-tier output with tested-once tier | Contradicts D3 |
| same, 418–420 | Blocker "Kite API access confirmed" | D10: not confirmed |
| `archive/STRATEGY_SPECIFICATION_AUDIT.md` 690 | Kite limits and price stated as fact | Unverified |
| same, 781 | Nifty 500 data plan | D1: Nifty 100 |
| same, E.5 / B.9 | DL breach "open question"; conflict demand-only | Permanent deletion (PS 2613–2647); both directions (PS 821–850) |

---

## 9. Effect of user decisions D12–D17 (v2.1)

| Decision | Discrepancies or items affected | Outcome |
|---|---|---|
| D12 Rulebook-strict | PR1, PR3–PR6, PR8, PR10–PR13, PR16, PR17; RC5 | Rulebook result is primary; Pine fills only silent, non-conflicting gaps; conflicts or ambiguities → Manual. Per-item table in DECISION_LOG D12 |
| D13 Zero-base | PR7; §5 | Pine score kept as reference, tagged `ZB-PINE-REF`; rulebook does not define it |
| D14 Daily-execution trend | PR13; RB 1193, 1232, 1672–1711 | Weekly and Monthly evaluated. Roles set by D21 |
| D15 Coinciding | RB 528, 1833, 1853, 1856; RC5 | HTF zone counts while its DL is untouched; entry eligibility unchanged (D3) |
| D16 MIT + WIT | RB 1389–1405, 1786–1804, 3589–3616; RC8 | 75/125-min execution in scope. WIT trend per D22 |
| D17 Kite | - | Pending verification (B6), including 75/125 construction |
| D21 MIT trend roles (B13) | RB 1232, 1378, 1667, 1896 | Weekly = gate; Monthly = mandatory context; Weekly vs Monthly-location conflict → RB 1232 "extreme caution" → Manual; matrix rejections unchanged |
| D22 WIT trend (B14) | RB 1370, 1574, 1668, 1768, 1883–1904; RC14 | Generic matrix with WIT roles; Daily is the only trend gate; underspecified rows → Manual |
| D23 HTF candles (B8) | RB 1104–1179; PS 295–297, 312–316 | Calendar-aligned Y/HY/Q; incomplete periods excluded; insufficient history reported. **TradingView parity unverified** |

## 10. Verification log

| Check | Result |
|---|---|
| Pine SHA-256 before and after editing | `14293fa5d3c8e5ba9309b45804a840bb5d8c43d47c193ebb6bca0480bc0a5519`, unchanged |
| Rulebook SHA-256 before and after editing | `039883be6b97ca39b00e5afe80f219a5d759dae99fa9c4179475f506a275d54b`, unchanged |
| Application / skill files | Unchanged (hashes compared) |
| Network / broker / credentials | None used |
| Line numbers | Rechecked with `grep -n` against the current files |
