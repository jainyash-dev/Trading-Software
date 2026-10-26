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
| B16 | HTF freshness from finer candles | **Implemented** (`nse/mtf-freshness/`) under D24-D28. Real-data and TradingView validation are still open (B6-B10, B17) |

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
| **B17** | **Validated NSE trading calendar** | Without it, D28 applies: a period completes only when the next period's data arrives (one session late), and every missing weekday is an unverified gap, so zones spanning holidays become UNKNOWN_DATA_GAP. Holiday and special-session handling is unvalidated. | D28 (A5); RB 186, 3323 | Candle construction, period completion, data-gap detection | **Scanner** (production use), **Validation** | Obtain an official NSE holiday/session calendar; validate boundaries and holidays against exchange data and TradingView. Not production-ready until done |

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
- **B17:** NSE trading calendar (holidays, special sessions): not yet obtained. The official Nifty 100 constituent file: not yet obtained.

### 4D. Historical-data and backtesting validation
- **B11:** point-in-time Nifty 100 membership and delisted/merged history.
- **B15:** intraday history depth for WIT.
- **B9, B12:** buffer determinism and fill/cost assumptions.
- Any backtest on today's constituents is survivorship-biased and is **not** validation evidence.

---

## Part 5: Readiness summary

| Area | Status |
|---|---|
| Documentation | ✅ Consistent with D1–D17 and D21–D28 |
| Scanner implementation | ⛔ **Not ready.** Needs B6 (data source), B7 (adjustment), B8 + B10 (TradingView verification) and B17 (validated NSE calendar) before outputs can be trusted. B16 is implemented. No user decisions remain for the scanner logic itself. |
| Historical validation | ⛔ **Not ready.** Additionally needs B9, B11, B12, B15. |

**Implementation status (2026-10-26):**
- **Zone Engine** (`nse/zone-engine/zone_engine.py`, 61 synthetic tests in `tests/test_zone_engine.py`): single-timeframe detection, scoring, freshness, invalidation and zone-level eligibility. All 13 audit mutations and the P12 ambiguity are caught.
- **HTF freshness orchestrator** (`nse/mtf-freshness/mtf_freshness.py`, 26 synthetic tests in `tests/test_mtf_freshness.py`): implements B16 under D24-D28. It applies completed finer candles to W/M/Q/HY/Y (and D, from an intraday base) zones; it never adds eligibility, only removes it (`eligible_after_overlay`). 18 targeted mutations are caught.
- Neither component is validated against TradingView (B8, B10), uses real data (B6, B7) or has a validated NSE calendar (B17). Trend, location, conflict, coinciding, R:R and the scanner remain unbuilt.
