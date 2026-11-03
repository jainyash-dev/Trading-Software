# Phase 1 Correctness Audit

**Project:** NSE GTF Demand & Supply Swing-Trading Research System
**Date:** 2026-10-26
**Scope:** the Zone Engine (`nse/zone-engine/zone_engine.py`), the HTF freshness orchestrator (`nse/mtf-freshness/mtf_freshness.py`) and their tests. It also covers the uncommitted calendar module (`nse/calendar/nse_calendar.py`), insofar as Phase 1 depends on it.
**Status:**
- Findings, H1/H2 fixes and the M3 decision (option c) are approved by the user (2026-10-26): D33-D35.
- The second-pass review (section 4A) found four more counterexamples, fixed as P1-P3. The user approved them on 2026-10-27 as D36-D38, and approved the D30 special-session rule provisionally.
- The final review (section 4B) found two more gaps and closed them.
- **Committed:** the calendar infrastructure in `d72415f` and the remediation (H1, H2, M3, D36-D38) in `b7a51cc`, both on `nse-phase1` on 2026-10-27. The audit baseline was `16f17af`.
- L4 and L10 were fixed on 2026-10-27 (section 4C) and committed in `bdaa09d`.
- **Status update 2026-10-28:** L1-L3 fixed in the working tree (uncommitted; section 5). The official calendar for 2021-2025 is transcribed (D40, proposed), and one real-data pipeline check exists (INFY Q1 2022). Everything else in this report remains synthetic evidence.
- **Project status:** Phase 1 in progress; external validation pending.

All evidence in this report is **synthetic**. Nothing here shows correctness on real NSE data, parity with TradingView, or any trading result.

---

## 1. Executive verdict and scope

**Verdict: NOT READY TO DECLARE COMPLETE.**

- The audit found two high-severity defects (H1, H2). Each broke an approved decision (D30 and D27, respectively).
- Both are now fixed in the working tree, with regression tests that fail on the committed code and pass on the fix (section 6).
- A second review of those fixes (section 4A) found four more ways a zone could be fabricated, or not blocked, despite unresolved data quality. They are fixed the same way and were approved as D36-D38.
- The remediation is committed (`b7a51cc`).
- The verdict stays **NOT READY TO DECLARE COMPLETE**, by user decision: Phase 1 is in progress and external validation is pending.
- Evidence is synthetic only; nothing has been validated on real NSE data or against TradingView.

"Phase 1" covers zone detection, core scoring (/7), freshness, invalidation and eligibility on completed candles, plus the HTF freshness overlay (B16). Scanner-level work is out of scope: confluence /14, MTFA, R:R, sizing, entries and alerts. Those requirements appear in the matrix as NOT IMPLEMENTED (planned).

## 2. Repository state

| Item | Value |
|---|---|
| Branch | `nse-phase1` (`main` untouched at `3d0f4ef`) |
| HEAD | `16f17af` Add HTF freshness orchestrator (B16) with synthetic tests |
| Tests at HEAD (committed code only) | 403 / 403 pass |
| Tests in the working tree, before remediation | 418 / 418 (adds the 15 uncommitted calendar tests) |
| Tests in the working tree, after H1/H2 remediation | 423 / 423 (adds 5 tests) |
| Tests in the working tree, after the second pass (section 4A) | 427 / 427 (adds 4 tests; strengthens 3 existing ones; changes 1 committed assertion, see P3) |
| Tests in the working tree, after the final review (section 4B) | 429 / 429 (adds 2 tests) |
| Committed | `d72415f` (calendar infrastructure, 418 tests on its own tree), `b7a51cc` (remediation, 429 tests) |
| Working tree after L4/L10 (section 4C, uncommitted) | 439 / 439 (adds 10 tests; strengthens 1) |
| Rulebook SHA-256 | `039883be6b97ca39b00e5afe80f219a5d759dae99fa9c4179475f506a275d54b` (unchanged) |
| Pine Script SHA-256 | `14293fa5d3c8e5ba9309b45804a840bb5d8c43d47c193ebb6bca0480bc0a5519` (unchanged) |
| Secrets / broker / network scan | nothing found under `nse/` or in the NSE tests |

The rows above describe the audit as it ran from baseline `16f17af`.

**Committed since the baseline:**
- `d72415f`, external-validation Step 1:
  - `nse/calendar/`, `nse/data/calendar/`, `nse/docs/DATA_REQUIREMENTS.md`, `tests/test_nse_calendar.py`;
  - edits to `DECISION_LOG.md` (D29-D32) and `IMPLEMENTATION_BLOCKERS.md`.
- `b7a51cc`, the remediation:
  - `nse/mtf-freshness/mtf_freshness.py`, `nse/zone-engine/zone_engine.py`;
  - `tests/test_mtf_freshness.py`, `tests/test_zone_engine.py`;
  - this report;
  - `DECISION_LOG.md` (v2.5: D33-D35, P1-P3) and `IMPLEMENTATION_BLOCKERS.md`.

## 3. Requirements traceability matrix

**Status key:**

| Status | Meaning |
|---|---|
| SYNTH-TESTED | A test with hand-derived expectations exercises the rule. Synthetic only. |
| CODE-REVIEW | Verified by reading the code; no dedicated test. |
| FIXED | Was a defect; fixed, with the commit or working-tree state stated in the row. |
| MANUAL REVIEW (by design) | The engine flags the case for a human and never decides it. |
| EXT-UNVERIFIED | Needs real NSE data or TradingView to confirm. |
| NOT IMPLEMENTED | Planned for a later phase. Not a defect. |
| N/A (human) | A discipline, psychology or process rule with no automation target. |

A passing test is not taken as proof that a requirement is met. It shows only that the synthetic case behaves as derived by hand.

### 3.1 Phase 1 requirements (zone engine and freshness)

