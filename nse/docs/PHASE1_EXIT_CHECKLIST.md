# Phase 1 Exit Checklist and Acceptance Matrix

**Status: DRAFT [PROPOSED], 2026-10-28.** No written Phase 1 acceptance criteria existed;
this matrix assembles them from the existing documents and the user's scope decisions
below. It adds no trading rule. It is not accepted until the user accepts it (row 22).

**Project status:** Phase 1 in progress; external validation pending. **Phase 1 is not
complete:** rows marked "Blocks acceptance: Yes" and not DONE are unresolved.

## 1. Scope

**User decisions, 2026-10-28:**
1. Scanner-level trend, location, conflict, eligibility pipeline and the 2:1 R:R pipeline
   (spec §6-§8) are **out of Phase 1**. No scanner work is started.
2. **No intraday (75/125-minute) outputs** until the session and gap design (audit M4b)
   is explicitly approved.
3. This checklist is a draft, not automatic acceptance.
4. The Rulebook and Pine Script are not changed.
5. Raw evidence stays out of git (D31); clean-checkout tests are not made to pass by
   changing that policy.

**Update 2026-10-29:** the user's `CLAUDE.md` asks for the full scanner and G0-G8. They
are built in `nse/research/` as post-Phase-1 work (`RESEARCH_PIPELINE.md`; D41 `PROPOSED`).
This changes nothing below: Phase 1 acceptance still covers only the scope above, the
scanner rows stay out of Phase 1, and intraday output stays blocked (decision 2). The test
counts in section 3 are those of 2026-10-28. The current counts come from
`python3 -m nse.validation.run_all`.

Phase 1 therefore covers zone detection, core scoring (/7), freshness, invalidation and
zone-level eligibility on completed candles, the HTF freshness overlay (B16), and their
external validation in the order B17, B18, B7, B8/B10 (audit §10 row 9) over the D29
window, with INFY as the provisional control stock. Passing tests show implementation
behaviour only; nothing here measures or claims strategy performance.

## 2. Acceptance matrix

Status: **DONE**, **OPEN (external evidence)**, **OPEN (user decision)**, **DEFERRED**
(out of Phase 1 by user decision).

| # | Criterion | Status | Evidence | Remaining action | Blocks acceptance |
|---|---|---|---|---|---|
| 1 | Zone detection, core /7, freshness, invalidation (audit §3.1 rows 1-31) | DONE (synthetic) | `tests/test_zone_engine.py`; audit §3.1 | Rows 13 (Wick-to-Wick) and 31 (drop a timeframe in a 6+ base mess) are NOT IMPLEMENTED; see row 20 | No, if row 20 defers them |
| 2 | Tested, invalidated, supply or flagged zones never eligible (D3) | DONE | `test_no_tested_invalidated_supply_or_flagged_zone_is_ever_eligible`; audit §5 sweeps | - | No |
| 3 | Candidates only from `eligible_after_overlay` (audit M4) | DONE | `tests/test_repo.py` `test_nse_code_keeps_the_phase1_safety_boundaries` | - | No |
| 4 | No broker, network or order code (D10, D17, D31, D32) | DONE | same test | - | No |
| 5 | HTF overlay: sessions, gaps, per-date ambiguity (D24-D28, D30, D33-D39) | DONE (synthetic) | `tests/test_mtf_freshness.py`; commits `b7a51cc`, `bdaa09d` | - | No |
| 6 | Engine input validation (audit L1-L3) | DONE, uncommitted | `test_input_validation_gaps_from_the_audit` | Commit (row 21) | Yes, until committed |
| 7 | Official calendar circulars for 2021-2025 (B17, D29, D30) | DONE, uncommitted | `nse/data/calendar/sources.csv` (19 sources, every hash, reference, date and title checked against its file 2026-10-28); `events.csv` (105 events); `tests/test_nse_calendar_data.py` (independent re-transcription) | Commit (row 21) | Yes, until committed |
| 8 | 2023 Bakri Id | DONE, uncommitted | NSE/CMTR/57285 (ZIP as served): 28 June normal, 29 June holiday; `test_amendments_add_and_move_holidays`, `test_bakri_id_2023_follows_the_amendment` | Commit (row 21) | Yes, until committed |
| 9 | Facts vs inferred hours | DONE | Every event date and time checked against its own source's text: only the 20 Jan 2024 hours (09:15-15:30) are not printed by NSE/MSD/60340 and come from NSE/CMTR/41180; `test_hours_not_printed_by_their_own_source_are_marked` | User accepts or rejects the inference (row 18) | Yes (via row 18) |
| 10 | Muhurat and shortened sessions excluded (D30) | DONE | 5 Muhurat and 2 DR-switch sessions; `test_muhurat_inside_regular_clock_hours_is_still_excluded`, `test_disaster_recovery_session_is_excluded_as_shortened` | - | No |
| 11 | Normal cash-market hours 09:15-15:30 | OPEN (external evidence) | NSE/CMTR/41180 (2019, effective 3 Jun 2019); NSE/CMTR/65729 (2024, "standard market timings") | Systematic review of NSE timing circulars, June 2019 to December 2025 | Yes |
| 12 | Calendar reconciled with official EOD files | OPEN (external evidence) | Q1 2022 clean (61 files); 2023-12-29 normal | EOD files for the rest of 2021-2025 (download needs user approval); UDiFF format sample for dates after the legacy-to-UDiFF switch (B18) | Yes |
| 13 | EOD format and provenance (B18) | DONE for the legacy files held | Strict loader accepts all 62 archives; 126 manifest records match 64 files by size and SHA-256 | Format continuity for the rest of 2022-2023; UDiFF (see row 12) | Yes, with row 12 |
| 14 | Real-data pipeline | DONE for INFY Q1 2022, uncommitted | `tests/test_nse_replay.py` `RealInfyQ1Of2022`: no gap; 61/61 daily rows match the Yahoo Finance reference; W/M holiday-period candles match recomputed aggregates | Yahoo republishes exchange data: not independent (rows 15-17) | No (independent checks are rows 15-17) |
| 15 | TradingView calendar and HTF spot checks (B17, B8, D23) | OPEN (external evidence) | none recorded | Record the checks in §4 | Yes |
| 16 | HTF candle values against TradingView (B8; spec §10.2 case 13) | OPEN (external evidence) | none recorded | Recorded W/M/Q/HY/Y boundary and OHLC comparisons for INFY | Yes |
| 17 | Pine parity references (B10; spec §10.2 cases 1-10, 12) | OPEN (external evidence) | none recorded | Recorded indicator outputs on D/W/M charts; case 11 (75/125 alignment) is deferred with row 19 | Yes |
| 18 | D40 (calendar decisions) | OPEN (user decision) | `DECISION_LOG.md` D40, status `PROPOSED` | Review its wording, the two schema changes (`downloaded_on=UNKNOWN`; empty `source_ref` only on `UNRESOLVED` rows, unused today) and the 20 Jan 2024 inferred hours | Yes |
| 19 | 75/125-minute session and gap overlay (audit M4b; spec §10.2 case 11) | DEFERRED (user decision 2) | no intraday output exists | Approve a design before any intraday output | No |
| 20 | Audit proposals M1, L5-L9; audit rows 13 and 31 | OPEN (user decision) | audit §3.1, §5; M1 has a report-only label since 2026-10-29 (`LEGOUT_WINDOW_OPEN`; engine unchanged) | Accept or defer each (`DECISION_REGISTER.md` §2) | Yes, until decided |
| 21 | Commit of the working tree | OPEN (user decision) | `git status`: calendar tables, docs, engine fix, tests, manifest Q1 rows, replay/reference code | Explicit-path commit after authorisation | Yes |
| 22 | Acceptance of this checklist | OPEN (user decision) | this document | Accept, or amend and accept | Yes |
| 23 | Corporate actions (B7) | OPEN (external evidence) | none | Adjustment source and convention; INFY corporate actions 2021-2025 (INFY is the control stock only on this condition) | Yes |
| 24 | Acceptance run on the committed tree with evidence present | OPEN | Local working-tree runs only (§3) | After row 21: re-run in acceptance mode on the committed tree, with the git-ignored evidence present | Yes |

