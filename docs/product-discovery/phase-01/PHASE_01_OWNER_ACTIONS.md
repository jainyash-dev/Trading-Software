# Phase 01: owner actions

**Dated 2026-11-10.** Only you can do these. Everything else in Phase 01 is prepared, not
decided. In order of effect:

## 1. Dhanteras dates (CAL-2): one decision, large effect

Read [T002_DHANTERAS_EVIDENCE_REPORT.md](T002_DHANTERAS_EVIDENCE_REPORT.md), section 4, and choose one option:

- **A (recommended):** confirm the four rows as regular equity sessions (`CONFIRMED`,
  09:15-15:30). This removes the ED-44 history cut.
- **B:** delete the rows.
- **C:** keep them UNRESOLVED.

Then authorise the calendar edit (Phase 01 did not make it).

Decision: ______  Date: ______

## 2. NIFTY 100 review (B11-R): 271 rows

Read [T001_NIFTY100_OWNER_REVIEW.md](T001_NIFTY100_OWNER_REVIEW.md), then work through
[T001_nifty100_owner_worksheet.csv](T001_nifty100_owner_worksheet.csv) in priority order:

1. **P1:** the 25 count exceptions. Without all 25, no period can be verified.
2. **P2a:** the 10 E03 rows. Check `ind_prs23082021.pdf` page 5 yourself.
3. **P2b:** the 4 dummy-ISIN rows. Accept or reject the inference.
4. **P3:** the 232 remaining rows, by release.

Write the decisions into `nse/data/universe/nifty100_review.csv` (decision, reviewer,
reviewed_on, notes), then re-run the conversion command in `nse/data/universe/README.md`.

## 3. Decisions the review cannot settle

- **Dummy spin-off seats (5 periods):** how should a seat that never trades be represented?
- **Pre-2021 universe:** limit membership-based research to 2021 onwards, or source an
  official earlier baseline?

## 4. Identity evidence (ED-37)

If you can obtain them, supply official documents that date the new ISIN and its price
scale for:
- BAJFINANCE, 2016-09-09;
- GRASIM, 2016-10-07;
- YESBANK, 2020-03-16.

Until then these stay unjoined, and GRASIM and YESBANK are DATA_INSUFFICIENT in every
current scan.

## 5. TradingView samples (B8 / B10 / B17)

Follow the checklist in
[T005_TRADINGVIEW_VALIDATION_PROTOCOL.md](T005_TRADINGVIEW_VALIDATION_PROTOCOL.md), section 4.
It covers 34 observations; start with the INFY daily and weekly OHLC and the calendar
screenshots. Also confirm two things this repository cannot verify: whether your
TradingView plan allows chart-data export, and whether it has a split-adjustment toggle.

## 6. Pre-existing failures in your working tree (not caused by Phase 01)

- Em dashes in `docs/product-discovery/08_PRIORITISED_IMPLEMENTATION_ROADMAP.md` fail
  `test_repo`.
- `nse/research/backtest.py:909` imports `run_manifest`, which fails architecture rule A2.
- Another session edited `platform/` during Phase 01 (`routes.py`, `schedule.py`,
  `openapi.json`, a new `test_product_flow.py`). The platform suite passes with those edits.
  Two writers in one tree is a risk to owner work: one owner per file at a time
  (`docs/AGENT_OWNERSHIP.md`).
