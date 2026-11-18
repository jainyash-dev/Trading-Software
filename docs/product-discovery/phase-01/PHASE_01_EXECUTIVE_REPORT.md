# Phase 01: data decisions and evidence readiness, executive report

**Dated 2026-11-10. Scope: T-001, T-002, T-005, T-014. Phase D not started.**

## 1. Summary

Phase 01 is **complete as a preparation phase. The underlying data blockers stay open.**
These are two different meanings of "complete":

- **Preparation, done.** Each task has an evidence-based package. Every owner decision is
  identified, with blank decision fields. Test results are recorded as observed.
- **Data readiness, not done.** Membership is uncertified, the four Dhanteras dates are
  UNRESOLVED, three ISIN changes are unevidenced, and no TradingView sample exists. R1
  and R2 stay open, and `DATA_READY` stays false.

Three findings change what the owner should do first:

1. **The Dhanteras evidence is already complete** (T-002).
   - All four official circulars are in the repository and hash-verified. Each states
     that the equity market ran on regular hours, with an evening extension for Gold
     ETFs and SGBs only.
   - The owner's one decision would remove the ED-44 history cut. Today every scan sees
     no candle before 28 Oct 2019.
2. **The NIFTY 100 review is gated by 25 count-exception rows** (T-001).
   - Unless every one of them is accepted, no period is verified.
   - A simulation in scratch storage shows that accepting all 271 rows would verify 177
     of 185 periods. The other 8 need identity evidence or a dummy-seat rule; no review
     decision can verify them.
   - There is no membership at all before 2020-12-31.
3. **Instrument search had two real defects, now fixed** (T-014).
   - It never read ISINs from NSE's `EQUITY_L.csv` (spaced header).
   - It collapsed each symbol to a single ISIN.
   - Search now lists each (symbol, ISIN) separately, and marks a result verified only
     for that exact identity.
   - Scans stay fail-closed for BAJFINANCE, GRASIM and YESBANK across their unevidenced
     ISIN changes.

## 2. Task matrix

| Task | Status | Evidence | Files changed | Tests | Remaining work |
|---|---|---|---|---|---|
| T-001 | **BLOCKED_OWNER_INPUT** (package complete) | 271/271 rows inventoried; 271/271 cited files hash-match; conversion re-run identical; no overlaps or conflicts; full-acceptance simulation (177/185) | New: `T001_NIFTY100_OWNER_REVIEW.md`, `T001_nifty100_owner_worksheet.csv`, `tools/build_t001_worksheet.py`. Canonical universe files unchanged | `risk_instruments` group 130/130 (includes membership) | Owner decisions in `nifty100_review.csv`; dummy-seat rule; pre-2021 decision |
| T-002 | **BLOCKED_OWNER_INPUT** (evidence verified) | 4 circulars read in full, hashes match `sources.csv`; 4 bhavcopies held, hashes match manifest | New: `T002_DHANTERAS_EVIDENCE_REPORT.md`. Calendar unchanged | `data` group 127/127 | Owner chooses option A/B/C (CAL-2); then an authorised calendar edit |
| T-005 | **BLOCKED_EVIDENCE** (protocol ready) | Plan and readiness §6 reviewed against current data; 34-observation matrix; intake checklist | New: `T005_TRADINGVIEW_VALIDATION_PROTOCOL.md`, `T005_tradingview_comparison_worksheet.csv`. Canonical plan and templates unchanged | No comparison possible (no samples) | Owner TradingView exports; engineering comparison driver (T005-G1) |
| T-014 | **PARTIALLY_IMPLEMENTED** | Real-data behaviour matrix before and after; real `instruments.resolve` at the three break dates | Changed: `platform/gtf_platform/integration/reference.py`. New: `platform/tests/test_instrument_search.py` | New tests 8/8; platform suite 37/37 (final run) | L1 historical-symbol marking, L2 ISIN not carried to the scan, L5 browser check |

A recommendation is not owner approval. No task is COMPLETE_VERIFIED.

## 3. Objective and scope

The objective was to establish what is verified, what needs owner input, what evidence is
missing and what must stay blocked, for T-001, T-002, T-005 and T-014. Out of scope and
not touched:
- Phase D;
- live quotes, broker, paper trading, WIT, LLM assistant, parse cache;
- qualification logic;
- `nse/sources/`;
- the Rulebook.

