# P0 remediation final report

**Dated 2026-11-10. P0 is not certified. `DATA_READY` is false.**

Branch `main`, HEAD `9e302df1a81c2b13696d8fab61f05d377481be2e` before and after.
Nothing was staged or committed. Protected Rulebook PDF, Rulebook Markdown, and Pine
hashes are unchanged. The pre-existing dirty working tree was kept.

Owner decision register: [P0_OWNER_DECISIONS.md](P0_OWNER_DECISIONS.md).

## A. Executive summary

D59 is recorded and implemented. Membership-based Nifty 100 research is labelled from
2020-12-31 onward. That label is not certification. No review row was accepted. The
three unevidenced ISIN breaks stay unjoined. Price gaps keep the classifications already
investigated, with raw OHLC unchanged. `SRTRANSFIN` was collected through the approved
D56 script and returned an empty list, which is not coverage. Calendar equity sessions
were recounted at 2,466 with 12 excluded sessions and no missing archive date. A
comparison command exists and does not close T-005.

What remains blocked: human review of 271 membership rows, five dummy seats, the three
identity documents, corporate-action completeness, the BE/BZ series question, the
CROMPGREAV 2016 ratio, the 2024-01-20 inferred hours, and all 34 TradingView observations.

What was not attempted: strategy or zone changes, back-adjustment, automatic membership
acceptance, automatic ISIN joins, broker execution, and UI work.

## B. Owner decisions

D59 is the only new approval in this pass. Section 2 of the owner register is still
required. The binding ones are:

| ID | Question | Recommendation | Required before further certification |
|---|---|---|---|
| OD-MEM-1 | Accept or reject each of the 271 review rows | Use the worksheet. Do not treat `ACCEPT_RECOMMENDED` as approval | Yes |
| OD-MEM-2 | DUMMYREL's inferred ISIN | Leave the period unverified | Yes, for that seat |
| OD-MEM-3 | How dummy seats with no candles are represented | Keep them unverified | Yes, for those dates |
| OD-ID-1, OD-ID-2, OD-ID-3 | Documents naming the new ISIN and session for BAJFINANCE, GRASIM, YESBANK | Do not join | Yes. GRASIM alone keeps every date from 2020-12-31 unverified |
| OD-PX-1 | May candles use BE/BZ when EQ is absent? | Leave the EQ filter | Only if the EQ holes should be filled |
| OD-PX-2 | Ratio for the CROMPGREAV scheme of 2016-03-15 | Do not invent one | Only for continuity across that date |
| TV-1, TV-2, TV-3 | The 34 TradingView observations, the unnamed SMA dates, and the export/split toggle | Do not close T-005 | Yes, for external validation |
| OD-CA-1 | A separate adjusted series, or a second corporate-action source | Do not adjust. Empty lists stay uncovered | Only if an adjusted series is wanted |
| OD-CAL-1 | Confirm or replace the inferred 09:15-15:30 on 2024-01-20 | Keep the inference visible | No, unless that session should become unresolved |

## C. Evidence and certification

| Subject | Status |
|---|---|
| Calendar and EOD, 2016-2025 | Reproduced without a new full rehash. 2,466 equity sessions, 12 excluded, 2,478 archive dates. Missing equity dates: none. Archives outside equity or excluded sessions: none. The four Dhanteras dates are `NORMAL_SPECIAL` and trading days. `eod_ready` was true on the regenerated coverage report. `data_ready` is false |
| Membership | Not certified. 271 decisions blank. 185 periods unverified. Worksheet: `P0_NIFTY100_OWNER_REVIEW_WORKSHEET.csv`. E03 page 5 was not transcribed: the PDF has no plaintext of those names |
| Research window | D59. As-of dates before 2020-12-31 on a membership file carry `MEMBERSHIP_BEFORE_PROVISIONAL_WINDOW`. Candles before that date can still warm indicators. They are not a survivorship-controlled universe |
| Identity | BAJFINANCE 2016-09-09, GRASIM 2016-10-07, and YESBANK 2020-03-16 stay `DATA_INSUFFICIENT`. No `ISIN_CHANGE` row was invented. A previous-close match was not treated as identity |
| Corporate actions | 145 coverage rows. 47 latest bodies are `[]`, including `SRTRANSFIN` collected 2026-11-10 (HTTP 200, SHA-256 `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`). An earlier TLS failure is logged as `NOT_COLLECTED` and was not treated as coverage. G0 stays manual where the window is absent. Completeness is not claimed |
| Price continuity | EQ-only loader unchanged. ADANIPOWER 2021 and CGPOWER 2021-2022 remain BE trading paths. ADANIPOWER 2025-09-22 remains an unadjusted 1:5 split across two ISINs. CROMPGREAV 2016-03-15 remains an unparsed scheme with ratio 0,0 |
| TradingView | 0 observations. `compare-references` compares supplied files only. `t005_closed` is false |
| Certified research range | None |

## D. Engineering

Implemented:

- D59 limitation in `universe.limitations` and on a backtest whose scans carry it.
- `compare-references` in the research CLI. It requires a calendar, uses series EQ, and does not set `assume_regular_session`.
- `run_manifest` moved to the portfolio layer so `backtest.py` no longer imports a higher layer. Architecture group passed.
- Living status lines for D59, the 47 empty corporate-action responses, and the comparison command.
- UUID-shaped markdown links that the docs check treated as files were turned into plain text, including the four links in the Priority 03 executive report.
- 97 em dashes in 17 product-discovery documents were replaced with a spaced hyphen so the repository text rule passes. The sentences were not rewritten.

Tests:

- Full `python3 -m nse.validation.run_all` before the em-dash replacement and the ED-47 wording fix: 1,313 tests, 2 failures. `repository` failed on em dashes. `council` failed because ED-47 did not match the engineering-decision format. Architecture passed, so the former `backtest.py` layer violation is closed. `local_data` and `reference_comparison` passed. The Yahoo reference check is not TradingView validation.
- After those two documentation fixes, `repository` (15 tests) and `council` (30 tests) passed. The other groups were not repeated, because the fixes did not change code.

Platform tests were not run. No platform file was changed.

Files deliberately left without `ACCEPTED` or a new ratio: `nifty100_review.csv`, `instrument_records.csv`, raw OHLC, and the qualification gates.

## E. Next work package

One package, and it is an owner package: fill `P0_NIFTY100_OWNER_REVIEW_WORKSHEET.csv` and, with it, supply official documents that name the new ISIN and the session for BAJFINANCE on 2016-09-09, GRASIM on 2016-10-07, and YESBANK on 2020-03-16.

A completed review without those three documents still leaves GRASIM's open period unverified, so every membership date from 2020-12-31 stays `UNIVERSE_UNVERIFIED`. This package was not started.
