# P2-P4 Cross-Phase Integration Report

**Date:** 2026-11-17. Fixture data only; see `P2_P3_P4_BROWSER_VALIDATION.md` for screenshots (BR-nn).

| Journey | Path exercised | Result | Evidence |
|---|---|---|---|
| 1 Stock analysis | Symbol -> stored bundle -> M/W/D -> zones -> explanation -> missing evidence | PASS. Chart uses `/candles` + stored `/bundle?scan_key`; mismatches shown as STALE/MISSING, never substituted | BR-01..07, API, vitest `evidence.test.ts` |
| 2 Opportunity discovery | Real pipeline scan job -> stored envelope -> scanner outcome -> opportunity ingest -> watchlist -> history | PASS after two key-mismatch defects were fixed. No qualification recomputed in the UI | BR-16..20, 23, OPP, vitest |
| 3 Trade planning | Opportunity/stored candidate -> draft -> geometry/R:R/sizing -> checklist -> approve (journal row) -> journal cancel -> plan mirror | PASS. Journal remains canonical; no order path | BR-08..13, 15, PLAN |
| 4 Plan overlay | Stored plan -> chart overlay -> journal cancel -> overlay withdrawn | PASS. Cancelled/rejected/expired/closed/unconfirmed/invalidated plans not drawn | BR-11, BR-14, vitest `plans.test.ts` |
| 5 Uncertified data | Fixture labels on chart, scanner, opportunities, plans; no CERTIFIED claim | PASS. Data certification FIXTURE/UNCERTIFIED only; plan `source_quality` FIXTURE; certified-claim scan in BR-18 false | BR-02, 16, 18; PLAN `test_certified_source_downgraded_to_exploratory` |
| 6 Failure and recovery | Journal mirror failure, interrupted mirror + restart, journal unavailable, entry missing, identity mismatch, concurrent cancels, scan beyond data, missing symbol file | PASS. No partial failure shows a successful-looking state | PLAN `test_ir04_*`, BR-17 |

## P5 / P6 regression

- `platform/tests` 100 PASS includes `test_portfolio_p5.py` and `test_journal_p6.py` and the store
  concurrency companion; P5 caps and accounting and P6 journal lifecycle untouched (no change to
  `nse/research/store.py`, `valuation.py`, or journal routes other than the added plan-sync step after an
  event write).
- The only journal-adjacent behaviour change: after a journal event is committed the platform mirrors
  terminal states onto linked plans. It never writes the journal.

## P0 / D66

No P0 file, certification output, or D66 rule was touched. P0 certified symbol-dates remain 0; CERTIFIED
discovery and planning stay refused.

## authorises_order

No route added (63 registrations; `openapi.json` equality test passes). Every plan/journal response in the
changed paths carries `authorises_order: false`. Approval and journal-cancel messages state no order was
sent or touched. The existing adversarial security suite (`test_api_security.py`) passes.
