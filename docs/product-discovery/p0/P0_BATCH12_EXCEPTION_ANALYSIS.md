# P0 Batch 12 - Price, calendar and exception analysis

**Date:** 2026-11-15
**Batch status:** COMPLETE_WITH_ISSUES. Every listed exception was investigated. All stay fail-closed. Resolutions that change gate outcomes need owner decisions or an approved engineering change.
**Inputs:** fresh isolated build `build_A` (builder 1.6.0; byte-identical to `nse/output/p0_isolated_2026-11-15/` data outputs; see `P0_BATCH13_ENGINEERING_READINESS.md`), held bhavcopies, saved NSE CA API bodies, parser `nse/research/corporate_actions.py`.
**Changes made:** none to prices, records, parser or rules.

## 1. Price-continuity gate, 1.6.0 (verified counts)

| Value | Member-dates |
|---|---|
| CONTINUOUS | 122,646 |
| PREVCLOSE_BREAK_ACROSS_EXCLUDED_SESSION | 700 |
| NO_EQ_ROW | 383 |
| PRICE_SCALE_EVENT_ON_STEP (BONUS 15, SPLIT 10, DEMERGER 5, RIGHTS 4, UNPARSED 3, BONUS+SPLIT 2) | 39 |
| PRIOR_SESSION_NON_EQ | 4 |
| ISIN_CHANGE_ON_STEP | 3 |
| STEP_ACROSS_EXCLUDED_SESSION | 2 |
| UNEXPLAINED_PRICE_SCALE_GAP | 1 |
| **Total** | **123,778** |

## 2. Parser capability (the core Batch 12 question)

Facts (code read):
- `_part_row` emits BONUS as `(b, a+b)`, so non-unit integer ratios such as 2:3 already exist in `actions.csv`.
- The face-value branch emits SPLIT/CONSOLIDATION **only when the factor is a whole number** (`abs(r - round(r)) < 1e-9`). Otherwise the part falls through to `UNPARSED_PRICE_ACTION`.
- `load()` stores ratios as floats; nothing outside `corporate_actions.py` reads `ratio_from`/`ratio_to` (searched `nse/`). OHLC is never adjusted (R-12 keeps raw prices). The ratio is used only for classification and reconciliation keys (`event_key`).

### 2.1 Unparsed events

| Event | Saved subject | Bhavcopy step (held) | Parser outcome | Kind of gap | Recommendation |
|---|---|---|---|---|---|
| **VBL 2024-09-12** (in window) | "Face Value Split (Sub-Division) - From Rs 5/- Per Share To Rs 2/- Per Share" | 1,569.15 -> 645.60 (old ISIN `INE200M01021` -> new `INE200M01039`); consistent with factor 2.5 | UNPARSED | **Engineering**: terms present, ratio 5/2 not whole | ENG-1 below |
| **BRITANNIA 2021-05-25** (in window) | "Scheme Of Arangement- Bonus - 1 Debenture For 1 Equity Share Held" (plus a Rs 12.50 dividend part) | 3,379.10 -> close 3,439.50; no scale step | UNPARSED | **Classification**: distribution of a debt security, not a share ratio | OWN-1 below |
| **TVSMOTOR 2025-08-25** (in window) | "Scheme Of Arrangement - Bonus Ncrps 4:1" | 3,294.60 -> 3,284.70; no scale step | UNPARSED | **Classification**: bonus non-convertible redeemable preference shares; "4:1" is not an equity share ratio | OWN-1 below |
| **CGPOWER 2016-03-15** (pre-window) | " Scheme Of Arrangement" | not examined (before D59 window) | UNPARSED | **Evidence**: no terms anywhere held | Needs scheme terms (issuer scheme document or NSE circular); acquisition needs authorization. Affects pre-2020-12-31 continuity only |

**ENG-1 (engineering recommendation, not implemented):** in `_part_row`'s face-value branch, represent a non-integer factor as a reduced integer fraction, for example `fractions.Fraction(old) / Fraction(new)` = 5/2 -> `("SPLIT", 2, 5)`, matching the existing BONUS convention (`ratio_from:ratio_to` is old:new share count). Guard against floating-point face values by parsing the decimal text with `Fraction(str)`. Tests: VBL subject -> `SPLIT 2:5`; the ten-unparsed-subjects regression (`test_the_ten_unparsed_subjects_do_not_become_ratios`) must be reviewed. VBL's subject is one of those ten, so that test's expectation changes, which needs an ED entry and review, not a silent update. Effect on outputs: VBL 2024-09-12 moves from `PRICE_SCALE_EVENT_ON_STEP:UNPARSED_PRICE_EVENT` / `UNPARSED_EVENT` to `...:SPLIT`. **No member-date certifies as a result**, because D66 completeness is still unproved. Category: engineering (ED), reversible, no rule change.

**OWN-1 (owner decision):** whether a scheme distributing a non-equity security (debentures, NCRPS) without an equity share-count change is (a) a non-price-scale event like a dividend under R-12, or (b) stays an unparsed price event. This is classification policy, so it is owner-reserved. The bhavcopy steps above show no scale break, but a value distribution still moves price by the instrument's value (BRITANNIA's debenture had a face value; not quantified here). Default: stays UNPARSED (fail-closed).

## 3. Exceptions

