# Testing report (2026-11-02)

## Commands and actual results

```
python3 -m nse.validation.run_all                # totals ran 992, failures 0, errors 0, skipped 0; verdict PASS
python3 -m nse.validation.run_all --acceptance   # totals ran 992, failures 0, errors 0, skipped 0; verdict PASS
python3 -m nse.research.cli scenarios-run        # 19 PASS, 0 FAIL, 0 INVALID, 0 UNAVAILABLE
python3 -m nse.research.cli health               # exit 0: 4 OK, 3 WARNING (calendar B17, EOD data B7/B18, owner inputs)
```
Baseline at the start of the session: 714 tests, 2 failures (both from new owner files at the
repository root; fixed by admitting them to the root allow-list and pinning the PDF hash).

## By group (final run)

| Group | Tests | Kind |
|---|---|---|
| repository (+ repository_checks) | 14 | Boundaries: protected hashes, no network/broker code, no raw `.eligible`, every test grouped |
| zone_engine | 65 | Unit (synthetic) |
| mtf_freshness | 43 | Unit (synthetic) |
| data | 90 | Loader, calendar, replay; includes real local files |
| strategy_gates | 69 | G0-G8 unit tests, X/14 display, quantity regression |
| lookahead | 10 | Prefix invariance, future touches, incomplete candles |
| integration | 26 | Real pipeline end to end (synthetic data) |
| adversarial | 19 | Invariant attacks (q1-q12), mutation canaries |
| reports | 9 | Report schema and reconciliation |
| data_readiness | 20 | Inventory, corporate actions, references |
| backtest | 46 | Metrics, portfolio rules, walk-forward, sensitivity |
| acquisition | 32 | Ingestion, quarantine, plan, daily update; one real archive |
| store | 41 | Migrations, import, journal rules |
| research_assistant | 44 | Explain, self-audit, alerts, narrative |
| dashboard | 24 | Decision bundles, HTML pages |
| risk_instruments | 58 | Rulebook sizing examples, identity records |
| scenarios | 31 | Scenario schema, library, mutation |
| health | 7 | Health checks |
| hooks | 9 | Guard and post-edit hooks |
| council | 23 | LLM Council skill structure |
| validation_framework | 8 | Runner hygiene |
| legacy_day_trader_skills | 304 | Pre-existing US day-trading pack |
| local_data, reference_comparison | (checks) | Calendar circular hashes, EOD vs manifest, INFY OHLC vs a Yahoo reference |

## Categories

- **Unit tests:** passed (all groups above).
- **Integration tests:** passed; real components, synthetic data (no pipeline mocks).
- **Repository tests:** passed.
- **Reference-data validation:** PARTIAL and pre-existing: INFY Q1 2022 daily OHLC vs Yahoo
  Finance (not an independent source). No zone or TradingView reference exists.
- **External validation:** NOT performed. No TradingView comparison has been recorded.
- **Real-data run (not validation):** scan of INFY, TCS, RELIANCE, HDFCBANK, ITC at
  2022-03-31 on official bhavcopies; every downstream command ran; all 7 candidates are
  DATA_INSUFFICIENT (12 of 55 weekly candles; no completed Q/HY/Y history).

## Defects found and fixed this session (each with a regression test)

| Defect | Found by | Test |
|---|---|---|
| `levels.quantity_range` float rounding (100.30 / 100.10 gave 4999, not 5000) | risk workstream | `Levels.test_quantity_uses_exact_prices_regression` |
| Risk plan FAIL when only some buffer choices failed (spec 6.3: MANUAL) | rulebook audit | `AuditRegressions.test_buffer_dependent_failure_is_manual` |
| X/14 crossover counted a cross on the zone's creation bar (RB 570 "pre-existing") | rulebook audit | `CrossoverPreExistingZone` |
| Backtest cap counting basis and cap > 10 unlabelled | rulebook audit | `CapAuditRegressions` |
| HIGH: journal accepted a zone that a later stored scan showed as tested | independent review | `JournalReviewRegressions` |
| Journal accepted plans below 2:1 and an 11th trade in a month | independent review | same, `test_monthly_summary_and_ceiling` |
| Limitations dropped in alerts, daily/comparison reports, risk plans | independent review | `ReviewRegressions` (alerts, risk), `NarrativeLimitationsReviewRegression` |
| Dashboard could draw a chart from a different replay | independent review | `BundleMatchReviewRegression` |
| Risk plans and alerts trusted an edited status | independent review | `ReviewRegressions` |
| Migration check missed DELETE inside triggers and REPLACE | independent review | `DestructiveSqlReviewRegression` |
| `instruments.resolve` listed future symbols | independent review | `PointInTimeReviewRegression` |
| ZONE_PROXIMITY fired below the PL | independent review | fixed (`0 <= dist`); no dedicated test |

## Tests changed (not weakened)

- `test_repo.test_root_matches_the_reel`: the owner's `PRODUCT_MASTER_STATUS.md` and the
  Rulebook PDF admitted at the root; the PDF is now hash-pinned (new test).
- `test_research_backtest.Model.test_nothing_has_a_default`: still requires all 10 execution
  assumptions to have no default; allows only the two optional portfolio rules (None = not
  applied, recorded as a limitation).
- `test_research_store.test_monthly_summary_and_ceiling`: now expects the 11th trade in a
  month to be refused (RB 2392) instead of recorded and flagged.
- `test_research_alerts.test_status_changed_on_a_real_status_difference`: the edited
  previous status is now backed by a matching G4 FAIL, because inconsistent scans are refused.

## Not tested

- Walk-forward pooled de-duplication across folds (hard to construct with the builders).
- Backtest bookkeeping edge: an open-at-end trade can be counted excluded by a later
  price-scale event; incomplete bars after a signal are skipped without an assumption event
  (counts only; R metrics unaffected).
- Browser rendering beyond one headless screenshot of the dashboard.
