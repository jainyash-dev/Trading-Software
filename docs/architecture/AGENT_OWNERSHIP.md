# Platform agent ownership

> Product Prompt 00. Who may edit the desktop product. Research-engine ownership stays
> in [docs/AGENT_OWNERSHIP.md](../AGENT_OWNERSHIP.md) and still applies to `nse/`.
> If the two pages disagree about an `nse/` path, the research page plus the source
> hierarchy there wins. This page adds `platform/` and the product documents.

## 1. Integration lead

The Chair of the session that owns a prompt is the integration lead for that prompt.
The lead assigns files before any second agent starts, settles contract conflicts by
citing the engine source or the Rulebook, and is the only writer of the shared contract
files once Prompt 00 has exited.

Reviewers are read-only. A review that edits a document is discarded and redone.

## 2. Occupied right now (2026-11-09)

This checkout is dirty. Treat these prefixes as locked by the work already in the tree
until that workstream says it has stopped.

| Prefix | Workstream | Product prompt |
|---|---|---|
| `nse/eod/`, `nse/calendar/`, `nse/data/`, `nse/research/acquisition.py`, `instruments.py`, `universe.py`, `membership.py`, `corporate_actions.py`, `marketdata.py`, `eod_coverage.py`, `nse/docs/DATA_SOURCE_REGISTRY.md`, `REAL_DATA_READINESS.md` | Data readiness | 01 |
| `nse/zone-engine/`, `nse/mtf-freshness/`, `nse/research/scanner.py`, `qualification.py`, `pipeline.py`, `models.py`, `reports.py`, `backtest.py`, `execution_policy.py`, `risk.py`, `store.py`, `decision_replay.py`, `run_manifest.py`, `cli.py`, `structure.py`, `trend.py`, `levels.py` | Research pipeline | 02. The engine zone id stays as implemented unless this workstream edits it. Platform code joins on the stable reference in the domain model and still passes the engine id into `journal_add` |
| `docs/product/`, `docs/architecture/` | This blueprint | 00, until it exits |

Read any of these. Do not write them from another prompt. A bug found in a locked file
is recorded for that workstream.

`docs/ARCHITECTURE.md`, `docs/AGENT_OWNERSHIP.md`, `docs/MILESTONE_STATUS.md`, and
`docs/PRODUCT_ROADMAP.md` are shared indexes. Prompt 00 may add a pointer. Later prompts
add a status row only in `docs/MILESTONE_STATUS.md`, which remains the state authority.

## 3. Platform paths

Created by Prompt 03 and Prompt 04. They do not exist yet. Adding the `platform`
directory updates `tests/test_repo.py` in that same change, because the root listing is
pinned. One prompt owns that test edit: Prompt 03.

| Path | Owner prompt | Notes |
|---|---|---|
| `platform/pyproject.toml` | 03 | Platform dependencies only. Root `dependencies` stay `[]` |
| `platform/gtf_platform/` | 03 | HTTP handlers. Import name `gtf_platform`. No `platform/__init__.py`, so the standard-library `platform` module is not shadowed |
| `platform/gtf_platform/jobs.py` | 03 | Scheduler and recovery. Scan execution is not started in the foundation |
| `platform/gtf_platform/db.py` | 03 | Platform SQLite, separate from the research store. Prompt 07 may add fill migrations. Prompt 12 may add paper migrations. Neither edits an earlier migration or `nse/research/store.py` |
| `platform/providers/` | 03 interface, 01 or a later data prompt for a concrete official fetch | No paid provider without OQ-1 |
| `platform/assistant/` | 13 | |
| `platform/tests/` | the prompt that adds the behaviour | Not `tests/test_*.py`, so `run_all` does not see an unassigned module |
| `platform/web/` shell, `src/design-system/` | 04 | |
| `platform/web/src/features/overview`, `scanner`, `watchlists` | 05 | |
| `platform/web/src/features/analysis`, `src/chart/` | 06 | |
| `platform/web/src/features/plans`, `portfolio` | 07 | |
| `platform/web/src/features/journal`, `reports` | 08 | |
| `platform/web/src/features/backtest` | 09 | |
| `platform/web/src/features/analytics` | 10 | |
| `platform/web/src/features/stress` | 11 | |
| `platform/web/src/features/paper` | 12 | |
| `platform/web/src/features/assistant` | 13 | |
| `platform/tests/certification/` | 14 | |
| `docs/architecture/API_CONTRACTS.md` | 03 after Prompt 00, via the integration lead | UI prompts are readers |
| `docs/architecture/DOMAIN_MODEL.md` | integration lead | |
| `docs/product/FRONTEND_SPECIFICATION.md` | 04 may clarify, not weaken status rules | |