| # | Requirement | Source | Code | Status |
|---|---|---|---|---|
| 1 | Strong candle = body > 50% of range | RB 402; D12 | `zone_engine.py` `is_base` / `legout_eval` | SYNTH-TESTED |
| 2 | Leg-out must be a closed candle | RB 771 | engine `_completed`, as-of filter | SYNTH-TESTED |
| 3 | Leg-out achievement (close beyond the leg-in/cluster extreme) | RB 739; PR3 | `legout_eval` | SYNTH-TESTED (objective minimum); judgement part MANUAL REVIEW |
| 4 | Strength score 2/1/0 by explosive leg-out count | RB 716-760 | `legout_step`, `_assess` | SYNTH-TESTED |
| 5 | Leg-out counted per zone; interrupted sequence flagged | PR5; D12 | `legout_step` | SYNTH-TESTED; `LEGOUT_SEQUENCE_INTERRUPTED` is MANUAL REVIEW |
| 6 | Relative size / context of the leg-out | RB 740-741 | flag `LEGOUT_RELATIVE_SIZE_CONTEXT` | MANUAL REVIEW |
| 7 | Base score: 1-3 = 2, 4-5 = 1 | RB 785-786 | `_assess` | SYNTH-TESTED |
| 8 | 6+ bases = garbage area, reject | RB 787, 800-806 | `cluster_step` | SYNTH-TESTED for 6 overlapping bases; a 6th base closing outside is MANUAL REVIEW by design (`BASE_CLOSED_OUTSIDE_CLUSTER`, D35) |
| 9 | Transition candles (body 50-75%) in the base count | RB 769; PR4 | both counts reported | MANUAL REVIEW (`BASE_COUNT_TRANSITION_AMBIGUITY`) |
| 10 | DBR, RBR, RBD, DBD patterns | RB 2100-2130 | `create` | SYNTH-TESTED |
| 11 | Proximal / distal lines, Body-to-Wick | RB 2112-2130 | `create` | SYNTH-TESTED |
| 12 | Exceptional distal line | RB 533-546; PS 1473-1490 | `create` | SYNTH-TESTED |
| 13 | Wick-to-Wick marking "as appropriate" | RB 1263; PR16 | none | NOT IMPLEMENTED (needs a decision) |
| 14 | Proximal line never moves after creation | RB 544 | `create` only writes it | CODE-REVIEW |
| 15 | Freshness: any candle touching the proximal line tests the zone | RB 264, 683-697 | engine `state_step`; overlay `_overlay` | SYNTH-TESTED (incl. gap-through, near miss, cross-through) |
| 16 | Freshness score 3 / 1.5 / 0 | RB 663-715 | `_assess` | SYNTH-TESTED |
| 17 | Tested zones excluded from candidates | D3; RB 260-293 | `_assess` `ZONE_TESTED`; overlay | SYNTH-TESTED; random sweeps (section 5) |
| 18 | Tested 2+ times = do not trade | RF1 (RB 600) | `_assess` | SYNTH-TESTED |
| 19 | 7/7 core minimum for Type 1 entries | RB 822-844; D4 | `_assess` line 746 | SYNTH-TESTED |
| 20 | Close beyond the distal line invalidates; a wick does not | RB 2063-2156; PS 2667 | `state_step`; overlay A1 | SYNTH-TESTED |
| 21 | HTF invalidation on the zone's own timeframe; base close = manual review | D24 | `_overlay` | SYNTH-TESTED |
| 22 | Only completed candles drive decisions | RB 771; D12 | engine `_completed`; overlay `_build_series` | SYNTH-TESTED inside the orchestrator; engine trusts the caller (M2) |
| 23 | HTF zone status updated every session | RB 292, 1508; B16 | orchestrator | SYNTH-TESTED |
| 24 | Excluded sessions kept out of candle construction | D30, D33 | `_classify`, `_overlay` | **FIXED**; was defect H1 (committed in `b7a51cc`) |
| 25 | Missing data never yields a fresh zone | D27, D34 | `_overlay`, `_build_series` | **FIXED**; was defect H2, plus S1-S3 (P1, P2) in section 4A |
| 25a | Daily zones get the same data-quality checks | D27, D34, D38 | `replay` D over D | **FIXED**; was S4 |
| 25b | Special session on regular hours counts as normal only from verified source data | D30 (provisional) | `nse_calendar.session_type` | SYNTH-TESTED (incl. the unverified-source refusal). Official circulars now registered for 20 Jan 2024 and 1 Feb 2025 (D40, proposed); **EXT-UNVERIFIED** against EOD data and TradingView |
| 26 | Pending zones (late achievement) | PR3, PR10, PR18 | `pending_step` | SYNTH-TESTED; window touch and leg-out count are MANUAL REVIEW |
| 27 | Zero-base zones, Pine scoring | D5, D13 | `zero_base_step`; tag `ZB-PINE-REF` | SYNTH-TESTED (against my reading of Pine) |
| 28 | Window-gap meaningfulness | RB 941 | `GAP_MEANINGFULNESS_UNVERIFIED` | MANUAL REVIEW |
| 29 | Calendar-aligned W/M/Q/HY/Y candles | D23; B8 | `period_key`, `_build_series` | SYNTH-TESTED (incl. year-end ISO week); EXT-UNVERIFIED against TradingView |
| 30 | 75m / 125m bars start at 09:15 within the 375-minute session | RB 186-193 | intraday validation | SYNTH-TESTED; EXT-UNVERIFIED |
| 31 | Drop one timeframe inside a 6+ base mess | RB 818-820 | none | NOT IMPLEMENTED |

### 3.2 Scanner-level and later requirements

