# Technical debt

> Real, verified debt only, with impact and the planned resolution. Correctness risks
> and evidence blockers live in `nse/docs/IMPLEMENTATION_BLOCKERS.md` and the risk
> register in `nse/docs/ENGINEERING_DECISIONS.md`; this list is engineering structure.
> Priority: P1 (fix before it causes a defect), P2 (fix when the area is next touched),
> P3 (accept unless circumstances change).

| ID | Debt | Evidence | Impact | Priority | Resolution | Status |
|---|---|---|---|---|---|---|
| TD-1 | CLI command handlers (`add_commands`, `cmd_*`) live inside 13 domain modules (backtest, acquisition, store, risk, scenarios, ...) | `cli.COMMAND_MODULES` | presentation code inside lower layers; handlers cannot use application-layer services such as `run_manifest` (TD-4) | P2 | move handlers into `nse/research/commands/` one module at a time, keeping `add_commands` names; no behaviour change | open |
| TD-2 | `decision_replay` imports `dashboard` inside its command handler | architecture exception X1 | the only allowed upward import | P3 | resolved by TD-1 (handler moves to the application layer) | open |
| TD-3 | Engines live in hyphenated folders loaded by file path (`deps.py`) | `nse/zone-engine`, `nse/mtf-freshness` | not importable as packages; static type checkers and IDEs cannot follow them | P3 | rename only with owner agreement (Phase 1 evidence and docs cite these paths); rule A6 contains the risk | accepted |
| TD-4 | `backtest-walk-forward` and `backtest-sensitivity` write no run manifest | ED-18 limits | those results are less reproducible than `scan` / `backtest` | P2 | after TD-1, call `run_manifest` from the moved handlers | open |
| TD-5 | `nse/docs/release/*` is a 2026-11-02 snapshot that predates the 2026-11-08 owner approvals (e.g. `UNRESOLVED_DECISIONS.md` still lists RB-VERSION-1 and P-LOC-2 as open) | `DECISION_LOG.md` 1F | a reader of the snapshot sees stale status | P2 | keep as a dated snapshot; current status is `docs/MILESTONE_STATUS.md`, `PRODUCT_MASTER_STATUS.md` and the decision log (pointer added) | mitigated |
| TD-6 | No type checking; annotations are partial | `pyproject.toml` | type errors are found by tests only | P3 | revisit `ty` when stable, or mypy on `nse/research` contracts first | open |
| TD-7 | No dedicated security scanner (bandit) | `docs/SKILLS_REGISTRY.md` | rule A8 and `test_repo` cover current patterns only | P3 | adopt if subprocess, file-write or third-party surface grows | accepted |
| TD-8 | The bhavcopy file pattern `cm*bhav.csv.zip` is spelled in five places | `inputs.py`, `inventory.py`, `instruments.py`, `run_all.py`, `run_manifest.py` | a format change (B18 UDiFF) must be edited everywhere | P2 | one constant in `nse_bhavcopy` when B18 is resolved | resolved (MP1): `nse_bhavcopy.archive_paths` / `ARCHIVE_PATTERNS` |
| TD-9 | No continuous integration | no `.github/workflows` | validation depends on someone running `run_all` | P2 | owner decision: a CI workflow running `python3 -m nse.validation.run_all --no-data` on 3.10 and 3.12 (pushing a workflow is an owner action) | owner decision |
| TD-10 | The legacy US `trader-*` pack and the NSE platform share one repository and README | root layout test, README | newcomers see a US day-trading README first | P3 | owner decision: split repositories or add an NSE section to the README | owner decision |
| TD-11 | Large modules: `store.py` (953 lines), `backtest.py` (915), `scenarios.py` (734) mix several concerns (CLI, schema, simulation, metrics) | `wc -l` | slower review; harder ownership splits | P3 | split only together with TD-1 or a real change in the area | accepted |
| TD-12 | No structured logging; commands print JSON or text to stdout | CLI | operational events are not machine-collected | P3 | introduce `logging` with run_id correlation when a scheduler or alerting runs unattended | open |
| TD-13 | A symbol's daily series is assembled by symbol, not by ISIN lineage | `nse_replay.daily_series`, `instruments.apply_to_input` | a renamed stock is DATA_INSUFFICIENT (`SYMBOL_HISTORY_SPLIT`) even with a verified SYMBOL_CHANGE record, so it loses candidates (fail-closed) | P2 | join bars across verified SYMBOL_CHANGE records only (never across ISIN changes or mergers), with its own tests and a lookahead check | resolved 2026-11-09 by ED-29 (D51) |
| TD-14 | Reference templates lack `export_sha256` on zone rows, the Pine script hash, `recorded_by`, separate settings columns and the Q/HY/Y to 3M/6M/12M mapping | `REAL_DATA_READINESS.md` §6 | TradingView exports cannot be recorded with full provenance | P2 | additive schema version of `nse_reference` / `refcheck` with a migration for `INFY/ohlc_reference.csv`, done when the owner starts recording (B8) | open |
| TD-16 | Universe membership is matched to inputs by symbol; `Membership.isin` is stored but not compared with the bhavcopy ISIN | QA 2026-11-09 | a member renamed during its period is looked up under the old symbol (the identity check then blocks it, fail-closed) | P2 | compare member ISIN with the input's ISIN at as_of once B11 data exists | open |
| TD-17 | Every real-data test and command re-parses all 2,478 archives (about 20 ms each, about 50 s per full load) | profile 2026-11-09: `_row` / `_decimal` dominate | Memory is bounded since ED-41: holding every row exceeded 8 GB and swapped, so four tests took 42 min. Time is still linear: `RealInventory` / `RealWindow` take 6 min 40 s, and a scan reads every file once or twice | P2 | a content-addressed parse cache keyed by archive SHA-256 (invalidated by `LOADER_VERSION`), or a faster row parser; behaviour must stay byte-identical | open (memory part resolved by ED-41) |
| TD-18 | The universe transcription builder (ED-32) is still a one-off script outside the repository; the identity builder is now in `.claude/skills/nse-data-engineering/scripts/` (PROMPT-01) and reproduces its output byte-identical | `nse/data/universe/` | a re-transcription after new evidence needs that builder re-created; the transcription files themselves are the reviewed artifact | P3 | move the transcription builder too, with fixture tests | partly resolved |
| TD-15 | `membership.py` rolls forward only from one baseline | ED-22 | dates before the held 31 Mar 2022 list need an earlier baseline or an owner-approved reverse step | P2 | a reverse step that undoes a reviewed release, with the same validation, if the owner approves it | open |

## Resolved in the foundation milestone (2026-11-08)

| Was | Resolution |
|---|---|
| `backtest.py` and `decision_replay.py` imported the CLI (hidden cycle) | ED-14, `nse/research/inputs.py` |
| `scenarios.parse_as_of` duplicated `cli._as_of` | ED-14 (alias of `inputs.parse_as_of`) |
| 16 unused imports | removed; `static_lint` gate (ED-17) |
| No dependency or Python-version declaration | `pyproject.toml` (ED-17) |
| Architecture documented but not enforced | `nse/validation/architecture.py` (ED-15) |
| Docs could cite removed commands or groups unnoticed | `nse/validation/docs_health.py` (ED-15) |
| Scan runs not identifiable or reproducible | `run_manifest.json` (ED-18) |
| `PRODUCT_MASTER_STATUS.md` section 7 contradicted the 2026-11-08 approvals | rows synchronised with `DECISION_LOG.md` 1F |