| ID | Original problem (re-verified) | Evidence | Technical or owner | Proposed resolution | Status |
|---|---|---|---|---|---|
| OD-PX-2 | CGPOWER and VBL unparsed | Section 2.1 | VBL: technical (ENG-1). CGPOWER: evidence | ENG-1 for VBL; CGPOWER terms need authorized acquisition | OPEN, fail-closed |
| OD-PX-3 | ADANIENSOL 2024-11-21 is the only `UNEXPLAINED_PRICE_SCALE_GAP` (confirmed from the 1.6.0 matrix) | Bhavcopy (held): prev 871.55, open = low = close = 697.25 = 0.8000 x prev, i.e. the 20% lower band. Previous session 2024-11-19 (2024-11-20 not a session). No corporate action in saved data | Owner: a reviewed market-move exception mechanism does not exist | If wanted: an owner rule naming the evidence required (price band hit, no CA record, PREVCLOSE intact). Not a corporate action, so it would not touch D66 | OPEN, fail-closed (1 member-date) |
| OD-PX-4 | 700 member-dates fail after a held Muhurat/shortened session | 1.6.0 matrix: 2021-11-08 (99), 2022-10-25 (100), 2023-11-13 (101), 2024-03-04 (100), 2024-05-21 (100), 2024-11-04 (100), 2025-10-23 (100) = 700 | Owner (widens a pass condition) | Adopt/decline. Even if adopted, all 700 still fail the CA gate | OPEN |
| OD-MEM-2/3 | Five dummy seats, no instrument record | 123 member-dates: NO_EQ_ROW 123, CA MISSING_COVERAGE 123; DUMMYREL 21, DUMMYSIEMS 49, DUMMYTATAM 18, DUMMYHDLVR 18, DUMMYITC 17 | Owner (accounting rule) | Keep non-tradable; never invent an ISIN. Optional rule for full-index counting only | OPEN, excluded |
| TV-1 | TradingView parity not established | `docs/product-discovery/phase-01/T005_tradingview_comparison_worksheet.csv`: 34 rows, `tradingview_observed` and `result` blank on 34/34 (re-counted) | External evidence | Owner supplies TradingView exports listed in `P0_TRADINGVIEW_VALIDATION_STATUS.md`. No Yahoo or other substitute | PENDING_EXTERNAL_EVIDENCE. Does not block P0 data gates |
| B11-P | No symbol/ISIN constituent baseline before 2020-12-31 | `IndexInclExcl.xls` name-only (prior registers) | Evidence | Official dated constituent list, or keep D59 | OPEN; D59 window kept |
| CGPOWER 2016-03-15 | see OD-PX-2 | - | - | - | OPEN |
| VBL 2024-09-12 | see OD-PX-2 / ENG-1 | - | - | - | OPEN |

Not in the original list but found: BRITANNIA 2021-05-25 and TVSMOTOR 2025-08-25 are the other two in-window UNPARSED events (OWN-1).

## 4. Calendar

Gate values in the 1.6.0 build: `TRADING_DAY` 123,778 of 123,778; `calendar_unresolved_dates_in_window` empty. Muhurat/shortened-session handling is OD-PX-4 above. Archives held on non-sessions (7 dates, listed in the summary) are not treated as sessions.

## 5. Additional source investigation: NSE capital-market (Listing) circulars

Question: do NSE CM corporate-action circulars give cash-equity evidence beyond F&O?

| Finding | Grade |
|---|---|
| NSE Listing department issues "Change in ISIN" circulars (`NSE/CML/<n>`) for events that change the ISIN (sub-division, consolidation). NSE/CML/35870 (2017) states the code-change date (record date) and that the new ISIN applies to trades from the ex-date | Verified (document text read; public archive; not held) |
| These circulars are issued by the Listing department to all members, not by the F&O department, so in principle they are not limited to F&O symbols | Inference (Sutlej Textiles' F&O status was not checked) |
| Bonus issues normally keep the ISIN (NSDL issuer page, per search excerpt: bonus shares should get "the same ISIN"), so bonuses would **not** get a Change-in-ISIN circular | Documented (excerpt); not verified for NSE circulars |
| NSE Listing also issues listing circulars for new securities (for example JIOFIN, NSE/CML/58021); whether every bonus allotment gets a "listing of further shares" circular is unknown | Unverified |
| No NSE CM circular series was found that announces every ex-date for cash equity | Searched; not found |

Assessment: NSE CML circulars are a second NSE channel for **ISIN-changing** events only. They do not give complete cash-equity coverage, and they are the same institution as FAOP (not independent of each other). F&O adjustment circulars are not complete cash-equity coverage either. CDSL content is still unverified; CDSL is **not** claimed as Source B.

## 6. Engineering recommendations summary

| ID | Recommendation | Type | Changes certification count? |
|---|---|---|---|
| ENG-1 | Fractional face-value ratios as reduced integer fractions | ED (engineering) | No (D66 still blocks) |
| ENG-2 | Regenerate `P0_MEMBERSHIP_BACKLOG.csv` text per row (Batch 11 section 3) | Docs | No |
| ENG-3 | Add `provider` and `upstream_chain` to the future CA source ledger; review rejects shared-publisher pairs (Batch 7 F-1) | Process | No |
| OWN-1 | Classification of non-equity security distributions | Owner | No |