| Area | Source | Status |
|---|---|---|
| C1 risk and position sizing | RB 37-76, 2157-2265 | NOT IMPLEMENTED |
| C2 minimum 2:1 R:R; RF8 | RB 77-114, 607 | NOT IMPLEMENTED |
| C3 top-down approach completed; TDA steps Y to Daily; HTF conflict | RB 115-156, 1080-1538 | NOT IMPLEMENTED (hierarchy accepted by the orchestrator only) |
| C4 MTFA: curve, 50 SMA clock, ATA, alignment matrix | RB 157-259, 1539-1983 | NOT IMPLEMENTED |
| C6 entry outside the zone; C7 SL buffer | RB 294-355, 1992-2156 | NOT IMPLEMENTED (D7 buffers kept as ranges) |
| H3 ITF trend, H4 curve, H5 closing concept, H6 authenticity; RF7 | RB 408-479, 606 | NOT IMPLEMENTED |
| M1-M5 sector, EMA 20, coinciding, exceptional marking, structural target | RB 480-560 | M4 exceptional DL SYNTH-TESTED (row 12); others NOT IMPLEMENTED |
| L1-L3 crossover, RSI/stochastic, gap | RB 561-593 | NOT IMPLEMENTED |
| RF2 inside opposing HTF zone; RF3 trend against | RB 601-602 | NOT IMPLEMENTED |
| RF4 garbage chart | RB 603 | Partly: 6+ bases (row 8); the visual judgement is N/A (human) |
| RF5, RF6, RF9, RF10 emotional, F&O, mental state, scared money | RB 604-609 | N/A (human); RF6 out of scope (long-only CNC, D2) |
| 10 essential pre-trade checks | RB 611-642 | NOT IMPLEMENTED |
| Section 2 Parts B-E: confluence, 15-point table, priority, decision matrix | RB 845-1079 | NOT IMPLEMENTED (D4: pre-entry /14; D6: sector "not evaluated") |
| Entry types, 10-trade limit, alerts, post-trade, order modification | RB 2347-2565 | NOT IMPLEMENTED |
| Special strategies 1-6 (confirmation entry, LOTL, weekly trailing, sector, gap, ATA) | RB 2566-3024 | NOT IMPLEMENTED (D9: no automated trailing stop) |
| Section 7 psychology | RB 3025-3437 | N/A (human) |
| Section 8 development path, journal, watchlist, reviews | RB 3438-4028 | NOT IMPLEMENTED or N/A (human) |

## 4. Confirmed high-severity defects (both fixed; approved as D33-D34; committed in `b7a51cc`)

### H1. Candles on excluded or non-trading sessions were used

- **Rule broken:** D30. Muhurat and shortened sessions are excluded from normal candle construction.
- **Affected path (HEAD `16f17af`):**
  - `mtf_freshness.py` `replay` (as-of cut, then `by_day`);
  - `_build_series` (aggregation);
  - `_overlay` (touch loop over every base candle);
  - `_validate`, which raised `ValueError` for any intraday candle outside 09:15-15:30.
- **Counterexamples:**
  - **Weekly zone, PL 95.2 (calendar mode).** The calendar marks Friday 14 Feb 2025 as `EXCLUDED_MUHURAT`. A daily candle exists for it, with low 95.0.
    - At HEAD, that candle was aggregated into week 2025-W07, so the weekly low became 95.0.
    - It was also counted as a `PL_TOUCH`, so the zone became `TESTED`.
  - **Muhurat-hours intraday candle.** A 75-minute candle from 18:00 to 19:15 crashed the whole replay with `ValueError: base candle 25 lies outside 09:15-15:30`.
  - **No calendar.** A Saturday daily candle was aggregated into the week as an ordinary session.
- **Fix:**
  - `_classify`, added at `mtf_freshness.py:324`, runs after the as-of cut and validation and **before** gap detection and aggregation.
  - Every set-aside candle goes into `MtfSnapshot.excluded_candles` with a classification. Nothing is dropped silently.
- **Classifications and their effect:**

  | Classification | When | Effect on zones |
  |---|---|---|
  | `EXCLUDED_MUHURAT`, `EXCLUDED_SHORTENED` | The calendar's `session_type` says so (D30) | Not aggregated; never a touch. If it reaches a zone's PL or DL after creation, the zone gets manual review `EXCLUDED_SESSION_TOUCH`. It is not `TESTED`, because no approved rule says what such a touch means, and it is not usable as fresh context. |
  | `UNVERIFIED_SESSION` | No calendar, and the candle is weekend-dated or intraday outside 09:15-15:30 | Not aggregated. Every zone whose span from first formation period to as_of contains the date gets status `UNVERIFIED_SESSION` (not fresh). |
  | `OUTSIDE_REGULAR_HOURS` | Calendar says a normal day, but the intraday candle lies outside 09:15-15:30 | Same as `UNVERIFIED_SESSION` (data conflicts with the calendar). |
  | `HOLIDAY`, `WEEKEND`, `NOT_A_TRADING_DAY` | Calendar says closed, yet a candle exists | Same as `UNVERIFIED_SESSION` (data conflicts with the calendar). |

- **Straddling candles:** an intraday candle that straddles 09:15 or 15:30 is still rejected as malformed. Only a candle lying wholly outside the session is classified.
- **Status precedence is now:** INVALIDATED > BASE_CLOSE_BEYOND_DL_PENDING > TESTED > UNVERIFIED_SESSION > UNKNOWN_DATA_GAP > FRESH.
- **Residual limitation:** without a calendar, a **weekday** Muhurat or shortened session whose candle carries regular-session timestamps cannot be told apart from a normal day. Example: an end-of-day row for Friday 1 Nov 2024. Only the `CALENDAR_UNVALIDATED` limitation marks this, which makes B17 a precondition for any real-data use.

### H2. Data gaps inside a zone's formation were ignored

