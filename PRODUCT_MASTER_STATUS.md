# PRODUCT_MASTER_STATUS.md

> **Product:** Day Trader Skill (NSE demand and supply research and decision support)
> **Purpose:** Master status register and roadmap.
> **Last updated:** 2026-11-02 (repository-verified; replaces the unverified baseline of the same date)
> **Release documents:** `nse/docs/release/` (architecture, implementation, testing, data, methodology traceability, unresolved decisions, security, readiness, roadmap, agent execution).

## 1. Status definitions

| Label | Meaning |
|---|---|
| `UNIT-TESTED` | Unit tests pass |
| `INTEGRATION-TESTED` | Real components wired together pass (no mocks of the pipeline) |
| `SYNTHETIC-VALIDATED` | Behaviour checked on labelled synthetic fixtures |
| `REAL-DATA-RUN` | Ran on official NSE files held locally; output not independently checked |
| `REAL-DATA-VALIDATED` | Checked on verified real market data against an expectation |
| `EXTERNALLY-VALIDATED` | Independently checked against an external reference (e.g. TradingView) |
| `PAPER-TRADING-VALIDATED` | Prospective simulated trading evidence collected |
| `NOT-VALIDATED` | Required evidence is absent |

Never collapse these into a generic "passed". Passing software tests establishes only the
behaviour they cover. Synthetic data validates mechanics, not market edge.

## 2. Product vision

An NSE stock research and decision-support system: ingest and validate EOD data, keep a
point-in-time universe, detect demand and supply zones on every timeframe, enforce
freshness through the MTF overlay, apply the Trading Rulebook gates G0-G8, explain every
result, replay any historical decision, backtest only under owner-supplied assumptions,
and present everything through reports and a static dashboard. AI explains recorded
evidence; it never overrides deterministic eligibility. Nothing places an order.

## 3. Product tracks

- **MIT (Daily / Swing):** first priority. Implemented end to end; data history is the
  binding constraint.
- **WIT (Intraday 75/125-minute):** BLOCKED by design (audit M4b, B6, D32). Gate logic for
  WIT roles exists and is tested; every WIT result is BLOCKED.
- **LLM Council:** advisory engineering and trading review skill; not part of the decision path.

## 4. Verified baseline (2026-11-02)

Full validation: `python3 -m nse.validation.run_all` on this checkout. See
`nse/docs/release/TESTING_REPORT.md` for the exact final counts.

| Area | Status | Evidence |
|---|---|---|
| Zone Engine | UNIT-TESTED, INTEGRATION-TESTED, NOT-VALIDATED externally | `test_zone_engine` (65); no TradingView references (B10) |
| MTF freshness overlay | UNIT-TESTED, INTEGRATION-TESTED | `test_mtf_freshness` (43); B8 open |
| G0-G8 qualification (MIT) | UNIT-TESTED, INTEGRATION-TESTED, SYNTHETIC-VALIDATED | `test_research_gates`, `_e2e`, `_adversarial`, 19 scenarios |
| R1-R6 (owner-approved M1) | Implemented with focused regression tests | `TRACEABILITY.md` approvals table |
| Scanner, JSON/CSV reports | INTEGRATION-TESTED; REAL-DATA-RUN (5 symbols, 2022-03-31) | real run: all candidates DATA_INSUFFICIENT (12 of 55 weekly candles) |
| Pre-entry X/14 display | UNIT-TESTED; information only | `test_research_confluence` |
| Risk and position sizing | UNIT-TESTED | `test_research_risk` (Rulebook worked examples exact) |
| Data acquisition (offline inbox) | UNIT-TESTED; REAL-DATA-RUN | `test_research_acquisition`; 62 of 494 sessions held for 2022-2023 |
| Instrument identity | UNIT-TESTED; no records | `test_research_instruments`; B11 |
| Backtesting | UNIT-TESTED; no run on real history | `test_research_backtest`; B9, B12, B11 |
| Scenario laboratory | 19 SYNTHETIC scenarios PASS | `cli scenarios-run` |
| Decision replay, dashboard | UNIT-TESTED, INTEGRATION-TESTED; REAL-DATA-RUN | `test_research_dashboard` |
| Explain, alerts, narrative reports | UNIT-TESTED, INTEGRATION-TESTED | `test_research_explain`, `_alerts` |
| Store and journal (SQLite) | UNIT-TESTED | `test_research_store` |
| Health check | UNIT-TESTED | `test_research_health` |
| Real NSE data | 62 legacy bhavcopies (Q1 2022, 2023 samples); UDiFF unverified | `cli acquire-coverage` |
| Corporate actions | Interface only; no records | B7 |
| Historical Nifty 100 membership | Loader only; no data | B11 |
| TradingView validation | Not started | B8, B10, B17 |
| WIT | BLOCKED | M4b |
| Broker integration | Not implemented; not authorised | D10, D17 |

