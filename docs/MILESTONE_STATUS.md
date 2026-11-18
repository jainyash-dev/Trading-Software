# Milestone status

> States: NOT_STARTED, IN_PROGRESS, ENGINEERING_COMPLETE, EVIDENCE_BLOCKED,
> LIVE_VALIDATION_PENDING, COMPLETED. A milestone is COMPLETED only on its exit evidence;
> engineering completion and validation are separate states. Roadmap:
> `docs/PRODUCT_ROADMAP.md`. Test evidence: `docs/VALIDATION_SCORECARD.md`.
> **This file is the only authority for milestone state.** Capability status lives in
> `PRODUCT_MASTER_STATUS.md` and the readiness table; decision status in
> `nse/docs/DECISION_LOG.md`; `nse/docs/release/` is a dated snapshot. Other files link
> here rather than repeating milestone states.
>
> Working-tree note, 2026-11-10: uncommitted `platform/` work now includes overview,
> scanner, watchlists, stock analysis, plans, journal recording, portfolio reads,
> a labelled backtest request, report export, and backup. Release gates R1–R5 stay open.
> `DATA_READY` is not claimed. See `docs/implementation/`.

| Milestone | State | Evidence / blocker | Updated |
|---|---|---|---|
| MP0 Repository foundation | COMPLETED, with documented limitations | section 1 below | 2026-11-08 |
| MP1 Real NSE data readiness | ENGINEERING_COMPLETE (D47-D56 executed). Data: EOD 2016-2025 complete (2,466 of 2,466 trading days accepted since D58 confirmed the four Dhanteras dates, 2026-11-10), calendar 2016-2025 reconciled with no UNRESOLVED row, corporate actions and identity collected. **DATA_READY not claimed**: universe awaits human row review (B11-R). Research validation: none | sections 3-5 below; `nse/docs/REAL_DATA_READINESS.md` §0B | 2026-11-09 |
| MP2-MP8 | NOT_STARTED | repository milestones not named. The desktop series is Product Prompts 00–14 | 2026-11-09 |
| Product Prompt 00 Architecture blueprint | COMPLETED, with documented limitations | Nine blueprint files. `docs_health` PASS. Reviews incorporated in `docs/product/DECISIONS_AND_OPEN_QUESTIONS.md` section 8. No `nse/` code edited. R1–R5 remain open | 2026-11-09 |

## 1. MP0 exit criteria (Master Prompt 0, section 14)

| # | Criterion | Evidence |
|---|---|---|
| 1 | Repository inspected | baseline: branch `main`, HEAD `9e302df`, 41 modified and 8 untracked owner files preserved; import graph of all 44 Python modules under `nse/` built |
| 2 | Baseline architecture map | `docs/ARCHITECTURE.md` section 3; `python3 -m nse.validation.architecture --map` |
| 3 | Target architecture documented | `docs/ARCHITECTURE.md` (layers, rules, exceptions, change procedure) |
| 4 | Structural cleanup where safe | ED-14 (CLI dependency removed, duplicate parser merged), unused imports removed (section 2) |
| 5 | Business behaviour preserved | trading modules byte-identical (independent QA); full suite passes (scorecard) |
| 6 | Critical boundaries clear | rules A1-A10 enforced by `tests/test_architecture.py` |
| 7 | Duplicate and dead code addressed where verified | `scenarios.parse_as_of` duplicate merged; 16 unused imports removed; nothing deleted on static evidence alone |
| 8 | Five council perspectives | integrated in our own words (`llm-council` `advisor-perspectives.md`, Chairman synthesis); the requested upstream has no verifiable repository or license (`docs/SKILLS_REGISTRY.md`) |
| 9 | Emil Kowalski skills | four vendored verbatim and hash-pinned; others rejected with reasons |
| 10 | Graphify | evaluated and rejected with reasons; stdlib module map instead |
| 11 | Project management | repository-native: roadmap, this file, technical debt, blockers, decisions, agent ownership |
| 12 | Additional repositories | superpowers, anthropics/skills, ruff, uv, ty, pre-commit, pytest, import-linter, bandit, pip-audit, vulture evaluated |
| 13 | Registry | `docs/SKILLS_REGISTRY.md` |
| 14 | Instructions and agents | concise `CLAUDE.md`; `contrarian-reviewer`, `quant-researcher` agents; report contract on all agents |
| 15 | Council remains authoritative | `autonomous-gtf-project-council` section 6 updated; `tests/test_project_council_skill.py` |
| 16 | Formatting, linting, typing, testing workflows | ruff lint gate (formatter deliberately off), unittest / pytest, `run_all`; type checking deferred (TD-6) |
| 17 | Security and dependency checks | rule A8, `test_repo` network/broker ban, guard hook, no runtime dependencies; pip-audit / bandit deferred with reasons |
| 18 | Docs updated | `docs/*`, ED-14..ED-19, `PRODUCT_MASTER_STATUS.md` section 7 synchronised |
| 19 | Full suite and validation executed | `docs/VALIDATION_SCORECARD.md` |
| 20 | Protected files unchanged | hashes match the baseline (scorecard) |
| 21 | No user work discarded | no reset, clean, stash or checkout; owner diff reconstructed and compared |
| 22 | No commits or pushes | HEAD unchanged at `9e302df`; nothing staged |
| 23 | Debt and blockers documented | `docs/TECHNICAL_DEBT.md`, `nse/docs/IMPLEMENTATION_BLOCKERS.md` |
| 24 | Ready for MP1 | yes for engineering; MP1's data work needs owner-supplied files (D31) |