- **Rule broken:** D27. Freshness is never inferred from missing candles.
- **Affected path (HEAD):** `_overlay` checked only gaps with `g.date > created.end.date()`, that is, after the leg-out period.
- **Counterexample (no calendar):** six Mon-Fri weeks forming the weekly DBR, with the base week's Wednesday (22 Jan 2025) missing.
  - The zone was built from an incomplete weekly candle.
  - At HEAD it still reported `FRESH` with `usable_as_fresh_context = True`.
  - The same applies to a gap in the leg-in week or the leg-out week.
- **Fix** (`mtf_freshness.py:561`): gaps count from the first formation period (the leg-in, or the base if there is no leg-in) through as_of.
  - Calendar mode is unchanged: there, a known gap already ends the HTF series (`HTF_SERIES_TRUNCATED_AT_GAP`), so no zone can span it. The new test asserts this too.
- **How expected sessions are determined:**
  - **With a calendar:** `is_trading_day(d)` (`nse_calendar.py`: only NORMAL and NORMAL_SPECIAL days).
  - **Without a calendar:** every weekday is expected, and each missing weekday is an *unverified* gap.
  - **Cannot be classified without a validated calendar:** weekday holidays (they show as unverified gaps), weekday Muhurat or shortened sessions (they look normal), and weekend special sessions (they show as `UNVERIFIED_SESSION`).
- **Consequence of strict no-calendar handling.** I measured this on synthetic data: two years of weekdays with 30 random weekday holidays removed, 5 random series, W and M timeframes.
  - Every untouched demand zone was `UNKNOWN_DATA_GAP` without a calendar, both **before and after** the fix. Holidays after creation already caused this at HEAD.
  - With a calendar, the same zones were `FRESH`. The fix did not change the calendar-mode counts.
  - In practice, **no-calendar mode yields almost no fresh HTF context on real NSE data.** The safeguard is kept as approved, and B17 (calendar) is effectively mandatory.

## 4A. Second-pass review of the H1/H2 fixes

The review re-read the code paths named in the user's checklist:
- classification before aggregation;
- other routes for excluded candles;
- excluded touches;
- every formation and post-formation gap;
- status precedence;
- demand and supply;
- determinism and look-ahead.

| Check | Result |
|---|---|
| Classification precedes all aggregation and freshness | Yes. `replay` order: as-of cut, `_validate`, trailing-incomplete trim, `_classify`, then gaps, `_build_series`, engine, `_overlay`. Excluded candles reach only the excluded-touch loop and the unverified-session check. |
| Other routes for excluded candles | The default `as_of` (latest candle end) may come from an excluded candle. That only moves the cut, never adds data. Validation still sees them, which is correct (malformed input is still refused). No route into formation, invalidation or eligibility was found. |
| Excluded touch always blocks fresh use | Yes (manual review), but the status said `FRESH`: **S2**. |
| Gaps in leg-in, base, leg-out and after | A missing **first session of the leg-in period** was ignored: **S1**. A period with no data at all was stitched over: **S3**. |
| Precedence with several issues | Deterministic, a single if/elif chain. Untouched zones keep every session and gap reason. A tested or invalidated zone does not list gap reasons (it is already not fresh). Tested by `StatusPrecedence`. |
| Demand and supply | Exclusion and touch logic are side-symmetric (`_touches`); tested on both sides for H1 and M3. |
| Determinism and look-ahead | `_classify` is per candle. The prefix-equality and determinism tests still pass, so no look-ahead was introduced. |
| Daily zones | Could not be replayed at all (D over D refused), so they had no gap or session checks: **S4**. |

**Counterexamples found and fixed (each test failed before its fix and passes after; each fix reverted alone is caught):**

| ID | Minimal counterexample | Fix | Test |
|---|---|---|---|
| S1 | No calendar; Monday 13 Jan 2025 (first day of the leg-in week) missing. The weekly leg-in candle starts on Tuesday, so the gap fell before `formation_first_day`: zone `FRESH` | Count from the first **calendar day** of the first formation period (`period_bounds`) | `FormationGaps.test_gap_inside_a_formation_week_is_never_fresh`, now every weekday of all three formation weeks |
| S2 | A calendar-excluded Muhurat candle touches the PL: zone blocked by manual review, but `status == FRESH`. The same applied to `PARTIAL_FIRST_PERIOD` | **P1:** status `MANUAL_REVIEW` for an untouched zone with any manual-review flag | `ExcludedSessions` tests (status asserted) |
| S3 | Calendar mode; the week after the leg-in (a strong up week, 2025-W03) has no data. Joining W02 to W04 fabricated a DBR (`demand-1-2`) that never existed; the engine listed it eligible. Only H2 kept it from fresh use | **P2:** a period with no data ends the series (`HTF_SERIES_TRUNCATED_AT_GAP`), like a partly missing one | `FormationGaps.test_a_whole_missing_period_ends_the_series` |
| S4 | Daily candles with 14 Jan 2025 missing after creation: the bare engine reports the daily zone `ZONE_ELIGIBLE`; `replay(..., "D", htf=("D",))` raised `ValueError` | **P3:** allow D over a daily base | `DailyZones.test_missing_day_after_creation_blocks_a_daily_zone` |
| M3 | Five bases, then a base candle closing above the cluster: silently discarded | D35: `BASE_CLOSED_OUTSIDE_CLUSTER`, manual review, no zone | `BaseCount.test_base_closing_outside_a_full_cluster_needs_manual_review` (demand and supply; nothing fires below the cap) |

**Changed committed assertion (P3, approved as D38):** `InputValidation.test_refuses_bad_inputs` asserted that D over a daily base is refused. Under D38 that call is valid, so the assertion now uses an unknown timeframe (`"4H"`), which is still refused.