## 4. Work performed and files inspected

- **Baseline** (read-only first):
  - branch `main`, HEAD `9e302df1a81c2b13696d8fab61f05d377481be2e`;
  - nothing staged; 79 modified and 38 untracked entries; no deleted or renamed files;
  - the full status was saved to the session scratchpad.
- **Universe:**
  - every CSV and JSON in `nse/data/universe/`, its README and `evidence/sources.csv`;
  - `nse/research/membership.py` (conversion and review gate);
  - the conversion re-run in memory.
- **Calendar:**
  - `nse/data/calendar/` README, `events.csv` and `sources.csv`;
  - the four circular PDFs, read in full;
  - `nse/calendar/nse_calendar.py` event types;
  - D54, ED-31, ED-42, ED-43, ED-44;
  - the four bhavcopies and `nse/data/eod/manifest.csv`.
- **Validation:**
  - `REFERENCE_VALIDATION_PLAN.md`, `REAL_DATA_READINESS.md` §6;
  - `nse/data/reference/` templates and README;
  - `nse/eod/nse_reference.py`, `nse/research/refcheck.py`, `run_all.check_reference`;
  - `IMPLEMENTATION_BLOCKERS.md` (B8/B10/B17);
  - INFY corporate actions.
- **Identity:**
  - `platform/gtf_platform/integration/reference.py`, `routes.py`, `config.py` defaults,
    `integration/research.py` (scan wiring);
  - `instrument_records.csv`, `identity_report.json`, `EQUITY_L.csv`;
  - the web `InstrumentFinder` / `InstrumentSearch` and their Scanner and Watchlists callers;
  - `tests/test_research_instruments.py`.

## 5. Files changed

| File | Kind | Note |
|---|---|---|
| `platform/gtf_platform/integration/reference.py` | Modified (untracked owner file, fully read first) | T-014 fix only: header whitespace; one row per (symbol, ISIN); verification per (symbol, ISIN) |
| `platform/tests/test_instrument_search.py` | New | 8 synthetic tests |
| `docs/product-discovery/phase-01/*` | New | 8 reports, 2 worksheets, 1 read-only generator |

Nothing else was written. In particular, none of these changed:
- `nse/`;
- `nse/data/` (universe, calendar, EOD);
- `tests/`;
- the canonical plan and templates;
- the protected sources (hashes re-checked).

## 6. Owner decisions required

See [PHASE_01_OWNER_ACTIONS.md](PHASE_01_OWNER_ACTIONS.md):

1. CAL-2 option.
2. 271 review rows, the 25 exceptions first.
3. Dummy-seat representation.
4. The pre-2021 universe.
5. ED-37 identity evidence.
6. TradingView samples.

## 7. Remaining blockers and readiness impact

Full list: [PHASE_01_BLOCKERS.md](PHASE_01_BLOCKERS.md).

| Gate | Status |
|---|---|
| R1 Data ready | OPEN |
| R2 Research ready | OPEN |
| R3 Application ready | NOT MET |
| R4 Strategy validated | NOT STARTED |
| R5 Operationally ready | NOT STARTED |

No gate was closed, no readiness flag changed, and `DATA_READY` is false.

## 8. Tests

See [PHASE_01_TEST_REPORT.md](PHASE_01_TEST_REPORT.md). In short, the full suite had 2
failures before Phase 01 and has the same 2 after. Both are in pre-existing owner files.
Phase 01 added 8 passing platform tests, and the platform suite passes 37/37. Another
writer edited `platform/` during the session; that briefly broke the OpenAPI snapshot
test until they regenerated the snapshot.

## 9. Recommendation for Phase 02

**Can start safely now (engineering; needs no owner data):**
1. The TradingView comparison driver (T005-G1), with tests, so the first exports can be
   compared on arrival.
2. Search result clarity (T014-L1/L2): return `record_type` / `effective_from`, and show
   "identity resolved at the scan date" in the UI. Add a browser check.
3. Fix the two pre-existing `run_all` failures, if the owner authorises edits to those files.

**Must wait for the owner:**
- the CAL-2 calendar edit;
- any change to `nifty100_review.csv`;
- any identity join.

Any backtest or performance figure must also wait: master prompt section 13; R1 is open.
