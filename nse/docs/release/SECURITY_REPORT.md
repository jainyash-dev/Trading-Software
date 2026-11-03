# Security and reliability report (2026-11-02)

## Boundaries and how they are enforced

| Boundary | Enforcement | Evidence |
|---|---|---|
| No network, broker or order code in `nse/` | `test_repo` regex over every `.py`; guard hook refuses broker endpoints | repository group PASS |
| Candidates only through the MTF overlay | `test_repo` forbids `.eligible` outside the engine folders; adversarial q4 | PASS |
| Protected sources unchanged (Rulebook Markdown, Rulebook PDF, Pine) | SHA-256 pins in `nse/validation/protected.py` and `test_repo`; guard + post-edit hooks; `cli health` | hashes match at the end of the session |
| No commit / push / reset / clean / stash without authorisation | `.claude/hooks/guard.py` | hooks group PASS; the guard also blocked two of this session's own commands |
| No secrets | No credential is read or requested anywhere; no config file holds keys | review of new modules |
| Standard library only | `cli health` imports every module | 27 modules import |
| Determinism | No clock in reports; determinism tests in reports, dashboard, scenarios, acquisition ledger, store | PASS |
| Idempotent data handling | Duplicate archives and scans are no-ops; revisions quarantined; sources never moved or deleted | acquisition, store tests |
| Store integrity | Append-only tables (triggers), CHECK constraints on statuses, additive checksummed migrations, destructive-SQL detector (DELETE anywhere, REPLACE) | store tests |
| Edited outputs | Store import, risk plans and alerts refuse a status its own gates do not give | review regressions |

## Findings this session

All findings from the independent review were fixed with regression tests (see
`TESTING_REPORT.md`). Remaining low items: backtest open/excluded counting edge; ZONE_PROXIMITY
fix has no dedicated test.

## Not implemented (by design)

External notification delivery, network fetchers, broker connectivity, a server process.
Each needs owner approval and a separate security review before it is added.