**User decisions, 2026-10-27:**
- P1 approved as D36, P2 as D37, P3 as D38.
- The D30 special-session rule is approved provisionally: `NORMAL_SPECIAL` only when official source data verifies a genuine session on regular 09:15-15:30 hours.
- No special session, including the 1 Feb 2025 budget session, has been externally verified.

## 4B. Final review before commit (2026-10-27)

| Check | Result |
|---|---|
| D36 (P1) matches the approval | Yes. `_overlay` status chain; the only flags that reach it are `EXCLUDED_SESSION_TOUCH` and `PARTIAL_FIRST_PERIOD`. |
| D37 (P2) matches the approval | **Not fully.** A wholly missing period **after the last period with data** was not reported: `truncated_at` was None, so the series looked complete up to as-of. The zone itself was still `UNKNOWN_DATA_GAP` under D34. **Fixed:** a `for ... else` at the end of `_build_series` sets `truncated_at` from the first trailing gap. |
| D38 (P3) matches the approval | Yes. `replay` accepts D over D, and daily zones go through `_classify`, gaps, `_build_series` and `_overlay`. |
| Daily zones cannot bypass the overlay | **Inside the orchestrator, yes:** every D assessment gets an overlay state, and `eligible_after_overlay("D")` filters by it. **Outside it, no code prevents** a caller from using `run_engine(...).eligible` directly. That is the documented M4 contract; no consumer exists yet, and enforcing it is a scanner-integration design question. |
| D30 provisional rule matches the approval | Yes in code: a `CONFIRMED` row from a hash-verified source with exactly 09:15-15:30. **Coverage gap:** the unverified-source test used a HOLIDAY row only. **Added:** `test_regular_hours_special_session_needs_a_verified_source`. |
| Missing periods, unresolved gaps or excluded sessions silently giving fresh zones | None found after the fix above. All 15 audit mutations are caught (section 6.2). |

| New test | Proves | At the pre-fix code | After |
|---|---|---|---|
| `FormationGaps.test_a_missing_last_period_is_reported_as_truncation` | A trailing wholly missing expected period is reported as truncation; the zone is not fresh | FAIL (`None != '2025-W08'`) | pass |
| `Provenance.test_regular_hours_special_session_needs_a_verified_source` (`tests/test_nse_calendar.py`) | A regular-hours special session from an unverified source is refused, never `NORMAL_SPECIAL` | pass (guard: the code was already correct) | pass |

## 4C. L4 and L10 remediation (2026-10-27, committed in `bdaa09d`)

Both were approved by the user on 2026-10-27, L10 as option B. Trading eligibility logic is unchanged.

**L4: the serialisation contract.**
- `EngineResult.to_dict()` adds `derived`: the zone ids of `eligible`, `manual_review_zones`, `context_supply` and `fresh_zones`.
- `MtfSnapshot.to_dict()` adds each zone's `usable_as_fresh_context`, and `overlay[tf] = {kept: [ids], blocked: [{zone_id, reasons}]}`, taken from `eligible_after_overlay`.
- `MtfSnapshot.to_json()` writes dates and datetimes as ISO 8601 with sorted keys. `json_default` refuses any other type rather than stringifying it.

**L10 (option B): per-date ambiguity.**
- The calendar declares `UNRESOLVED_ERRORS`. `NseCalendar` declares `(CalendarAmbiguityError,)` only, so missing coverage is still fatal and `test_uncovered_year_stops_the_orchestrator` is unchanged.
- A candle on an ambiguous date is set aside as `CALENDAR_UNRESOLVED`. It is neither a test nor an `EXCLUDED_SESSION_TOUCH`.
- An ambiguous date is never a gap.
- Every period containing one is truncated (`HTF_SERIES_TRUNCATED_AT_UNRESOLVED_CALENDAR`): inside a period with data, between periods, or after the last data.
- Every zone whose formation-to-as-of span contains one is `UNVERIFIED_SESSION`, with the reason `CALENDAR_UNRESOLVED <date>`.
- The snapshot lists `unresolved_calendar_dates` and adds the limitation `CALENDAR_UNRESOLVED_DATES`.
- Any calendar error type that is not declared still stops the replay.

**Applied literally, with noted consequences:**
- A period is truncated even when its ambiguous date lies **after as_of**, or **before the first candle** of the first period. The calendar is static, published information, so this is not look-ahead, but it can withhold a period earlier than strictly necessary.
- Truncation is permanent for the series (L9).

**Tests:**
- L4: `test_serialised_derived_lists_equal_the_properties`, `Serialisation` (3 tests), and the strengthened prefix-equality test (JSON prefix-equal too).
- L10: `UnresolvedCalendarDates` (5 tests: candle, supply mirror, no data, period of only that date including the trailing case, other errors propagate) and `OrchestratorIntegration.test_unresolved_date_is_handled_per_date_by_the_orchestrator`.
- At `b7a51cc` sources, 10 of these fail (errors). The propagation guard passes there by design.

**Mutation checks:** 14 single-fix reversions were run against the full suite (5 for L4, 9 for L10), and **all are caught**.
- The first run left one survivor, L10-i: an ambiguous candle treated as a confirmed exclusion.
- It survived because no fixture's ambiguous candle touched the zone. The code was correct.
- A touching case was added to `test_candle_on_an_ambiguous_date_is_set_aside`, and L10-i is now caught.

## 5. Medium and low findings (status after the second pass)

