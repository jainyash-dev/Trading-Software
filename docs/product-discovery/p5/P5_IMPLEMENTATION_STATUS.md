# P5 Implementation Status - Portfolio and Risk Management

**Updated:** 2026-11-16 (final closure)  
**HEAD:** `69858d07ccb016b74bc1d518b66b9948656ad6cf`  
**Git:** no stage/commit/push in this work

Statuses are not interchangeable: IMPLEMENTED · UNIT_TESTED · INTEGRATION_TESTED · CONCURRENCY_TESTED · INDEPENDENTLY_REVIEWED · ACCEPTED · BLOCKED · NOT_IMPLEMENTED

---

## 1. Original scope

See master prompt P5 and `P5_BASELINE_AUDIT.md`.

## 2. Verified baseline

Canonical journal in `nse/research/store.py` already held WAP, partial fills/exits, D42/ED-3, `portfolio_at`, and concurrency tests in the dirty tree. Platform desk read `portfolio_at` without a second counter. Valuation, position risk, rich UI, dedicated UI tests, and repository hygiene were the closure gaps.

## 3. Batches

| Batch | Result |
|---|---|
| P5-0..P5-6 | Delivered earlier in-session (valuation, risk, API/UI, concurrency, first independent review) |
| P5-closure | EOD STALE policy doc; dedicated Portfolio vitest; reel/em-dash hygiene; STALE aggregate honesty; docs-health link fix; full green `run_all` |

## 4. Capability status

| Capability | Status |
|---|---|
| Canonical portfolio from journal | IMPLEMENTED · UNIT_TESTED · INTEGRATION_TESTED · CONCURRENCY_TESTED |
| Weighted average entry | IMPLEMENTED · UNIT_TESTED (retained) |
| Partial entry/exit | IMPLEMENTED · UNIT_TESTED (retained) |
| D42 monthly + open caps | IMPLEMENTED · CONCURRENCY_TESTED |
| ED-3 | IMPLEMENTED · CONCURRENCY_TESTED |
| PR-007 EOD valuation | IMPLEMENTED · UNIT_TESTED · INTEGRATION_TESTED |
| Position remaining risk | IMPLEMENTED · UNIT_TESTED |
| Market exposure | IMPLEMENTED · UNIT_TESTED |
| Sector exposure | IMPLEMENTED as UNAVAILABLE (D6) · UNIT_TESTED |
| Portfolio API | IMPLEMENTED · INTEGRATION_TESTED |
| Portfolio UI | IMPLEMENTED · UNIT_TESTED (dedicated vitest) |
| Independent review | INDEPENDENTLY_REVIEWED |
| P5 ACCEPTED | **No** (owner authority). Engineering recommendation: **ACCEPTANCE_READY** |

## 5. Final EOD staleness policy

Documented in `P5_EOD_STALENESS_POLICY.md`:

- No maximum-age threshold.
- Preserve `price_date`; older accepted closes are `STALE` and remain usable.
- Portfolio aggregate is `STALE` when any open mark is `STALE`.
- Never invent/interpolate; never use a future close; never call an EOD mark a live quote.
- Missing/invalid marks stay `UNAVAILABLE`.
- A future max-age cutoff requires a separate owner decision.

## 6. Files changed in closure

| Path | Change |
|---|---|
| `docs/product-discovery/p5/P5_EOD_STALENESS_POLICY.md` | New policy |
| `docs/product-discovery/p5/P5_CLOSURE_REPORT.md` | Final closure package |
| `docs/product-discovery/p5/P5_INDEPENDENT_REVIEW.md` | Updated (no broken agent markdown links) |
| `docs/product-discovery/p5/P5_IMPLEMENTATION_STATUS.md` | This file |
| `docs/implementation/AGENT_WORK_LOG.md` | Updated |
| `GTF_ENGINEERING_FIRST_ROADMAP.md` | Em dashes removed; kept as permanent root doc |
| `tests/test_repo.py` | Reel includes the roadmap |
| `platform/gtf_platform/integration/valuation.py` | Aggregate STALE honesty |
| `platform/web/src/features/workflow/WorkflowPages.tsx` | Portfolio loading/testids/STALE visibility |
| `platform/web/src/features/workflow/portfolio.test.tsx` | Dedicated UI suite |
| `platform/web/src/test/platformFetch.ts` | Portfolio fixture route |
| `platform/tests/test_portfolio_p5.py` | STALE aggregate + prior valuation tests |

## 7. Schema changes

None.

## 8. Exact validation evidence (closure)

| Suite | Result |
|---|---|
| `tests.test_research_store` + `tests.test_repo` | **96 PASS** |
| `platform/tests/test_portfolio_p5` | **17 PASS** |
| `platform/tests/test_product_flow` + `test_platform_api` | **39 PASS** (earlier closure pass; product/API unchanged after STALE aggregate) |
| Portfolio vitest | **10 PASS** |
| Full frontend vitest | **58 PASS** (earlier in closure; +10 portfolio) |
| `python3 -m nse.validation.run_all` | **1482 ran, 0 failures, 0 errors, 0 skipped** - verdict **PASS** |

Report artefact: `nse/output/validation/report.json`.

## 9. Independent review

Closure reviewer (agent id `875edce0-a70b-4385-9951-2a6850514ad1`): PASS_WITH_LIMITATIONS for Important aggregate-STALE issue; that issue was fixed and re-tested. No unresolved critical/important findings remain. See `P5_INDEPENDENT_REVIEW.md`.

## 10. Remaining limitations (explicit)

- No max-age refusal for STALE marks (policy; owner decision reserved).
- Sector and live drawdown remain UNAVAILABLE by design.
- Store unrealised stays UNAVAILABLE without a mark; platform unrealised only after EOD mark.
- Empty open book reports valuation UNAVAILABLE with reason (not a zero book).
- Portfolio UI does not show an `authorises_order` Fact (API remains false).
- Not P0 certification; not R1-R5 readiness; not profitability evidence.

## 11. Owner decisions still required

1. Final owner stamp of P5 as ACCEPTED (or not).
2. Optional future maximum-age threshold for STALE EOD marks.
