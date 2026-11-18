# Architecture

> Living document for the NSE research system. Enforced by
> `python3 -m nse.validation.architecture` (rules A1-A10, `tests/test_architecture.py`).
> The 2026-11-02 snapshot is in `nse/docs/release/ARCHITECTURE.md`; pipeline detail and
> commands are in `nse/docs/RESEARCH_PIPELINE.md`. Source code is the authority; this
> document and the generated module map are navigation aids.

## 1. System overview

A **modular monolith**, Python standard library only, run from local files. No service,
no database server, no network, no broker. One process per command.

```
 local NSE files ──> data layer ──> engines (Zone Engine + MTF overlay, path-loaded once)
 (bhavcopies, CSV,     marketdata      run_engine / replay -> MtfSnapshot
  calendar, universe)  inputs                     │
                                                  ▼ eligible_after_overlay / manual_review_after_overlay
                                  methodology: qualification (G0-G8) <- structure, trend,
                                               topdown, confluence, levels
                                                  │
                         research: scanner (the one pathway) ──> reports (JSON / CSV)
                                   decision_replay, scenarios, inventory
                                                  │
                         portfolio: backtest (reads scan_history), execution_policy,
                                    risk (sizing), store (SQLite journal)
                                                  │
                         application: cli, dashboard, explain, narrative, alerts,
                                      health, run_manifest
```

Every candidate comes from the overlay through `qualification`, called only by
`scanner`. Reports, decision replay, the dashboard, scenarios and the backtest all
consume scanner results; none re-evaluates eligibility.

## 2. Why this structure (and not another)

- The existing code already had clear responsibilities; the foundation milestone kept
  them and made the boundaries **enforceable** rather than moving files (ED-15).
- The engines live in folders with hyphens (`nse/zone-engine`, `nse/mtf-freshness`) and
  are loaded by file path through `nse/research/deps.py`, so every module shares one copy
  of each dataclass. Renaming those folders would touch the owner's Phase 1 evidence,
  docs and tests for no correctness gain; rule A6 keeps the loading in one place instead.
- No microservices, no plugin framework, no ORM: nothing in the product needs them.

## 3. Layers

A module may import only its own layer or a lower one (A2), at module level or inside a
function. Lowest first:

| Layer | Responsibility | Modules |
|---|---|---|
| contracts | Shared vocabulary: gate outcomes, statuses, trade types, result dataclasses, readiness table, protected hashes | `models`, `readiness`, `nse.validation.protected` |
| engines | Zone detection and scoring, MTF freshness overlay, bhavcopy parsing, replay, reference comparison, trading calendar | `zone_engine`, `mtf_freshness`, `nse_bhavcopy`, `nse_replay`, `nse_reference`, `nse_calendar`, loaded by `deps` |
| data | Daily inputs and data-quality findings, input loading, universe, instrument identity, corporate actions, EOD acquisition and manifest | `marketdata`, `inputs`, `universe`, `instruments`, `corporate_actions`, `acquisition`, `manifest_tool` |
| methodology | GTF rules on top of the overlay: curve/location, trend, top-down, HTF conflict, coinciding, levels, G0-G8 and status | `structure`, `trend`, `topdown`, `confluence`, `levels`, `qualification` |
| research | Scanning and point-in-time history, report schemas, decision replay, scenario laboratory, coverage inventories | `scanner`, `reports`, `decision_replay`, `scenarios`, `refcheck`, `inventory`, `eod_coverage` |
| portfolio | Backtest simulation, execution policy, position sizing, journal, store and itemised charges | `backtest`, `execution_policy`, `risk`, `store`, `charges` |
| application | Entry points and presentation: CLI, the research-run orchestrator, dashboard, explanations, alerts, health, run manifests | `cli`, `pipeline`, `dashboard`, `explain`, `narrative`, `alerts`, `health`, `run_manifest` |
| tooling | Validation and fixture generation | `nse.validation.*`, `nse.scenarios.*` |

Live module map (layer, imports, imported-by) for agents and reviewers:
`python3 -m nse.validation.architecture --map`.

### Permitted exceptions (each is technical debt with an owner)

| Id | Import | Reason | Debt |
|---|---|---|---|
| X1 | `decision_replay` -> `dashboard` | the `replay-decision` command handler writes `decision.html`; the import is inside `cmd_replay_decision`, so the bundle logic stays presentation-free | TD-2 |

### Command registration convention

Modules in any layer may expose `add_commands(subparsers)` and `cmd_*` handlers; `cli.py`
imports them by name (`COMMAND_MODULES`, a dynamic import the checker does not treat as a
dependency edge). Handlers share `nse/research/inputs.py` for the as-of parser and input
loading; nothing imports `cli` itself (A4). Moving every handler into the application
layer is recorded as TD-1, not done, because it would touch 13 modules for no
behavioural gain.

## 4. Rules enforced by `nse/validation/architecture.py`