### Medium
| ID | Finding | Kind |
|---|---|---|
| M1 | A zone whose 3-bar leg-out window is still open reports `INELIGIBLE / CORE_BELOW_7`, with no sign that its score can still change. | Reporting gap |
| M2 | The Zone Engine trusts the caller's `complete=True` flag and has no period clock. An in-progress vendor bar marked complete could create or test zones early. | API-contract risk. **Contract now documented** in `run_engine`: `time` must be the close time, so `as_of` drops unclosed candles. No code guard is possible without a clock. The orchestrator satisfies the contract. A TradingView loader (B10) must convert open-time stamps. |
| M3 | A base candle closing outside a full cluster was silently discarded. | **Resolved by D35** (manual-review event; the Rulebook question stays open) |
| M4 | `EngineResult.eligible` is valid only at the close of the last processed candle and has no data-quality checks. W/M zones touched mid-period stay listed, and the bare engine sees no gaps (S4). | Integration risk. No consumer exists yet. **Contract documented** in `EngineResult.eligible`: candidates come only from `MtfSnapshot.eligible_after_overlay`. With P3 that is now possible for D as well. 75m/125m zones still have no such path (see next row). |
| M4b | 75m/125m execution zones cannot be replayed through the orchestrator (`HTF_ORDER` stops at D), so they have no gap or session checks. | **Open.** Needs an intraday identity period (75m over 75m, or over 25m). This is a design change, proposed rather than made. |
| M5 | Without a calendar, the last period of a data set never completes (A5). Reviewed: it never completes early, base candles in it are still applied as touches, and an as-of beyond the data adds unverified weekday gaps (`UNKNOWN_DATA_GAP`). Conservative, not silent. | Expected limitation; validation needs B17 or data past 2025-12-31 |
| M6 | The Pine reference profile is my re-implementation from reading the code. Every `PINE_*` flag and parity expectation inherits any misreading. | EXT-UNVERIFIED (B10) |

### Low
| ID | Finding |
|---|---|
| L1 | Engine: candles after `as_of` are dropped before validation, so an out-of-order candle beyond as_of is not reported. **Fixed 2026-10-28, uncommitted:** the whole input is validated before the as_of cut. |
| L2 | Engine: zero and negative prices are accepted. **Fixed 2026-10-28, uncommitted:** refused as `ValueError`. |
| L3 | Mixed naive/aware times (or a naive `as_of` with aware candles) raise `TypeError` rather than `ValueError`. **Fixed 2026-10-28, uncommitted:** reported as `ValueError`. Test: `test_input_validation_gaps_from_the_audit`. |
| L4 | `EngineResult.to_dict()` omits the derived eligible and context lists. The snapshot's `to_dict()` also omitted `usable_as_fresh_context` and the overlay result, and was not JSON-serialisable. **Fixed 2026-10-27, committed in `bdaa09d` (section 4C).** |
| L5 | Engine minimum history is 3 candles; zero-base detection needs 4. |
| L6 | `Rules` overrides are not validated; the garbage label says "6+" even under a custom base maximum. |
| L7 | Daily candles are assumed to close at 15:30; the vendor timestamp convention is unknown (B6). |
| L8 | Supply zones' manual-review flags are hidden because their status is `CONTEXT_ONLY`. |
| L9 | In calendar mode, one missing session (now also a whole missing period, P2) ends the HTF series for good. Zones formed after the gap are never seen until the data is repaired. Not silent: `truncated_at` and `HTF_SERIES_TRUNCATED_AT_GAP`. Broad, but the alternative (segmenting the series and restarting the engine) is a design change, proposed only. |
| L10 | A calendar that raises `CalendarCoverageError` or `CalendarAmbiguityError` for any date in the replay range stops the whole replay. Safe (never silent), but coarse. **Fixed 2026-10-27 (option B), committed in `bdaa09d` (section 4C):** ambiguity is handled per date; missing coverage stays fatal. |

## 6. Invariants and adversarial tests

### 6.1 Invariants
| Invariant | Code path | Evidence | Result |
|---|---|---|---|
| A tested demand zone never qualifies | `zone_engine.py` `_assess`; `eligible_after_overlay` | 6,518 random engine zones (D, W, 75m, Q); 100 series replayed at every as-of | Holds (synthetic) |
| An unresolved gap or session never yields fresh | `_overlay` | H2 and H1 tests | **Violated at HEAD; holds after the fix** |
| A supply zone is never a long candidate | `_assess` supply branch | sweep | Holds |
| An invalidated zone never becomes eligible again | `state_step`; overlay stop | as-of sweep | Holds |
| The overlay only removes eligibility | `eligible_after_overlay` | 296 random checks; now also asserted in the monotonic property test | Holds |
| No lookahead | engine as-of filter; `replay` step 1 | prefix-equality test at every cut | Holds |
| Incomplete HTF periods never create or test zones | `_build_series` | completion tests | Holds in the orchestrator; engine depends on the caller (M2) |
| Excluded sessions never enter aggregation | `_classify` | H1 tests | **Violated at HEAD; holds after the fix** |
| No series is stitched across a known gap (calendar mode) | `_build_series` | S3 test | **Violated before P2; holds after** |
| An unresolved flag is never reported `FRESH` | `_overlay` | S2 tests | **Violated before P1; holds after** |