Documented limitations: the two new agents load only in a new Claude Code session; type
checking is not established (TD-6); no CI (TD-9, owner decision); walk-forward and
sensitivity runs write no manifest (TD-4).

## 2. MP0 change record (for review and manual rollback)

| Change | Files | Reverse by |
|---|---|---|
| Input adapters moved out of the CLI (ED-14) | `nse/research/inputs.py` (new); `cli.py`, `backtest.py`, `decision_replay.py`, `scenarios.py` | restoring the previous helper bodies; aliases keep call sites identical either way |
| Unused imports removed | `nse/calendar/nse_calendar.py`, `nse/eod/nse_reference.py`, `nse/eod/nse_replay.py`, `nse/mtf-freshness/mtf_freshness.py`, `nse/research/backtest.py`, `nse/research/models.py`, 8 test modules | re-adding the names (no behaviour depends on them) |
| Architecture and docs-health checks (ED-15) | `nse/validation/architecture.py`, `nse/validation/docs_health.py`, `tests/test_architecture.py`; `run_all` group `architecture` | deleting them and the group |
| Static lint check and report of checks not run (ED-17) | `nse/validation/run_all.py`, `tests/test_validation_runner.py`, `pyproject.toml` | removing `check_static_lint` and `checks_not_run` |
| Run manifests (ED-18) | `nse/research/run_manifest.py`, `cli.py` (scan, backtest), `tests/test_research_run_manifest.py`, `tests/test_research_backtest.py` | removing the two `run_manifest` calls in `cli.py` |
| CLAUDE.md concise; master prompt archived (ED-16) | `CLAUDE.md`, `docs/owner/MASTER_IMPLEMENTATION_PROMPT.md`, `tests/test_repo.py` | copying the archived file back to `CLAUDE.md` |
| Vendored design skills (ED-19) | `.claude/skills/{apple-design,emil-design-eng,break-ui,review-animations}/`, `.claude/vendored-skills.json`, `tests/test_claude_hooks.py`, `tests/test_repo.py` | deleting the folders and manifest |
| Agents and council staffing | `.claude/agents/contrarian-reviewer.md`, `quant-researcher.md`, report contract in the five existing agents, council skill section 6, `tests/test_project_council_skill.py` | deleting the two agents and the appended paragraph |
| Council lenses strengthened | `.claude/skills/llm-council/references/advisor-perspectives.md` | removing the added sentences and section |
| Environment | `pyproject.toml`, `.env.example`, `.gitignore` (root-anchored `.venv`, `.ruff_cache`, `.pytest_cache`) | deleting the files / lines |
| Documentation | `docs/*.md`, `nse/docs/ENGINEERING_DECISIONS.md` ED-14..ED-19, `PRODUCT_MASTER_STATUS.md` (sections 7, 8, 9, 12), one-line snapshot notes in three `nse/docs/release/` files | editing the files |

No file was moved or deleted except the copy of the master prompt (the original content
is kept byte-identical in `docs/owner/`). `nse/sources/`, the Rulebook PDF, the Pine
Script, gate logic, eligibility, statuses and limits were not touched.

## 3. MP1 exit criteria (Master Prompt 1, section 16)

