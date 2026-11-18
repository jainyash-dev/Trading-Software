# Phase 01: blockers after the phase

**Dated 2026-11-10.** Status words: OPEN (nothing changed), NARROWED (better evidence or a
clearer decision, still open), FIXED (closed with evidence).

| ID | Blocker | Status after Phase 01 | What changed | What closes it | Who |
|---|---|---|---|---|---|
| B11-R | NIFTY 100 point-in-time membership not certified (271 rows undecided, 185 periods unverified) | **OPEN, NARROWED** | Review package and worksheet. Every cited file is hash-checked (271/271). A simulation shows full acceptance would verify 177 of 185 periods, with 8 left by identity findings | Owner decisions in `nifty100_review.csv`, the 25 count exceptions first | Owner |
| B11-R2 | No membership before 2020-12-31 | **OPEN** (newly stated) | Documented: 2016-2020 bhavcopies are held, but no universe exists for them | An official dated list for an earlier baseline, or an owner decision to limit research to 2021 onwards | Owner |
| B11-I | Dummy spin-off seats have no identity record (5) | **OPEN** | These 5 periods cannot be verified by review | Owner rule for representing dummy seats | Owner |
| CAL-2 (D54) | Four Dhanteras dates UNRESOLVED; ED-44 cuts all history before 2019-10-28 | **CLOSED (D58, 2026-11-10)** | Owner approved option A. The four rows are CONFIRMED (NORMAL_SPECIAL); tests updated; a real scan replays from 2016 with no cut | n/a | n/a |
| ED-37 | BAJFINANCE 2016-09-09, GRASIM 2016-10-07, YESBANK 2020-03-16: ISIN changes without official evidence | **OPEN** | Fail-closed resolution confirmed on real records. GRASIM and YESBANK are DATA_INSUFFICIENT for every current scan | Official documents dating each new ISIN and its price scale | Owner / evidence |
| B8 / B10 / B17 | No TradingView observation; engine not externally validated | **OPEN** | Protocol updated to 2016-2025 coverage; 34-row worksheet; intake checklist | Owner TradingView exports, then the comparison | Owner |
| T005-G1 | No driver that replays with the official calendar (Q/HY/Y) and runs `compare_zones` / `compare_trend` on real data | **OPEN** (newly stated) | Identified | A tested comparison command (Phase 02 engineering) | Engineering |
| T014-D1/D2 | Instrument search ignored EQUITY_L ISINs; merged ISINs per symbol; verified per symbol | **FIXED** | `reference.py` fix + 8 tests | n/a | n/a |
| T014-L1/L2 | Historical symbols not marked; chosen ISIN not carried into the scan | **OPEN** | Documented; fail-closed in `nse` | UI and API change (Phase 02) | Engineering |
| RA-1 | `run_all` fails: em-dash rule in `docs/product-discovery/08_PRIORITISED_IMPLEMENTATION_ROADMAP.md` (owner file) | **OPEN, pre-existing** | Seen in the baseline; not caused by Phase 01. Phase 01 files contain no em dash | Owner edits the file, or the rule's exemptions | Owner |
| RA-2 | `run_all` fails: architecture rule A2, `nse/research/backtest.py:909` imports `run_manifest` (owner change) | **OPEN, pre-existing** | Seen in the baseline; not caused by Phase 01 | Move the import or record an approved exception | Owner / engineering |
| PL-1 | Platform OpenAPI snapshot test failed mid-session (`include_fixtures` parameter) | **FIXED by another writer** | Caused by concurrent edits to `routes.py`; the snapshot was regenerated at 12:03:25 by that writer. Final platform run 37/37 | n/a | n/a |

## Release gates (reassessed; none closed)

| Gate | Status | Reason |
|---|---|---|
| R1 Data ready | **OPEN** | B11-R, B11-R2, CAL-2 and ED-37 are open. `DATA_READY` stays false |
| R2 Research ready | **OPEN** | No external validation (B8/B10/B17); no comparison driver |
| R3 Application ready | **NOT MET** | Backend tests only; the browser was not exercised |
| R4 Strategy validated | **NOT STARTED** | No real-data performance study. None is claimed |
| R5 Operationally ready | **NOT STARTED** | No operational verification in this phase |
