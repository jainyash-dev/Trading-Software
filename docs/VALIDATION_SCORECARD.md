# Validation scorecard

> Baseline and current results of the repository's own checks. Software tests establish
> the behaviour they cover; they are not external validation and say nothing about
> profitability. Capability readiness: `python3 -m nse.research.cli readiness`.
> Update this file after each milestone from an actual `run_all` report.

## 1. Results

| Check | Baseline (MP0 start, 2026-11-08) | After MP0 (2026-11-09) | After MP1 (2026-11-09) |
|---|---|---|---|
| `python3 -m nse.validation.run_all` (Python 3.12.7, Anaconda) | PASS, 1,084 tests in 22 groups, 0 failures, 0 skipped | PASS, 1,131 tests in 23 groups, 0 failures, 0 skipped | PASS, 1,218 tests in 23 groups, 0 failures, 0 skipped |
| Same command on Python 3.10.20 (`/usr/local/bin/python3.10`) | not run | PASS, 1,131 tests | PASS, 1,218 tests |
| `python3 -m pytest -q` (pytest 7.4.4) | passed (count not recorded) | 1,131 passed | 1,218 passed |
| `local_data` (calendar circulars hash-verified, EOD archives vs manifest) | PASS | PASS | PASS (22 calendar sources incl. 3 new) |
| `reference_comparison` (INFY OHLC reference vs replayed bhavcopies) | PASS | PASS | PASS |
| `static_lint` (ruff 0.17.4, rules F and E9) | did not exist; pyflakes found 16 unused imports | PASS, 0 findings | PASS, 0 findings |
| `python3 -m nse.validation.architecture` (A1-A10) | did not exist | PASS, 48 modules, 0 violations | PASS, 49 modules, 0 violations |
| `python3 -m nse.validation.docs_health` | did not exist | PASS, 0 findings | PASS, 0 findings |
| Protected hashes (Pine, Rulebook Markdown, Rulebook PDF) | match pins | match pins (unchanged) | match pins (unchanged) |
| `git diff --check` | clean | clean | clean |

New tests in MP0: `tests/test_architecture.py` (28), `tests/test_research_run_manifest.py`
(13), and additions to `test_validation_runner`, `test_claude_hooks`, `test_repo`,
`test_research_backtest`. No existing assertion was removed or weakened; the changed
expectations are listed in `docs/MILESTONE_STATUS.md` section 2.

New tests in MP1: `tests/test_nse_eod_evidence.py` (26; 6 use the official samples),
`tests/test_research_membership.py` (35, synthetic), and additions to
`test_research_instruments` (+14), `test_research_acquisition` (+7),
`test_research_eod_coverage` (+4) and `test_nse_calendar_data` (+1). Changed expectations,
each cited:
- synthetic legacy fixtures dated 2025 moved back 364 days (ED-20);
- the UDiFF-under-a-legacy-name reason changed from FORMAT_UNVERIFIED_B18 to PARSE_FAILED, still quarantined (ED-20);
- the UDiFF-like stub is REFUSED rather than NOT_LOADED (ED-20).

No assertion was removed. Independent QA checked that the fixture shifts kept their meaning.

### After the owner decisions D47-D51 (2026-11-09, same day)

| Check | Result |
|---|---|
| `python3 -m nse.validation.run_all` | **PASS**, 1,245 tests, 0 failures, 0 skipped. The run takes about 6 min 40 s, because the real-data checks now read all 1,233 archives (TD-17) |
| `local_data`, `reference_comparison`, `static_lint` | PASS, PASS, PASS |
| `python3 -m nse.validation.architecture` | PASS, 49 modules, 0 violations |
| `python3 -m nse.validation.docs_health` | PASS, 0 findings |
| Protected hashes | unchanged |
| `git diff --check` | clean |
| Real-data scan, 2025-12-26, INFY / RELIANCE / ETERNAL / TMPV / BAJFINANCE with `--instruments` | ETERNAL and TMPV histories joined through verified ISIN continuity; BAJFINANCE DATA_INSUFFICIENT (unexplained ISIN change); no candidate ACTIONABLE (all G0 MANUAL across Muhurat sessions, DQ-1) |

Changed expectations in this round, each cited in its test:
- **Re-pinned real-data counts (D47):** 62 to 1,233 files; 1,171 to 0 missing.
- **Calendar window 2016-2025 (D48).**
- **Q1 2022 tests filter to Q1:** the raw folder now holds 2021-2025.
- **Review gate in the membership tests (D49).**
- **Point-in-time lineage conflicts (QA).**
- **`RowValueError` subclass (ED-30).**
- **Evidence copies compared by CSV member:** NSE re-zips archives (R-8).

## 2. Behaviour-preservation evidence (MP0)

| Evidence | Result |
|---|---|
| Real-data scan, 5 symbols (INFY, TCS, RELIANCE, HDFCBANK, ITC), as-of 2022-03-31, local bhavcopies, calendar, manifest: pre-MP0 code vs current code | all seven report files byte-identical (only the new `run_manifest.json` sidecar differs) |
| Synthetic long history (`tests/_research.py`): `scan` and `replay-decision`, pre-MP0 vs current | byte-identical |
| Independent QA source comparison | trading modules byte-identical; `mtf_freshness`, `models` differ only in removed unused `typing` names |

## 3. What this does not show

| Not shown | Why | Where tracked |
|---|---|---|
| External validation (TradingView, independent data) | no reference records yet | B8, B10, B17 |
| Real-history evaluation of the strategy | 62 of 1,233 trading days in 2021-2025 accepted (`REAL_DATA_READINESS.md` §0.2) | DATA-1, D31 |
| Profitability, win rate, expectancy | never claimed without a real dataset and an execution model | master prompt section 13 |
| Type correctness | no type checker | TD-6 |
| CI on every change | no CI | TD-9 |