Scanner-level items (spec §6-§8, including RF8 and R:R >= 2) are DEFERRED by user
decision 1 and do not block Phase 1.

## 3. What each test result proves (measured 2026-10-28)

| Run | Result | Proves | Does not prove |
|---|---|---|---|
| Full suite, local working tree | 514 run; 514 passed; 0 failed, 0 errors, 0 skipped | Every test, including the 17 real-data tests, passes on this machine with the git-ignored evidence present | That the result reproduces from git: the evidence is not in git and the tree is not committed |
| Same, `NSE_PHASE1_ACCEPTANCE=1` | 514 run; 514 passed | None of the real-data tests skipped on this machine | Same limit as above |
| Clean export (tracked and untracked non-ignored files of the working tree, no ignored evidence) | 497 entries: 493 passed, 4 class-level skips (17 tests not run), 0 failed, 0 errors | Every test that needs no local evidence passes; each missing prerequisite is named (`PREREQUISITE MISSING: ...`) instead of hidden | Anything about the 17 real-data tests. It is not a fresh git checkout: it includes uncommitted and untracked files |
| Clean export, `NSE_PHASE1_ACCEPTANCE=1` | 493 passed, 4 errors | Acceptance mode refuses to pass without the evidence | - |
| Circulars present, committed (`e470519`) manifest | Q1 reconciliation test skipped: "manifest.csv lists 1 of the 61 Q1 2022 EOD archives"; in acceptance mode it fails with the same message | A checkout without the Q1 manifest rows reports a missing data prerequisite instead of 60 false "missing session" dates | That Q1 reconciles: that needs the 61 manifest rows (row 21) |

No fresh-checkout run of the final state exists yet. It requires the commit (row 21)
and, by design (D31), a copy of the git-ignored evidence: the 19 circular files in
`nse/data/calendar/circulars/`, the 64 EOD files in `nse/data/eod/raw/`, matching
`sources.csv` and `manifest.csv` by SHA-256.

## 4. TradingView checks still to record (rows 15-16)

Symbol `NSE:INFY`, timezone Asia/Kolkata, regular session only. Record the dividend and
split adjustment settings, and save each screenshot with its SHA-256.

| Date | Calendar says | Check |
|---|---|---|
| 26 Jan, 1 Mar, 18 Mar 2022 | HOLIDAY | No daily bar; that week has 4 sessions |
| 31 Mar 2022 | NORMAL | Bar present; month and quarter close on it |
| 24 Oct 2022 | Muhurat, excluded | Record whether TradingView shows a bar, and its OHLC |
| 26 Oct 2022 | HOLIDAY | No bar; our week 24-28 Oct is built from 25, 27 and 28 Oct only |
| 28 / 29 Jun 2023 | NORMAL / HOLIDAY | Bar on 28 June, none on 29 June |
| 20 Jan 2024, 1 Feb 2025 | NORMAL_SPECIAL | Saturday bar present |
| 2 Mar, 18 May 2024 | Shortened, excluded | Record whether a bar exists |
