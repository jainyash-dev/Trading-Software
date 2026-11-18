# GTF P4 - Test report

**Date:** 2026-11-15

## Commands and results

| Suite | Command | Result |
|---|---|---|
| P4 unit/API | `cd platform && python3 -m unittest tests.test_trade_planning -v` | **6 passed** |
| Platform full | `cd platform && python3 -m unittest discover -s tests` | **58 passed** |
| Web vitest | `cd platform/web && npm test -- --run` | **48 passed** |
| Web build | `cd platform/web && npm run build` | **PASS** |
| Architecture | `python3 -m nse.validation.run_all --no-data --group architecture` | **PASS** |
| Repository | `python3 -m nse.validation.run_all --no-data --group repository` | **PASS** |
| Quant-related groups | `run_all --group backtest --group lookahead --group risk_instruments` | **325 passed** (quant reviewer) |

## Skipped

| Item | Reason |
|---|---|
| Full `run_all` with local_data | P0 incomplete / owner bhavcopies may be UNAVAILABLE; not a P4 defect |
| Visual screenshot matrix | Not run this session |
| Official broker tariff verification | By design (no hardcoded tariff) |
| Live concurrency stress beyond P1 store tests | Cap/ED-3 concurrency already certified in P1; not re-run as a long soak |

## Coverage notes

P4 tests exercise: draft create + idempotency, preview portfolio/geometry/manual-exec fields, submit/reject/reopen/cancel/history, BLOCKED refuse, notes, approve + planned-vs-actual, CERTIFIED demotion, tested-overlay geometry BLOCKED, approved+journal cancel refuse (409).

Product-flow regression retained for approve/journal/portfolio/ED-3/partial-fill paths.