## 4. Shared files that need a single editor

| File | Rule |
|---|---|
| `tests/test_repo.py` | Prompt 03 adds `platform` to the root list. Nobody else edits it for the desktop work |
| Root `pyproject.toml` | Stays the research toolchain. Prompt 03 does not add runtime dependencies. Test paths for `platform/tests` are invoked explicitly so this file need not change |
| `nse/validation/run_all.py` | Unchanged by UI prompts. Platform tests are a separate command |
| `nse/research/store.py` | Prompt 02 while that workstream is active. New fill tables go to `platform/db` so the journal file is not a second writer's target |
| `nse/docs/ENGINEERING_DECISIONS.md` | Research and data workstreams. Architecture recommendations for the desktop live in [the decisions note](../product/DECISIONS_AND_OPEN_QUESTIONS.md) so two writers do not take the same ED number |

## 5. Review roles

| Role | Agent | When |
|---|---|---|
| Product requirements | integration lead, checked by a read-only reviewer | Prompt 00 and any scope change |
| Backend | implementer writes; independent reviewer reads | Prompt 03 |
| Frontend | implementer writes | Prompts 04–08, 13 |
| Market data | data-validator, read-only | Prompt 01 and any provider adapter |
| Quantitative research | quant-researcher, read-only | Prompts 02, 07, 09–12 |
| Trading rules | trading-rule-auditor, read-only | Any change under `nse/research/qualification.py` or the engines |
| Security and reliability | independent reviewer | Prompt 03 token boundary, Prompt 13 logs, Prompt 14 |
| Contrarian | contrarian-reviewer | Prompt 00 architecture, Prompt 11, Prompt 14 |
| Test engineering | test-engineer | when a defect is confirmed |

Two agents never receive the same writable path.

## 6. Concurrent-work rules

1. One writer per path. A second agent with the same path stops.
2. Implementation prompts use a separate git worktree. They do not clean this checkout.
3. No commit, push, reset, stash, or history rewrite unless the owner asks in that conversation.
4. `nse/sources/` and the Rulebook PDF are not writable.
5. A contract change is a document edit by the integration lead before the code that depends on it.
6. Fixture data used by the UI carries `fixture: true` and is not stored under `nse/data/eod/raw/`.
7. Network code stays out of `nse/`. A fetch, if built, lives under `platform/providers/` or the existing external scripts.
8. Vendored skills under `.claude/skills/` that are hash-pinned are not edited. Re-vendor them if a new upstream is required.

## 7. Context each prompt loads

| Prompt | Read first |
|---|---|
| 01 | `nse/docs/REAL_DATA_READINESS.md`, `DATA_SOURCE_REGISTRY.md`, this page's lock table |
| 02 | `docs/PROMPT2_DATA_CONTRACT.md`, `docs/ARCHITECTURE.md`, `nse/docs/DECISION_REGISTER.md` |
| 03–04 | `docs/architecture/API_CONTRACTS.md`, `SYSTEM_ARCHITECTURE.md`, `DOMAIN_MODEL.md` |
| 05, 06, 08, 13 | `docs/product/FRONTEND_SPECIFICATION.md` and the API contract |
| 07 | `docs/product/FRONTEND_SPECIFICATION.md`, `docs/architecture/API_CONTRACTS.md`, and the fill write order in `docs/architecture/DOMAIN_MODEL.md` |
| 09–12 | `nse/research/execution_policy.py` headers and the domain model sections on backtest and paper |
| 14 | the roadmap's release gates and `docs/MILESTONE_STATUS.md` |

## 8. Report contract

Unchanged from the research ownership page: files changed, findings with locations,
commands and counts, unresolved risks, and each statement marked as fact, assumption,
recommendation, or owner decision.