## 5. Product module inventory

| ID | Module | Status | Source | Remaining dependency |
|---|---|---|---|---|
| P01 | NSE EOD ingestion | Implemented (legacy format; offline inbox, plan, ingest, daily update, quarantine, ledger) | `nse/eod/nse_bhavcopy.py`, `nse/research/acquisition.py` | Owner download of missing sessions (D31) |
| P02 | UDiFF support | Detected and quarantined, never ingested | `acquisition.detect_format` | Real UDiFF sample (B18) |
| P03 | Normalization / quality | Implemented | `marketdata.py`, `nse_bhavcopy.py` | Real-data coverage |
| P04 | Corporate actions | Partial: records interface, G0 MANUAL, PREVCLOSE discontinuity detection; no adjustment | `corporate_actions.py` | B7 source and convention |
| P05 | Universe management | Implemented (effective-dated) | `universe.py` | Constituent files |
| P06 | Nifty 100 point-in-time | Blocked | `universe.py` | B11 |
| P07 | Zone Engine | Implemented | `nse/zone-engine/` | B10 |
| P08 | MTF overlay | Implemented | `nse/mtf-freshness/` | B8 |
| P09 | Scanner | Implemented | `scanner.py`, `cli.py` | History depth |
| P10 | Trend | Implemented (SMA-50 clock, R2) | `trend.py` | B8 |
| P11 | Location / curve | Implemented (R1); P-LOC-2 MANUAL | `structure.py` | P-LOC-2 decision |
| P12 | HTF conflict | Implemented | `structure.py` | none (manual bands) |
| P13 | Coinciding / aggressive | Implemented (R3, R6); Aggressive MANUAL | `structure.py`, `_g6` | Aggressive criteria |
| P14 | Trade levels / R:R | Implemented (ranges; B9) | `levels.py` | B9 |
| P15 | Position sizing / risk | Implemented (separate risk plan) | `risk.py` | B9 buffer choice |
| P16 | Market / sector context | Not evaluated by design (D6) | checklist SECTOR | Owner decision to define sector rules |
| P17 | News research | Not implemented (no approved source) | - | Source policy |
| P18 | Fundamentals | Not implemented | - | Defined metrics and source |
| P19 | Ranking / reports | Implemented: status order, JSON/CSV, markdown daily / stock / comparison; no numeric ranking that could override a gate | `reports.py`, `narrative.py` | - |
| P20 | Historical replay | Implemented: point-in-time scans, decision bundles | `scanner.scan_history`, `decision_replay.py` | Real history |
| P21 | Backtesting | Implemented: metrics, breakdowns, monthly cap, concurrency, walk-forward, sensitivity; all assumptions owner-supplied | `backtest.py` | B9, B11, B12 |
| P22 | Paper trading | Journal implemented; no simulator loop | `store.py` journal | Validated scanner |
| P23 | Trade journal | Implemented (Rulebook constraints) | `store.py` | - |
| P24 | Dashboard / charts | Implemented (static HTML, SVG) | `dashboard.py` | - |
| P25 | Alerts | Implemented (stdout, JSONL); no external delivery | `alerts.py` | Owner approval for delivery |
| P26 | TradingView integration | Reference comparison tooling only | `refcheck.py`, `nse_reference.py` | B8, B10 records |
| P27 | Broker integration | Not authorised | - | Explicit approval, much later |
| P28 | WIT | Blocked | - | M4b, B6, B15 |

