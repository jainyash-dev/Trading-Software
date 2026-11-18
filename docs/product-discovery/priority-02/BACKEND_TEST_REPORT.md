# Backend test report

Command, from the repository root:

```
PYTHONPATH=platform python3 -m pytest platform/tests -q -p no:cacheprovider
```

Result: **37 passed**, 2 existing Pydantic deprecation warnings in the OpenAPI security test. No assertion was removed or weakened.

## Product flow (`platform/tests/test_product_flow.py`)

Isolated temporary databases. Prices come from `tests/_research.py` `long_mit_candles` through `scanner.scan`. The fixture must produce `ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING` or the class fails setup.

| Test | What it checks |
|---|---|
| `test_plan_approval_journal_portfolio_export_and_backup` | Draft quantity is null. Preview has combinations. Approve writes one journal row and no `TRIGGERED`. A second approve returns the same `entry_id`. Order submission then `TRIGGERED`. Portfolio at the fill time: monthly 1, open 1, valuation and sector `UNAVAILABLE`, `authorises_order` false. `CLOSED_MANUAL` then a later read: open 0, monthly still 1. A second plan on the same zone returns 409 `ONE_ORDER_PER_ZONE`. |
| `test_browser_timestamp_is_converted_to_the_naive_scan_clock` | `recorded_at` `2024-02-02T10:00:00+00:00` is stored as naive `2024-02-02T15:30:00` (IST). Added after the browser approval failed closed on a mixed clock. |
| `test_rejected_candidate_cannot_be_planned_and_export_matches_bytes` | A stored `REJECTED` candidate cannot be planned. Export body equals the stored `candidates.csv`. Completeness `PARTIAL` is not reported as a complete scan. |
| Live portfolio read inside the approval test | `GET /api/v1/portfolio` with no `at`, after a February 2024 fill, returns 200, `open_positions` 1, valuation `UNAVAILABLE`. This is the call that had been HTTP 500 in the browser. |

## Other platform coverage in the same 37

- Scheduler: saved false overrides the process flag; a non-boolean stored value does not enable the scheduler; a missing row falls back to the process flag. The scheduler does not download.
- MIT scan job writes `candidates.csv` and `run_manifest.json`. Export body equals the file.
- Security: `/api/v1/journal` is implemented; `/api/v1/fills` is not. `journal_add` and `journal_event` are allowed only from `platform/gtf_platform/integration/desk.py`.
- OpenAPI document matches the current routes.

## Research-engine tests run because the journal boundary was exercised

```
PYTHONPATH=.:tests python3 -m unittest \
  test_research_store.Journal.test_fill_after_ten_verified_sessions_is_refused_and_expired_still_records \
  test_research_store.Journal.test_two_connections_cannot_both_commit_an_eleventh_trigger
```

Both passed. `nse/research/store.py` was not modified. Ten verified sessions still refuse a late fill. An `EXPIRED` event can still be recorded. Two connections still cannot both commit an eleventh trigger.

## Lint and architecture

`.venv/bin/ruff check platform/gtf_platform/integration/desk.py platform/tests/test_product_flow.py`: all checks passed.

`python3 -m nse.validation.architecture`: **FAIL**, 50 modules, 1 violation.

```
A2 nse/research/backtest.py:909: portfolio layer imports nse.research.run_manifest (application layer)
```

That file was not edited in this pass. The failure is recorded rather than patched from here, because the manifest helper sits on the research side of a layer rule and moving it is a separate design choice.

## Not run

`python3 -m nse.validation.run_all` was not run. It covers the whole research tree, local data, and lint, and this pass did not change `nse/` code. The targeted journal tests above are the research boundary that the platform calls.
