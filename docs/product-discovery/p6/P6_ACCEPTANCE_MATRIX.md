# P6 Acceptance Matrix - Trading Journal and Performance Reporting

**Date:** 2026-11-17  
**HEAD:** `69858d07ccb016b74bc1d518b66b9948656ad6cf`  
**Owner ACCEPTED:** not claimed  
**Engineering recommendation:** `P6_ACCEPTANCE_READY`

| # | Acceptance criterion | Status | Evidence |
|---|---|---|---|
| 1 | Original P6 requirements reconciled | `PASS` | `P6_BASELINE_AUDIT.md` |
| 2 | Journal lifecycle complete and validated | `PASS` | Store ALLOWED + product-flow + P6 journeys |
| 3 | Partial fills/exits preserve canonical accounting | `PASS` | P5 retained; journey B |
| 4 | Journal event history auditable | `PASS` | Append-only tables |
| 5 | Duplicate/invalid lifecycle events handled | `PASS` | print_key / idempotency / refusals |
| 6 | Charges honest; never invented | `PASS` | ABSENT/ACTUAL/ESTIMATED; JOURNAL_NOTE fixed |
| 7 | Notes and review history | `PASS` | `journal_notes` + API/UI |
| 8 | Screenshot attachments safe | `PASS` | Magic validation + UI upload + GET |
| 9 | Mistake taxonomy structured | `PASS` | `P6-RB-1` / `journal_taxonomy.py` |
| 10 | Search/filters over canonical records | `PASS` | `journal_query` + UI filters |
| 11 | Planned-vs-actual preserves plan | `PASS` | `journal_planned_versus_actual` |
| 12 | Performance breakdowns documented | `PASS` | `P6_METRIC_DEFINITIONS.md` |
| 13 | Gross/net and missing-charge unambiguous | `PASS` | net_state labels |
| 14 | Setup performance uses reliable ids | `PASS` | trade_type + setup_label |
| 15 | Exports reproducible/safe | `PASS` | `gtf-journal-export-v1` |
| 16 | UI and API reflect canonical journal | `PASS` | JournalPage + desk |
| 17 | P5 accounting/risk unchanged | `PASS` | portfolio suite green |
| 18 | P1 security/readiness intact | `PASS` | api_security green |
| 19 | Paper-book unimplemented/deferred | `PASS` | TJ-012 / `paper` |
| 20 | No broker/order authority | `PASS` | `authorises_order=false` |
| 21 | End-to-end journeys | `PASS` | `test_journal_p6` journeys + store P6 |
| 22 | Full regression validation | `PASS` | `run_all` 1512/0/0/0 PASS |
| 23 | Independent review clean | `PASS` | remediation re-review PASS |
| 24 | Required documentation complete | `PASS` | `docs/product-discovery/p6/*` |
| 25 | No unauthorized git mutation | `PASS` | no stage/commit/push |

## Deferred

| ID | Item |
|---|---|
| TJ-012 | Paper book |
| TJ-008 | Dedicated missed-trade type |
| B12 | Owner dated tariff file |