| # | Criterion | State | Evidence |
|---|---|---|---|
| 1 | Existing data architecture understood | met | baseline in the MP1 report; `DATA_SOURCE_REGISTRY.md` |
| 2 | Acquisition plan generated and reviewed | met | `acquire-plan` 2021-2025: 62 held, 1,178 missing rows, of which 1,171 are calendar trading days. File names were wrong for post-switch dates (legacy names after 2024-07-05); fixed, and URLs added (ED-20) |
| 3 | Legacy and UDiFF ingestion implemented and tested | met | ED-20; `test_nse_eod_evidence` (26, 6 on official samples), `test_research_acquisition.SourceSelection` (7) |
| 4 | Coverage measured and documented | met (coverage itself insufficient) | `eod-coverage` 2.0.0: 1,233 trading days; 62 accepted (5.03%); 1,171 missing; `research_ready` false (`REAL_DATA_READINESS.md` §0.2) |
| 5 | Provenance and quality validation | met | four file states, dataset id, manifest and loader versions (ED-24); evidence registries (ED-23) |
| 6 | Historical Nifty 100 | precisely evidence-blocked | converter built (ED-22); official evidence held; human-reviewed transcription and ad-hoc notices missing (B11) |
| 7 | Corporate actions and identity | identity integrated; corporate actions evidence-blocked | ED-21 (plus 4 review fixes); B7 needs per-symbol records and an adjustment decision |
| 8 | D40 | reconciled by evidence | NSE/MSD/59999, 60300 and 60318 held; owner approval kept; factual note in `DECISION_LOG.md` 1F |
| 9 | INFY TradingView parity | precisely evidence-blocked | B8 / B10 / B17: no export exists; matrix P1-P10 (`REAL_DATA_READINESS.md` §6) |
| 10 | Historical as-of safety | met | dated identity findings, prefix-invariant labels (`QaRegressions20261109`), `lookahead` group |
| 11 | Scanner-facing identity and data validation | met | `inputs.load` and `scenarios._inputs` apply `apply_to_input`; `--instruments` on four commands |
| 12 | All tests and validations pass | met | `run_all` PASS, 1,218 tests (scorecard) |
| 13 | Protected files unchanged | met | hashes match the pins |
| 14 | No user work lost | met | no reset, stash, clean or checkout; owner files edited only additively |
| 15 | Precise evidence requirements for blockers | met | `IMPLEMENTATION_BLOCKERS.md` Part 9 |
| 16 | Ready for MP2, or limitations documented | limitations documented | MP2 research needs the owner backfill (DATA-1) and, for survivorship-free history, B11 |

### MP1 change record (for review and manual rollback)

| Change | Files | Reverse by |
|---|---|---|
| UDiFF loader, source selection, cross-check, archive discovery (ED-20) | `nse/eod/nse_bhavcopy.py`; callers in `acquisition`, `manifest_tool`, `inventory`, `inputs`, `instruments`, `run_manifest`, `marketdata`, `run_all` | restoring the legacy-only loader (`LOADER_VERSION` 1.0.0) and the five globs |
| Identity on every bhavcopy input (ED-21) | `instruments.apply_to_input`, `inputs.py`, `scenarios.py`, `models.IDENTITY_UNVERIFIED`, `--instruments` in `cli.py`, `backtest.py`, `decision_replay.py` | removing the call in `inputs.load` / `scenarios._inputs` |
| Membership converter (ED-22) | `nse/research/membership.py` (new), `universe.py` (`isin`, `balance`), architecture layer, `run_all` group | deleting the module and its test |
| Coverage states and dataset id (ED-24) | `nse/research/eod_coverage.py` | restoring report 1.0.0 |
| Evidence (ED-23) | `nse/data/eod/evidence/`, `nse/data/universe/evidence/`, `nse/data/corporate_actions/raw/`, three circulars and rows in `nse/data/calendar/` | deleting the added files and rows |
| D40 note | `nse/data/calendar/events.csv` (2024-01-20 note only) | restoring the previous note |
| Test fixture date shifts (specification correction, ED-20) | `test_nse_replay`, `test_research_acquisition`, `test_research_data`, `test_research_instruments` | shifting the dates back (only together with reverting ED-20) |
| Readiness and documentation | `readiness.py`, `docs/*`, `nse/docs/*` (DATA_SOURCE_REGISTRY new), `PRODUCT_MASTER_STATUS.md` | editing the files |

## 4. Owner decisions D47-D51 executed (2026-11-09)