## 6. Non-negotiable invariants (enforced in code and tests)

1. Only fresh demand zones are candidates; tested, invalidated and unknown-freshness zones never are.
2. Candidates come only from `MtfSnapshot.eligible_after_overlay` / `manual_review_after_overlay` (`tests/test_repo.py` forbids `.eligible` elsewhere).
3. Status is the most restrictive gate outcome (`models.derive_status`); the best status is `ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING`, always with the manual checklist. No status approves a trade.
4. No network, broker or order code under `nse/` (D10, D17, D31, D32).
5. Protected sources (Rulebook Markdown and PDF, Pine Script) are hash-pinned; the guard hook refuses writes.
6. No commit, push, reset, clean or stash without owner authorisation (guard hook).

## 7. Open decisions and blockers

Exact texts: `nse/docs/DECISION_REGISTER.md`; consolidated list: `nse/docs/release/UNRESOLVED_DECISIONS.md`.

| Item | Status |
|---|---|
| R1-R6 | USER_APPROVED (2026-11-02), implemented and tested |
| RB-VERSION-1 | NEW: the root PDF and the protected Markdown are different revisions; owner to declare the authoritative one |
| P-LOC-2 | Owner decision (price inside a tested HTF demand) |
| D40 | PROPOSED (20 Jan 2024 session hours inferred) |
| D41 | PROPOSED except R1-R6 |
| B9, B12 | Owner execution model for backtests |
| B7, B11, B18, B8, B10, B17 | Evidence needed (corporate actions, constituents, UDiFF sample, TradingView references, calendar validation) |
| M4b, B6, B15 | WIT design and intraday data |

## 8. Roadmap

See `nse/docs/release/NEXT_PHASE_ROADMAP.md`. The next five actions, in dependency order:
1. Owner decides RB-VERSION-1 and P-LOC-2.
2. Owner downloads the missing 2021-2025 legacy bhavcopies (plan: `cli acquire-plan`) and one UDiFF sample; ingest with `acquire-ingest`.
3. Owner supplies Nifty 100 constituent history (B11) and corporate-action records (B7).
4. Record TradingView references for an agreed symbol set (B8, B10) and run `refcheck`.
5. Owner supplies a backtest execution model (B9, B12); run walk-forward on point-in-time scans.

## 9. Architecture

`nse/docs/release/ARCHITECTURE.md` describes the implemented modules and their
dependency graph.

## 10. Evidence standards

For every claim: source path, test path, exact command, result, data kind (synthetic,
real-data run, external). Synthetic and real-data-run evidence never upgrade to
"validated".

## 11. Final readiness classification

**Integrated research platform** (software complete for MIT on local data; not
historical-data-ready, not backtest-validated, not paper-trading-ready, not live-ready).

## 12. Change log

| Date | Change |
|---|---|
| 2026-11-02 | Initial master status baseline prepared from available project reports and conversation context. |
| 2026-11-02 | Repository-verified rewrite after the integrated build: acquisition, instruments, risk, X/14 display, backtest extensions, scenario library, decision replay, dashboard, explain/alerts/narrative, store/journal, health; RB-VERSION-1 found; quantity rounding defect fixed. |

## 13. Maintenance

- Update after each milestone, citing code, tests and evidence.
- Do not mark work complete on an AI Council recommendation alone.
- Keep unresolved questions visible; correct this file when the repository contradicts it.
