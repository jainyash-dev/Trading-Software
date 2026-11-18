# Phase 01: test report

**Dated 2026-11-10.** All commands were run from the repository root with system
`python3` (3.12, Anaconda) and pytest 7.4.4. No test was modified, skipped or weakened.

## 1. Full validation suite

| Command | Before Phase 01 changes | After |
|---|---|---|
| `python3 -m nse.validation.run_all` | ran 1,305; failures 2; errors 0; skipped 0; verdict FAIL (14m00s) | ran 1,305; failures 2; errors 0; skipped 0; verdict FAIL (12m51s) |

Both failures are identical before and after, and neither comes from a Phase 01 file:

| Failing test | Cause | Phase 01 involvement |
|---|---|---|
| `test_repo.Repo.test_no_em_dashes_and_no_personal_email` | Em dashes in 16 files under `docs/product-discovery/`. These are earlier product-discovery documents and a `priority-03/` folder that another writer created during this session | None. A direct scan finds no em dash in any Phase 01 file. Phase 01 files were cleaned to comply |
| `test_architecture.RealTree.test_the_repository_satisfies_every_architecture_rule` | A2: `nse/research/backtest.py:909` imports `nse.research.run_manifest` (portfolio layer into application layer) | None. `backtest.py` is an owner modification and was not touched |

Every other group passed:

| Group | Tests |
|---|---|
| zone_engine | 65 |
| mtf_freshness | 46 |
| data | 127 |
| strategy_gates | 82 |
| lookahead | 13 |
| integration | 53 |
| adversarial | 28 |
| reports | 26 |
| data_readiness | 51 |
| backtest | 78 |
| acquisition | 40 |
| store | 57 |
| research_assistant | 44 |
| dashboard | 24 |
| risk_instruments | 130 |
| scenarios | 31 |
| health | 7 |
| hooks | 12 |
| council | 30 |
| validation_framework | 14 |
| legacy | 304 |

Plus `local_data`, `reference_comparison` and `static_lint` (ruff 0.17.4).
`reference_comparison` PASS compares INFY Q1 2022 with **Yahoo Finance** rows. That
checks republished data, not TradingView, and is not external validation.

## 2. Targeted runs (Phase 01 scope)

| Command | Result | Covers |
|---|---|---|
| `python3 -m nse.validation.run_all --group risk_instruments` | 130 ran, 0 failures | Universe/membership (`test_research_membership`), instrument identity (`test_research_instruments`), risk caps |
| `python3 -m nse.validation.run_all --group data` | 127 ran, 0 failures | Bhavcopy loading, EOD evidence, calendar and calendar data, replay |
| `python3 -m nse.validation.run_all --group data_readiness` | 51 ran, 0 failures | Readiness, EOD coverage, unresolved-date scope (ED-31/ED-42/ED-44) |
| `python3 -m nse.validation.run_all --group repository` | 15 ran, 1 failure | The em-dash failure above |
| `PYTHONPATH=platform python3 -m pytest -q -p no:cacheprovider platform/tests` (before) | 24 passed | Platform API and security |
| Same, mid-session | 32 passed, 1 failed (OpenAPI snapshot) | Caused by another writer's concurrent `routes.py` change |
| Same, final | **37 passed, 0 failed** | Includes the 8 new search tests and 4 tests the other writer added |
| `PYTHONPATH=platform python3 -m pytest -q -p no:cacheprovider platform/tests/test_instrument_search.py` | 8 passed | T-014 search contract (synthetic fixtures) |
| `python3 -m nse.validation.docs_health` | First run PASS, 0 findings. Final run FAIL, 4 findings: broken links in `priority-03/PRIORITY_03_EXECUTIVE_REPORT.md` lines 105-108, a file another writer created during this session | Phase 01 docs: 0 findings in both runs |
| `python3 -m nse.validation.architecture` | FAIL, 1 violation (A2, pre-existing) | n/a |
| `ruff check` on the three Phase 01 Python files | All checks passed | n/a |
| `git diff --check` | Clean | Tracked files. The new files were checked separately: no trailing whitespace |

## 3. Real-data checks (not unit tests)

These read real repository data in memory and wrote nothing canonical:

- `membership.convert` re-run: identical to the on-disk universe and report.
- Full-acceptance simulation on a scratch copy of the review file: 177 of 185 periods
  would be verified. Simulation only, not a decision.
- SHA-256 of all 38 universe evidence files, all 271 cited source files, the 4 Dhanteras
  circulars and the 4 Dhanteras bhavcopies: all match their records.
- `instruments.resolve` on real records at the BAJFINANCE, GRASIM and YESBANK break dates:
  `UNKNOWN_INSTRUMENT` from each break, so they fail closed.
- `search_instruments` on real data, before and after the fix: the behaviour matrix in
  `T014_INSTRUMENT_IDENTITY_AUDIT.md`.

## 4. Not run

- The web frontend tests (`platform/web`, vitest) and any browser check.
- Any TradingView comparison: there are no samples.
- The platform tests under the pinned FastAPI 0.121.0: the installed version is 0.116.1.

## 5. Integrity checks

| Check | Result |
|---|---|
| Rulebook PDF and `nse/sources/` SHA-256 | Unchanged (`e41cd0e7…`, `14293fa5…`, `039883be…`) |
| Staged files | 0 |
| Commits | None |
| `git status` entries | 117 before and 117 after. The new files are inside directories that were already untracked (`docs/`, `platform/`) |

Synthetic tests are not external validation. Passing tests are not evidence of
profitability.