| Decision | Outcome | Evidence |
|---|---|---|
| D47 EOD backfill 2021-2025 | Done: 1,171 official files downloaded, verified and ingested; 1,233 of 1,233 trading days accepted; 0 quarantined | ED-25, ED-30; `nse/output/data_readiness/backfill_report.json`, coverage report |
| D48 calendar 2016-2020 | Done: 18 circulars, 106 rows. The 4 Dhanteras dates were UNRESOLVED until D58 | ED-26, ED-31 |
| D49 Nifty 100 transcription | Prepared and cross-checked; **awaiting human review** (gate enforced in code) | ED-27, ED-32; `nse/data/universe/README.md` |
| D50 corporate-action policy | Implemented: separate event store; prices never adjusted | ED-28 |
| D51 identity continuity | Implemented: verified-ISIN lineage join; otherwise DATA_INSUFFICIENT | ED-29, ED-32 |

DATA_READY needs B11-R (human review) and B11-I (ISIN-change evidence for 13 members, listing records for 4). The approvals did not cover the 2016-2020 EOD files (DATA-2) or a universe-wide corporate-action collection (B7-C); both are owner questions in `nse/docs/DECISION_REGISTER.md`.

## 5. Owner decisions D52-D56 executed (2026-11-09)

| Decision | Engineering | Data | Evidence |
|---|---|---|---|
| D52 / DQ-1 excluded-session PREVCLOSE | Done: strict explanation rule; G1 MANUAL for an unobserved excluded session in a zone's span | All 12 excluded-session bhavcopies 2016-2025 held (NSE serves them), so the discontinuity is removed at source | ED-33, ED-34; `test_research_data.ExcludedSessionD52` |
| D53 / B11-R independent verification, human review | Done: row-level review gate | Every row verified by an independent agent (rows added later by a second one); **human review not done** | ED-35; `nse/data/universe/README.md` |
| D54 / CAL-2 Dhanteras | Done: unresolved dates block only ranges containing them, including in `run_all` | Closed by D58 (2026-11-10): the 4 dates are confirmed regular sessions and their files accepted; the rule stays for any future unresolved date | ED-31, ED-42, ED-44 |
| D55 / DATA-2 EOD 2016-2020 | Done: download, ingest, 2 exact layout variants, memory-bounded loading | 1,242 files; 2,466 of 2,466 equity sessions 2016-2025 accepted after D58. Coverage regenerated 2026-11-10: `eod_ready` true, `data_ready` false | ED-38, ED-41; `nse/output/data_readiness/eod_coverage_2016_2025.json` |
| D56 / B7-C, B11-I corporate actions and ISIN changes | Done: collection script, fail-closed classifier, ISIN-change evidence rule | 189 symbols requested, 145 covered, 2,064 events; 27 of 30 ISIN changes evidenced | ED-37, ED-39 |

Remaining for DATA_READY: the human row review (B11-R). (CAL-2 was closed by D58 on 2026-11-10.) Not covered by any approval: pre-2021 membership (B11-P).

## 6. Product Prompt 00 (2026-11-09)

The owner issued the GTF Trading Intelligence Platform blueprint (Product Prompts 00–14).
Prompt 00 writes product and architecture documents only. It does not change `nse/`.
The catalogue is [docs/product/MASTER_PROMPT_ROADMAP.md](product/MASTER_PROMPT_ROADMAP.md).
State is `COMPLETED` for the blueprint only. Implementation has not started. Release
gates R1–R5 in the roadmap stay open. `DATA_READY` is not claimed.

## 6. PROMPT-01 real NSE data readiness and certification (2026-11-09)

| Gate | State |
|---|---|
| A raw EOD 2016-2025 | PASS: 2,466 of 2,466 equity sessions. Regenerated coverage 2026-11-10: `eod_ready` true, `data_ready` false |
| B calendar | PASS; CAL-2 closed by D58 (2026-11-10) |
| C universe | NOT CERTIFIED: human review pending (B11-R) |
| D identity | PASS, with 3 unevidenced ISIN changes contained |
| E corporate actions | PARTLY: 145 of 191 covered; completeness audited |
| F data quality and point in time | Code check closed (ED-46): missing or unverified corporate-action coverage is G0 MANUAL. Data certification stays PARTLY: empty official responses are not coverage, and `nse/docs/REAL_DATA_READINESS.md` §0C still describes the old gap until Prompt 01 refreshes it |
| G reproducibility | Code check closed (ED-46): the scan manifest fingerprints `--instruments` and `coverage.csv`. Data certification stays PARTLY until Prompt 01 refreshes §0C |

Verdict: **PARTIALLY_READY**; DATA_READY not claimed. Details: `nse/docs/REAL_DATA_READINESS.md` §0C and `nse/docs/IMPLEMENTATION_BLOCKERS.md` Part 12.