### 6.2 Tests added (`tests/test_mtf_freshness.py`)
| Test | Proves | Does not prove | At HEAD | After fix |
|---|---|---|---|---|
| `ExcludedSessions.test_calendar_excluded_session_is_not_aggregated_or_counted` (demand and supply) | A calendar-excluded day is not in the weekly candle or the touch count; its PL touch yields manual review; it is listed in `excluded_candles`; no gap is invented | That D30 sessions are correctly identified on real circulars (B17) | FAIL (`PL_TOUCH` counted) | pass |
| `ExcludedSessions.test_evening_intraday_candle_is_excluded_not_a_crash` | A Sunday or weekday evening intraday candle is classified, not a crash: `EXCLUDED_MUHURAT` with a calendar, `UNVERIFIED_SESSION` or `OUTSIDE_REGULAR_HOURS` otherwise; zone blocked | Vendor timestamp conventions for Muhurat data | ERROR (`ValueError`) | pass |
| `ExcludedSessions.test_weekend_candle_without_a_calendar_is_unverified` | Without a calendar, a weekend candle is not aggregated and blocks fresh use of zones whose span contains it; the same data without it stays FRESH | Anything about weekday special sessions without a calendar (undetectable) | FAIL (usable as fresh) | pass |
| `FormationGaps.test_gap_inside_a_formation_week_is_never_fresh` (leg-in, base, leg-out) | A missing weekday in any formation week gives `UNKNOWN_DATA_GAP` without a calendar; with one, the series ends at the gap and no zone exists | Gaps before the leg-in (not checked; they do not change the zone's candles) | FAIL x3 (FRESH) | pass |
| `PeriodBoundaries.test_year_end_week_month_and_year_split` | ISO 2025-W01 spans 30 Dec 2024 to 3 Jan 2025; M, Q, HY and Y split at 31 Dec; the next week and month stay in progress | TradingView's own period alignment (B8) | pass (guard) | pass |
| Strengthened `ReplayProperties.test_tested_and_invalidated_are_monotonic` | Overlay-kept zones are a subset of engine-eligible zones and are demand | Behaviour on real price paths | pass | pass |
| `FormationGaps.test_a_whole_missing_period_ends_the_series` (S3) | A no-data period ends the calendar-mode series; without a calendar the stitched zone is `UNKNOWN_DATA_GAP` | That truncation is the best remedy (L9) | FAIL | pass |
| `DailyZones.test_missing_day_after_creation_blocks_a_daily_zone` (S4) | Daily zones replayed over daily data get gap checks in both modes; the bare engine would have listed the zone eligible | 75m/125m zones (M4b) | ERROR | pass |
| `StatusPrecedence.test_several_issues_give_one_status_and_keep_every_reason` | Unverified session outranks a gap and both reasons are kept; a touch on an unverified weekend candle is not trusted | Precedence for tested/invalidated zones with gaps (not reasons-complete by design) | pass (guard) | pass |
| `BaseCount.test_base_closing_outside_a_full_cluster_needs_manual_review` (M3) | Recorded with boundaries, disposition and source; no zone; no garbage label; nothing below the 5-base cap | What the Rulebook intends (open) | FAIL | pass |

**Mutation check:** each part of the fix was reverted on its own and the suite rerun. Every reversion was caught.
- excluded candles kept;
- excluded touch ignored;
- excluded touch ignored on the supply side;
- unverified session ignored;
- gaps after creation only (the HEAD rule);
- gaps from the base instead of the leg-in;
- the out-of-hours check removed.

The last mutation first survived, because the evening test used a Sunday; the test was extended with a weekday evening case and now catches it.

**Second pass (S1-S4 and M3):** each fix was reverted on its own and the suite rerun. Every reversion was caught.
- period-start gap counting;
- `MANUAL_REVIEW` status;
- whole-period truncation;
- D over D;
- the M3 event;
- the M3 event firing below the cap.

All seven first-pass mutations are still caught against the final code.

**Final run (2026-10-27):** 15 mutations, each reverted alone against the **full** suite, all caught.
- the 7 first-pass mutations;
- the 6 second-pass mutations;
- the trailing-gap truncation removed (D37);
- the D30 source-verification check relaxed for special sessions.

### 6.3 Remaining proposed adversarial tests (not added)
Ranked by risk to freshness, invalidation, no-lookahead, period boundaries or the remove-only rule:

1. **Engine fed an in-progress bar marked complete (M2).** A contract test; the contract is now documented in `run_engine`. A test would only restate it.
2. **Two clusters ending on the same bar, plus a zero-base creation on that bar.** Checks that leg-out tracking stays per zone.
3. **Out-of-order candle beyond `as_of` (L1).** Input validation only.
4. **`LEGOUT_WINDOW_OPEN` reporting (M1).** Needs the M1 fix first.
5. **Non-positive prices and mixed time types (L2, L3).**

Dropped as redundant:
- supply mirrors of gap-through and pending-window touch, because they use the same comparison already covered by `SupplyMirror`;
- calendar-only Muhurat reconciliation, already covered in `test_nse_calendar.py`.

## 7. Rulebook vs Pine differences

**Classes:**

| Class | Meaning |
|---|---|
| 1 | Intentional and documented |
| 2 | Required by the Rulebook, not implemented |
| 3 | Ambiguous: manual review |
| 4 | Potential defect |
| 5 | Not verifiable without TradingView |

| Area | Difference | Class |
|---|---|---|
| Pattern detection | Pine treats a close beyond the prior extreme as strong; the Rulebook requires body > 50% (PR1). The Rulebook view wins; Pine-only zones are reported | 1, 5 |
| Achievement | Pine's close-beyond rule is used as the objective minimum (PR3) | 1, 3 |
| Base counting | Maximum raised from 3 to 5 (PR4) | 1 |
| Base counting | Transition candles not counted | 3 |
| Base counting | 6th base closing outside the cluster (M3) | 3 |
| Leg-out counting | Per zone; broken sequence flagged (PR5) | 1, 3 |
| Leg-out counting | Pending zone's failed first leg-out (PR18) | 3 |
| Zero-base | Base score 2.0 from Pine, tagged `ZB-PINE-REF` (D13) | 1 |
| Geometry | Body-to-Wick only; Wick-to-Wick not implemented (PR16) | 2, 3 |
| Freshness | Same touch rule; both counts kept (D25) | 1 |
| Freshness | Pending-window touch flagged (PR10) | 3 |
| Invalidation | Close beyond DL in both | 1, 5 |
| Invalidation | HTF on its own timeframe; base close = manual review (D24) | 1 |
| HTF timing | Overlay tests earlier than Pine (PR8) | 1, 5 |
| HTF timing | Pine creates W/M zones one bar later | 1, 5 |
| Pending window | 1 later bar on chart TFs, 2 on the HTF engine | 1, 5 |
| Candle construction | Calendar periods; 75/125m alignment; drawing limits | 5 |
| Candle construction | Excluded sessions (D30): Pine sees whatever TradingView supplies | 5 |

No class-4 Pine-fidelity defect was found by code reading. H1 and H2 were orchestrator defects, not Pine differences.

## 8. External-validation blockers

| ID | Needs | Blocks |
|---|---|---|
| B17 | Official NSE CMTR circulars (PDFs) and transcribed `events.csv` | Any real-data use of the orchestrator (H1/H2 residuals) |
| B18 | Bhavcopy samples (legacy and UDiFF) to fix the loader format | Daily data |
| B6 | Kite Connect capability verification (not needed for local EOD files) | Broker-sourced data, including intraday |
| B7 | Corporate-action source and adjustment convention | Zone detection across splits/bonuses |
| B8 / B10 | TradingView exports with the indicator; manual zone records | Period alignment and Pine parity (M6) |
| B11 | Point-in-time Nifty 100 membership | Universe history |
| B12 | User-approved backtest execution assumptions (gap fills, same-bar entry/SL, costs, price bands) | Historical validation (backtesting) only |
| B15 | Confirmed intraday history depth for WIT validation | WIT (75m/125m) validation |

## 9. M3: the sixth base candle (unresolved, by user decision)

**Rulebook wording:**
- RB 787: "**6 or more base candles** | **0** | ... This is a **'Garbage Area.'** REJECT."
- RB 800-806: "A 'Garbage Area' is specifically defined as: 6+ overlapping base candles; No clear explosive leg-out breaking free; Price wandering sideways within a messy range; ..."
- RB 814: "IF a chart shows 6+ overlapping base candles without a clear, explosive departure → THEN verbally declare 'Garbage Area' ..."

**Minimal example (daily, synthetic):**
- a leg-in 100 / 101 / 94 / 95 (open / high / low / close);
- five base candles 95 / 96 / 94.5 / 95.3, each inside 94.5-96 with a body of 20%;
- then a sixth candle.

| Sixth candle | Body | Engine today |
|---|---|---|
| A: 95.3 / 96 / 94.6 / 95.5 (inside the cluster) | 14% | `GARBAGE_AREA_6_PLUS_BASES` event and rejection; no zone |
| B: 95.3 / 97 / 94.6 / 96.2 (weak, **closes above** the cluster high 96) | 38% | **No zone, no garbage event, no rejection record**: the cluster is discarded silently |
| C: 95.3 / 99.5 / 95.2 / 99.3 (strong, closes above) | 93% | Leg-out: a 5-base zone (base score 1), via pending |

**Competing interpretations of case B:**
1. **Counts as a 6th base:** it is a base candle by body (≤ 50%), and RB 787 counts base candles. The cluster is a garbage area and is reported as such.
2. **Does not count:** RB 802 requires "overlapping" bases. A candle that closes outside the range does not overlap the cluster in the same way, so the cluster simply ends with 5 bases and no leg-out (no zone, no garbage label).
3. **A weak breakout:** RB 806 and 814 describe "no clear explosive departure". Case B is a non-explosive departure, so the area is garbage under either count. That reading points to interpretation 1's outcome by a different route.

**What is at stake:**
- No zone is created in case B under any interpretation, so eligibility is not affected.
- The difference is the audit trail (a garbage label, and the RB 820 instruction to drop a timeframe) and whether the following candles may start a new cluster.

**Decision (user, 2026-10-26): option (c), recorded as D35.**
- Case B now records the event `BASE_CLOSED_OUTSIDE_CLUSTER`, with a `rejected_patterns` entry of disposition `MANUAL_REVIEW`. The entry carries the cluster start, the candle index, the base count (5), the cluster high and low (96 / 94.5) and the close (96.2).
- It does not use the garbage-area label, and no zone is created.
- Below the 5-base cap, the same candle simply ends the cluster: no event, because nothing is ambiguous there.
- Cases A and C are unchanged.
- The Rulebook question itself remains open.

## 10. Remediation plan and remaining decisions

| Priority | Item | Status |
|---|---|---|
| 1 | H1 session classification and exclusion (D33) | Done; committed in `b7a51cc` |
| 2 | H2 formation-period gaps (D34) | Done; committed in `b7a51cc` |
| 3 | S1-S4 follow-ups: P1 `MANUAL_REVIEW` status, P2 whole-period truncation, P3 D over D | Done; approved 2026-10-27 as D36-D38; committed in `b7a51cc` (D38 changed one committed assertion) |
| 4 | M3 manual-review event (D35) | Done; committed in `b7a51cc` |
| 5 | Decision log (v2.6) and blockers updated | Done |
| 6 | M4b: intraday identity periods so 75m/125m zones get gap and session checks | **Proposed design change**; needed before WIT execution zones are trusted |
| 7 | M1 `LEGOUT_WINDOW_OPEN` | Proposed |
| 8 | Low items | L4 and L10 done 2026-10-27, committed in `bdaa09d`. L1-L3 done 2026-10-28, uncommitted. L5-L9 still proposed. |
| 9 | External validation: B17, then B18, then B7, then B8/B10 | Waiting for the user's files. None of B6, B7, B8, B10, B11, B12, B15, B17 or B18 is resolved. INFY is the provisional control stock, conditional on corporate-action evidence; none is in the repository. |

**Status of the decisions carried over from Step 1 (as of 2026-10-27):**
- **D30 regular-hours special sessions:** approved provisionally. No session is externally verified.
- **`.gitignore` for raw data:** approved; committed in `bdaa09d`.
- **Sample stocks:** INFY is approved as the provisional control stock for 2022-2023, conditional on corporate-action evidence. The rest of the sample list is not decided.
- **Committing Step 1 and the remediation:** done (`d72415f`, `b7a51cc`).
