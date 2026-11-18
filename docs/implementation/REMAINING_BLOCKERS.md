# Remaining blockers

| ID | Kind | What is still required |
|---|---|---|
| B11-R / T-001 | Owner | A human decision on each row of `nse/data/universe/nifty100_review.csv` |
| ~~CAL-2 / T-002~~ | Closed | Closed 2026-11-10 by owner decision D58: the four dates are confirmed regular equity sessions |
| B11-I / T-004 | Evidence | Official price-scale records before BAJFINANCE, GRASIM, and YESBANK can be joined |
| B7 / R-10 | Evidence | Empty corporate-action responses are still not coverage |
| B8, B10, B17 / T-005 | Owner samples | TradingView exports. The intake plan exists. No sample was fabricated |
| B12 | Owner file | A dated cost schedule. Typed percentages are labelled as this-run inputs only |
| OQ-1 | Owner | A quote source before any session monitor. T-019 was not built |
| OQ-2 | Owner | An assistant provider. T-021 was not built |
| Browser proof | Verification | The new screens were not clicked against a running API |
| Stale envelopes | Operations | A scan saved before the G0 coverage rule can still display an old PASS until it is re-run |
| ~~T-017 test~~ | Closed (P1 2026-11-17) | Automated isolated restore proof: `test_backup_restore_preserves_journal_records_and_rejects_incomplete` (record-level journal + incomplete/permission failures; live files unchanged) |