| Rule | Meaning | Why |
|---|---|---|
| A1 | Every module under `nse/` has exactly one layer | a new module must be placed deliberately |
| A2 | Imports go to the same or a lower layer (exceptions listed above) | domain logic never depends on presentation |
| A3 | No module-level import cycles | cycles hide initialisation-order bugs |
| A4 | Nothing imports `nse.research.cli` | the CLI is an entry point, not a library |
| A5 | Standard library and `nse` only | reproducible on any Python 3.10+ without installs |
| A6 | Only `deps.py` and the engine chain load modules by path | one shared copy of each engine |
| A7 | `run_engine`, `core_score`, `eligible_after_overlay`, `manual_review_after_overlay`, `derive_status`, `parse_as_of` are defined once; the actionable status is a string constant only in `models.py` and the frozen store migration | one implementation of each business rule |
| A8 | No `eval`, `exec`, `pickle`, `marshal`, `shelve`, `os.system`, `os.popen` (called, imported by name or via `getattr`), no `shell=` other than a literal `False` | no code execution from data, no shell injection |
| A9 | `qualification` is imported by `scanner` only | one qualification pathway; backtest, replay and reports reach it through the scanner |
| A10 | Only the listed audit-view modules (`scanner`, `structure`, `refcheck`, `decision_replay`, and the engines) read an engine result's raw `.assessments` | every new reader of unfiltered zones is a reviewed change; candidates come from the overlay methods |

Imports are read statically (absolute, relative, `importlib.import_module("literal")`); a
module name computed at run time (`cli.COMMAND_MODULES`) is not an edge. A7 matches by
definition name, so a renamed copy of a rule is not caught; A9 and A10 and review are
the guard against that.

Related checks elsewhere: `tests/test_repo.py` forbids network and broker imports and any
raw `.eligible` read outside the engines; `tests/test_research_adversarial.py` q4 forbids
`run_engine(` in `nse/research`.

## 5. Data flow and contracts

| Stage | Contract | Defined in |
|---|---|---|
| Input | `marketdata.DailyInput(symbol, candles, provenance, sessions, findings)`; findings carry `known_at` (no lookahead) | `marketdata.py` |
| Engines | `mtf_freshness.replay(...) -> MtfSnapshot`; zones only via `eligible_after_overlay(tf)` / `manual_review_after_overlay(tf)` | `mtf_freshness.py` |
| Gates | `models.GateResult` per G0-G8; outcome in PASS / FAIL / MANUAL / DATA_INSUFFICIENT / BLOCKED / NOT_EVALUATED | `models.py` |
| Status | `models.derive_status(gates)`: most restrictive wins; best status is ACTIONABLE_CANDIDATE_MANUAL_CHECKS_PENDING | `models.py` |
| Results | `scanner.ScanResult` -> `reports.write_all` (scan.json, candidates.csv, fresh_zones.csv, blocked_zones.csv, data_quality.csv, summary.json, readiness.json) | `scanner.py`, `reports.py` |
| Research run | `pipeline.run` calls `scanner.scan`, then attaches trade plans and portfolio checks without changing a status. `research.json` embeds the scan. Code revision stays in `run_manifest.json` | `pipeline.py` (ED-45) |
| Provenance | `run_manifest.json` sidecar: run id, inputs and dataset hash, methodology and code revision, outputs (ED-18) | `run_manifest.py` |
| History | `scanner.scan_history` (point-in-time) -> `backtest.run` | `scanner.py`, `backtest.py` |

Outputs are deterministic: identical inputs, configuration and as-of give identical
bytes (no clock reads; `generated_at` is caller-supplied). Machine- and moment-specific
facts live only in `run_manifest.json`.

## 6. Technology choices

| Choice | Reason |
|---|---|
| Python 3.10+, standard library only at runtime | Verified on 3.10 and 3.12; no dependency drift; runs offline |
| unittest tests, run by `run_all` or pytest | existing convention; `run_all` refuses unassigned test modules and empty groups |
| ruff (dev only, pinned) with pyflakes fallback | fast lint; `run_all` reports UNAVAILABLE rather than PASS without a linter |
| SQLite (`store.py`) for the optional journal | stdlib, single file, checksummed migrations |
| Static HTML + inline SVG dashboard | no web server, no JS framework; reproducible pages |
| No Graphify, import-linter or bandit | evaluated in `docs/SKILLS_REGISTRY.md`; the stdlib checker covers the needed rules |

## 7. Change procedure

1. Place a new module in a layer (`LAYERS` in `nse/validation/architecture.py`) and in
   section 3 above.
2. Need an upward import? Prefer moving the shared code down (as `inputs.py` was). If an
   exception is unavoidable, add it to `EXCEPTIONS` with a reason and a TD id.
3. Run `python3 -m nse.validation.architecture` and `python3 -m nse.validation.run_all`.

Rollback: every structural change in the foundation milestone is a small, file-local edit
listed in `docs/MILESTONE_STATUS.md` (MP0 change record) and reversible by hand; no file
was moved except the owner's master prompt, which is kept byte-identical (hash-pinned).

## 8. Desktop product

The research system in this document is the domain engine of the GTF Trading Intelligence
Platform. The browser UI, local API, charting choice, and prompt series are specified
in [docs/architecture/SYSTEM_ARCHITECTURE.md](architecture/SYSTEM_ARCHITECTURE.md) and
[docs/product/MASTER_PROMPT_ROADMAP.md](product/MASTER_PROMPT_ROADMAP.md). Those documents
do not move modules under `nse/` and do not relax rules A1–A10. New application code is
specified to live outside `nse/`, so the standard-library rule and the network ban stay
intact.
